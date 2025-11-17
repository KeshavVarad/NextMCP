"""
Auth Metadata Protocol for NextMCP.

This module defines the protocol-level metadata that MCP servers use to announce
their authentication and authorization requirements to clients/hosts.

This is the critical piece that allows hosts (like Claude Desktop, Cursor, etc.)
to discover what auth a server needs and present the appropriate UI.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuthFlowType(str, Enum):
    """Supported authentication flow types."""

    OAUTH2_PKCE = "oauth2-pkce"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2-client-credentials"
    API_KEY = "api-key"
    JWT = "jwt"
    BASIC = "basic"
    CUSTOM = "custom"


class AuthRequirement(str, Enum):
    """Authentication requirement levels."""

    REQUIRED = "required"  # All requests must be authenticated
    OPTIONAL = "optional"  # Authentication enhances functionality but isn't required
    NONE = "none"  # No authentication


@dataclass
class AuthProviderMetadata:
    """
    Metadata for a single OAuth/auth provider.

    This describes one authentication provider (e.g., Google, GitHub)
    that the server supports.
    """

    name: str  # Provider name: "google", "github", etc.
    type: str  # Provider type: "oauth2", "api-key", etc.
    flows: list[AuthFlowType]  # Supported flows
    authorization_url: str | None = None  # OAuth authorization endpoint
    token_url: str | None = None  # OAuth token endpoint
    scopes: list[str] = field(default_factory=list)  # Available OAuth scopes
    supports_refresh: bool = False  # Whether refresh tokens are supported
    supports_pkce: bool = True  # Whether PKCE is supported
    metadata_url: str | None = None  # Well-known metadata URL

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "flows": [flow.value for flow in self.flows],
            "authorization_url": self.authorization_url,
            "token_url": self.token_url,
            "scopes": self.scopes,
            "supports_refresh": self.supports_refresh,
            "supports_pkce": self.supports_pkce,
            "metadata_url": self.metadata_url,
        }


@dataclass
class AuthMetadata:
    """
    Complete authentication metadata for an MCP server.

    This is the top-level structure that servers expose to announce their
    authentication requirements, supported providers, scopes, and permissions.

    Example JSON representation:
    {
        "auth": {
            "requirement": "required",
            "providers": [
                {
                    "name": "google",
                    "type": "oauth2",
                    "flows": ["oauth2-pkce"],
                    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "scopes": ["profile", "email", "drive.readonly"],
                    "supports_refresh": true,
                    "supports_pkce": true
                }
            ],
            "required_scopes": ["profile", "email"],
            "optional_scopes": ["drive.readonly", "gmail.readonly"],
            "permissions": ["file.read", "email.send"],
            "supports_multi_user": true,
            "session_management": "server-side"
        }
    }
    """

    requirement: AuthRequirement = AuthRequirement.NONE
    providers: list[AuthProviderMetadata] = field(default_factory=list)
    required_scopes: list[str] = field(default_factory=list)  # Minimum scopes needed
    optional_scopes: list[str] = field(default_factory=list)  # Additional scopes
    permissions: list[str] = field(default_factory=list)  # Custom permissions
    roles: list[str] = field(default_factory=list)  # Available roles
    supports_multi_user: bool = False  # Multi-user/multi-tenant support
    session_management: str = "server-side"  # "server-side", "client-side", "stateless"
    token_refresh_enabled: bool = False  # Server handles token refresh
    error_codes: dict[str, str] = field(default_factory=dict)  # Auth error code docs

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "requirement": self.requirement.value,
            "providers": [provider.to_dict() for provider in self.providers],
            "required_scopes": self.required_scopes,
            "optional_scopes": self.optional_scopes,
            "permissions": self.permissions,
            "roles": self.roles,
            "supports_multi_user": self.supports_multi_user,
            "session_management": self.session_management,
            "token_refresh_enabled": self.token_refresh_enabled,
            "error_codes": self.error_codes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthMetadata":
        """
        Create AuthMetadata from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AuthMetadata instance
        """
        providers = [
            AuthProviderMetadata(
                name=p["name"],
                type=p["type"],
                flows=[AuthFlowType(f) for f in p.get("flows", [])],
                authorization_url=p.get("authorization_url"),
                token_url=p.get("token_url"),
                scopes=p.get("scopes", []),
                supports_refresh=p.get("supports_refresh", False),
                supports_pkce=p.get("supports_pkce", True),
                metadata_url=p.get("metadata_url"),
            )
            for p in data.get("providers", [])
        ]

        return cls(
            requirement=AuthRequirement(data.get("requirement", "none")),
            providers=providers,
            required_scopes=data.get("required_scopes", []),
            optional_scopes=data.get("optional_scopes", []),
            permissions=data.get("permissions", []),
            roles=data.get("roles", []),
            supports_multi_user=data.get("supports_multi_user", False),
            session_management=data.get("session_management", "server-side"),
            token_refresh_enabled=data.get("token_refresh_enabled", False),
            error_codes=data.get("error_codes", {}),
        )

    def add_provider(
        self,
        name: str,
        type: str,
        flows: list[AuthFlowType],
        authorization_url: str | None = None,
        token_url: str | None = None,
        scopes: list[str] | None = None,
        supports_refresh: bool = False,
        supports_pkce: bool = True,
    ) -> None:
        """
        Add an authentication provider.

        Args:
            name: Provider name (e.g., "google", "github")
            type: Provider type (e.g., "oauth2", "api-key")
            flows: Supported authentication flows
            authorization_url: OAuth authorization endpoint
            token_url: OAuth token endpoint
            scopes: Available scopes
            supports_refresh: Whether refresh tokens are supported
            supports_pkce: Whether PKCE is supported
        """
        provider = AuthProviderMetadata(
            name=name,
            type=type,
            flows=flows,
            authorization_url=authorization_url,
            token_url=token_url,
            scopes=scopes or [],
            supports_refresh=supports_refresh,
            supports_pkce=supports_pkce,
        )
        self.providers.append(provider)

    def add_required_scope(self, scope: str) -> None:
        """Add a required OAuth scope."""
        if scope not in self.required_scopes:
            self.required_scopes.append(scope)

    def add_optional_scope(self, scope: str) -> None:
        """Add an optional OAuth scope."""
        if scope not in self.optional_scopes:
            self.optional_scopes.append(scope)

    def add_permission(self, permission: str) -> None:
        """Add a custom permission."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def add_role(self, role: str) -> None:
        """Add a role."""
        if role not in self.roles:
            self.roles.append(role)

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the metadata configuration.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if self.requirement == AuthRequirement.REQUIRED and not self.providers:
            errors.append("Authentication is required but no providers configured")

        for provider in self.providers:
            if provider.type == "oauth2":
                if not provider.authorization_url:
                    errors.append(f"Provider '{provider.name}' missing authorization_url")
                if not provider.token_url:
                    errors.append(f"Provider '{provider.name}' missing token_url")

        # Check for scope conflicts
        scope_overlap = set(self.required_scopes) & set(self.optional_scopes)
        if scope_overlap:
            errors.append(f"Scopes cannot be both required and optional: {scope_overlap}")

        return len(errors) == 0, errors


