"""
Google OAuth MCP Server Example.

This example demonstrates how to build an MCP server with Google OAuth authentication.
Users authenticate via Google OAuth 2.0 and can access tools based on their OAuth scopes.

Features demonstrated:
- Google OAuth 2.0 with PKCE
- Offline access (refresh tokens)
- Scope-based access control
- Google Drive file access
- Gmail integration

Setup:
1. Create a Google Cloud Project at https://console.cloud.google.com
2. Enable Google Drive API and Gmail API
3. Create OAuth 2.0 credentials (Web application)
4. Add authorized redirect URI: http://localhost:8080/oauth/callback
5. Download credentials and set environment variables:
   export GOOGLE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
   export GOOGLE_CLIENT_SECRET="your_client_secret"

Usage:
   python examples/auth/google_oauth_server.py
"""

import asyncio
import os
from typing import Any

from nextmcp import NextMCP
from nextmcp.auth import (
    AuthContext,
    GoogleOAuthProvider,
    requires_auth_async,
    requires_scope_async,
)

# Initialize MCP server
mcp = NextMCP("Google OAuth Example")

# Configure Google OAuth provider
google_oauth = GoogleOAuthProvider(
    client_id=os.getenv("GOOGLE_CLIENT_ID", "your_google_client_id"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_google_client_secret"),
    redirect_uri="http://localhost:8080/oauth/callback",
    scope=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",
    ],
)


@mcp.tool()
async def get_authorization_url(state: str | None = None) -> dict[str, str]:
    """
    Get Google OAuth authorization URL.

    This tool generates the URL users should visit to authorize the app.
    Requests offline access for refresh tokens.

    Args:
        state: Optional state parameter for CSRF protection

    Returns:
        Dict with 'url', 'state', and 'verifier' (store verifier securely!)

    Example:
        result = await get_authorization_url()
        # Send user to result['url']
        # Store result['verifier'] for token exchange
    """
    return google_oauth.generate_authorization_url(state=state)


@mcp.tool()
@requires_auth_async(provider=google_oauth)
async def get_my_profile(auth: AuthContext) -> dict[str, Any]:
    """
    Get the authenticated user's Google profile.

    Requires OAuth authentication with profile and email scopes.

    Args:
        auth: Authentication context (injected by middleware)

    Returns:
        User profile information from Google

    Example:
        profile = await get_my_profile(auth={
            "access_token": "ya29...",
            "scopes": [
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email"
            ]
        })
    """
    user_info = auth.metadata.get("user_info", {})

    return {
        "user_id": auth.user_id,
        "email": auth.username,  # GoogleOAuthProvider uses email as username
        "name": user_info.get("name"),
        "given_name": user_info.get("given_name"),
        "family_name": user_info.get("family_name"),
        "picture": user_info.get("picture"),
        "locale": user_info.get("locale"),
        "scopes": list(auth.scopes),
    }


@mcp.tool()
@requires_auth_async(provider=google_oauth)
@requires_scope_async("https://www.googleapis.com/auth/drive.readonly")
async def list_drive_files(
    auth: AuthContext,
    page_size: int = 10,
    query: str | None = None,
) -> dict[str, Any]:
    """
    List files in user's Google Drive.

    Requires OAuth authentication with Drive read scope.

    Args:
        auth: Authentication context (injected by middleware)
        page_size: Number of files to return (max 100)
        query: Optional search query (e.g., "name contains 'report'")

    Returns:
        List of Drive files

    Example:
        files = await list_drive_files(
            auth={
                "access_token": "ya29...",
                "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
            },
            page_size=10,
            query="mimeType='application/pdf'"
        )
    """
    import aiohttp

    access_token = auth.metadata.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    params = {
        "pageSize": min(page_size, 100),
        "fields": "files(id,name,mimeType,createdTime,modifiedTime,size,webViewLink)",
    }

    if query:
        params["q"] = query

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params=params,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                files = data.get("files", [])
                return {
                    "count": len(files),
                    "files": [
                        {
                            "id": file["id"],
                            "name": file["name"],
                            "type": file["mimeType"],
                            "created": file.get("createdTime"),
                            "modified": file.get("modifiedTime"),
                            "size": file.get("size"),
                            "link": file.get("webViewLink"),
                        }
                        for file in files
                    ],
                }
            else:
                error_data = await resp.json()
                return {"error": f"Google Drive API error: {error_data}"}


