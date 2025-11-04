# API Key Authentication Example

This example demonstrates how to use API key authentication to protect MCP tools with role-based access control.

## Features

- **API Key Provider**: Validates requests using pre-configured API keys
- **Role-Based Access**: Different keys have different roles (admin, user, viewer)
- **Permission Control**: Fine-grained permissions per key
- **Public & Protected Tools**: Mix of authenticated and unauthenticated tools
- **Async Support**: All tools use async/await

## Project Structure

```
auth_api_key/
├── server.py      # Main server with protected tools
└── README.md      # This file
```

## Running the Example

```bash
cd examples/auth_api_key
python server.py
```

## API Keys

The server has three pre-configured API keys:

| API Key | User | Role | Permissions |
|---------|------|------|-------------|
| `admin-key-123` | admin | admin | read:*, write:*, delete:* |
| `user-key-456` | alice | user | read:posts, write:own_posts |
| `viewer-key-789` | bob | viewer | read:posts |

## Available Tools

### Public (No Auth)
- `public_info()` - Get server information

### Authenticated (Any Valid Key)
- `get_profile()` - Get your user profile
- `list_posts()` - List blog posts

### User or Admin Role Required
- `create_post(title, content)` - Create a new post

### Admin Role Required
- `delete_post(post_id)` - Delete a post
- `server_stats()` - View server statistics

## How It Works

### 1. Configure the API Key Provider

```python
from nextmcp.auth import APIKeyProvider

api_key_provider = APIKeyProvider(
    valid_keys={
        "admin-key-123": {
            "user_id": "admin1",
            "username": "admin",
            "roles": ["admin"],
            "permissions": ["read:*", "write:*", "delete:*"],
        }
    }
)
```

### 2. Protect Tools with Authentication

```python
from nextmcp.auth import requires_auth_async, AuthContext

@app.tool()
@requires_auth_async(provider=api_key_provider)
async def protected_tool(auth: AuthContext) -> dict:
    """This tool requires authentication."""
    return {
        "user": auth.username,
        "roles": [r.name for r in auth.roles]
    }
```

### 3. Add Role-Based Access Control

```python
from nextmcp.auth import requires_role_async

@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("admin")
async def admin_only_tool(auth: AuthContext) -> dict:
    """Only users with admin role can access this."""
    return {"action": "performed", "by": auth.username}
```

## Testing the Authentication

### Test with Admin Key

```python
# This will work - admin has all permissions
result = await client.invoke_tool(
    "delete_post",
    {"post_id": 1},
    auth={"api_key": "admin-key-123"}
)
```

### Test with User Key

```python
# This will work - user can create posts
result = await client.invoke_tool(
    "create_post",
    {"title": "My Post", "content": "Content here"},
    auth={"api_key": "user-key-456"}
)

# This will FAIL - user cannot delete posts
result = await client.invoke_tool(
    "delete_post",
    {"post_id": 1},
    auth={"api_key": "user-key-456"}  # PermissionDeniedError!
)
```

### Test with Viewer Key

```python
# This will work - viewer can list posts
result = await client.invoke_tool(
    "list_posts",
    {"limit": 5},
    auth={"api_key": "viewer-key-789"}
)

# This will FAIL - viewer cannot create posts
result = await client.invoke_tool(
    "create_post",
    {"title": "Post", "content": "Content"},
    auth={"api_key": "viewer-key-789"}  # PermissionDeniedError!
)
```

## Key Concepts

### AuthContext

The `AuthContext` object contains information about the authenticated user:

- `authenticated` - Whether authentication succeeded
- `user_id` - Unique user identifier
- `username` - Human-readable username
- `roles` - Set of Role objects
- `permissions` - Set of Permission objects
- `metadata` - Additional user data

### Middleware Stacking

Decorators are applied from bottom to top:

```python
@app.tool()                                  # 3. Register as tool
@requires_auth_async(provider=api_key_provider)  # 2. Check authentication
@requires_role_async("admin")                # 1. Check role (first to execute)
async def tool(auth: AuthContext):
    pass
```

### Generating API Keys

```python
from nextmcp.auth import APIKeyProvider

# Generate a secure random API key
new_key = APIKeyProvider.generate_key()
print(f"New API key: {new_key}")
# Output: "a1b2c3d4e5f6..." (64 character hex string)
```

## Security Best Practices

1. **Never commit API keys to version control**
2. **Use environment variables for production keys**
3. **Rotate keys regularly**
4. **Use different keys for different environments**
5. **Implement key expiration if needed**
6. **Log authentication attempts**
7. **Use HTTPS/TLS in production**

## Production Configuration

For production, load API keys from environment variables or a secure config file:

```python
import os
from nextmcp.auth import APIKeyProvider

api_key_provider = APIKeyProvider(
    valid_keys={
        os.environ["ADMIN_API_KEY"]: {
            "user_id": "admin1",
            "roles": ["admin"],
        },
        os.environ["USER_API_KEY"]: {
            "user_id": "user1",
            "roles": ["user"],
        },
    }
)
```

## Custom Validation

You can provide a custom validation function:

```python
def validate_api_key(api_key: str) -> dict | None:
    """Custom validation logic."""
    # Query database, external service, etc.
    user = database.find_user_by_api_key(api_key)
    if user:
        return {
            "user_id": user.id,
            "username": user.name,
            "roles": user.roles,
        }
    return None

provider = APIKeyProvider(key_validator=validate_api_key)
```

## Next Steps

- See `examples/auth_jwt/` for JWT token authentication
- See `examples/auth_rbac/` for advanced RBAC scenarios
- See `examples/auth_custom/` for custom auth providers
