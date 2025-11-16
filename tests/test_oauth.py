"""
Tests for OAuth 2.0 authentication providers.

Tests for PKCE, OAuth base provider, and specific OAuth providers (GitHub, Google).
"""

import base64
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nextmcp.auth.oauth import OAuthConfig, OAuthProvider, PKCEChallenge
from nextmcp.auth.oauth_providers import GitHubOAuthProvider, GoogleOAuthProvider


def create_mock_aiohttp_response(status: int, json_data: dict | None = None, text_data: str = ""):
    """Helper to create a properly mocked aiohttp response."""
    mock_response = AsyncMock()
    mock_response.status = status
    if json_data is not None:
        mock_response.json = AsyncMock(return_value=json_data)
    if text_data:
        mock_response.text = AsyncMock(return_value=text_data)
    mock_response.__aenter__.return_value = mock_response
    # __aexit__ must return False/None to not suppress exceptions
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


def create_mock_aiohttp_session(**responses):
    """
    Helper to create a properly mocked aiohttp ClientSession.

    Args:
        **responses: Keyword arguments where key is method name ('get', 'post')
                    and value is the mock response
    """
    mock_session = MagicMock()

    for method, response in responses.items():
        # Create a method that returns the response (which is already an async context manager)
        method_mock = MagicMock(return_value=response)
        setattr(mock_session, method, method_mock)

    return mock_session


class TestPKCEChallenge:
    """Tests for PKCE challenge generation."""

    def test_pkce_generation(self):
        """Test PKCE challenge is generated correctly."""
        challenge = PKCEChallenge.generate()

        assert isinstance(challenge.verifier, str)
        assert isinstance(challenge.challenge, str)
        assert challenge.method == "S256"

        # Verifier should be 43+ characters (base64url encoded 32 bytes)
        assert len(challenge.verifier) >= 43

        # Challenge should be 43+ characters (base64url encoded SHA256 hash)
        assert len(challenge.challenge) >= 43

    def test_pkce_verifier_uniqueness(self):
        """Test that each PKCE generation produces unique verifiers."""
        challenge1 = PKCEChallenge.generate()
        challenge2 = PKCEChallenge.generate()

        assert challenge1.verifier != challenge2.verifier
        assert challenge1.challenge != challenge2.challenge

    def test_pkce_challenge_derivation(self):
        """Test that challenge is correctly derived from verifier."""
        challenge = PKCEChallenge.generate()

        # Manually compute challenge from verifier
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(challenge.verifier.encode("utf-8")).digest()
        ).decode("utf-8").rstrip("=")

        assert challenge.challenge == expected_challenge

    def test_pkce_no_padding(self):
        """Test that PKCE values don't contain base64 padding."""
        challenge = PKCEChallenge.generate()

        # Base64url encoding should not have padding (=)
        assert "=" not in challenge.verifier
        assert "=" not in challenge.challenge


class TestOAuthConfig:
    """Tests for OAuth configuration."""

    def test_oauth_config_creation(self):
        """Test OAuth configuration creation."""
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_secret",
            authorization_url="https://provider.com/oauth/authorize",
            token_url="https://provider.com/oauth/token",
            redirect_uri="http://localhost:8080/callback",
            scope=["read", "write"],
        )

        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_secret"
        assert config.authorization_url == "https://provider.com/oauth/authorize"
        assert config.token_url == "https://provider.com/oauth/token"
        assert config.redirect_uri == "http://localhost:8080/callback"
        assert config.scope == ["read", "write"]

    def test_oauth_config_optional_secret(self):
        """Test OAuth config with optional client secret (for PKCE)."""
        config = OAuthConfig(
            client_id="test_client_id",
            authorization_url="https://provider.com/oauth/authorize",
            token_url="https://provider.com/oauth/token",
        )

        assert config.client_secret is None


