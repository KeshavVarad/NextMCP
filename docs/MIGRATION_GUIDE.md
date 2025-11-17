# Migration Guide: Adding Auth to Your MCP Server

This guide shows you how to add NextMCP authentication to your existing MCP server or migrate from FastMCP to NextMCP with auth.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Adding OAuth to Existing Servers](#adding-oauth-to-existing-servers)
3. [Migration from FastMCP](#migration-from-fastmcp)
4. [Adding Session Management](#adding-session-management)
5. [Migrating from Decorators to Middleware](#migrating-from-decorators-to-middleware)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Before (No Auth):

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def get_user_data(user_id: str) -> dict:
    """Get user data - anyone can call this!"""
    return {"user_id": user_id, "data": "sensitive info"}
```

### After (With OAuth):

```python
from fastmcp import FastMCP
from nextmcp.auth import GoogleOAuthProvider, create_auth_middleware
from nextmcp.session import MemorySessionStore
from nextmcp.protocol import AuthRequirement

mcp = FastMCP("My Server")

# Set up OAuth
google = GoogleOAuthProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
)

# Enable auth enforcement
auth_middleware = create_auth_middleware(
    provider=google,
    requirement=AuthRequirement.REQUIRED,
    session_store=MemorySessionStore(),
    required_scopes=["profile", "email"],
)

mcp.use(auth_middleware)

@mcp.tool()
def get_user_data(user_id: str) -> dict:
    """Get user data - now requires OAuth authentication!"""
    # Request automatically has _auth_context injected
    return {"user_id": user_id, "data": "sensitive info"}
```

**That's it!** Your server now requires OAuth authentication for all requests.

---

## Adding OAuth to Existing Servers

### Step 1: Install Dependencies

If using OAuth, ensure you have the oauth extras:

```bash
pip install "nextmcp[oauth]"
```

### Step 2: Choose Your OAuth Provider

NextMCP includes two built-in providers:

#### GitHub OAuth:

```python
from nextmcp.auth import GitHubOAuthProvider

github = GitHubOAuthProvider(
    client_id="your_github_client_id",
    client_secret="your_github_client_secret",
    redirect_uri="http://localhost:8080/oauth/callback",  # Optional
    scope=["read:user", "repo"],  # Optional
)
```

**Get credentials**: https://github.com/settings/developers

#### Google OAuth:

```python
from nextmcp.auth import GoogleOAuthProvider

google = GoogleOAuthProvider(
    client_id="your_google_client_id",
    client_secret="your_google_client_secret",
    redirect_uri="http://localhost:8080/oauth/callback",  # Optional
    scope=["openid", "email", "profile"],  # Optional
)
```

**Get credentials**: https://console.cloud.google.com

### Step 3: Add Session Store

Choose a session store based on your needs:

#### Development (In-Memory):

```python
from nextmcp.session import MemorySessionStore

session_store = MemorySessionStore()
```

**Pros**: Fast, simple
**Cons**: Lost on restart, not distributed

#### Production (File-Based):

```python
from nextmcp.session import FileSessionStore

session_store = FileSessionStore(".sessions")
```

**Pros**: Persists across restarts
**Cons**: Single-server only

#### Future (Redis - Coming Soon):

```python
# from nextmcp.session import RedisSessionStore
# session_store = RedisSessionStore("redis://localhost:6379")
```

**Pros**: Distributed, scalable
**Cons**: Requires Redis

### Step 4: Apply Middleware

```python
from nextmcp.auth import create_auth_middleware
from nextmcp.protocol import AuthRequirement

middleware = create_auth_middleware(
    provider=google,  # or github
    requirement=AuthRequirement.REQUIRED,
    session_store=session_store,
    required_scopes=["profile", "email"],
)

# Apply to your server
mcp.use(middleware)
```

### Step 5: Expose Auth Metadata (Optional but Recommended)

Let clients discover your auth requirements:

```python
from nextmcp.protocol import AuthMetadata, AuthFlowType

# Build metadata
metadata = AuthMetadata(
    requirement=AuthRequirement.REQUIRED,
    supports_multi_user=True,
    token_refresh_enabled=True,
)

metadata.add_provider(
    name="google",
    type="oauth2",
    flows=[AuthFlowType.OAUTH2_PKCE],
    authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=["openid", "email", "profile"],
    supports_refresh=True,
)

# Expose via an endpoint
@mcp.tool()
def get_auth_metadata() -> dict:
    """Get server authentication requirements."""
    return metadata.to_dict()
```

---

## Migration from FastMCP

If you're using FastMCP and want to add auth:

### Pattern 1: Add Auth to All Tools

```python
# Before
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def tool1():
    pass

@mcp.tool()
def tool2():
    pass

# After - Add middleware
from nextmcp.auth import create_auth_middleware, GoogleOAuthProvider
from nextmcp.session import MemorySessionStore

google = GoogleOAuthProvider(client_id="...", client_secret="...")
mcp.use(create_auth_middleware(
    provider=google,
    session_store=MemorySessionStore(),
))

# All tools now require auth automatically!
```

### Pattern 2: Mix Public and Protected Tools

```python
from nextmcp.protocol import AuthRequirement

# Create middleware with OPTIONAL auth
middleware = create_auth_middleware(
    provider=google,
    requirement=AuthRequirement.OPTIONAL,
    session_store=MemorySessionStore(),
)

mcp.use(middleware)

@mcp.tool()
def public_tool():
    """Anyone can call this."""
    return "public data"

@mcp.tool()
def protected_tool():
    """Requires auth but middleware handles it."""
    # Check if authenticated
    # (would need to access _auth_context from request)
    return "protected data"
```

For fine-grained control, use decorators on specific tools:

```python
from nextmcp.auth import requires_auth_async

@mcp.tool()
async def public_tool():
    """No auth needed."""
    return "public"

@mcp.tool()
@requires_auth_async(provider=google)
async def protected_tool(auth: AuthContext):
    """This specific tool requires auth."""
    return f"Hello {auth.username}"
```

---

## Adding Session Management

### Basic Setup:

```python
from nextmcp.session import FileSessionStore, SessionData

# Create session store
session_store = FileSessionStore(".sessions")

# Middleware automatically manages sessions
middleware = create_auth_middleware(
    provider=google,
    session_store=session_store,
    auto_refresh_tokens=True,  # Automatically refresh expiring tokens
)

mcp.use(middleware)
```

### Manual Session Management:

```python
import time
from nextmcp.session import SessionData

# Create session manually
session = SessionData(
    user_id="user123",
    access_token="ya29.a0...",
    refresh_token="1//01...",
    expires_at=time.time() + 3600,
    scopes=["profile", "email"],
    user_info={"email": "user@example.com"},
    provider="google",
)

session_store.save(session)

# Load session
loaded = session_store.load("user123")

# Check expiration
if loaded.needs_refresh():
    # Token expires soon, refresh it
    pass

# Clean up expired sessions
session_store.cleanup_expired()
```

---

## Migrating from Decorators to Middleware

If you're using decorator-based auth, consider migrating to middleware for automatic enforcement:

### Before (Decorator-Based):

```python
from nextmcp.auth import requires_auth_async, requires_scope_async

@mcp.tool()
@requires_auth_async(provider=google)
@requires_scope_async("read:data")
async def tool1(auth: AuthContext):
    return "data"

@mcp.tool()
@requires_auth_async(provider=google)
@requires_scope_async("read:data")
async def tool2(auth: AuthContext):
    return "data"

# Every tool needs decorators - tedious!
```

### After (Middleware-Based):

```python
from nextmcp.auth import create_auth_middleware

# One-time setup
middleware = create_auth_middleware(
    provider=google,
    required_scopes=["read:data"],
)

mcp.use(middleware)

# All tools automatically protected!
@mcp.tool()
def tool1():
    return "data"

@mcp.tool()
def tool2():
    return "data"
```

### When to Use Decorators:

Use decorators when different tools need different auth:

```python
# Use middleware for base auth
middleware = create_auth_middleware(provider=google)
mcp.use(middleware)

# Use decorators for tool-specific requirements
@mcp.tool()
@requires_scope_async("basic:read")
async def basic_tool(auth: AuthContext):
    return "basic data"

@mcp.tool()
@requires_scope_async("admin:write")
async def admin_tool(auth: AuthContext):
    return "admin data"
```

---

## Common Patterns

### Pattern 1: Multi-Provider Support

```python
from nextmcp.auth import GitHubOAuthProvider, GoogleOAuthProvider

# Set up both providers
github = GitHubOAuthProvider(client_id="...", client_secret="...")
google = GoogleOAuthProvider(client_id="...", client_secret="...")

# You can switch providers or use different ones for different tools
# (See examples/auth/multi_provider_server.py for full example)
```

### Pattern 2: Per-Tool Permissions

```python
from nextmcp.auth import PermissionManifest

# Define permissions
manifest = PermissionManifest()
manifest.define_tool_permission("read_files", scopes=["files:read"])
manifest.define_tool_permission("write_files", scopes=["files:write"])
manifest.define_tool_permission("admin_panel", roles=["admin"])

# Apply manifest to middleware
middleware = AuthEnforcementMiddleware(
    provider=google,
    session_store=session_store,
    manifest=manifest,
)

mcp.use(middleware)
```

### Pattern 3: Custom User Data

```python
# Store custom data in sessions
session.metadata = {
    "preferences": {"theme": "dark"},
    "subscription": "premium",
    "last_login": time.time(),
}

session_store.save(session)
```

### Pattern 4: Token Refresh

```python
# Automatic refresh (recommended)
middleware = create_auth_middleware(
    provider=google,
    session_store=session_store,
    auto_refresh_tokens=True,  # Enabled by default
)

# Manual refresh
from nextmcp.auth.oauth import OAuthProvider

session = session_store.load("user123")
if session.needs_refresh() and session.refresh_token:
    # Refresh token
    token_data = await provider.refresh_access_token(session.refresh_token)

    # Update session
    session_store.update_tokens(
        user_id="user123",
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in"),
    )
```

---

## Troubleshooting

### Problem: "No credentials provided"

**Solution**: Ensure client sends auth credentials in request:

```python
# Client must send:
request = {
    "method": "tools/call",
    "params": {"name": "my_tool"},
    "auth": {
        "access_token": "ya29.a0...",
    }
}
```

### Problem: "Authentication failed"

**Possible causes**:
1. Invalid OAuth token
2. Token expired
3. Wrong provider credentials

**Debug**:
```python
# Test OAuth provider directly
result = await provider.authenticate({"access_token": "..."})
print(result.success, result.error)
```

### Problem: "Missing required scopes"

**Solution**: User needs to re-authorize with additional scopes:

```python
# Generate new auth URL with required scopes
auth_url_data = provider.generate_authorization_url()
print(auth_url_data["url"])
# User must visit this URL
```

### Problem: Sessions not persisting

**Check**:
```python
# FileSessionStore - check directory exists
session_store = FileSessionStore(".sessions")
print(list(session_store.directory.glob("session_*.json")))

# MemorySessionStore - sessions lost on restart (expected)
```

### Problem: "Token expired" errors

**Solutions**:
1. Enable auto-refresh:
   ```python
   middleware = create_auth_middleware(auto_refresh_tokens=True)
   ```

2. Ensure refresh tokens are saved:
   ```python
   # Check session has refresh token
   session = session_store.load("user123")
   print(session.refresh_token)  # Should not be None
   ```

3. Re-authenticate user if refresh fails

---

## Best Practices

1. **Always use HTTPS in production** - OAuth tokens are sensitive

2. **Use FileSessionStore or Redis in production** - MemorySessionStore loses sessions on restart

3. **Enable auto-refresh** - Users won't see token expiration errors

4. **Validate scopes** - Request minimum scopes needed

5. **Handle errors gracefully** - Show clear messages to users

6. **Clean up expired sessions** - Run periodic cleanup:
   ```python
   import asyncio

   async def cleanup_loop():
       while True:
           await asyncio.sleep(3600)  # Every hour
           session_store.cleanup_expired()
   ```

7. **Expose auth metadata** - Let clients discover your auth requirements

8. **Test with real OAuth** - Use integration tests with actual credentials

---

## Next Steps

- See [ARCHITECTURE.md](ARCHITECTURE.md) for how auth works internally
- See [HOST_INTEGRATION.md](HOST_INTEGRATION.md) for host integration
- Check [examples/auth/](../examples/auth/) for complete examples
- Read [OAuth Testing Setup Guide](OAUTH_TESTING_SETUP.md) for testing

---

## Need Help?

- Check examples: `examples/auth/`
- Read tests: `tests/test_request_middleware.py`
- Open an issue: https://github.com/anthropics/nextmcp/issues
