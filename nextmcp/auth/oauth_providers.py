"""
Ready-to-use OAuth providers for common services.

Provides GitHub and Google OAuth providers with sensible defaults.
"""

from typing import Any

from nextmcp.auth.oauth import OAuthConfig, OAuthProvider


class GitHubOAuthProvider(OAuthProvider):
    """
    GitHub OAuth provider.

    Implements OAuth 2.0 for GitHub with standard scopes.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        redirect_uri: str = "http://localhost:8080/oauth/callback",
        scope: list[str] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize GitHub OAuth provider.

        Args:
            client_id: GitHub OAuth app client ID
            client_secret: GitHub OAuth app client secret (optional for PKCE)
            redirect_uri: OAuth callback URI
            scope: OAuth scopes to request (default: ["read:user"])
            **kwargs: Additional configuration
        """
        config = OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            redirect_uri=redirect_uri,
            scope=scope or ["read:user"],
        )
        super().__init__(config, **kwargs)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get GitHub user information.

        Args:
            access_token: GitHub access token

        Returns:
            User information dictionary

        Raises:
            ValueError: If user info retrieval fails
        """
        import aiohttp

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.github.com/user", headers=headers) as resp:
                if resp.status != 200:
                    raise ValueError(f"Failed to get user info: {await resp.text()}")
                return await resp.json()

    def extract_user_id(self, user_info: dict[str, Any]) -> str:
        """
        Extract GitHub user ID.

        Args:
            user_info: GitHub user information

        Returns:
            User ID as string
        """
        return str(user_info["id"])

    def extract_username(self, user_info: dict[str, Any]) -> str | None:
        """
        Extract GitHub username.

        Args:
            user_info: GitHub user information

        Returns:
            GitHub login username
        """
        return user_info.get("login")

    def get_additional_auth_params(self) -> dict[str, str]:
        """
        GitHub-specific authorization parameters.

        Returns:
            Empty dict (GitHub doesn't need additional params)
        """
        return {}


class GoogleOAuthProvider(OAuthProvider):
    """
    Google OAuth provider.

    Implements OAuth 2.0 for Google with standard scopes.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/oauth/callback",
        scope: list[str] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth app client ID
            client_secret: Google OAuth app client secret
            redirect_uri: OAuth callback URI
            scope: OAuth scopes to request (default: ["openid", "email", "profile"])
            **kwargs: Additional configuration
        """
        config = OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            redirect_uri=redirect_uri,
            scope=scope or ["openid", "email", "profile"],
        )
        super().__init__(config, **kwargs)

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get Google user information.

        Args:
            access_token: Google access token

        Returns:
            User information dictionary

        Raises:
            ValueError: If user info retrieval fails
        """
        import aiohttp

        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/oauth2/v2/userinfo", headers=headers
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Failed to get user info: {await resp.text()}")
                return await resp.json()

    def extract_user_id(self, user_info: dict[str, Any]) -> str:
        """
        Extract Google user ID.

        Args:
            user_info: Google user information

        Returns:
            User ID as string
        """
        return user_info["id"]

    def extract_username(self, user_info: dict[str, Any]) -> str | None:
        """
        Extract Google email as username.

        Args:
            user_info: Google user information

        Returns:
            User's email address
        """
        return user_info.get("email")

    def get_additional_auth_params(self) -> dict[str, str]:
        """
        Google-specific authorization parameters.

        Returns:
            Dict with access_type and prompt parameters for refresh tokens
        """
        return {
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",
        }