class MockOAuthProvider(OAuthProvider):
    """Mock OAuth provider for testing base class."""

    async def get_user_info(self, access_token: str):
        """Mock user info retrieval."""
        return {
            "id": "12345",
            "login": "testuser",
            "email": "test@example.com",
        }

    def get_additional_auth_params(self):
        """Mock additional auth params."""
        return {"extra_param": "value"}

    def extract_user_id(self, user_info):
        """Extract user ID from user info."""
        return str(user_info["id"])


class TestOAuthProvider:
    """Tests for OAuth base provider."""

    def test_provider_initialization(self):
        """Test OAuth provider initialization."""
        config = OAuthConfig(
            client_id="test_client",
            client_secret="test_secret",
            authorization_url="https://provider.com/oauth/authorize",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)

        assert provider.config == config
        assert provider._pending_auth == {}

    def test_generate_authorization_url(self):
        """Test OAuth authorization URL generation."""
        config = OAuthConfig(
            client_id="test_client",
            authorization_url="https://provider.com/oauth/authorize",
            token_url="https://provider.com/oauth/token",
            redirect_uri="http://localhost:8080/callback",
            scope=["read", "write"],
        )

        provider = MockOAuthProvider(config)
        auth_data = provider.generate_authorization_url()

        # Check returned data
        assert "url" in auth_data
        assert "state" in auth_data
        assert "verifier" in auth_data

        # Check URL contains required parameters
        url = auth_data["url"]
        assert "https://provider.com/oauth/authorize" in url
        assert "client_id=test_client" in url
        # URL encoded redirect_uri
        assert ("redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback" in url or
                "redirect_uri=http://localhost:8080/callback" in url)
        assert "response_type=code" in url
        assert f"state={auth_data['state']}" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        # URL encoded scopes (+ or %20 for spaces)
        assert "scope=read+write" in url or "scope=read%20write" in url

        # Check PKCE is stored
        assert auth_data["state"] in provider._pending_auth

    def test_generate_authorization_url_custom_state(self):
        """Test authorization URL generation with custom state."""
        config = OAuthConfig(
            client_id="test_client",
            authorization_url="https://provider.com/oauth/authorize",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)
        custom_state = "my_custom_state_123"
        auth_data = provider.generate_authorization_url(state=custom_state)

        assert auth_data["state"] == custom_state
        assert custom_state in provider._pending_auth

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self):
        """Test exchanging authorization code for access token."""
        config = OAuthConfig(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://provider.com/oauth/token",
            redirect_uri="http://localhost:8080/callback",
        )

        provider = MockOAuthProvider(config)

        # Generate auth URL to create PKCE
        auth_data = provider.generate_authorization_url()
        state = auth_data["state"]
        verifier = auth_data["verifier"]

        # Mock the HTTP response
        mock_response = {
            "access_token": "mock_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "mock_refresh_token",
            "scope": "read write",
        }

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(200, json_data=mock_response)
            mock_session_inst = create_mock_aiohttp_session(post=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__.return_value = AsyncMock()

            # Exchange code for token
            token_data = await provider.exchange_code_for_token(
                code="auth_code_123", state=state
            )

            assert token_data["access_token"] == "mock_access_token"
            assert token_data["refresh_token"] == "mock_refresh_token"

        # PKCE should be consumed
        assert state not in provider._pending_auth

    @pytest.mark.asyncio
    async def test_exchange_code_with_external_verifier(self):
        """Test token exchange with externally stored verifier."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
            redirect_uri="http://localhost:8080/callback",
        )

        provider = MockOAuthProvider(config)

        # Don't use provider's generate_authorization_url
        # Instead, provide verifier manually
        external_verifier = PKCEChallenge.generate().verifier

        mock_response = {
            "access_token": "mock_access_token",
            "token_type": "Bearer",
        }

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(200, json_data=mock_response)
            mock_session_inst = create_mock_aiohttp_session(post=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__.return_value = AsyncMock()

            # Exchange with external verifier
            token_data = await provider.exchange_code_for_token(
                code="auth_code_123",
                state="external_state",
                verifier=external_verifier,
            )

            assert token_data["access_token"] == "mock_access_token"

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_state(self):
        """Test token exchange with invalid state raises error."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)

        # Try to exchange without generating auth URL first
        with pytest.raises(ValueError, match="Invalid state or expired authorization"):
            await provider.exchange_code_for_token(
                code="auth_code_123", state="invalid_state"
            )

    @pytest.mark.asyncio
    async def test_exchange_code_token_error(self):
        """Test token exchange handles error responses."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)
        auth_data = provider.generate_authorization_url()

        # Mock error response
        mock_error = {"error": "invalid_grant", "error_description": "Code expired"}

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(400, json_data=mock_error)
            mock_session_inst = create_mock_aiohttp_session(post=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValueError, match="Token exchange failed"):
                await provider.exchange_code_for_token(
                    code="invalid_code", state=auth_data["state"]
                )

    @pytest.mark.asyncio
    async def test_refresh_access_token(self):
        """Test refreshing access token."""
        config = OAuthConfig(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)

        mock_response = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(200, json_data=mock_response)
            mock_session_inst = create_mock_aiohttp_session(post=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__.return_value = AsyncMock()

            token_data = await provider.refresh_access_token("old_refresh_token")

            assert token_data["access_token"] == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_token_error(self):
        """Test refresh token handles error responses."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)

        mock_error = {"error": "invalid_grant", "error_description": "Refresh token expired"}

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(400, json_data=mock_error)
            mock_session_inst = create_mock_aiohttp_session(post=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValueError, match="Token refresh failed"):
                await provider.refresh_access_token("invalid_refresh_token")

    @pytest.mark.asyncio
    async def test_authenticate_with_access_token(self):
        """Test authentication using OAuth access token."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)

        credentials = {
            "access_token": "valid_access_token",
            "refresh_token": "valid_refresh_token",
            "scopes": ["read", "write"],
        }

        result = await provider.authenticate(credentials)

        assert result.success is True
        assert result.context is not None
        assert result.context.authenticated is True
        assert result.context.user_id == "12345"
        assert result.context.username == "testuser"

        # OAuth provider should add scopes as permissions
        assert result.context.has_permission("read")
        assert result.context.has_permission("write")

        # Metadata should contain OAuth info
        assert result.context.metadata["oauth_provider"] == "MockOAuthProvider"
        assert result.context.metadata["access_token"] == "valid_access_token"
        assert result.context.metadata["refresh_token"] == "valid_refresh_token"

    @pytest.mark.asyncio
    async def test_authenticate_missing_access_token(self):
        """Test authentication fails without access token."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
        )

        provider = MockOAuthProvider(config)

        result = await provider.authenticate({})

        assert result.success is False
        assert result.error == "Missing access_token"

    @pytest.mark.asyncio
    async def test_authenticate_user_info_error(self):
        """Test authentication fails when user info retrieval fails."""
        config = OAuthConfig(
            client_id="test_client",
            token_url="https://provider.com/oauth/token",
        )

        # Create provider that raises error on get_user_info
        class FailingOAuthProvider(MockOAuthProvider):
            async def get_user_info(self, access_token):
                raise Exception("User info API error")

        provider = FailingOAuthProvider(config)

        result = await provider.authenticate({"access_token": "token"})

        assert result.success is False
        assert "OAuth authentication failed" in result.error


