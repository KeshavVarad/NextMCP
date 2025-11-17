"""
GitHub OAuth MCP Server Example.

This example demonstrates how to build an MCP server with GitHub OAuth authentication.
Users authenticate via GitHub OAuth 2.0 and can access tools based on their OAuth scopes.

Features demonstrated:
- GitHub OAuth 2.0 with PKCE
- Scope-based access control
- User repository access
- Authorization URL generation

Setup:
1. Create a GitHub OAuth App at https://github.com/settings/developers
2. Set redirect URI to: http://localhost:8080/oauth/callback
3. Copy Client ID and Client Secret
4. Set environment variables:
   export GITHUB_CLIENT_ID="your_client_id"
   export GITHUB_CLIENT_SECRET="your_client_secret"  # Optional for PKCE

Usage:
   python examples/auth/github_oauth_server.py
"""

import asyncio
import os
from typing import Any

from nextmcp import NextMCP
from nextmcp.auth import (
    AuthContext,
    GitHubOAuthProvider,
    requires_auth_async,
    requires_scope_async,
)

# Initialize MCP server
mcp = NextMCP("GitHub OAuth Example")

# Configure GitHub OAuth provider
github_oauth = GitHubOAuthProvider(
    client_id=os.getenv("GITHUB_CLIENT_ID", "your_github_client_id"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),  # Optional with PKCE
    redirect_uri="http://localhost:8080/oauth/callback",
    scope=["read:user", "repo"],  # Requested scopes
)


@mcp.tool()
async def get_authorization_url(state: str | None = None) -> dict[str, str]:
    """
    Get GitHub OAuth authorization URL.

    This tool generates the URL users should visit to authorize the app.
    No authentication required to call this tool.

    Args:
        state: Optional state parameter for CSRF protection

    Returns:
        Dict with 'url', 'state', and 'verifier' (store verifier securely!)

    Example:
        result = await get_authorization_url()
        # Send user to result['url']
        # Store result['verifier'] for later token exchange
    """
    return github_oauth.generate_authorization_url(state=state)


@mcp.tool()
@requires_auth_async(provider=github_oauth)
async def get_my_profile(auth: AuthContext) -> dict[str, Any]:
    """
    Get the authenticated user's GitHub profile.

    Requires OAuth authentication with 'read:user' scope.

    Args:
        auth: Authentication context (injected by middleware)

    Returns:
        User profile information from GitHub

    Example:
        # After OAuth flow completes with access token
        profile = await get_my_profile(auth={
            "access_token": "gho_...",
            "scopes": ["read:user", "repo"]
        })
    """
    # Access token is available in auth.metadata
    access_token = auth.metadata.get("access_token")

    # Get user info from GitHub
    user_info = auth.metadata.get("user_info", {})

    return {
        "user_id": auth.user_id,
        "username": auth.username,
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "bio": user_info.get("bio"),
        "company": user_info.get("company"),
        "location": user_info.get("location"),
        "scopes": list(auth.scopes),
    }


@mcp.tool()
@requires_auth_async(provider=github_oauth)
@requires_scope_async("repo")
async def list_my_repositories(
    auth: AuthContext,
    visibility: str = "all",
    sort: str = "updated",
) -> dict[str, Any]:
    """
    List the authenticated user's repositories.

    Requires OAuth authentication with 'repo' scope.

    Args:
        auth: Authentication context (injected by middleware)
        visibility: Repository visibility filter (all, public, private)
        sort: Sort order (created, updated, pushed, full_name)

    Returns:
        List of user's repositories

    Example:
        repos = await list_my_repositories(
            auth={"access_token": "gho_...", "scopes": ["repo"]},
            visibility="public",
            sort="updated"
        )
    """
    import aiohttp

    access_token = auth.metadata.get("access_token")

    # Call GitHub API
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    params = {
        "visibility": visibility,
        "sort": sort,
        "per_page": 10,  # Limit for example
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.github.com/user/repos",
            headers=headers,
            params=params,
        ) as resp:
            if resp.status == 200:
                repos = await resp.json()
                return {
                    "count": len(repos),
                    "repositories": [
                        {
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "description": repo["description"],
                            "private": repo["private"],
                            "url": repo["html_url"],
                            "stars": repo["stargazers_count"],
                            "language": repo["language"],
                            "updated_at": repo["updated_at"],
                        }
                        for repo in repos
                    ],
                }
            else:
                error_data = await resp.json()
                return {"error": f"GitHub API error: {error_data}"}


