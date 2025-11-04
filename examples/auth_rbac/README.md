# RBAC (Role-Based Access Control) Example

Advanced example demonstrating fine-grained permission control with the RBAC system.

## Features

- **Fine-Grained Permissions**: Specific permissions like `read:posts`, `write:posts`
- **Permission Wildcards**: `admin:*` matches all admin permissions, `*` matches everything
- **RBAC Configuration**: Load roles and permissions from configuration
- **Permission-Based Access**: `@requires_permission` instead of `@requires_role`
- **Role Hierarchies**: Different roles with different permission sets

## Roles and Permissions

| Role | Permissions | Capabilities |
|------|-------------|--------------|
| viewer | read:posts | Read posts only |
| author | read:posts, write:posts | Create and edit posts |
| editor | read/write/delete:posts | Full post management |
| moderator | All post perms + read:users | Manage posts + view users |
| admin | * (all) | Full access to everything |

## Permission Matrix

| Permission | viewer | author | editor | moderator | admin |
|-----------|--------|--------|--------|-----------|-------|
| read:posts | ✓ | ✓ | ✓ | ✓ | ✓ |
| write:posts | ✗ | ✓ | ✓ | ✓ | ✓ |
| delete:posts | ✗ | ✗ | ✓ | ✓ | ✓ |
| read:users | ✗ | ✗ | ✗ | ✓ | ✓ |
| write:users | ✗ | ✗ | ✗ | ✗ | ✓ |
| delete:users | ✗ | ✗ | ✗ | ✗ | ✓ |

## Running the Example

```bash
cd examples/auth_rbac
python server.py
```

## Key Concepts

### Permission-Based Access

Instead of checking roles, check specific permissions:

```python
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("write:posts")  # Specific permission
async def create_post(auth: AuthContext, title: str) -> dict:
    pass
```

This allows:
- **Flexibility**: Users can have permissions without roles
- **Granularity**: Fine-grained access control
- **Clarity**: Explicit permission requirements

### Loading RBAC Configuration

```python
from nextmcp.auth import RBAC

rbac = RBAC()

config = {
    "permissions": [
        {"name": "read:posts", "description": "Read posts"}
    ],
    "roles": [
        {
            "name": "viewer",
            "permissions": ["read:posts"]
        }
    ]
}

rbac.load_from_config(config)
```

### Permission Wildcards

```python
# Admin has all permissions
rbac.define_permission("*")

# Matches any permission check
auth_context.has_permission("read:posts")  # True
auth_context.has_permission("write:users")  # True
auth_context.has_permission("anything")  # True
```

### Checking Permissions

```python
from nextmcp.auth import RBAC

rbac = RBAC()

# Check if user has permission
if rbac.check_permission(auth_context, "write:posts"):
    # Allow action
    pass

# Require permission (raises PermissionDeniedError if missing)
rbac.require_permission(auth_context, "delete:posts")
```

## Testing Different Roles

### Viewer (Read-Only)

```python
# Works
list_posts(auth={"api_key": "viewer-key"})

# Fails - PermissionDeniedError
create_post(title="Post", content="...", auth={"api_key": "viewer-key"})
```

### Author (Create/Edit)

```python
# Works
create_post(title="My Post", content="...", auth={"api_key": "author-key"})
update_post(post_id=1, title="Updated", auth={"api_key": "author-key"})

# Fails - PermissionDeniedError
delete_post(post_id=1, auth={"api_key": "author-key"})
```

### Editor (Full Post Management)

```python
# All work
list_posts(auth={"api_key": "editor-key"})
create_post(..., auth={"api_key": "editor-key"})
update_post(..., auth={"api_key": "editor-key"})
delete_post(post_id=1, auth={"api_key": "editor-key"})

# Fails - no user management permission
list_users(auth={"api_key": "editor-key"})
```

### Admin (Full Access)

```python
# Everything works - wildcard permission
list_posts(auth={"api_key": "admin-key"})
delete_post(..., auth={"api_key": "admin-key"})
list_users(auth={"api_key": "admin-key"})
create_user(..., auth={"api_key": "admin-key"})
delete_user(..., auth={"api_key": "admin-key"})
```

## Best Practices

1. **Use specific permissions over roles** when possible
2. **Define clear permission naming conventions** (resource:action)
3. **Document permission requirements** for each tool
4. **Use wildcards sparingly** (only for admin/superuser roles)
5. **Load RBAC config from files** in production
6. **Version your permission schemas** as they evolve

## Next Steps

- See `nextmcp/auth/rbac.py` for full RBAC system implementation
- See `examples/auth_api_key/` for simpler auth example
- See `examples/auth_jwt/` for token-based auth
