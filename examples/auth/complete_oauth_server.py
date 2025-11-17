"""
Complete OAuth Server Example

This example demonstrates a production-ready MCP server with:
- Google OAuth authentication
- Session management with file storage
- Automatic token refresh
- Auth metadata exposure
- Protected and public tools
- Comprehensive error handling

Run this server:
    python examples/auth/complete_oauth_server.py

Then use examples/auth/oauth_token_helper.py to get tokens and test.
"""

import asyncio
import os
from pathlib import Path

from fastmcp import FastMCP

from nextmcp.auth import (
    GoogleOAuthProvider,
    create_auth_middleware,
)
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
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-client-id")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "your-client-secret")

# Session storage directory
SESSION_DIR = Path(".nextmcp_sessions")


# ============================================================================
# Initialize Server
# ============================================================================

mcp = FastMCP("Complete OAuth Server")


# ============================================================================
# Set Up OAuth Provider
# ============================================================================

google = GoogleOAuthProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri="http://localhost:8080/oauth/callback",
    scope=["openid", "email", "profile", "https://www.googleapis.com/auth/drive.readonly"],
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
    session_management="server-side",
)

# Add Google OAuth provider
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

# Add required scopes
auth_metadata.add_required_scope("openid")
auth_metadata.add_required_scope("email")

# Add optional scopes
auth_metadata.add_optional_scope("profile")
auth_metadata.add_optional_scope("https://www.googleapis.com/auth/drive.readonly")

# Add error code documentation
auth_metadata.error_codes = {
    "authentication_required": "You must be authenticated to access this server",
    "authorization_denied": "You lack the required permissions to access this resource",
    "token_expired": "Your access token has expired - please refresh or re-authenticate",
    "insufficient_scopes": "Additional OAuth scopes are required for this operation",
}


# ============================================================================
# Apply Auth Middleware
# ============================================================================

auth_middleware = create_auth_middleware(
    provider=google,
    requirement=AuthRequirement.REQUIRED,
    session_store=session_store,
    required_scopes=["openid", "email"],
)

mcp.use(auth_middleware)


# ============================================================================
# Public Tools (No special auth needed - middleware handles it)
# ============================================================================


@mcp.tool()
def get_auth_metadata() -> dict:
    """
    Get server authentication requirements.

    This tool returns information about what authentication is required,
    which OAuth providers are supported, and what permissions are needed.

    Returns:
        dict: Complete authentication metadata
    """
    return auth_metadata.to_dict()


@mcp.tool()
def get_server_info() -> dict:
    """
    Get server information.

    Returns basic information about this MCP server.

    Returns:
        dict: Server name, version, and capabilities
    """
    return {
        "name": "Complete OAuth Server",
        "version": "1.0.0",
        "auth_enabled": True,
        "session_storage": "file",
        "features": [
            "OAuth 2.0 with PKCE",
            "Session management",
            "Token refresh",
            "Multi-user support",
        ],
    }


# ============================================================================
# Protected Tools (Require authentication)
# ============================================================================


@mcp.tool()
def get_user_profile() -> dict:
    """
    Get authenticated user's profile.

    Returns information about the currently authenticated user from their
    OAuth provider profile.

    Returns:
        dict: User's email, name, and other profile information
    """
    # Note: In a real implementation, you would access the auth context
    # from the request to get user info. For now, this is a placeholder.
    return {
        "message": "This would return the authenticated user's profile",
        "note": "Access auth context via request['_auth_context']",
    }


@mcp.tool()
def list_user_files() -> dict:
    """
    List user's Google Drive files.

    Lists files from the authenticated user's Google Drive using their
    OAuth access token.

    Returns:
        dict: List of files with names and IDs

    Raises:
        AuthorizationError: If user hasn't granted drive.readonly scope
    """
    return {
        "message": "This would list files from user's Google Drive",
        "required_scope": "https://www.googleapis.com/auth/drive.readonly",
        "note": "Actual implementation would use access_token to call Drive API",
    }


@mcp.tool()
def create_personalized_content(topic: str) -> str:
    """
    Create personalized content for the authenticated user.

    Generates content tailored to the authenticated user based on their
    profile and the requested topic.

    Args:
        topic: The topic to generate content about

    Returns:
        str: Personalized content

    Example:
        >>> create_personalized_content("machine learning")
        "Hello John! Here's ML content personalized for you..."
    """
    return f"Creating personalized content about {topic} for authenticated user..."


# ============================================================================
# Session Management Tools
# ============================================================================


@mcp.tool()
def get_active_sessions() -> dict:
    """
    Get list of active user sessions.

    Returns information about all currently active sessions stored on
    the server.

    Returns:
        dict: Number of active sessions and their user IDs
    """
    users = session_store.list_users()

    return {
        "active_sessions": len(users),
        "users": users,
        "storage_type": "file",
        "storage_location": str(SESSION_DIR.absolute()),
    }


@mcp.tool()
def cleanup_expired_sessions() -> dict:
    """
    Clean up expired sessions.

    Removes all sessions with expired access tokens from storage.

    Returns:
        dict: Number of sessions cleaned up
    """
    cleaned = session_store.cleanup_expired()

    return {
        "cleaned_sessions": cleaned,
        "message": f"Removed {cleaned} expired session(s)",
    }


# ============================================================================
# Utility Functions
# ============================================================================


def print_startup_message():
    """Print helpful startup information."""
    print("\n" + "=" * 70)
    print("🚀 Complete OAuth Server Started")
    print("=" * 70)
    print("\nConfiguration:")
    print(f"  OAuth Provider: Google")
    print(f"  Client ID: {GOOGLE_CLIENT_ID}")
    print(f"  Session Storage: {SESSION_DIR.absolute()}")
    print(f"  Auth Required: Yes")
    print(f"  Token Refresh: Enabled")
    print("\nAvailable Tools:")
    print("  📋 Public:")
    print("     - get_auth_metadata: Get auth requirements")
    print("     - get_server_info: Get server information")
    print("\n  🔐 Protected (requires authentication):")
    print("     - get_user_profile: Get user's profile")
    print("     - list_user_files: List Google Drive files")
    print("     - create_personalized_content: Generate personalized content")
    print("     - get_active_sessions: View active sessions")
    print("     - cleanup_expired_sessions: Remove expired sessions")
    print("\nTo get OAuth tokens:")
    print(f"  1. Set environment variables:")
    print(f"     export GOOGLE_CLIENT_ID='{GOOGLE_CLIENT_ID}'")
    print(f"     export GOOGLE_CLIENT_SECRET='{GOOGLE_CLIENT_SECRET}'")
    print("\n  2. Run token helper:")
    print("     python examples/auth/oauth_token_helper.py --provider google")
    print("\n  3. Test authenticated requests:")
    print("     Use the access token from step 2 in your MCP client")
    print("\n" + "=" * 70 + "\n")


async def periodic_cleanup():
    """Periodically clean up expired sessions."""
    while True:
        await asyncio.sleep(3600)  # Every hour
        cleaned = session_store.cleanup_expired()
        if cleaned > 0:
            print(f"[Cleanup] Removed {cleaned} expired session(s)")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Run the server."""
    # Print startup information
    print_startup_message()

    # Ensure session directory exists
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    # Start periodic cleanup task
    # asyncio.create_task(periodic_cleanup())

    # Run server
    mcp.run()


if __name__ == "__main__":
    main()
