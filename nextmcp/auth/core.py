"""
Core authentication framework for NextMCP.

This module provides the foundational classes for authentication and authorization
in MCP servers, adapted for stdio and WebSocket transports.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Permission:
    """
    Represents a single permission that can be granted to users.

    Permissions are fine-grained capabilities like "read:posts", "write:posts",
    "admin:users", etc.
    """

    name: str
    description: str = ""
    resource: str | None = None  # Optional resource this permission applies to

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Permission):
            return self.name == other.name
        return False

    def matches(self, required: str) -> bool:
        """
        Check if this permission matches a required permission string.

        Supports wildcards:
        - "admin:*" matches "admin:users", "admin:posts", etc.
        - "*" matches everything

        Args:
            required: Required permission string

        Returns:
            True if this permission satisfies the requirement
        """
        if self.name == "*":
            return True

        if "*" in self.name:
            prefix = self.name.split("*")[0]
            return required.startswith(prefix)

        return self.name == required


@dataclass
class Role:
    """
    Represents a role with a collection of permissions.

    Roles are named collections of permissions like "admin", "editor", "viewer", etc.
    """

    name: str
    description: str = ""
    permissions: set[Permission] = field(default_factory=set)

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.name == other.name
        return False

    def add_permission(self, permission: Permission | str) -> None:
        """Add a permission to this role."""
        if isinstance(permission, str):
            permission = Permission(permission)
        self.permissions.add(permission)

    def has_permission(self, permission_name: str) -> bool:
        """Check if this role has a specific permission."""
        return any(p.matches(permission_name) for p in self.permissions)


@dataclass
class AuthContext:
    """
    Represents the authentication context for a request.

    This contains information about the authenticated user, their credentials,
    roles, and permissions. It's passed to tools that require authentication.
    """

    authenticated: bool = False
    user_id: str | None = None
    username: str | None = None
    roles: set[Role] = field(default_factory=set)
    permissions: set[Permission] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(r.name == role_name for r in self.roles)

    def has_permission(self, permission_name: str) -> bool:
        """
        Check if user has a specific permission.

        Checks both direct permissions and permissions from roles.
        """
        # Check direct permissions
        if any(p.matches(permission_name) for p in self.permissions):
            return True

        # Check role permissions
        return any(r.has_permission(permission_name) for r in self.roles)

    def add_role(self, role: Role | str) -> None:
        """Add a role to this auth context."""
        if isinstance(role, str):
            role = Role(role)
        self.roles.add(role)

    def add_permission(self, permission: Permission | str) -> None:
        """Add a permission to this auth context."""
        if isinstance(permission, str):
            permission = Permission(permission)
        self.permissions.add(permission)


@dataclass
class AuthResult:
    """
    Result of an authentication attempt.

    Contains whether authentication succeeded, the auth context if successful,
    and any error message if failed.
    """

    success: bool
    context: AuthContext | None = None
    error: str | None = None

    @classmethod
    def success_result(cls, context: AuthContext) -> "AuthResult":
        """Create a successful auth result."""
        return cls(success=True, context=context)

    @classmethod
    def failure(cls, error: str) -> "AuthResult":
        """Create a failed auth result."""
        return cls(success=False, error=error)


class AuthProvider(ABC):
    """
    Base class for authentication providers.

    Providers implement specific authentication strategies like API keys,
    JWT tokens, OAuth flows, etc.
    """

    def __init__(self, **config: Any):
        """
        Initialize the auth provider with configuration.

        Args:
            **config: Provider-specific configuration
        """
        self.config = config

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> AuthResult:
        """
        Authenticate a user with the given credentials.

        Args:
            credentials: Authentication credentials (provider-specific format)

        Returns:
            AuthResult indicating success/failure and auth context
        """
        pass

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """
        Validate that credentials are in the correct format.

        Args:
            credentials: Credentials to validate

        Returns:
            True if credentials are valid format, False otherwise
        """
        return True

    @property
    def name(self) -> str:
        """Get the provider name."""
        return self.__class__.__name__
