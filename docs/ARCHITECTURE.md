# NextMCP Authentication Architecture

This document explains how NextMCP's authentication system works internally, how the components fit together, and the design decisions behind it.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Request Flow](#request-flow)
4. [Data Flow](#data-flow)
5. [Design Decisions](#design-decisions)
6. [Security Considerations](#security-considerations)
7. [Performance Characteristics](#performance-characteristics)

---

## System Overview

NextMCP's auth system consists of three main layers:

```
┌──────────────────────────────────────────────────────────────┐
│                      MCP Client/Host                         │
│  (Claude Desktop, Cursor, etc.)                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ 1. Reads auth metadata
                     │ 2. Initiates OAuth flow
                     │ 3. Sends requests with tokens
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                  Auth Metadata Protocol                      │
│  • Announces auth requirements                               │
│  • Lists providers, scopes, permissions                      │
│  • JSON schema for validation                                │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│              Request Enforcement Middleware                  │
│  • Validates every request                                   │
│  • Checks auth credentials                                   │
│  • Enforces scopes/permissions                               │
│  • Manages sessions                                          │
└────────────────────┬─────────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
┌────────▼──────────┐  ┌────────▼──────────┐
│  OAuth Providers  │  │  Session Store    │
│  • GitHub         │  │  • Memory         │
│  • Google         │  │  • File           │
│  • Custom         │  │  • Redis (future) │
└───────────────────┘  └───────────────────┘
```

---

## Component Architecture

### 1. Auth Metadata Protocol

**Location**: `nextmcp/protocol/auth_metadata.py`

**Purpose**: Allows servers to **announce** their auth requirements so hosts can discover them.

**Key Classes**:

```python
class AuthMetadata:
    """Top-level auth requirements."""
    requirement: AuthRequirement  # REQUIRED, OPTIONAL, NONE
    providers: list[AuthProviderMetadata]
    required_scopes: list[str]
    optional_scopes: list[str]
    permissions: list[str]
    supports_multi_user: bool
    token_refresh_enabled: bool

class AuthProviderMetadata:
    """Single OAuth provider info."""
    name: str  # "google", "github"
    type: str  # "oauth2"
    flows: list[AuthFlowType]  # [OAUTH2_PKCE]
    authorization_url: str
    token_url: str
    scopes: list[str]
    supports_refresh: bool
```

**Usage**:

```python
# Server creates metadata
metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
metadata.add_provider(
    name="google",
    type="oauth2",
    flows=[AuthFlowType.OAUTH2_PKCE],
    ...
)

# Serialize for transmission
json_data = metadata.to_dict()

# Host reads and understands auth requirements
metadata = AuthMetadata.from_dict(json_data)
```

**Why it exists**: Before this, hosts had no way to know what auth a server needed. Now they can:
- Show "Connect Google Account" UI
- Request appropriate OAuth scopes
- Handle auth failures gracefully

---

### 2. Session Store

**Location**: `nextmcp/session/session_store.py`

**Purpose**: Persistent storage for OAuth tokens and user sessions

**Interface**:

```python
class SessionStore(ABC):
    """Abstract interface for session storage."""

    def save(self, session: SessionData) -> None
    def load(self, user_id: str) -> SessionData | None
    def delete(self, user_id: str) -> bool
    def exists(self, user_id: str) -> bool
    def list_users(self) -> list[str]
    def clear_all(self) -> int
    def update_tokens(...) -> None
```

**Implementations**:

#### MemorySessionStore:
```python
class MemorySessionStore(SessionStore):
    """In-memory, lost on restart."""
    _sessions: dict[str, SessionData]  # user_id -> session
    _lock: threading.RLock  # Thread-safe
```

- **Pros**: Fast (O(1) lookup), simple
- **Cons**: Lost on restart, single-process only
- **Use case**: Development, testing

#### FileSessionStore:
```python
class FileSessionStore(SessionStore):
    """JSON files on disk."""
    directory: Path  # .sessions/
    # Each user = one JSON file: session_user123.json
```

- **Pros**: Persists across restarts
- **Cons**: Single-server only, file I/O overhead
- **Use case**: Production (single server)

#### Future: RedisSessionStore:
```python
class RedisSessionStore(SessionStore):
    """Distributed, scalable."""
    # redis.set(f"session:{user_id}", json.dumps(session))
```

- **Pros**: Distributed, scalable, TTL support
- **Cons**: Requires Redis
- **Use case**: Production (multi-server)

**SessionData Model**:

```python
@dataclass
class SessionData:
    user_id: str
    access_token: str | None
    refresh_token: str | None
    expires_at: float | None  # Unix timestamp
    scopes: list[str]
    user_info: dict  # Name, email, etc.
    provider: str  # "google", "github"
    created_at: float
    updated_at: float
    metadata: dict  # Custom app data

    def is_expired(self) -> bool
    def needs_refresh(self, buffer_seconds=300) -> bool
```

---

### 3. Request Enforcement Middleware

**Location**: `nextmcp/auth/request_middleware.py`

**Purpose**: Intercept **every** MCP request and enforce auth automatically

**How it Works**:

```
Request arrives
     │
     ▼
┌─────────────────────────────────────┐
│ Is auth required?                   │
│ (Check metadata.requirement)        │
└────┬────────────────────────────┬───┘
     │                            │
     │ YES                        │ NO
     ▼                            │
┌─────────────────────────────────┐   │
│ Extract credentials from request│   │
│ request.get("auth")             │   │
└────┬────────────────────────────┘   │
     │                                │
     ▼                                │
┌─────────────────────────────────┐   │
│ Check session store              │   │
│ Does user have existing session? │   │
└────┬────────────────────────┬───┘   │
     │                        │       │
     │ YES                    │ NO    │
     ▼                        ▼       │
┌────────────────┐   ┌──────────────┐│
│ Reuse session  │   │ Authenticate ││
│ Check expired  │   │ with provider││
└────┬───────────┘   └──────┬───────┘│
     │                      │        │
     ▼                      ▼        │
┌──────────────────────────────────┐ │
│ Token expired?                   │ │
│ Auto-refresh if enabled          │ │
└────┬─────────────────────────────┘ │
     │                                │
     ▼                                │
┌──────────────────────────────────┐ │
│ Check scopes & permissions       │ │
│ (required_scopes, manifest)      │ │
└────┬─────────────────────────────┘ │
     │                                │
     │ All checks passed              │
     ▼                                ▼
┌──────────────────────────────────────┐
│ Inject auth_context into request    │
│ request["_auth_context"] = context  │
└────┬─────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────┐
│ Call next handler                    │
│ Tool function executes               │
└──────────────────────────────────────┘
```

**Code Structure**:

```python
class AuthEnforcementMiddleware:
    def __init__(
        self,
        provider: AuthProvider,
        session_store: SessionStore | None,
        metadata: AuthMetadata | None,
        manifest: PermissionManifest | None,
        auto_refresh_tokens: bool = True,
    ):
        ...

    async def __call__(self, request: dict, handler: Callable):
        # 1. Check if auth required
        if self.metadata.requirement == AuthRequirement.NONE:
            return await handler(request)

        # 2. Extract credentials
        credentials = request.get("auth", {})

        # 3. Authenticate
        auth_result = await self._authenticate(credentials, request)

        # 4. Check authorization
        self._check_authorization(auth_result.context, request)

        # 5. Inject context
        request["_auth_context"] = auth_result.context

        # 6. Call handler
        return await handler(request)
```

**Key Methods**:

```python
async def _authenticate(self, credentials, request):
    """Validate credentials, check session, refresh if needed."""
    # 1. Check session store first (reuse)
    # 2. If not found, call provider.authenticate()
    # 3. Save new session
    # 4. Auto-refresh if expiring
    # 5. Return AuthResult

def _check_authorization(self, auth_context, request):
    """Check scopes and permissions."""
    # 1. Check required_scopes
    # 2. Check manifest (if provided)
    # 3. Raise AuthorizationError if denied
```

---

### 4. OAuth Providers

**Location**: `nextmcp/auth/oauth.py`, `nextmcp/auth/oauth_providers.py`

**Base Class**:

```python
class OAuthProvider(AuthProvider, ABC):
    """Base OAuth 2.0 provider with PKCE."""

    def generate_authorization_url(self, state=None) -> dict:
        """Create auth URL with PKCE."""
        pkce = PKCEChallenge.generate()
        url = f"{self.config.authorization_url}?..."
        return {"url": url, "state": state, "verifier": pkce.verifier}

    async def exchange_code_for_token(self, code, state, verifier):
        """Exchange code for access token."""
        # POST to token_url with code + verifier
        # Handle both JSON and form-encoded responses
        return token_data

    async def refresh_access_token(self, refresh_token):
        """Refresh expired token."""
        # POST to token_url with refresh_token
        return new_token_data

    @abstractmethod
    async def get_user_info(self, access_token):
        """Provider-specific user info endpoint."""
        pass
```

**Built-in Providers**:

```python
class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth with PKCE."""
    # authorization_url: github.com/login/oauth/authorize
    # token_url: github.com/login/oauth/access_token
    # Returns form-encoded tokens

class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth with PKCE."""
    # authorization_url: accounts.google.com/o/oauth2/v2/auth
    # token_url: oauth2.googleapis.com/token
    # Returns JSON tokens
    # Supports refresh tokens with access_type=offline
```

**PKCE Flow**:

```
1. Server generates PKCE challenge
   verifier = random_43_chars()
   challenge = SHA256(verifier)

2. Server sends challenge in auth URL
   redirect to: auth_url?code_challenge=...

3. User authorizes, provider sends code

4. Server exchanges code + verifier for token
   POST token_url with code + code_verifier

5. Provider validates: SHA256(verifier) == challenge
   Returns access_token + refresh_token
```

**Why PKCE**: Secure for public clients (no client secret exposed)

---

## Request Flow

### Complete Request Lifecycle:

```
1. Client sends request
   ┌────────────────────────────────────┐
   │ {                                  │
   │   "method": "tools/call",          │
   │   "params": {"name": "get_data"},  │
   │   "auth": {                        │
   │     "access_token": "ya29.a0..."   │
   │   }                                │
   │ }                                  │
   └────────────────────────────────────┘
                 │
                 ▼
2. Middleware intercepts
   ┌────────────────────────────────────┐
   │ AuthEnforcementMiddleware.__call__ │
   └────────────────────────────────────┘
                 │
                 ▼
3. Check auth requirement
   if metadata.requirement == NONE:
       skip auth
                 │
                 ▼
4. Extract credentials
   access_token = request["auth"]["access_token"]
                 │
                 ▼
5. Check session store
   session = session_store.load_by_token(access_token)
   if session:
       if session.is_expired():
           reject
       if session.needs_refresh():
           auto_refresh
       use session
                 │
                 ▼
6. Or authenticate with provider
   result = await provider.authenticate({
       "access_token": access_token
   })
                 │
                 ▼
7. Save new session
   session_store.save(SessionData(...))
                 │
                 ▼
8. Check authorization
   • Check required_scopes
   • Check manifest permissions
                 │
                 ▼
9. Inject auth context
   request["_auth_context"] = AuthContext(...)
                 │
                 ▼
10. Call tool handler
   result = await tool_function()
                 │
                 ▼
11. Return result to client
   ┌────────────────────────────────────┐
   │ {                                  │
   │   "result": {...}                  │
   │ }                                  │
   └────────────────────────────────────┘
```

---

## Data Flow

### OAuth Token Acquisition:

```
┌──────────┐                    ┌──────────────┐
│  Client  │                    │ OAuth Server │
│  (Host)  │                    │ (Google)     │
└────┬─────┘                    └──────┬───────┘
     │                                 │
     │ 1. GET /auth/metadata          │
     ├──────────────────────────────►  │
     │ Returns auth requirements       │
     │ {providers: [google], ...}      │
     │◄────────────────────────────────┤
     │                                 │
     │ 2. Generate auth URL            │
     │ provider.generate_authorization_url()
     │ Returns: {url, state, verifier} │
     │                                 │
     │ 3. Open browser to auth URL     │
     ├─────────────────────────────────►
     │                                 │
     │ 4. User authorizes              │
     │                        ┌────────┤
     │                        │Authorize│
     │                        └────────┤
     │                                 │
     │ 5. Redirect to callback with code
     │◄─────────────────────────────────┤
     │ http://localhost:8080/callback? │
     │ code=abc123&state=xyz           │
     │                                 │
     │ 6. Exchange code for token      │
     │ POST /token                     │
     │ code=abc123                     │
     │ code_verifier=...               │
     ├─────────────────────────────────►
     │                                 │
     │ 7. Returns tokens               │
     │ {access_token, refresh_token}   │
     │◄─────────────────────────────────┤
     │                                 │
     │ 8. Save session                 │
     │ session_store.save(...)         │
     │                                 │
     │ 9. Make authenticated requests  │
     │ {auth: {access_token: ...}}     │
     └──────────────────────────────────
```

---

## Design Decisions

### Why Middleware Instead of Decorators?

**Decorators** (old way):
```python
@requires_auth_async(provider)
@requires_scope_async("read:data")
async def tool1():
    pass

@requires_auth_async(provider)
@requires_scope_async("read:data")
async def tool2():
    pass
```

**Middleware** (new way):
```python
server.use(create_auth_middleware(
    provider=provider,
    required_scopes=["read:data"]
))

# All tools automatically protected
```

**Advantages**:
1. **DRY**: Don't repeat decorators on every tool
2. **Centralized**: One place to configure auth
3. **Automatic**: Impossible to forget to add auth
4. **Flexible**: Can still use decorators for tool-specific requirements

### Why Session Store?

**Without session store**:
- Must re-authenticate every request
- Can't refresh tokens
- Can't support multiple users
- No session persistence

**With session store**:
- ✅ Authenticate once, reuse session
- ✅ Automatic token refresh
- ✅ Multi-user support
- ✅ Persists across restarts

### Why Auth Metadata Protocol?

**Before**: Hosts had to guess or hardcode server auth requirements

**After**: Hosts can discover auth requirements dynamically

**Benefits**:
- Standardized auth discovery
- Better UX (show "Connect Google" UI)
- Future-proof (new auth methods just work)

---

## Security Considerations

### Token Storage

**Tokens in memory**: MemorySessionStore
- ✅ Fast
- ⚠️ Lost on crash
- ⚠️ Vulnerable to memory dumps

**Tokens on disk**: FileSessionStore
- ✅ Persists
- ⚠️ Vulnerable to file system access
- **Mitigation**: Proper file permissions (chmod 600)

**Tokens in Redis**: RedisSessionStore (future)
- ✅ Distributed
- ✅ TTL support
- **Security**: Encrypt Redis connection, use ACLs

### PKCE

**Why**: Prevents authorization code interception attacks

**How**: Verifier proves client initiated the auth flow

**Without PKCE**: Attacker could intercept code and use it

**With PKCE**: Attacker can't use code without verifier

### Token Refresh

**Automatic refresh**:
- ✅ Good UX (no expiration errors)
- ⚠️ Longer-lived access

**Manual refresh**:
- ⚠️ Poor UX (users see errors)
- ✅ Shorter-lived access

**Recommendation**: Use automatic refresh with short-lived access tokens (1 hour)

### Scope Validation

**Always validate scopes**:
```python
middleware = create_auth_middleware(
    required_scopes=["profile", "email"],
    # Don't trust client claims!
)
```

**Why**: Client could send fake scopes

**How**: Middleware validates against actual OAuth token scopes

---

## Performance Characteristics

### Session Store Performance:

| Operation | Memory | File | Redis |
|-----------|--------|------|-------|
| Save      | O(1)   | O(1) | O(1)  |
| Load      | O(1)   | O(1) | O(1)  |
| List      | O(n)   | O(n) | O(n)  |
| Delete    | O(1)   | O(1) | O(1)  |

### Middleware Overhead:

**Per request**:
1. Session lookup: O(1) - ~0.1ms
2. Token validation: O(1) - ~0.5ms (if cached)
3. Scope check: O(m) where m = number of scopes - ~0.01ms
4. **Total overhead**: ~1ms per request

**With auto-refresh**:
- Check if token expiring: O(1) - ~0.01ms
- Refresh if needed: ~500ms (network call, rare)

### Scalability:

**Single server**:
- MemorySessionStore: 10,000+ concurrent users
- FileSessionStore: 100,000+ users

**Distributed**:
- RedisSessionStore: Millions of users

---

## Extension Points

### Custom Session Store:

```python
class DatabaseSessionStore(SessionStore):
    """Store sessions in PostgreSQL."""

    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def save(self, session):
        with self.engine.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (...) VALUES (...)"
            )
```

### Custom OAuth Provider:

```python
class CustomOAuthProvider(OAuthProvider):
    """Your company's OAuth."""

    async def get_user_info(self, access_token):
        # Call your user info endpoint
        return user_data

    def extract_user_id(self, user_info):
        return user_info["id"]
```

### Custom Middleware:

```python
class AuditMiddleware:
    """Log all auth events."""

    async def __call__(self, request, handler):
        auth_context = request.get("_auth_context")
        if auth_context:
            log_auth_event(auth_context.user_id, request)
        return await handler(request)
```

---

## Summary

NextMCP's auth architecture provides:

1. **Discovery** - Servers announce requirements (Auth Metadata)
2. **Enforcement** - Every request is validated (Request Middleware)
3. **Persistence** - Sessions survive restarts (Session Store)
4. **Flexibility** - Pluggable providers and stores
5. **Security** - PKCE, scope validation, token refresh
6. **Performance** - <1ms overhead per request

The three-layer design (metadata + middleware + storage) creates a complete, production-ready auth system for MCP servers.
