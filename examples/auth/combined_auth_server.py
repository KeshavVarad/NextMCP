"""
Combined Authentication & Authorization MCP Server Example.

This comprehensive example demonstrates using all NextMCP auth features together:
- Multiple auth providers (API Key, JWT, OAuth)
- Role-Based Access Control (RBAC)
- Permission system
- OAuth scopes
- Permission manifests
- Error handling

Features demonstrated:
- APIKeyProvider for service accounts
- GitHubOAuthProvider for user authentication
- RBAC with hierarchical roles
- Fine-grained permissions
- OAuth scope enforcement
- Manifest-based security
- Custom error handling

Usage:
   python examples/auth/combined_auth_server.py
"""

import asyncio
import os
from typing import Any

from nextmcp import NextMCP
from nextmcp.auth import (
    APIKeyProvider,
    AuthContext,
    GitHubOAuthProvider,
    ManifestViolationError,
    OAuthRequiredError,
    Permission,
    PermissionManifest,
    RBAC,
    Role,
    ScopeInsufficientError,
    requires_auth_async,
    requires_manifest_async,
    requires_permission_async,
    requires_role_async,
    requires_scope_async,
)

# Initialize MCP server
mcp = NextMCP("Combined Auth Example")

# ========================================================================
# 1. SETUP RBAC SYSTEM
# ========================================================================

print("Setting up RBAC system...")

rbac = RBAC()

# Define roles
admin_role = rbac.define_role("admin", "Administrator with full access")
editor_role = rbac.define_role("editor", "Content editor")
viewer_role = rbac.define_role("viewer", "Read-only access")
service_role = rbac.define_role("service", "Service account for automation")

# Define permissions
rbac.define_permission("*", "All permissions")
rbac.define_permission("read:*", "Read all")
rbac.define_permission("write:*", "Write all")
rbac.define_permission("automation:*", "Automation permissions")
rbac.define_permission("admin:all", "Admin all")
rbac.define_permission("read:posts", "Read posts")
rbac.define_permission("write:posts", "Write posts")
rbac.define_permission("read:pages", "Read pages")
rbac.define_permission("write:pages", "Write pages")
rbac.define_permission("admin:users", "Manage users")

# Assign permissions to roles
rbac.assign_permission_to_role("admin", "*")
rbac.assign_permission_to_role("editor", "read:*")
rbac.assign_permission_to_role("editor", "write:posts")
rbac.assign_permission_to_role("editor", "write:pages")
rbac.assign_permission_to_role("viewer", "read:*")
rbac.assign_permission_to_role("service", "read:*")
rbac.assign_permission_to_role("service", "write:*")
rbac.assign_permission_to_role("service", "automation:*")

print(f"✓ Registered {len(rbac.list_roles())} roles\n")

# ========================================================================
# 2. SETUP AUTH PROVIDERS
# ========================================================================

print("Setting up authentication providers...")

# API Key provider for service accounts and testing
api_key_provider = APIKeyProvider(
    valid_keys={
        "admin_key_123": {
            "user_id": "admin1",
            "username": "Admin User",
            "roles": ["admin"],
            "permissions": ["admin:all"],
        },
        "editor_key_456": {
            "user_id": "editor1",
            "username": "Editor User",
            "roles": ["editor"],
            "permissions": ["read:posts", "write:posts", "read:pages", "write:pages"],
        },
        "viewer_key_789": {
            "user_id": "viewer1",
            "username": "Viewer User",
            "roles": ["viewer"],
            "permissions": ["read:posts", "read:pages"],
        },
        "service_key_abc": {
            "user_id": "service1",
            "username": "Automation Service",
            "roles": ["service"],
            "permissions": ["automation:jobs", "read:all", "write:all"],
        },
    }
)