# JSON Schema for validation (can be used by hosts)
AUTH_METADATA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NextMCP Auth Metadata",
    "description": "Authentication metadata for MCP servers",
    "type": "object",
    "properties": {
        "requirement": {
            "type": "string",
            "enum": ["required", "optional", "none"],
            "description": "Authentication requirement level",
        },
        "providers": {
            "type": "array",
            "description": "List of supported authentication providers",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "flows": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "oauth2-pkce",
                                "oauth2-client-credentials",
                                "api-key",
                                "jwt",
                                "basic",
                                "custom",
                            ],
                        },
                    },
                    "authorization_url": {"type": ["string", "null"]},
                    "token_url": {"type": ["string", "null"]},
                    "scopes": {"type": "array", "items": {"type": "string"}},
                    "supports_refresh": {"type": "boolean"},
                    "supports_pkce": {"type": "boolean"},
                    "metadata_url": {"type": ["string", "null"]},
                },
                "required": ["name", "type", "flows"],
            },
        },
        "required_scopes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Minimum required OAuth scopes",
        },
        "optional_scopes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional OAuth scopes that enhance functionality",
        },
        "permissions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Custom permission strings",
        },
        "roles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Available user roles",
        },
        "supports_multi_user": {
            "type": "boolean",
            "description": "Whether server supports multiple users",
        },
        "session_management": {
            "type": "string",
            "enum": ["server-side", "client-side", "stateless"],
            "description": "Session management strategy",
        },
        "token_refresh_enabled": {
            "type": "boolean",
            "description": "Whether server handles token refresh",
        },
        "error_codes": {
            "type": "object",
            "description": "Documentation for auth error codes",
            "additionalProperties": {"type": "string"},
        },
    },
    "required": ["requirement"],
}
