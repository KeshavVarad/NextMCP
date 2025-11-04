#!/usr/bin/env python3
"""
JWT Authentication Example

This example demonstrates how to use JWT (JSON Web Tokens) for authentication.
Shows token generation, validation, expiration, and role-based access.

Usage:
    # Generate a token first
    python generate_token.py --user alice --role user

    # Then use it with the server
    python server.py

Requirements:
    pip install PyJWT
"""

import asyncio

from nextmcp import NextMCP
from nextmcp.auth import AuthContext, JWTProvider, requires_auth_async, requires_role_async

# Create the MCP app
app = NextMCP("jwt-auth-server", description="Demonstrates JWT authentication")

# Secret key for JWT signing (in production, use environment variable!)
SECRET_KEY = "your-secret-key-change-in-production"

# Configure JWT provider
jwt_provider = JWTProvider(
    secret_key=SECRET_KEY,
    algorithm="HS256",
    verify_exp=True,  # Verify token expiration
)


# Public tool - no authentication
@app.tool()
async def public_info() -> dict:
    """Get public server information (no auth required)."""
    return {
        "server": "JWT Auth Demo",
        "version": "1.0.0",
        "auth": "JWT",
        "note": "Use generate_token.py to create tokens",
    }


# Tool to login and get a JWT token
@app.tool()
async def login(username: str, password: str) -> dict:
    """
    Login with username/password and receive a JWT token.

    In a real application, this would validate against a database.
    For this demo, we accept any username and password.
    """
    # In production: validate against database, hash passwords, etc.
    # For demo purposes, we'll accept any credentials

    # Determine role based on username (demo only!)
    if username == "admin":
        roles = ["admin"]
        permissions = ["read:*", "write:*", "delete:*"]
    elif username.startswith("user"):
        roles = ["user"]
        permissions = ["read:posts", "write:own_posts"]
    else:
        roles = ["viewer"]
        permissions = ["read:posts"]

    # Generate JWT token (expires in 1 hour)
    token = jwt_provider.create_token(
        user_id=f"user_{username}",
        roles=roles,
        permissions=permissions,
        username=username,
        expires_in=3600,  # 1 hour
    )

    return {
        "status": "success",
        "message": f"Login successful for {username}",
        "token": token,
        "expires_in": 3600,
        "token_type": "Bearer",
        "user": {"username": username, "roles": roles},
    }


# Authenticated tool
@app.tool()
@requires_auth_async(provider=jwt_provider)
async def whoami(auth: AuthContext) -> dict:
    """Get information about the authenticated user."""
    return {
        "user_id": auth.user_id,
        "username": auth.username,
        "roles": [r.name for r in auth.roles],
        "permissions": [p.name for p in auth.permissions],
        "authenticated": auth.authenticated,
    }


# List posts - requires authentication
@app.tool()
@requires_auth_async(provider=jwt_provider)
async def list_posts(auth: AuthContext, limit: int = 10) -> dict:
    """List blog posts (requires valid JWT token)."""
    posts = [
        {"id": 1, "title": "JWT Authentication in MCP", "author": "admin"},
        {"id": 2, "title": "Role-Based Access Control", "author": "alice"},
        {"id": 3, "title": "Secure API Design", "author": "bob"},
    ]

    return {
        "posts": posts[:limit],
        "total": len(posts),
        "requested_by": auth.username,
    }


# Create post - requires user or admin role
@app.tool()
@requires_auth_async(provider=jwt_provider)
@requires_role_async("user", "admin")
async def create_post(auth: AuthContext, title: str, content: str) -> dict:
    """Create a new blog post (requires user or admin role)."""
    new_post = {
        "id": 4,
        "title": title,
        "content": content,
        "author": auth.username,
        "created_at": "2025-01-15T10:30:00Z",
    }

    return {
        "status": "created",
        "post": new_post,
        "message": f"Post created by {auth.username}",
    }


# Update post - requires user or admin role
@app.tool()
@requires_auth_async(provider=jwt_provider)
@requires_role_async("user", "admin")
async def update_post(auth: AuthContext, post_id: int, title: str, content: str) -> dict:
    """Update an existing post (requires user or admin role)."""
    # In production: verify ownership or admin status
    return {
        "status": "updated",
        "post_id": post_id,
        "title": title,
        "updated_by": auth.username,
        "message": f"Post {post_id} updated",
    }


# Delete post - admin only
@app.tool()
@requires_auth_async(provider=jwt_provider)
@requires_role_async("admin")
async def delete_post(auth: AuthContext, post_id: int) -> dict:
    """Delete a blog post (admin only)."""
    return {
        "status": "deleted",
        "post_id": post_id,
        "deleted_by": auth.username,
        "message": f"Post {post_id} deleted by admin",
    }


# Admin dashboard - admin only
@app.tool()
@requires_auth_async(provider=jwt_provider)
@requires_role_async("admin")
async def admin_dashboard(auth: AuthContext) -> dict:
    """View admin dashboard with server statistics."""
    return {
        "server_stats": {
            "total_users": 156,
            "active_sessions": 42,
            "total_posts": 1234,
            "disk_usage_gb": 45.6,
        },
        "recent_activity": [
            {"user": "alice", "action": "created_post", "timestamp": "2025-01-15T10:25:00Z"},
            {"user": "bob", "action": "updated_post", "timestamp": "2025-01-15T10:20:00Z"},
        ],
        "accessed_by": auth.username,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("JWT Authentication Example Server")
    print("=" * 60)
    print()
    print("Quick Start:")
    print("  1. Generate a token:")
    print("     python generate_token.py --user admin --role admin")
    print()
    print("  2. Use the token to authenticate:")
    print("     - Pass as 'token' in credentials")
    print("     - Token expires after 1 hour")
    print()
    print("Available Tools:")
    print("  - public_info()        - No auth required")
    print("  - login()              - Get JWT token")
    print("  - whoami()             - Check your auth status")
    print("  - list_posts()         - Requires valid token")
    print("  - create_post()        - Requires user/admin role")
    print("  - update_post()        - Requires user/admin role")
    print("  - delete_post()        - Requires admin role")
    print("  - admin_dashboard()    - Requires admin role")
    print()
    print("User Roles:")
    print("  - admin     - Full access to all tools")
    print("  - user      - Can create and update posts")
    print("  - viewer    - Read-only access")
    print()
    print("Starting server...")
    print("=" * 60)

    app.run()
