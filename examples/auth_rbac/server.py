#!/usr/bin/env python3
"""
RBAC (Role-Based Access Control) Example

This example demonstrates advanced RBAC with fine-grained permissions,
hierarchical roles, and permission-based access control.

Features:
- Fine-grained permissions (read:posts, write:posts, etc.)
- Permission wildcards (admin:*, *)
- RBAC configuration loading from dict
- Permission-based access control (@requires_permission)
- Role hierarchies

Usage:
    python server.py
"""

from nextmcp import NextMCP
from nextmcp.auth import (
    APIKeyProvider,
    AuthContext,
    RBAC,
    requires_auth_async,
    requires_permission_async,
    requires_role_async,
)

# Create the MCP app
app = NextMCP("rbac-server", description="Demonstrates advanced RBAC")

# Initialize RBAC system
rbac = RBAC()

# Define RBAC configuration
rbac_config = {
    "permissions": [
        {"name": "read:posts", "description": "Read blog posts"},
        {"name": "write:posts", "description": "Create and edit posts"},
        {"name": "delete:posts", "description": "Delete posts"},
        {"name": "read:users", "description": "View user list"},
        {"name": "write:users", "description": "Create and edit users"},
        {"name": "delete:users", "description": "Delete users"},
        {"name": "admin:*", "description": "All admin permissions"},
        {"name": "*", "description": "All permissions"},
    ],
    "roles": [
        {
            "name": "viewer",
            "description": "Read-only access to posts",
            "permissions": ["read:posts"],
        },
        {
            "name": "author",
            "description": "Can create and edit posts",
            "permissions": ["read:posts", "write:posts"],
        },
        {
            "name": "editor",
            "description": "Can create, edit, and delete posts",
            "permissions": ["read:posts", "write:posts", "delete:posts"],
        },
        {
            "name": "moderator",
            "description": "Can manage posts and view users",
            "permissions": ["read:posts", "write:posts", "delete:posts", "read:users"],
        },
        {
            "name": "admin",
            "description": "Full access to everything",
            "permissions": ["*"],  # Wildcard - matches all permissions
        },
    ],
}

# Load RBAC configuration
rbac.load_from_config(rbac_config)

# Configure API key provider with RBAC roles
api_key_provider = APIKeyProvider(
    valid_keys={
        "admin-key": {
            "user_id": "admin1",
            "username": "admin",
            "roles": ["admin"],
        },
        "moderator-key": {
            "user_id": "mod1",
            "username": "moderator",
            "roles": ["moderator"],
        },
        "editor-key": {
            "user_id": "editor1",
            "username": "editor",
            "roles": ["editor"],
        },
        "author-key": {
            "user_id": "author1",
            "username": "alice",
            "roles": ["author"],
        },
        "viewer-key": {
            "user_id": "viewer1",
            "username": "bob",
            "roles": ["viewer"],
        },
    }
)


