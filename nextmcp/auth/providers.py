"""
Built-in authentication providers for NextMCP.

This module provides ready-to-use authentication providers for common use cases.
"""

import logging
import secrets
from collections.abc import Callable
from typing import Any

from nextmcp.auth.core import AuthContext, AuthProvider, AuthResult, Permission, Role

logger = logging.getLogger(__name__)


class APIKeyProvider(AuthProvider):
    """
    API Key authentication provider.

    Validates requests using API keys. Supports:
    - Simple key validation
    - Key-to-user mapping
    - Role assignment per key
    - Permission assignment per key
    """

    def __init__(
        self,
        valid_keys: dict[str, dict[str, Any]] | None = None,
        key_validator: Callable[[str], dict[str, Any] | None] | None = None,
        **config: Any,
    ):
        """
        Initialize API key provider.

        Args:
            valid_keys: Dictionary mapping API keys to user config.
                       Example: {"key123": {"user_id": "user1", "roles": ["admin"]}}
            key_validator: Optional custom validation function
            **config: Additional configuration
        """
        super().__init__(**config)
        self.valid_keys = valid_keys or {}
        self.key_validator = key_validator

    async def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        """
        Authenticate using an API key.

        Expected credentials format:
        {
            "api_key": "the-api-key-string"
        }

        Args:
            credentials: Credentials containing api_key

        Returns:
            AuthResult with auth context if successful
        """
        api_key = credentials.get("api_key")

        if not api_key:
            return AuthResult.failure("Missing api_key in credentials")

        # Use custom validator if provided
        if self.key_validator:
            user_config = self.key_validator(api_key)
            if not user_config:
                logger.warning("API key validation failed (custom validator)")
                return AuthResult.failure("Invalid API key")
        # Otherwise check against valid_keys
        elif api_key in self.valid_keys:
            user_config = self.valid_keys[api_key]
        else:
            logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
            return AuthResult.failure("Invalid API key")

        # Build auth context from user config
        context = AuthContext(
            authenticated=True,
            user_id=user_config.get("user_id", "unknown"),
            username=user_config.get("username"),
            metadata=user_config.get("metadata", {}),
        )

        # Add roles
        for role_name in user_config.get("roles", []):
            context.add_role(Role(role_name))

        # Add permissions
        for perm_name in user_config.get("permissions", []):
            context.add_permission(Permission(perm_name))

        logger.info(f"API key authentication successful for user: {context.user_id}")
        return AuthResult.success_result(context)

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate that credentials contain an api_key."""
        return "api_key" in credentials

    @staticmethod
    def generate_key(length: int = 32) -> str:
        """
        Generate a secure random API key.

        Args:
            length: Length of the key in bytes (default 32)

        Returns:
            Hex-encoded API key
        """
        return secrets.token_hex(length)


class JWTProvider(AuthProvider):
    """
    JWT (JSON Web Token) authentication provider.

    Validates and decodes JWT tokens. Requires PyJWT library.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        verify_exp: bool = True,
        **config: Any,
    ):
        """
        Initialize JWT provider.

        Args:
            secret_key: Secret key for verifying JWT signatures
            algorithm: JWT algorithm (default: HS256)
            verify_exp: Whether to verify token expiration (default: True)
            **config: Additional configuration
        """
        super().__init__(**config)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.verify_exp = verify_exp

        # Check if PyJWT is available
        try:
            import jwt  # noqa: F401

            self._jwt = jwt
        except ImportError as err:
            raise ImportError(
                "PyJWT is required for JWT authentication. " "Install with: pip install PyJWT"
            ) from err

    async def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        """
        Authenticate using a JWT token.

        Expected credentials format:
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }

        Expected token payload:
        {
            "sub": "user_id",
            "username": "optional_username",
            "roles": ["role1", "role2"],
            "permissions": ["perm1", "perm2"],
            "exp": 1234567890
        }

        Args:
            credentials: Credentials containing JWT token

        Returns:
            AuthResult with auth context if successful
        """
        token = credentials.get("token")

        if not token:
            return AuthResult.failure("Missing token in credentials")

        try:
            # Decode and verify JWT
            payload = self._jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": self.verify_exp},
            )

            # Build auth context from token payload
            context = AuthContext(
                authenticated=True,
                user_id=payload.get("sub", "unknown"),
                username=payload.get("username"),
                metadata=payload.get("metadata", {}),
            )

            # Add roles from token
            for role_name in payload.get("roles", []):
                context.add_role(Role(role_name))

            # Add permissions from token
            for perm_name in payload.get("permissions", []):
                context.add_permission(Permission(perm_name))

            logger.info(f"JWT authentication successful for user: {context.user_id}")
            return AuthResult.success_result(context)

        except self._jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return AuthResult.failure("Token expired")
        except self._jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return AuthResult.failure("Invalid token")
        except Exception as e:
            logger.error(f"JWT authentication error: {e}", exc_info=True)
            return AuthResult.failure("Authentication failed")

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate that credentials contain a token."""
        return "token" in credentials

    def create_token(
        self,
        user_id: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        expires_in: int = 3600,
        **claims: Any,
    ) -> str:
        """
        Create a JWT token.

        Args:
            user_id: User ID (stored in 'sub' claim)
            roles: List of role names
            permissions: List of permission names
            expires_in: Token expiration time in seconds
            **claims: Additional claims to include

        Returns:
            Encoded JWT token string
        """
        import time

        payload = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "roles": roles or [],
            "permissions": permissions or [],
            **claims,
        }

        return self._jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


class SessionProvider(AuthProvider):
    """
    Session-based authentication provider.

    Manages user sessions with session IDs and in-memory session storage.
    For production, consider using a persistent session store.
    """

    def __init__(self, session_timeout: int = 3600, **config: Any):
        """
        Initialize session provider.

        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
            **config: Additional configuration
        """
        super().__init__(**config)
        self.session_timeout = session_timeout
        self._sessions: dict[str, dict[str, Any]] = {}

    async def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        """
        Authenticate using a session ID.

        Expected credentials format:
        {
            "session_id": "session-uuid-string"
        }

        Args:
            credentials: Credentials containing session_id

        Returns:
            AuthResult with auth context if successful
        """
        import time

        session_id = credentials.get("session_id")

        if not session_id:
            return AuthResult.failure("Missing session_id in credentials")

        # Check if session exists
        if session_id not in self._sessions:
            logger.warning(f"Invalid session ID: {session_id}")
            return AuthResult.failure("Invalid session")

        session = self._sessions[session_id]

        # Check if session is expired
        if time.time() > session.get("expires_at", 0):
            logger.info(f"Session expired: {session_id}")
            del self._sessions[session_id]
            return AuthResult.failure("Session expired")

        # Build auth context from session
        context = AuthContext(
            authenticated=True,
            user_id=session.get("user_id", "unknown"),
            username=session.get("username"),
            metadata=session.get("metadata", {}),
        )

        # Add roles
        for role_name in session.get("roles", []):
            context.add_role(Role(role_name))

        # Add permissions
        for perm_name in session.get("permissions", []):
            context.add_permission(Permission(perm_name))

        logger.info(f"Session authentication successful for user: {context.user_id}")
        return AuthResult.success_result(context)

    def create_session(
        self,
        user_id: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        username: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new session.

        Args:
            user_id: User ID
            roles: List of role names
            permissions: List of permission names
            username: Optional username
            metadata: Optional metadata dictionary

        Returns:
            Session ID string
        """
        import time

        session_id = secrets.token_urlsafe(32)

        self._sessions[session_id] = {
            "user_id": user_id,
            "username": username,
            "roles": roles or [],
            "permissions": permissions or [],
            "metadata": metadata or {},
            "created_at": time.time(),
            "expires_at": time.time() + self.session_timeout,
        }

        logger.info(f"Created session for user: {user_id}")
        return session_id

    def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session.

        Args:
            session_id: Session ID to destroy

        Returns:
            True if session was destroyed, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Destroyed session: {session_id}")
            return True
        return False

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate that credentials contain a session_id."""
        return "session_id" in credentials

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from storage.

        Returns:
            Number of sessions cleaned up
        """
        import time

        now = time.time()
        expired = [sid for sid, sess in self._sessions.items() if now > sess.get("expires_at", 0)]

        for session_id in expired:
            del self._sessions[session_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)
