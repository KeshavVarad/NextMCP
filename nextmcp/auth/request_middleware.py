"""
Request-level auth enforcement middleware for NextMCP.

This module provides middleware that intercepts ALL MCP requests and enforces
authentication and authorization automatically, without requiring decorators
on individual tools.

This is the runtime enforcement layer that makes auth actually work in production.
"""

import logging
from typing import Any, Callable

from nextmcp.auth.core import AuthContext, AuthProvider, AuthResult
from nextmcp.auth.errors import AuthenticationError, AuthorizationError
from nextmcp.auth.manifest import PermissionManifest
from nextmcp.protocol.auth_metadata import AuthMetadata, AuthRequirement
from nextmcp.session.session_store import SessionStore

logger = logging.getLogger(__name__)


class AuthEnforcementMiddleware:
    """
    Middleware that enforces authentication and authorization on every request.

    This middleware:
    1. Extracts auth credentials from request
    2. Validates tokens using the auth provider
    3. Loads session data
    4. Checks scopes and permissions
    5. Populates auth context
    6. Rejects unauthorized requests with structured errors

    Example:
        # In your MCP server setup
        auth_middleware = AuthEnforcementMiddleware(
            provider=google_oauth,
            session_store=MemorySessionStore(),
            metadata=auth_metadata,
            manifest=permission_manifest
        )

        # Apply to all requests
        server.use(auth_middleware)
    """

    def __init__(
        self,
        provider: AuthProvider,
        session_store: SessionStore | None = None,
        metadata: AuthMetadata | None = None,
        manifest: PermissionManifest | None = None,
        credentials_key: str = "auth",
        auto_refresh_tokens: bool = True,
    ):
        """
        Initialize auth enforcement middleware.

        Args:
            provider: Auth provider for validation
            session_store: Session storage (optional)
            metadata: Auth metadata for requirement checking
            manifest: Permission manifest for tool requirements
            credentials_key: Key in request where credentials are found
            auto_refresh_tokens: Automatically refresh expired tokens
        """
        self.provider = provider
        self.session_store = session_store
        self.metadata = metadata or AuthMetadata()
        self.manifest = manifest
        self.credentials_key = credentials_key
        self.auto_refresh_tokens = auto_refresh_tokens

    async def __call__(
        self,
        request: dict[str, Any],
        handler: Callable,
    ) -> Any:
        """
        Process request with auth enforcement.

        Args:
            request: MCP request dictionary
            handler: Next middleware/handler in chain

        Returns:
            Response from handler

        Raises:
            AuthenticationError: If authentication fails
            AuthorizationError: If authorization fails
        """
        # Check if authentication is required
        if self.metadata.requirement == AuthRequirement.NONE:
            # No auth required, pass through
            return await handler(request)

        # Extract credentials from request
        credentials = request.get(self.credentials_key, {})

        # If auth is optional and no credentials provided, allow request
        if self.metadata.requirement == AuthRequirement.OPTIONAL and not credentials:
            logger.debug("Optional auth: no credentials provided, allowing request")
            return await handler(request)

        # Auth is required or credentials were provided
        if not credentials:
            raise AuthenticationError(
                "Authentication required but no credentials provided",
                required_scopes=self.metadata.required_scopes,
                providers=self.metadata.providers,
            )

        # Authenticate using provider
        auth_result = await self._authenticate(credentials, request)

        if not auth_result.success:
            raise AuthenticationError(
                auth_result.error or "Authentication failed",
                required_scopes=self.metadata.required_scopes,
                providers=self.metadata.providers,
            )

        auth_context = auth_result.context

        # Check authorization (scopes, permissions, manifest)
        self._check_authorization(auth_context, request)

        # Inject auth context into request for handlers
        request["_auth_context"] = auth_context

        # Call next handler
        return await handler(request)

    async def _authenticate(
        self,
        credentials: dict[str, Any],
        request: dict[str, Any],
    ) -> AuthResult:
        """
        Authenticate the request.

        Args:
            credentials: Auth credentials
            request: Full request data

        Returns:
            AuthResult with success status and context
        """
        # Extract access token
        access_token = credentials.get("access_token")
        if not access_token:
            return AuthResult.failure("No access_token in credentials")

        # Check session store first
        user_id = None
        if self.session_store:
            # Try to find user by token (this is a simple implementation)
            # In production, you might want to decode JWT or lookup by token hash
            for uid in self.session_store.list_users():
                session = self.session_store.load(uid)
                if session and session.access_token == access_token:
                    user_id = uid

                    # Check if token needs refresh
                    if self.auto_refresh_tokens and session.needs_refresh():
                        logger.info(f"Token expiring soon for user {user_id}, refreshing...")
                        try:
                            await self._refresh_token(session)
                        except Exception as e:
                            logger.warning(f"Token refresh failed for {user_id}: {e}")

                    # Check if token is expired
                    if session.is_expired():
                        return AuthResult.failure("Access token expired")

                    # Build auth context from session
                    auth_context = AuthContext(
                        authenticated=True,
                        user_id=session.user_id,
                        username=session.user_info.get("login") or session.user_info.get("email"),
                        metadata={
                            "oauth_provider": session.provider,
                            "access_token": session.access_token,
                            "refresh_token": session.refresh_token,
                            "user_info": session.user_info,
                        },
                    )

                    # Add scopes from session
                    for scope in session.scopes:
                        auth_context.add_scope(scope)

                    return AuthResult.success_result(auth_context)

        # No session found, authenticate with provider
        result = await self.provider.authenticate(credentials)

        # If successful and we have session store, save session
        if result.success and self.session_store and result.context:
            try:
                from nextmcp.session.session_store import SessionData

                session = SessionData(
                    user_id=result.context.user_id,
                    access_token=access_token,
                    refresh_token=credentials.get("refresh_token"),
                    scopes=list(result.context.scopes),
                    user_info=result.context.metadata.get("user_info", {}),
                    provider=self.provider.name,
                )
                self.session_store.save(session)
                logger.info(f"Created new session for user: {result.context.user_id}")
            except Exception as e:
                logger.warning(f"Failed to save session: {e}")

        return result

    async def _refresh_token(self, session: "SessionData") -> None:
        """
        Refresh an expired token.

        Args:
            session: Session data with refresh token

        Raises:
            ValueError: If refresh fails
        """
        if not session.refresh_token:
            raise ValueError("No refresh token available")

        # Import OAuth provider types
        from nextmcp.auth.oauth import OAuthProvider

        if not isinstance(self.provider, OAuthProvider):
            raise ValueError("Token refresh only supported for OAuth providers")

        # Refresh token
        token_data = await self.provider.refresh_access_token(session.refresh_token)

        # Update session
        if self.session_store:
            import time

            session.access_token = token_data.get("access_token")
            if "refresh_token" in token_data:
                session.refresh_token = token_data["refresh_token"]
            if "expires_in" in token_data:
                session.expires_at = time.time() + token_data["expires_in"]

            self.session_store.save(session)
            logger.info(f"Refreshed token for user: {session.user_id}")

    def _check_authorization(
        self,
        auth_context: AuthContext,
        request: dict[str, Any],
    ) -> None:
        """
        Check if user is authorized for this request.

        Args:
            auth_context: Authenticated user context
            request: Request data

        Raises:
            AuthorizationError: If user lacks required authorization
        """
        # Extract tool name from request (MCP format)
        tool_name = request.get("params", {}).get("name")
        if not tool_name:
            # Not a tool call, allow
            return

        # Check required scopes from metadata
        if self.metadata.required_scopes:
            has_all_scopes = all(
                auth_context.has_scope(scope) for scope in self.metadata.required_scopes
            )
            if not has_all_scopes:
                missing_scopes = [
                    scope
                    for scope in self.metadata.required_scopes
                    if not auth_context.has_scope(scope)
                ]
                raise AuthorizationError(
                    f"Missing required scopes: {', '.join(missing_scopes)}",
                    required=missing_scopes,
                    user_id=auth_context.user_id,
                )

        # Check manifest if provided
        if self.manifest:
            allowed, error_message = self.manifest.check_tool_access(tool_name, auth_context)
            if not allowed:
                # Get tool definition for detailed error
                tool_def = self.manifest.tools.get(tool_name)

                from nextmcp.auth.errors import ManifestViolationError

                raise ManifestViolationError(
                    message=error_message or "Access denied by permission manifest",
                    tool_name=tool_name,
                    required_roles=tool_def.roles if tool_def else [],
                    required_permissions=tool_def.permissions if tool_def else [],
                    required_scopes=tool_def.scopes if tool_def else [],
                    user_id=auth_context.user_id,
                    auth_context=auth_context,
                )

        logger.debug(f"Authorization check passed for {auth_context.user_id} on {tool_name}")


class SessionData:
    """Forward declaration for type hints (actual class in session_store.py)."""

    pass


def create_auth_middleware(
    provider: AuthProvider,
    requirement: AuthRequirement = AuthRequirement.REQUIRED,
    session_store: SessionStore | None = None,
    manifest: PermissionManifest | None = None,
    required_scopes: list[str] | None = None,
) -> AuthEnforcementMiddleware:
    """
    Helper function to create auth enforcement middleware.

    Args:
        provider: Auth provider
        requirement: Auth requirement level
        session_store: Session storage (optional)
        manifest: Permission manifest (optional)
        required_scopes: Required OAuth scopes (optional)

    Returns:
        Configured AuthEnforcementMiddleware

    Example:
        middleware = create_auth_middleware(
            provider=github_oauth,
            requirement=AuthRequirement.REQUIRED,
            session_store=MemorySessionStore(),
            required_scopes=["repo", "user"]
        )
    """
    metadata = AuthMetadata(
        requirement=requirement,
        required_scopes=required_scopes or [],
    )

    return AuthEnforcementMiddleware(
        provider=provider,
        session_store=session_store,
        metadata=metadata,
        manifest=manifest,
    )