@app.tool()
async def show_rbac_config() -> dict:
    """View the current RBAC configuration (no auth required)."""
    config = rbac.to_dict()

    return {
        "message": "Current RBAC Configuration",
        "total_roles": len(config["roles"]),
        "total_permissions": len(config["permissions"]),
        "roles": config["roles"],
        "permissions": config["permissions"],
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
async def check_my_permissions(auth: AuthContext) -> dict:
    """Check what permissions you have based on your roles."""
    # Get user's roles
    user_roles = [rbac.get_role(r.name) for r in auth.roles]

    # Collect all permissions from roles
    all_permissions = set()
    for role in user_roles:
        if role:
            all_permissions.update(role.permissions)

    return {
        "user": auth.username,
        "user_id": auth.user_id,
        "roles": [r.name for r in auth.roles],
        "permissions": [p.name for p in all_permissions],
        "can_read_posts": rbac.check_permission(auth, "read:posts"),
        "can_write_posts": rbac.check_permission(auth, "write:posts"),
        "can_delete_posts": rbac.check_permission(auth, "delete:posts"),
        "can_read_users": rbac.check_permission(auth, "read:users"),
        "can_write_users": rbac.check_permission(auth, "write:users"),
    }


# Permission-based access control examples

@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("read:posts")
async def list_posts(auth: AuthContext) -> dict:
    """List all posts (requires read:posts permission)."""
    return {
        "posts": [
            {"id": 1, "title": "RBAC in MCP", "author": "admin"},
            {"id": 2, "title": "Permission Systems", "author": "alice"},
            {"id": 3, "title": "Security Best Practices", "author": "bob"},
        ],
        "accessed_by": auth.username,
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("write:posts")
async def create_post(auth: AuthContext, title: str, content: str) -> dict:
    """Create a post (requires write:posts permission)."""
    return {
        "status": "created",
        "post": {
            "id": 4,
            "title": title,
            "content": content,
            "author": auth.username,
        },
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("write:posts")
async def update_post(auth: AuthContext, post_id: int, title: str) -> dict:
    """Update a post (requires write:posts permission)."""
    return {
        "status": "updated",
        "post_id": post_id,
        "new_title": title,
        "updated_by": auth.username,
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("delete:posts")
async def delete_post(auth: AuthContext, post_id: int) -> dict:
    """Delete a post (requires delete:posts permission)."""
    return {
        "status": "deleted",
        "post_id": post_id,
        "deleted_by": auth.username,
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("read:users")
async def list_users(auth: AuthContext) -> dict:
    """List all users (requires read:users permission)."""
    return {
        "users": [
            {"id": 1, "username": "admin", "role": "admin"},
            {"id": 2, "username": "alice", "role": "author"},
            {"id": 3, "username": "bob", "role": "viewer"},
        ],
        "accessed_by": auth.username,
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("write:users")
async def create_user(auth: AuthContext, username: str, role: str) -> dict:
    """Create a new user (requires write:users permission)."""
    return {
        "status": "created",
        "user": {"id": 4, "username": username, "role": role},
        "created_by": auth.username,
    }


@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("delete:users")
async def delete_user(auth: AuthContext, user_id: int) -> dict:
    """Delete a user (requires delete:users permission)."""
    return {
        "status": "deleted",
        "user_id": user_id,
        "deleted_by": auth.username,
        "note": "Only admins have this permission",
    }


if __name__ == "__main__":
    print("=" * 70)
    print("RBAC (Role-Based Access Control) Example")
    print("=" * 70)
    print()
    print("This example demonstrates fine-grained permission control.")
    print()
    print("Roles and Their Permissions:")
    print("-" * 70)

    for role_config in rbac_config["roles"]:
        print(f"  {role_config['name'].upper():15} - {role_config['description']}")
        print(f"                  Permissions: {', '.join(role_config['permissions'])}")

    print()
    print("API Keys:")
    print("-" * 70)
    print("  admin-key      - Full access (admin role)")
    print("  moderator-key  - Manage posts + view users")
    print("  editor-key     - Create, edit, delete posts")
    print("  author-key     - Create and edit posts")
    print("  viewer-key     - Read-only access")
    print()
    print("Available Tools:")
    print("-" * 70)
    print("  show_rbac_config()       - View RBAC configuration")
    print("  check_my_permissions()   - Check your permissions")
    print()
    print("  Requires read:posts:")
    print("    - list_posts()")
    print()
    print("  Requires write:posts:")
    print("    - create_post(title, content)")
    print("    - update_post(post_id, title)")
    print()
    print("  Requires delete:posts:")
    print("    - delete_post(post_id)")
    print()
    print("  Requires read:users:")
    print("    - list_users()")
    print()
    print("  Requires write:users:")
    print("    - create_user(username, role)")
    print()
    print("  Requires delete:users:")
    print("    - delete_user(user_id)")
    print()
    print("Starting server...")
    print("=" * 70)

    app.run()