class TestGitHubOAuthProvider:
    """Tests for GitHub OAuth provider."""

    def test_github_provider_initialization(self):
        """Test GitHub provider initialization with default config."""
        provider = GitHubOAuthProvider(
            client_id="github_client_id",
            client_secret="github_secret",
        )

        assert provider.config.client_id == "github_client_id"
        assert provider.config.client_secret == "github_secret"
        assert provider.config.authorization_url == "https://github.com/login/oauth/authorize"
        assert provider.config.token_url == "https://github.com/login/oauth/access_token"
        assert provider.config.scope == ["read:user"]

    def test_github_provider_custom_scope(self):
        """Test GitHub provider with custom scopes."""
        provider = GitHubOAuthProvider(
            client_id="github_client_id", scope=["repo", "user:email"]
        )

        assert provider.config.scope == ["repo", "user:email"]

    @pytest.mark.asyncio
    async def test_github_get_user_info(self):
        """Test GitHub user info retrieval."""
        provider = GitHubOAuthProvider(client_id="test_client")

        mock_user_data = {
            "id": 12345,
            "login": "octocat",
            "email": "octocat@github.com",
            "name": "The Octocat",
        }

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(200, json_data=mock_user_data, text_data="success")
            mock_session_inst = create_mock_aiohttp_session(get=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__.return_value = AsyncMock()

            user_info = await provider.get_user_info("test_access_token")

            assert user_info["id"] == 12345
            assert user_info["login"] == "octocat"

    @pytest.mark.asyncio
    async def test_github_get_user_info_error(self):
        """Test GitHub user info retrieval with error."""
        provider = GitHubOAuthProvider(client_id="test_client")

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(401, text_data="Unauthorized")
            mock_session_inst = create_mock_aiohttp_session(get=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValueError, match="Failed to get user info"):
                await provider.get_user_info("invalid_token")

    def test_github_extract_user_id(self):
        """Test extracting user ID from GitHub user info."""
        provider = GitHubOAuthProvider(client_id="test_client")

        user_info = {"id": 12345, "login": "octocat"}
        user_id = provider.extract_user_id(user_info)

        assert user_id == "12345"

    def test_github_extract_username(self):
        """Test extracting username from GitHub user info."""
        provider = GitHubOAuthProvider(client_id="test_client")

        user_info = {"id": 12345, "login": "octocat"}
        username = provider.extract_username(user_info)

        assert username == "octocat"


class TestGoogleOAuthProvider:
    """Tests for Google OAuth provider."""

    def test_google_provider_initialization(self):
        """Test Google provider initialization with default config."""
        provider = GoogleOAuthProvider(
            client_id="google_client_id",
            client_secret="google_secret",
        )

        assert provider.config.client_id == "google_client_id"
        assert provider.config.client_secret == "google_secret"
        assert provider.config.authorization_url == "https://accounts.google.com/o/oauth2/v2/auth"
        assert provider.config.token_url == "https://oauth2.googleapis.com/token"
        assert provider.config.scope == ["openid", "email", "profile"]

    def test_google_additional_auth_params(self):
        """Test Google-specific auth parameters."""
        provider = GoogleOAuthProvider(
            client_id="google_client_id",
            client_secret="google_secret",
        )

        params = provider.get_additional_auth_params()

        assert params["access_type"] == "offline"
        assert params["prompt"] == "consent"

    @pytest.mark.asyncio
    async def test_google_get_user_info(self):
        """Test Google user info retrieval."""
        provider = GoogleOAuthProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        mock_user_data = {
            "id": "google123",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }

        with patch("aiohttp.ClientSession") as MockSession:
            mock_resp = create_mock_aiohttp_response(200, json_data=mock_user_data, text_data="success")
            mock_session_inst = create_mock_aiohttp_session(get=mock_resp)
            MockSession.return_value.__aenter__.return_value = mock_session_inst
            MockSession.return_value.__aexit__.return_value = AsyncMock()

            user_info = await provider.get_user_info("test_access_token")

            assert user_info["id"] == "google123"
            assert user_info["email"] == "user@gmail.com"

    def test_google_extract_user_id(self):
        """Test extracting user ID from Google user info."""
        provider = GoogleOAuthProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        user_info = {"id": "google123", "email": "user@gmail.com"}
        user_id = provider.extract_user_id(user_info)

        assert user_id == "google123"

    def test_google_extract_username(self):
        """Test extracting username from Google user info."""
        provider = GoogleOAuthProvider(
            client_id="test_client",
            client_secret="test_secret",
        )

        user_info = {"id": "google123", "email": "user@gmail.com"}
        username = provider.extract_username(user_info)

        assert username == "user@gmail.com"