@mcp.tool()
@requires_auth_async(provider=github_oauth)
@requires_scope_async("repo")
async def create_repository(
    auth: AuthContext,
    name: str,
    description: str = "",
    private: bool = False,
) -> dict[str, Any]:
    """
    Create a new GitHub repository.

    Requires OAuth authentication with 'repo' scope.

    Args:
        auth: Authentication context (injected by middleware)
        name: Repository name
        description: Repository description
        private: Whether repository should be private

    Returns:
        Created repository information

    Example:
        repo = await create_repository(
            auth={"access_token": "gho_...", "scopes": ["repo"]},
            name="my-new-repo",
            description="Created via MCP",
            private=False
        )
    """
    import aiohttp

    access_token = auth.metadata.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    data = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": True,  # Initialize with README
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json=data,
        ) as resp:
            if resp.status == 201:
                repo = await resp.json()
                return {
                    "success": True,
                    "repository": {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "url": repo["html_url"],
                        "clone_url": repo["clone_url"],
                        "private": repo["private"],
                    },
                }
            else:
                error_data = await resp.json()
                return {
                    "success": False,
                    "error": f"Failed to create repository: {error_data}",
                }


# OAuth Flow Example
async def example_oauth_flow():
    """
    Example of complete OAuth flow.

    This demonstrates the full OAuth 2.0 authorization code flow with PKCE.
    """
    print("=== GitHub OAuth Flow Example ===\n")

    # Step 1: Generate authorization URL
    print("Step 1: Generating authorization URL...")
    auth_data = github_oauth.generate_authorization_url()
    print(f"Authorization URL: {auth_data['url']}")
    print(f"State: {auth_data['state']}")
    print(f"PKCE Verifier: {auth_data['verifier'][:20]}...")
    print("\nUser should visit this URL and authorize the app.\n")

    # Step 2: After user authorizes, you receive a code
    # (This is normally done via a web callback)
    print("Step 2: User authorizes and you receive authorization code...")
    print("(In real app, this comes from OAuth callback)\n")

    # Simulating received code
    authorization_code = "simulated_code_from_github"
    state_from_callback = auth_data["state"]
    verifier = auth_data["verifier"]

    # Step 3: Exchange code for access token
    print("Step 3: Exchanging code for access token...")
    try:
        # This would actually exchange the code (requires real code from GitHub)
        # token_data = await github_oauth.exchange_code_for_token(
        #     code=authorization_code,
        #     state=state_from_callback,
        #     verifier=verifier
        # )
        print("(Skipping actual exchange - requires real authorization code)")
        print("Token data would contain: access_token, refresh_token, scope, etc.\n")
    except Exception as e:
        print(f"Note: {e}\n")

    # Step 4: Authenticate with access token
    print("Step 4: Using access token to authenticate...")
    print("(In real app, pass access_token to tool calls as auth credentials)")
    print("\nExample tool call:")
    print('  profile = await get_my_profile(auth={')
    print('      "access_token": "gho_...",')
    print('      "scopes": ["read:user", "repo"]')
    print('  })\n')


if __name__ == "__main__":
    # Run the server
    print("Starting GitHub OAuth MCP Server...")
    print("\nAvailable tools:")
    print("  - get_authorization_url(): Get OAuth URL")
    print("  - get_my_profile(): Get authenticated user's profile")
    print("  - list_my_repositories(): List user's repositories")
    print("  - create_repository(): Create a new repository")
    print("\nRunning OAuth flow example...\n")

    # Show OAuth flow example
    asyncio.run(example_oauth_flow())

    print("\n" + "=" * 60)
    print("To use this server with MCP:")
    print("1. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET env vars")
    print("2. Run: mcp run examples/auth/github_oauth_server.py")
    print("3. Call get_authorization_url() to get OAuth URL")
    print("4. Have user authorize at that URL")
    print("5. Exchange code for token (handle OAuth callback)")
    print("6. Use access token in subsequent tool calls")
    print("=" * 60)
