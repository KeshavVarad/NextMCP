"""
Tests for authentication providers.

Tests for APIKeyProvider, JWTProvider, and SessionProvider.
"""

import pytest

from nextmcp.auth.providers import APIKeyProvider, JWTProvider, SessionProvider


class TestAPIKeyProvider:
    """Tests for API Key authentication provider."""

    def test_provider_initialization(self):
        """Test basic provider initialization."""
        provider = APIKeyProvider(valid_keys={"test-key": {"user_id": "user1", "roles": ["admin"]}})

        assert provider.valid_keys == {"test-key": {"user_id": "user1", "roles": ["admin"]}}

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful API key authentication."""
        provider = APIKeyProvider(
            valid_keys={
                "test-key-123": {
                    "user_id": "user1",
                    "username": "alice",
                    "roles": ["admin"],
                    "permissions": ["read:posts", "write:posts"],
                }
            }
        )

        result = await provider.authenticate({"api_key": "test-key-123"})

        assert result.success is True
        assert result.context is not None
        assert result.context.authenticated is True
        assert result.context.user_id == "user1"
        assert result.context.username == "alice"
        assert result.context.has_role("admin")
        assert result.context.has_permission("read:posts")
        assert result.context.has_permission("write:posts")

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test authentication with invalid API key."""
        provider = APIKeyProvider(valid_keys={"valid-key": {"user_id": "user1"}})

        result = await provider.authenticate({"api_key": "invalid-key"})

        assert result.success is False
        assert result.error == "Invalid API key"
        assert result.context is None

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test authentication with missing API key."""
        provider = APIKeyProvider(valid_keys={"test-key": {"user_id": "user1"}})

        result = await provider.authenticate({})

        assert result.success is False
        assert result.error == "Missing api_key in credentials"

    @pytest.mark.asyncio
    async def test_custom_validator(self):
        """Test API key provider with custom validator function."""

        def custom_validator(api_key: str):
            if api_key == "custom-key":
                return {"user_id": "custom-user", "roles": ["user"]}
            return None

        provider = APIKeyProvider(key_validator=custom_validator)

        # Valid custom key
        result = await provider.authenticate({"api_key": "custom-key"})
        assert result.success is True
        assert result.context.user_id == "custom-user"

        # Invalid custom key
        result = await provider.authenticate({"api_key": "wrong-key"})
        assert result.success is False

    def test_generate_key(self):
        """Test API key generation."""
        key1 = APIKeyProvider.generate_key()
        key2 = APIKeyProvider.generate_key()

        # Keys should be different
        assert key1 != key2

        # Default length is 32 bytes = 64 hex chars
        assert len(key1) == 64
        assert len(key2) == 64

        # Custom length
        key3 = APIKeyProvider.generate_key(length=16)
        assert len(key3) == 32  # 16 bytes = 32 hex chars

    def test_validate_credentials(self):
        """Test credentials validation."""
        provider = APIKeyProvider()

        assert provider.validate_credentials({"api_key": "test"}) is True
        assert provider.validate_credentials({}) is False
        assert provider.validate_credentials({"other": "value"}) is False


class TestJWTProvider:
    """Tests for JWT authentication provider."""

    def test_provider_initialization(self):
        """Test JWT provider initialization."""
        provider = JWTProvider(secret_key="test-secret")

        assert provider.secret_key == "test-secret"
        assert provider.algorithm == "HS256"
        assert provider.verify_exp is True

    def test_create_token(self):
        """Test JWT token creation."""
        provider = JWTProvider(secret_key="test-secret")

        token = provider.create_token(
            user_id="user123",
            roles=["admin", "editor"],
            permissions=["read:all", "write:all"],
            username="alice",
        )

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful JWT authentication."""
        provider = JWTProvider(secret_key="test-secret")

        # Create a token
        token = provider.create_token(
            user_id="user123",
            roles=["admin"],
            permissions=["read:posts"],
            username="alice",
        )

        # Authenticate with the token
        result = await provider.authenticate({"token": token})

        assert result.success is True
        assert result.context is not None
        assert result.context.authenticated is True
        assert result.context.user_id == "user123"
        assert result.context.username == "alice"
        assert result.context.has_role("admin")
        assert result.context.has_permission("read:posts")

    @pytest.mark.asyncio
    async def test_expired_token(self):
        """Test authentication with expired token."""
        provider = JWTProvider(secret_key="test-secret")

        # Create a token that expires immediately
        token = provider.create_token(user_id="user123", expires_in=-1)

        # Try to authenticate
        result = await provider.authenticate({"token": token})

        assert result.success is False
        assert result.error == "Token expired"

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test authentication with invalid token."""
        provider = JWTProvider(secret_key="test-secret")

        result = await provider.authenticate({"token": "invalid.token.here"})

        assert result.success is False
        assert result.error == "Invalid token"

    @pytest.mark.asyncio
    async def test_missing_token(self):
        """Test authentication with missing token."""
        provider = JWTProvider(secret_key="test-secret")

        result = await provider.authenticate({})

        assert result.success is False
        assert result.error == "Missing token in credentials"

    @pytest.mark.asyncio
    async def test_token_with_custom_claims(self):
        """Test JWT with custom claims."""
        provider = JWTProvider(secret_key="test-secret")

        token = provider.create_token(user_id="user123", custom_field="custom_value", number=42)

        result = await provider.authenticate({"token": token})

        assert result.success is True
        # Custom claims should be in the token payload (though not in our AuthContext)

    def test_validate_credentials(self):
        """Test credentials validation."""
        provider = JWTProvider(secret_key="test-secret")

        assert provider.validate_credentials({"token": "test"}) is True
        assert provider.validate_credentials({}) is False
        assert provider.validate_credentials({"other": "value"}) is False

    @pytest.mark.asyncio
    async def test_wrong_secret_key(self):
        """Test JWT verification fails with wrong secret key."""
        provider1 = JWTProvider(secret_key="secret1")
        provider2 = JWTProvider(secret_key="secret2")

        # Create token with provider1
        token = provider1.create_token(user_id="user123")

        # Try to verify with provider2 (different secret)
        result = await provider2.authenticate({"token": token})

        assert result.success is False
        assert result.error == "Invalid token"


class TestSessionProvider:
    """Tests for session-based authentication provider."""

    def test_provider_initialization(self):
        """Test session provider initialization."""
        provider = SessionProvider(session_timeout=1800)

        assert provider.session_timeout == 1800
        assert provider._sessions == {}

    def test_create_session(self):
        """Test session creation."""
        provider = SessionProvider()

        session_id = provider.create_session(
            user_id="user123",
            username="alice",
            roles=["admin"],
            permissions=["read:all"],
            metadata={"ip": "192.168.1.1"},
        )

        assert isinstance(session_id, str)
        assert len(session_id) > 0
        assert session_id in provider._sessions

        # Check session data
        session = provider._sessions[session_id]
        assert session["user_id"] == "user123"
        assert session["username"] == "alice"
        assert session["roles"] == ["admin"]
        assert session["permissions"] == ["read:all"]
        assert session["metadata"] == {"ip": "192.168.1.1"}

    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful session authentication."""
        provider = SessionProvider()

        # Create a session
        session_id = provider.create_session(
            user_id="user123", username="alice", roles=["admin"], permissions=["read:posts"]
        )

        # Authenticate with session ID
        result = await provider.authenticate({"session_id": session_id})

        assert result.success is True
        assert result.context is not None
        assert result.context.authenticated is True
        assert result.context.user_id == "user123"
        assert result.context.username == "alice"
        assert result.context.has_role("admin")
        assert result.context.has_permission("read:posts")

    @pytest.mark.asyncio
    async def test_invalid_session_id(self):
        """Test authentication with invalid session ID."""
        provider = SessionProvider()

        result = await provider.authenticate({"session_id": "invalid-session"})

        assert result.success is False
        assert result.error == "Invalid session"

    @pytest.mark.asyncio
    async def test_missing_session_id(self):
        """Test authentication with missing session ID."""
        provider = SessionProvider()

        result = await provider.authenticate({})

        assert result.success is False
        assert result.error == "Missing session_id in credentials"

    @pytest.mark.asyncio
    async def test_expired_session(self):
        """Test authentication with expired session."""
        provider = SessionProvider(session_timeout=0)  # Expire immediately

        # Create a session
        session_id = provider.create_session(user_id="user123")

        # Session should expire immediately
        import time

        time.sleep(0.1)

        result = await provider.authenticate({"session_id": session_id})

        assert result.success is False
        assert result.error == "Session expired"
        # Session should be removed
        assert session_id not in provider._sessions

    def test_destroy_session(self):
        """Test session destruction."""
        provider = SessionProvider()

        # Create a session
        session_id = provider.create_session(user_id="user123")
        assert session_id in provider._sessions

        # Destroy it
        result = provider.destroy_session(session_id)
        assert result is True
        assert session_id not in provider._sessions

        # Try to destroy non-existent session
        result = provider.destroy_session("non-existent")
        assert result is False

    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        provider = SessionProvider(session_timeout=0)  # Expire immediately

        # Create several sessions
        _session1 = provider.create_session(user_id="user1")
        _session2 = provider.create_session(user_id="user2")
        _session3 = provider.create_session(user_id="user3")

        assert len(provider._sessions) == 3

        # Wait for expiration
        import time

        time.sleep(0.1)

        # Cleanup
        cleaned = provider.cleanup_expired_sessions()

        assert cleaned == 3
        assert len(provider._sessions) == 0

    def test_cleanup_no_expired_sessions(self):
        """Test cleanup when no sessions are expired."""
        provider = SessionProvider(session_timeout=3600)

        # Create sessions
        _session1 = provider.create_session(user_id="user1")
        _session2 = provider.create_session(user_id="user2")

        # Cleanup (none should be expired)
        cleaned = provider.cleanup_expired_sessions()

        assert cleaned == 0
        assert len(provider._sessions) == 2

    def test_validate_credentials(self):
        """Test credentials validation."""
        provider = SessionProvider()

        assert provider.validate_credentials({"session_id": "test"}) is True
        assert provider.validate_credentials({}) is False
        assert provider.validate_credentials({"other": "value"}) is False