# GitHub OAuth provider for user authentication
github_oauth = GitHubOAuthProvider(
    client_id=os.getenv("GITHUB_CLIENT_ID", "demo_client_id"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    scope=["read:user", "repo"],
)

print("✓ Configured API Key provider")
print("✓ Configured GitHub OAuth provider\n")

# ========================================================================
# 3. SETUP PERMISSION MANIFEST
# ========================================================================

print("Setting up permission manifest...")

manifest = PermissionManifest()

# Define OAuth scope mappings
manifest.define_scope(
    "repo:read",
    "Read repository access",
    {"github": ["repo", "public_repo"]},
)

manifest.define_scope(
    "repo:write",
    "Write repository access",
    {"github": ["repo"]},
)

# Define tool requirements
manifest.define_tool_permission(
    "view_content",
    roles=["viewer", "editor", "admin"],
    permissions=["read:posts", "read:pages"],
    description="View content",
)

manifest.define_tool_permission(
    "edit_content",
    roles=["editor", "admin"],
    permissions=["write:posts", "write:pages"],
    description="Edit content",
)

manifest.define_tool_permission(
    "manage_users",
    roles=["admin"],
    permissions=["admin:users"],
    description="Manage user accounts",
)

manifest.define_tool_permission(
    "github_repo_access",
    scopes=["repo:read"],
    description="Access GitHub repositories via OAuth",
)

manifest.define_tool_permission(
    "dangerous_operation",
    roles=["admin"],
    permissions=["admin:all"],
    scopes=["admin:full"],
    description="Dangerous admin operation",
    dangerous=True,
)

print(f"✓ Configured {len(manifest.tools)} protected tools\n")

# ========================================================================
# 4. DEFINE TOOLS WITH DIFFERENT AUTH STRATEGIES
# ========================================================================

# --- Public Tools (No Auth) ---

@mcp.tool()
async def get_public_info() -> dict[str, Any]:
    """
    Get public information.

    No authentication required.

    Returns:
        Public information
    """
    return {
        "service": "Combined Auth MCP Server",
        "version": "1.0.0",
        "auth_methods": ["api_key", "github_oauth"],
        "public": True,
    }


@mcp.tool()
async def get_github_auth_url(state: str | None = None) -> dict[str, str]:
    """
    Get GitHub OAuth authorization URL.

    No authentication required to get the URL.

    Args:
        state: Optional CSRF protection state

    Returns:
        Authorization URL and PKCE data
    """
    return github_oauth.generate_authorization_url(state=state)


# --- Basic Auth Required ---

@mcp.tool()
@requires_auth_async(provider=api_key_provider)
async def get_my_profile(auth: AuthContext) -> dict[str, Any]:
    """
    Get authenticated user's profile.

    Requires: Any valid authentication

    Args:
        auth: Authentication context (injected)

    Returns:
        User profile
    """
    return {
        "user_id": auth.user_id,
        "username": auth.username,
        "roles": [r.name for r in auth.roles],
        "permissions": [p.name for p in auth.permissions],
        "scopes": list(auth.scopes),
    }


# --- Role-Based Access ---

@mcp.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("viewer", "editor", "admin")
async def view_content(auth: AuthContext, content_id: str) -> dict[str, Any]:
    """
    View content.

    Requires: viewer, editor, or admin role

    Args:
        auth: Authentication context (injected)
        content_id: Content ID to view

    Returns:
        Content data
    """
    return {
        "content_id": content_id,
        "title": "Sample Article",
        "body": "This is sample content...",
        "author": "system",
        "viewed_by": auth.username,
    }


@mcp.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("editor", "admin")
async def edit_content(
    auth: AuthContext,
    content_id: str,
    new_content: str,
) -> dict[str, Any]:
    """
    Edit content.

    Requires: editor or admin role

    Args:
        auth: Authentication context (injected)
        content_id: Content ID to edit
        new_content: New content

    Returns:
        Update result
    """
    return {
        "success": True,
        "content_id": content_id,
        "updated_by": auth.username,
        "message": "Content updated successfully",
    }


@mcp.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("admin")
async def manage_users(
    auth: AuthContext,
    action: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Manage user accounts.

    Requires: admin role

    Args:
        auth: Authentication context (injected)
        action: Action to perform (create, delete, modify)
        user_id: Target user ID

    Returns:
        Action result
    """
    return {
        "success": True,
        "action": action,
        "target_user": user_id,
        "performed_by": auth.username,
        "message": f"User {action} completed",
    }


# --- Permission-Based Access ---

@mcp.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("write:posts")
async def create_post(
    auth: AuthContext,
    title: str,
    content: str,
) -> dict[str, Any]:
    """
    Create a new post.

    Requires: write:posts permission

    Args:
        auth: Authentication context (injected)
        title: Post title
        content: Post content

    Returns:
        Created post
    """
    return {
        "success": True,
        "post_id": "post123",
        "title": title,
        "author": auth.username,
        "message": "Post created successfully",
    }


# --- Manifest-Based Access ---

@mcp.tool()
@requires_auth_async(provider=api_key_provider)
@requires_manifest_async(manifest=manifest)
async def dangerous_operation(
    auth: AuthContext,
    confirmation: str,
) -> dict[str, Any]:
    """
    Perform dangerous admin operation.

    Requires: admin role + admin:all permission + admin:full scope
    (enforced by manifest, marked as dangerous)

    Args:
        auth: Authentication context (injected)
        confirmation: Confirmation string

    Returns:
        Operation result
    """
    if confirmation != "I CONFIRM":
        return {"success": False, "error": "Invalid confirmation"}

    return {
        "success": True,
        "performed_by": auth.username,
        "warning": "Dangerous operation completed",
    }


# --- OAuth Scope-Based Access (if using GitHub OAuth) ---

# Note: This would use github_oauth provider instead of api_key_provider
# Shown as example - would need actual OAuth flow to use

@mcp.tool()
async def example_github_tool_info() -> dict[str, str]:
    """
    Example info about GitHub OAuth tool.

    This demonstrates how to use GitHub OAuth.

    Returns:
        Example information
    """
    return {
        "note": "To use GitHub OAuth tools:",
        "step1": "Call get_github_auth_url() to get authorization URL",
        "step2": "User authorizes at that URL",
        "step3": "Exchange code for access token",
        "step4": "Use access token in auth parameter",
        "example_tool": "list_user_repos (requires repo scope)",
    }


# ========================================================================
# 5. ERROR HANDLING DEMONSTRATION
# ========================================================================

async def demonstrate_errors():
    """Demonstrate specialized error handling."""
    print("\n" + "=" * 60)
    print("ERROR HANDLING DEMONSTRATION")
    print("=" * 60 + "\n")

    # 1. OAuthRequiredError
    print("1. OAuthRequiredError - when OAuth is needed:")
    try:
        raise OAuthRequiredError(
            "GitHub OAuth required for this operation",
            provider="github",
            scopes=["repo"],
            authorization_url=github_oauth.generate_authorization_url()["url"],
        )
    except OAuthRequiredError as e:
        print(f"   Error: {e}")
        print(f"   Provider: {e.provider}")
        print(f"   Required scopes: {e.scopes}")
        print(f"   Auth URL: {e.authorization_url[:50]}...")
        print()

    # 2. ScopeInsufficientError
    print("2. ScopeInsufficientError - when user lacks scopes:")
    try:
        raise ScopeInsufficientError(
            "Insufficient OAuth scopes",
            required_scopes=["repo:write"],
            current_scopes=["repo:read"],
            user_id="user123",
        )
    except ScopeInsufficientError as e:
        print(f"   Error: {e}")
        print(f"   Required: {e.required_scopes}")
        print(f"   Current: {e.current_scopes}")
        print(f"   User: {e.user_id}")
        print()

    # 3. ManifestViolationError
    print("3. ManifestViolationError - when manifest check fails:")
    try:
        raise ManifestViolationError(
            "Access denied by manifest",
            tool_name="dangerous_operation",
            required_roles=["admin"],
            required_permissions=["admin:all"],
            required_scopes=["admin:full"],
            user_id="user123",
        )
    except ManifestViolationError as e:
        print(f"   Error: {e}")
        print(f"   Tool: {e.tool_name}")
        print(f"   Required roles: {e.required_roles}")
        print(f"   Required permissions: {e.required_permissions}")
        print(f"   Required scopes: {e.required_scopes}")
        print()


# ========================================================================
# 6. COMPREHENSIVE DEMONSTRATION
# ========================================================================

async def demonstrate_all_features():
    """Demonstrate all auth features."""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE AUTH DEMONSTRATION")
    print("=" * 60 + "\n")

    # Test 1: Public access
    print("Test 1: Public access (no auth required)")
    result = await get_public_info()
    print(f"✓ {result['service']}\n")

    # Test 2: Basic auth
    print("Test 2: Basic auth (API key)")
    result = await get_my_profile(auth={"api_key": "viewer_key_789"})
    print(f"✓ Authenticated as {result['username']}")
    print(f"  Roles: {', '.join(result['roles'])}\n")

    # Test 3: Role-based access (allowed)
    print("Test 3: Role-based access - viewer viewing content (allowed)")
    try:
        result = await view_content(
            auth={"api_key": "viewer_key_789"},
            content_id="article1",
        )
        print(f"✓ {result['viewed_by']} viewed content\n")
    except Exception as e:
        print(f"✗ {e}\n")

    # Test 4: Role-based access (denied)
    print("Test 4: Role-based access - viewer editing content (denied)")
    try:
        result = await edit_content(
            auth={"api_key": "viewer_key_789"},
            content_id="article1",
            new_content="Updated",
        )
        print(f"✓ Unexpected success\n")
    except Exception as e:
        print(f"✓ Correctly denied: Permission denied\n")

    # Test 5: Editor can edit
    print("Test 5: Role-based access - editor editing content (allowed)")
    try:
        result = await edit_content(
            auth={"api_key": "editor_key_456"},
            content_id="article1",
            new_content="Updated content",
        )
        print(f"✓ {result['updated_by']} edited content\n")
    except Exception as e:
        print(f"✗ {e}\n")

    # Test 6: Admin access
    print("Test 6: Admin-only access - managing users (allowed)")
    try:
        result = await manage_users(
            auth={"api_key": "admin_key_123"},
            action="create",
            user_id="newuser1",
        )
        print(f"✓ {result['performed_by']} managed users\n")
    except Exception as e:
        print(f"✗ {e}\n")

    # Test 7: Permission-based access
    print("Test 7: Permission-based access - creating post (allowed)")
    try:
        result = await create_post(
            auth={"api_key": "editor_key_456"},
            title="New Post",
            content="Post content",
        )
        print(f"✓ {result['author']} created post\n")
    except Exception as e:
        print(f"✗ {e}\n")

    # Error handling demonstration
    await demonstrate_errors()

    # Summary
    print("=" * 60)
    print("FEATURE SUMMARY")
    print("=" * 60)
    print(f"Auth Providers: API Key, GitHub OAuth")
    print(f"Roles: {', '.join(r.name for r in rbac.list_roles())}")
    print(f"Protected Tools: {len(manifest.tools)}")
    print(f"Error Types: 3 specialized exceptions")
    print("=" * 60)


if __name__ == "__main__":
    print("Starting Combined Auth MCP Server...\n")

    # Run comprehensive demonstration
    asyncio.run(demonstrate_all_features())

    print("\n" + "=" * 60)
    print("KEY FEATURES DEMONSTRATED")
    print("=" * 60)
    print("1. Multiple Auth Providers (API Key, OAuth)")
    print("2. Role-Based Access Control (RBAC)")
    print("3. Fine-Grained Permissions")
    print("4. OAuth Scopes")
    print("5. Permission Manifests")
    print("6. Specialized Error Types")
    print("7. Declarative Security")
    print("8. Middleware Decorators")
    print("=" * 60)
