"""
Specialized authentication and authorization error types.

This module provides clear, structured exceptions for different auth failure scenarios:
- AuthenticationError: General authentication failure
- AuthorizationError: General authorization failure
- OAuthRequiredError: OAuth authentication is needed
- ScopeInsufficientError: User lacks required OAuth scopes
- ManifestViolationError: Permission manifest access check failed
"""

from typing import Any

from nextmcp.auth.core import AuthContext


class AuthenticationError(Exception):
    """
    Raised when authentication fails.

    This is a general authentication error for any auth failure.

    Attributes:
        message: Human-readable error message
        required_scopes: OAuth scopes required (optional)
        providers: Available auth providers (optional)
    """

    def __init__(
        self,
        message: str,
        required_scopes: list[str] | None = None,
        providers: list[Any] | None = None,
    ):
        """
        Initialize AuthenticationError.

        Args:
            message: Error message
            required_scopes: Required OAuth scopes
            providers: Available authentication providers
        """
        super().__init__(message)
        self.message = message
        self.required_scopes = required_scopes or []
        self.providers = providers or []


class AuthorizationError(Exception):
    """
    Raised when authorization fails.

    This is a general authorization error for permission/access denials.

    Attributes:
        message: Human-readable error message
        required: What was required for access
        user_id: User ID who was denied
    """

    def __init__(
        self,
        message: str,
        required: Any | None = None,
        user_id: str | None = None,
    ):
        """
        Initialize AuthorizationError.

        Args:
            message: Error message
            required: Required permissions/scopes/roles
            user_id: User ID
        """
        super().__init__(message)
        self.message = message
        self.required = required
        self.user_id = user_id


class OAuthRequiredError(Exception):
    """
    Raised when OAuth authentication is required but not provided.

    This error indicates that a tool or operation requires OAuth authentication.
    It can include the authorization URL to help users complete the OAuth flow.

    Attributes:
        message: Human-readable error message
        provider: OAuth provider name (e.g., "github", "google")
        scopes: Required OAuth scopes
        authorization_url: URL to initiate OAuth flow
        user_id: Current user ID (if partially authenticated)
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        scopes: list[str] | None = None,
        authorization_url: str | None = None,
        user_id: str | None = None,
    ):
        """
        Initialize OAuthRequiredError.

        Args:
            message: Error message
            provider: OAuth provider name
            scopes: Required OAuth scopes
            authorization_url: URL to start OAuth flow
            user_id: Current user ID
        """
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.scopes = scopes or []
        self.authorization_url = authorization_url
        self.user_id = user_id


class ScopeInsufficientError(Exception):
    """
    Raised when user lacks required OAuth scopes.

    This error indicates that the user is authenticated but doesn't have
    sufficient OAuth scopes to perform the requested operation.

    Attributes:
        message: Human-readable error message
        required_scopes: List of scopes required (user needs ANY one)
        current_scopes: List of scopes user currently has
        user_id: User ID who lacks scopes
    """

    def __init__(
        self,
        message: str,
        required_scopes: list[str] | None = None,
        current_scopes: list[str] | None = None,
        user_id: str | None = None,
    ):
        """
        Initialize ScopeInsufficientError.

        Args:
            message: Error message
            required_scopes: Scopes that are required
            current_scopes: Scopes the user currently has
            user_id: User ID
        """
        super().__init__(message)
        self.message = message
        self.required_scopes = required_scopes or []
        self.current_scopes = current_scopes or []
        self.user_id = user_id


class ManifestViolationError(Exception):
    """
    Raised when permission manifest access check fails.

    This error indicates that the user attempted to access a tool but failed
    the manifest-based access control check. The error includes details about
    what was required and what the user had.

    Attributes:
        message: Human-readable error message
        tool_name: Name of the tool that was denied
        required_roles: Roles that are required (user needs ANY one)
        required_permissions: Permissions required (user needs ANY one)
        required_scopes: OAuth scopes required (user needs ANY one)
        user_id: User ID who was denied access
        auth_context: Full authentication context for debugging
    """

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        required_roles: list[str] | None = None,
        required_permissions: list[str] | None = None,
        required_scopes: list[str] | None = None,
        user_id: str | None = None,
        auth_context: AuthContext | None = None,
    ):
        """
        Initialize ManifestViolationError.

        Args:
            message: Error message
            tool_name: Tool that was denied
            required_roles: Roles required for access
            required_permissions: Permissions required for access
            required_scopes: OAuth scopes required for access
            user_id: User ID
            auth_context: Full auth context
        """
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.required_roles = required_roles or []
        self.required_permissions = required_permissions or []
        self.required_scopes = required_scopes or []
        self.user_id = user_id
        self.auth_context = auth_context
