"""
Multi-Provider OAuth Server Example

This example demonstrates an MCP server that supports multiple OAuth providers:
- Google OAuth (for email and Drive access)
- GitHub OAuth (for repository access)

Users can authenticate with either provider, and the server maintains separate
sessions for each provider.

Run this server:
    python examples/auth/multi_provider_server.py

Features:
- Multiple OAuth provider support
- Provider-specific tools
- Cross-provider user identification
- Session management per provider
"""

import os
from pathlib import Path

from fastmcp import FastMCP

from nextmcp.auth import (
    GitHubOAuthProvider,
    GoogleOAuthProvider,
    requires_scope_async,
)
from nextmcp.auth.core import AuthContext
from nextmcp.protocol import (
    AuthFlowType,
    AuthMetadata,
    AuthRequirement,
)
from nextmcp.session import FileSessionStore

# ============================================================================
# Configuration
# ============================================================================

# Get OAuth credentials from environment
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "your-google-client-secret")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "your-github-client-id")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "your-github-client-secret")

# Session storage
SESSION_DIR = Path(".multi_provider_sessions")


# ============================================================================
# Initialize Server
# ============================================================================

mcp = FastMCP("Multi-Provider OAuth Server")


# ============================================================================
# Set Up OAuth Providers
# ============================================================================

google = GoogleOAuthProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri="http://localhost:8080/oauth/callback",
    scope=["openid", "email", "profile", "https://www.googleapis.com/auth/drive.readonly"],
)

github = GitHubOAuthProvider(
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    redirect_uri="http://localhost:8080/oauth/callback",
    scope=["read:user", "repo"],
)


# ============================================================================
# Set Up Session Store
# ============================================================================

session_store = FileSessionStore(SESSION_DIR)


# ============================================================================
# Create Auth Metadata
# ============================================================================

auth_metadata = AuthMetadata(
    requirement=AuthRequirement.REQUIRED,
    supports_multi_user=True,
    token_refresh_enabled=True,
)

# Add Google provider
auth_metadata.add_provider(
    name="google",
    type="oauth2",
    flows=[AuthFlowType.OAUTH2_PKCE],
    authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/drive.readonly"],
    supports_refresh=True,
    supports_pkce=True,
)

# Add GitHub provider
auth_metadata.add_provider(
    name="github",
    type="oauth2",
    flows=[AuthFlowType.OAUTH2_PKCE],
    authorization_url="https://github.com/login/oauth/authorize",
    token_url="https://github.com/login/oauth/access_token",
    scopes=["read:user", "repo"],
    supports_refresh=False,  # GitHub doesn't support refresh tokens
    supports_pkce=True,
)


# ============================================================================
# Public Tools
# ============================================================================


@mcp.tool()
def get_auth_metadata() -> dict:
    """
    Get server authentication requirements.

    Returns information about supported OAuth providers and required scopes.

    Returns:
        dict: Complete authentication metadata including both Google and GitHub
    """
    return auth_metadata.to_dict()


@mcp.tool()
def get_supported_providers() -> dict:
    """
    List supported OAuth providers.

    Returns:
        dict: Information about Google and GitHub OAuth providers
    """
    return {
        "providers": [
            {
                "name": "google",
                "display_name": "Google",
                "features": ["Email", "Drive access", "Profile"],
                "scopes": ["openid", "email", "profile", "drive.readonly"],
                "supports_refresh": True,
            },
            {
                "name": "github",
                "display_name": "GitHub",
                "features": ["Profile", "Repository access"],
                "scopes": ["read:user", "repo"],
                "supports_refresh": False,
            },
        ],
        "notes": [
            "You can authenticate with either provider",
            "Some tools require specific providers",
            "Google supports token refresh, GitHub doesn't",
        ],
    }


# ============================================================================
# Google-Specific Tools
# ============================================================================


@mcp.tool()
async def get_google_profile() -> dict:
    """
    Get user's Google profile.

    Requires Google OAuth authentication.

    Returns:
        dict: User's email, name, and Google-specific info
    """
    # In a real implementation, this would check the auth context
    # to ensure user authenticated with Google
    return {
        "message": "This would return Google profile information",
        "required_provider": "google",
        "required_scopes": ["openid", "email", "profile"],
    }


@mcp.tool()
async def list_google_drive_files() -> dict:
    """
    List files from user's Google Drive.

    Requires Google OAuth with drive.readonly scope.

    Returns:
        dict: List of files from Google Drive
    """
    return {
        "message": "This would list files from Google Drive",
        "required_provider": "google",
        "required_scopes": ["https://www.googleapis.com/auth/drive.readonly"],
    }


# ============================================================================
# GitHub-Specific Tools
# ============================================================================


