# JWT Authentication Example

This example demonstrates JWT (JSON Web Token) based authentication with automatic token expiration and role-based access control.

## Features

- **JWT Token Authentication**: Stateless token-based auth
- **Token Generation**: Built-in login endpoint
- **Expiration Handling**: Automatic token expiration validation
- **Role-Based Access**: Different roles with different permissions
- **Token Utility**: Helper script to generate tokens for testing

## Requirements

```bash
pip install PyJWT
```

## Running the Example

```bash
cd examples/auth_jwt

# Generate a token
python generate_token.py --user admin --role admin

# Start the server
python server.py
```

## How JWT Works

1. **Client logs in** with username/password
2. **Server generates JWT** signed with secret key
3. **Client includes token** in subsequent requests
4. **Server validates token** signature and expiration
5. **Server extracts user info** from token payload

## Available Roles

| Role | Permissions | Can Access |
|------|-------------|-----------|
| admin | read:*, write:*, delete:* | All tools |
| user | read:posts, write:own_posts | Create, update posts |
| viewer | read:posts | Read-only access |

## Tools

### Public (No Auth)
- `public_info()` - Server information
- `login(username, password)` - Get JWT token

### Authenticated
- `whoami()` - View your auth info
- `list_posts(limit)` - List posts

### User/Admin Role
- `create_post(title, content)` - Create post
- `update_post(post_id, title, content)` - Update post

### Admin Only
- `delete_post(post_id)` - Delete post
- `admin_dashboard()` - View server stats

## Token Generation

### Using the Utility

```bash
# Admin token (1 hour expiration)
python generate_token.py --user admin --role admin

# User token (2 hour expiration)
python generate_token.py --user alice --role user --expires 7200

# Viewer token
python generate_token.py --user bob --role viewer
```

### Programmatic Generation

```python
from nextmcp.auth import JWTProvider

provider = JWTProvider(secret_key="your-secret")

token = provider.create_token(
    user_id="user123",
    roles=["admin"],
    permissions=["read:*"],
    username="alice",
    expires_in=3600  # 1 hour
)
```

## Using Tokens

### With MCP Client

```python
# Authenticate with token
result = await client.invoke_tool(
    "whoami",
    {},
    auth={"token": "eyJhbGc..."}
)
```

### Token Structure

JWT tokens have three parts (separated by `.`):

```
header.payload.signature
```

Example payload:
```json
{
  "sub": "user_admin",
  "username": "admin",
  "roles": ["admin"],
  "permissions": ["read:*", "write:*"],
  "iat": 1705320000,
  "exp": 1705323600
}
```

## Security Features

- **Signature Verification**: Prevents token tampering
- **Expiration Validation**: Tokens auto-expire
- **Algorithm Specification**: HS256 by default
- **No Session Storage**: Stateless authentication

## Error Handling

### Expired Token
```python
# After token expires
result = await client.invoke_tool("whoami", {}, auth={"token": expired_token})
# Error: "Token expired"
```

### Invalid Token
```python
# Tampered or malformed token
result = await client.invoke_tool("whoami", {}, auth={"token": "invalid"})
# Error: "Invalid token"
```

### Insufficient Permissions
```python
# Viewer trying to create post
result = await client.invoke_tool(
    "create_post",
    {"title": "Post", "content": "Content"},
    auth={"token": viewer_token}
)
# Error: PermissionDeniedError
```

## Production Best Practices

1. **Use strong secret keys**: Generate with `secrets.token_urlsafe(32)`
2. **Store secrets securely**: Use environment variables
3. **Use HTTPS**: Prevent token interception
4. **Short expiration times**: Balance UX and security
5. **Refresh tokens**: Implement token refresh mechanism
6. **Revocation list**: Track revoked tokens if needed

## Advanced Usage

### Custom Claims

```python
token = provider.create_token(
    user_id="user123",
    roles=["user"],
    custom_field="custom_value",
    department="Engineering"
)
```

### Different Algorithms

```python
# RS256 (asymmetric)
provider = JWTProvider(
    secret_key=private_key,
    algorithm="RS256"
)
```

## Next Steps

- See `examples/auth_api_key/` for simpler API key auth
- See `examples/auth_rbac/` for complex permission scenarios