@mcp.tool()
@requires_auth_async(provider=google_oauth)
@requires_scope_async("https://www.googleapis.com/auth/gmail.readonly")
async def list_gmail_messages(
    auth: AuthContext,
    max_results: int = 10,
    query: str | None = None,
) -> dict[str, Any]:
    """
    List messages in user's Gmail inbox.

    Requires OAuth authentication with Gmail read scope.

    Args:
        auth: Authentication context (injected by middleware)
        max_results: Number of messages to return
        query: Optional Gmail search query (e.g., "is:unread")

    Returns:
        List of Gmail messages

    Example:
        messages = await list_gmail_messages(
            auth={
                "access_token": "ya29...",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
            },
            max_results=5,
            query="is:unread"
        )
    """
    import aiohttp

    access_token = auth.metadata.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    params = {
        "maxResults": max_results,
    }

    if query:
        params["q"] = query

    async with aiohttp.ClientSession() as session:
        # Get message list
        async with session.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params=params,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                messages = data.get("messages", [])

                # Get details for each message
                detailed_messages = []
                for msg in messages:
                    async with session.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                        headers=headers,
                        params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                    ) as detail_resp:
                        if detail_resp.status == 200:
                            detail = await detail_resp.json()
                            headers_dict = {
                                h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])
                            }
                            detailed_messages.append({
                                "id": detail["id"],
                                "from": headers_dict.get("From", "Unknown"),
                                "subject": headers_dict.get("Subject", "No Subject"),
                                "date": headers_dict.get("Date", "Unknown"),
                                "snippet": detail.get("snippet", ""),
                            })

                return {
                    "count": len(detailed_messages),
                    "messages": detailed_messages,
                }
            else:
                error_data = await resp.json()
                return {"error": f"Gmail API error: {error_data}"}


@mcp.tool()
@requires_auth_async(provider=google_oauth)
async def refresh_access_token(
    auth: AuthContext,
    refresh_token: str,
) -> dict[str, Any]:
    """
    Refresh an expired access token.

    Uses a refresh token to obtain a new access token.
    Google OAuth provides refresh tokens with offline access.

    Args:
        auth: Authentication context (injected by middleware)
        refresh_token: The refresh token from initial OAuth flow

    Returns:
        New access token and expiration info

    Example:
        new_token = await refresh_access_token(
            auth={
                "access_token": "old_token",  # Can be expired
                "scopes": [...]
            },
            refresh_token="1//..."
        )
    """
    try:
        token_data = await google_oauth.refresh_access_token(refresh_token)
        return {
            "success": True,
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope"),
            "token_type": token_data.get("token_type"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# OAuth Flow Example
async def example_oauth_flow():
    """
    Example of complete OAuth flow with Google.

    Demonstrates OAuth 2.0 authorization code flow with PKCE and refresh tokens.
    """
    print("=== Google OAuth Flow Example ===\n")

    # Step 1: Generate authorization URL
    print("Step 1: Generating authorization URL...")
    auth_data = google_oauth.generate_authorization_url()
    print(f"Authorization URL: {auth_data['url'][:80]}...")
    print(f"State: {auth_data['state']}")
    print(f"PKCE Verifier: {auth_data['verifier'][:20]}...")
    print("\nUser should visit this URL and authorize the app.")
    print("Note: URL includes access_type=offline for refresh tokens\n")

    # Step 2: After user authorizes, you receive a code
    print("Step 2: User authorizes and you receive authorization code...")
    print("(In real app, this comes from OAuth callback)\n")

    # Step 3: Exchange code for tokens
    print("Step 3: Exchanging code for access and refresh tokens...")
    print("(Skipping actual exchange - requires real authorization code)")
    print("Token data would contain:")
    print("  - access_token: For immediate API access")
    print("  - refresh_token: For getting new access tokens")
    print("  - expires_in: Token lifetime (typically 3600 seconds)")
    print("  - scope: Granted scopes\n")

    # Step 4: Using tokens
    print("Step 4: Using tokens...")
    print("Access token is used for API calls:")
    print('  files = await list_drive_files(auth={')
    print('      "access_token": "ya29...",')
    print('      "scopes": ["https://www.googleapis.com/auth/drive.readonly"]')
    print('  })\n')

    print("When access token expires, use refresh token:")
    print('  new_token = await refresh_access_token(')
    print('      auth={"access_token": "old_token", "scopes": [...]},')
    print('      refresh_token="1//..."')
    print('  )\n')


if __name__ == "__main__":
    # Run the server
    print("Starting Google OAuth MCP Server...")
    print("\nAvailable tools:")
    print("  - get_authorization_url(): Get OAuth URL")
    print("  - get_my_profile(): Get authenticated user's profile")
    print("  - list_drive_files(): List Google Drive files")
    print("  - list_gmail_messages(): List Gmail messages")
    print("  - refresh_access_token(): Refresh expired tokens")
    print("\nRunning OAuth flow example...\n")

    # Show OAuth flow example
    asyncio.run(example_oauth_flow())

    print("\n" + "=" * 60)
    print("To use this server with MCP:")
    print("1. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars")
    print("2. Enable Google Drive and Gmail APIs in Google Cloud Console")
    print("3. Run: mcp run examples/auth/google_oauth_server.py")
    print("4. Call get_authorization_url() to get OAuth URL")
    print("5. Have user authorize at that URL")
    print("6. Exchange code for tokens (handle OAuth callback)")
    print("7. Use access token in subsequent tool calls")
    print("8. Use refresh token when access token expires")
    print("=" * 60)
