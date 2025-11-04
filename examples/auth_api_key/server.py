#!/usr/bin/env python3
"""
API Key Authentication Example

This example demonstrates how to use API key authentication to protect MCP tools.
Shows both basic authentication and role-based access control.

Usage:
    python server.py

Testing:
    # Valid admin key
    python client.py --api-key admin-key-123

    # Valid user key
    python client.py --api-key user-key-456

    # Invalid key
    python client.py --api-key wrong-key
"""

import asyncio

from nextmcp import NextMCP
from nextmcp.auth import (
    APIKeyProvider,
    AuthContext,
    requires_auth_async,
    requires_role_async,
)

# Create the MCP app
app = NextMCP("api-key-auth-server", description="Demonstrates API key authentication")

# Configure API keys with roles and permissions
api_key_provider = APIKeyProvider(
    valid_keys={
        "admin-key-123": {
            "user_id": "admin1",
            "username": "admin",
            "roles": ["admin"],
            "permissions": ["read:*", "write:*", "delete:*"],
            "metadata": {"department": "IT"},
        },
        "user-key-456": {
            "user_id": "user1",
            "username": "alice",
            "roles": ["user"],
            "permissions": ["read:posts", "write:own_posts"],
            "metadata": {"department": "Marketing"},
        },
        "viewer-key-789": {
            "user_id": "viewer1",
            "username": "bob",
            "roles": ["viewer"],
            "permissions": ["read:posts"],
            "metadata": {"department": "Sales"},
        },
    }
)


# Public tool - no authentication required
@app.tool()
async def public_info() -> dict:
    """Get public server information (no auth required)."""
    return {
        "server": "API Key Auth Demo",
        "version": "1.0.0",
        "auth_required": "Use api_key parameter for protected tools",
    }


# Authenticated tool - requires valid API key
@app.tool()
@requires_auth_async(provider=api_key_provider)
async def get_profile(auth: AuthContext) -> dict:
    """Get the authenticated user's profile."""
    return {
        "user_id": auth.user_id,
        "username": auth.username,
        "roles": [r.name for r in auth.roles],
        "permissions": [p.name for p in auth.permissions],
        "metadata": auth.metadata,
    }


# Tool that requires authentication
@app.tool()
@requires_auth_async(provider=api_key_provider)
async def list_posts(auth: AuthContext, limit: int = 10) -> dict:
    """List blog posts (requires authentication)."""
    # Anyone authenticated can list posts
    return {
        "posts": [
            {"id": 1, "title": "First Post", "author": "admin"},
            {"id": 2, "title": "Second Post", "author": "alice"},
            {"id": 3, "title": "Third Post", "author": "bob"},
        ][:limit],
        "requested_by": auth.username,
    }


# Tool that requires specific role
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("user", "admin")
async def create_post(auth: AuthContext, title: str, content: str) -> dict:
    """Create a new blog post (requires user or admin role)."""
    return {
        "status": "created",
        "post": {
            "id": 4,
            "title": title,
            "content": content,
            "author": auth.username,
        },
        "message": f"Post created by {auth.username}",
    }


# Admin-only tool
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("admin")
async def delete_post(auth: AuthContext, post_id: int) -> dict:
    """Delete a blog post (admin only)."""
    return {
        "status": "deleted",
        "post_id": post_id,
        "deleted_by": auth.username,
        "message": f"Post {post_id} deleted by admin {auth.username}",
    }


# Admin-only server management tool
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("admin")
async def server_stats(auth: AuthContext) -> dict:
    """Get server statistics (admin only)."""
    return {
        "active_users": 42,
        "total_posts": 156,
        "disk_usage": "45%",
        "uptime": "12 days",
        "accessed_by": auth.username,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("API Key Authentication Example Server")
    print("=" * 60)
    print()
    print("Available API Keys:")
    print("  - admin-key-123  (admin role - full access)")
    print("  - user-key-456   (user role - can create posts)")
    print("  - viewer-key-789 (viewer role - read-only)")
    print()
    print("Available Tools:")
    print("  - public_info()       - No auth required")
    print("  - get_profile()       - Requires any valid key")
    print("  - list_posts()        - Requires any valid key")
    print("  - create_post()       - Requires user or admin role")
    print("  - delete_post()       - Requires admin role")
    print("  - server_stats()      - Requires admin role")
    print()
    print("Starting server...")
    print("=" * 60)

    app.run()