@mcp.tool()
async def get_github_profile() -> dict:
    """
    Get user's GitHub profile.

    Requires GitHub OAuth authentication.

    Returns:
        dict: User's GitHub username, repos, and profile info
    """
    return {
        "message": "This would return GitHub profile information",
        "required_provider": "github",
        "required_scopes": ["read:user"],
    }


@mcp.tool()
async def list_github_repos(visibility: str = "all") -> dict:
    """
    List user's GitHub repositories.

    Requires GitHub OAuth with repo scope.

    Args:
        visibility: "all", "public", or "private"

    Returns:
        dict: List of repositories
    """
    return {
        "message": f"This would list {visibility} repositories",
        "required_provider": "github",
        "required_scopes": ["repo"],
    }


@mcp.tool()
async def create_github_issue(repo: str, title: str, body: str) -> dict:
    """
    Create an issue on a GitHub repository.

    Requires GitHub OAuth with repo scope.

    Args:
        repo: Repository name (owner/repo)
        title: Issue title
        body: Issue description

    Returns:
        dict: Created issue information
    """
    return {
        "message": f"This would create issue '{title}' on {repo}",
        "required_provider": "github",
        "required_scopes": ["repo"],
    }


# ============================================================================
# Cross-Provider Tools
# ============================================================================


@mcp.tool()
async def get_unified_profile() -> dict:
    """
    Get unified user profile across providers.

    Works with either Google or GitHub authentication.
    Returns provider-specific information based on which provider was used.

    Returns:
        dict: Unified profile information
    """
    # In a real implementation, this would:
    # 1. Check which provider user authenticated with
    # 2. Fetch profile from that provider
    # 3. Return normalized profile data
    return {
        "message": "This would return profile from whichever provider user used",
        "supports": ["google", "github"],
    }


@mcp.tool()
async def link_provider_accounts() -> dict:
    """
    Link Google and GitHub accounts for the same user.

    Allows a user to authenticate with both providers and link their accounts
    for a unified experience.

    Returns:
        dict: Account linking status
    """
    return {
        "message": "This would link Google and GitHub accounts",
        "note": "User would need to authenticate with both providers",
        "benefits": [
            "Access Drive files AND GitHub repos",
            "Unified identity across providers",
            "Seamless cross-service operations",
        ],
    }


# ============================================================================
# Session Management
# ============================================================================


@mcp.tool()
async def get_active_sessions_by_provider() -> dict:
    """
    Get active sessions grouped by OAuth provider.

    Returns:
        dict: Sessions grouped by provider (Google vs GitHub)
    """
    all_sessions = session_store.list_users()

    # In a real implementation, you would:
    # 1. Load each session
    # 2. Check session.provider
    # 3. Group by provider

    return {
        "total_sessions": len(all_sessions),
        "message": "This would group sessions by provider",
        "note": "Session data includes 'provider' field",
    }


# ============================================================================
# Utility Functions
# ============================================================================


def print_startup_message():
    """Print helpful startup information."""
    print("\n" + "=" * 70)
    print("🚀 Multi-Provider OAuth Server Started")
    print("=" * 70)
    print("\nSupported OAuth Providers:")
    print("  🔵 Google OAuth")
    print("     - Scopes: openid, email, profile, drive.readonly")
    print("     - Refresh tokens: Yes")
    print("     - Use for: Email, Drive, Profile")
    print("\n  ⚫ GitHub OAuth")
    print("     - Scopes: read:user, repo")
    print("     - Refresh tokens: No")
    print("     - Use for: Repositories, Issues, Profile")
    print("\nAvailable Tools:")
    print("  📋 Public:")
    print("     - get_auth_metadata")
    print("     - get_supported_providers")
    print("\n  🔵 Google-specific:")
    print("     - get_google_profile")
    print("     - list_google_drive_files")
    print("\n  ⚫ GitHub-specific:")
    print("     - get_github_profile")
    print("     - list_github_repos")
    print("     - create_github_issue")
    print("\n  🔗 Cross-provider:")
    print("     - get_unified_profile")
    print("     - link_provider_accounts")
    print("     - get_active_sessions_by_provider")
    print("\nTo get OAuth tokens:")
    print("  Google:")
    print("    python examples/auth/oauth_token_helper.py --provider google")
    print("\n  GitHub:")
    print("    python examples/auth/oauth_token_helper.py --provider github")
    print("\n" + "=" * 70 + "\n")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Run the server."""
    # Print startup information
    print_startup_message()

    # Ensure session directory exists
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    # Note: In a real implementation, you would:
    # 1. Create separate middleware for each provider
    # 2. Route requests to appropriate provider based on token
    # 3. Or use a single middleware with provider detection

    # For now, this is a demonstration of the concept
    print("Note: This is a demonstration server.")
    print("For actual multi-provider support, you would need:")
    print("  - Provider detection from access token")
    print("  - Separate middleware per provider")
    print("  - Token routing logic")

    # Run server
    mcp.run()


if __name__ == "__main__":
    main()
