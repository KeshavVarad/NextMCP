"""
OAuth 2.0 authentication providers for NextMCP.

Implements OAuth 2.0 Authorization Code Flow with PKCE support.
"""

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from nextmcp.auth.core import AuthContext, AuthProvider, AuthResult, Permission


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""

    client_id: str
    client_secret: str | None = None  # Optional for PKCE
    authorization_url: str = ""
    token_url: str = ""
    redirect_uri: str = "http://localhost:8080/oauth/callback"
    scope: list[str] = field(default_factory=list)  # OAuth scopes to request


@dataclass
class PKCEChallenge:
    """PKCE challenge data for OAuth 2.0."""

    verifier: str
    challenge: str
    method: str = "S256"

    @classmethod
    def generate(cls) -> "PKCEChallenge":
        """
        Generate a new PKCE challenge.

        Returns:
            PKCEChallenge with verifier and challenge
        """
        # Generate cryptographically secure verifier (43-128 characters)
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

        # Create SHA256 challenge
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        return cls(verifier=verifier, challenge=challenge, method="S256")


class OAuthProvider(AuthProvider, ABC):
    """
    Base OAuth 2.0 provider with PKCE support.

    Implements Authorization Code Flow with optional PKCE.
    Subclasses implement provider-specific details.
    """

    def __init__(self, config: OAuthConfig, **kwargs: Any):
        """
        Initialize OAuth provider.

        Args:
            config: OAuth configuration
            **kwargs: Additional provider configuration
        """
        super().__init__(**kwargs)
        self.config = config
        self._pending_auth: dict[str, PKCEChallenge] = {}  # state -> PKCE

    def generate_authorization_url(self, state: str | None = None) -> dict[str, str]:
        """
        Generate OAuth authorization URL with PKCE.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Dict with 'url', 'state', and 'verifier' (store securely!)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        # Generate PKCE challenge
        pkce = PKCEChallenge.generate()
        self._pending_auth[state] = pkce

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "state": state,
            "code_challenge": pkce.challenge,
            "code_challenge_method": pkce.method,
        }

        if self.config.scope:
            params["scope"] = " ".join(self.config.scope)

        # Add provider-specific parameters
        params.update(self.get_additional_auth_params())

        # Properly encode URL parameters
        from urllib.parse import urlencode

        query_string = urlencode(params)
        url = f"{self.config.authorization_url}?{query_string}"

        return {
            "url": url,
            "state": state,
            "verifier": pkce.verifier,  # Client must store this!
        }

    async def exchange_code_for_token(
        self, code: str, state: str, verifier: str | None = None
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            state: State parameter for CSRF protection
            verifier: PKCE verifier (if not stored in provider)

        Returns:
            Token response with access_token, refresh_token, etc.

        Raises:
            ValueError: If state is invalid or token exchange fails
        """
        import aiohttp

        # Get PKCE verifier
        if verifier is None:
            pkce = self._pending_auth.pop(state, None)
            if not pkce:
                raise ValueError("Invalid state or expired authorization")
            verifier = pkce.verifier

        # Build token request
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "code_verifier": verifier,
        }

        # Add client secret if provided (confidential clients)
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(self.config.token_url, data=data) as resp:
                if resp.status != 200:
                    # Try to get error details
                    try:
                        error_data = await resp.json()
                    except Exception:
                        error_data = await resp.text()
                    raise ValueError(f"Token exchange failed: {error_data}")

                # GitHub returns form-encoded, Google returns JSON
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await resp.json()
                else:
                    # Parse form-encoded response (GitHub uses this)
                    from urllib.parse import parse_qs

                    text = await resp.text()
                    parsed = parse_qs(text)
                    # Convert lists to single values where appropriate
                    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token response

        Raises:
            ValueError: If token refresh fails
        """
        import aiohttp

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
        }

        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(self.config.token_url, data=data) as resp:
                if resp.status != 200:
                    # Try to get error details
                    try:
                        error_data = await resp.json()
                    except Exception:
                        error_data = await resp.text()
                    raise ValueError(f"Token refresh failed: {error_data}")

                # GitHub returns form-encoded, Google returns JSON
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await resp.json()
                else:
                    # Parse form-encoded response (GitHub uses this)
                    from urllib.parse import parse_qs

                    text = await resp.text()
                    parsed = parse_qs(text)
                    # Convert lists to single values where appropriate
                    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from OAuth provider.

        Args:
            access_token: OAuth access token

        Returns:
            User information dictionary

        Raises:
            ValueError: If user info retrieval fails
        """
        pass

    @abstractmethod
    def get_additional_auth_params(self) -> dict[str, str]:
        """
        Get provider-specific authorization parameters.

        Returns:
            Dictionary of additional parameters to add to auth URL
        """
        return {}

    async def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        """
        Authenticate using OAuth access token.

        Expected credentials:
        {
            "access_token": "oauth_access_token",
            "refresh_token": "oauth_refresh_token",  # optional
            "scopes": ["scope1", "scope2"]  # optional
        }

        Args:
            credentials: Authentication credentials

        Returns:
            AuthResult with success status and auth context
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return AuthResult.failure("Missing access_token")

        try:
            # Get user info from OAuth provider
            user_info = await self.get_user_info(access_token)

            # Build auth context
            context = AuthContext(
                authenticated=True,
                user_id=self.extract_user_id(user_info),
                username=self.extract_username(user_info),
                metadata={
                    "oauth_provider": self.name,
                    "access_token": access_token,
                    "refresh_token": credentials.get("refresh_token"),
                    "user_info": user_info,
                },
            )

            # Add OAuth scopes as both scopes and permissions
            # This maintains backward compatibility while enabling scope-specific features
            for scope in credentials.get("scopes", []):
                context.add_scope(scope)  # Add as OAuth scope
                context.add_permission(
                    Permission(scope)
                )  # Also add as permission for backward compat

            return AuthResult.success_result(context)

        except Exception as e:
            return AuthResult.failure(f"OAuth authentication failed: {e}")

    @abstractmethod
    def extract_user_id(self, user_info: dict[str, Any]) -> str:
        """
        Extract user ID from provider's user info.

        Args:
            user_info: User information from OAuth provider

        Returns:
            User ID string
        """
        pass

    def extract_username(self, user_info: dict[str, Any]) -> str | None:
        """
        Extract username from provider's user info.

        Args:
            user_info: User information from OAuth provider

        Returns:
            Username string or None
        """
        return user_info.get("login") or user_info.get("email")
