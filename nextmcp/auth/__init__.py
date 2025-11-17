"""
Authentication and authorization for NextMCP.

This module provides a comprehensive auth system inspired by next-auth,
adapted for the Model Context Protocol (MCP).

Includes support for:
- API Key, JWT, and Session authentication
- OAuth 2.0 with PKCE (GitHub, Google, and custom providers)
- Role-Based Access Control (RBAC)
- Fine-grained permissions
"""

from nextmcp.auth.core import (
    AuthContext,
    AuthProvider,
    AuthResult,
    Permission,
    Role,
)
from nextmcp.auth.errors import (
    AuthenticationError,
    AuthorizationError,
    ManifestViolationError,
    OAuthRequiredError,
    ScopeInsufficientError,
)
from nextmcp.auth.manifest import PermissionManifest, ScopeDefinition, ToolPermission
from nextmcp.auth.middleware import (
    requires_auth,
    requires_auth_async,
    requires_manifest_async,
    requires_permission,
    requires_permission_async,
    requires_role,
    requires_role_async,
    requires_scope_async,
)
from nextmcp.auth.oauth import OAuthConfig, OAuthProvider, PKCEChallenge
from nextmcp.auth.oauth_providers import GitHubOAuthProvider, GoogleOAuthProvider
from nextmcp.auth.providers import (
    APIKeyProvider,
    JWTProvider,
    SessionProvider,
)
from nextmcp.auth.rbac import RBAC, PermissionDeniedError
from nextmcp.auth.request_middleware import (
    AuthEnforcementMiddleware,
    create_auth_middleware,
)

__all__ = [
    # Core
    "AuthContext",
    "AuthProvider",
    "AuthResult",
    "Permission",
    "Role",
    # Errors
    "AuthenticationError",
    "AuthorizationError",
    "OAuthRequiredError",
    "ScopeInsufficientError",
    "ManifestViolationError",
    "PermissionDeniedError",
    # Manifest
    "PermissionManifest",
    "ScopeDefinition",
    "ToolPermission",
    # Middleware (decorators)
    "requires_auth",
    "requires_auth_async",
    "requires_manifest_async",
    "requires_permission",
    "requires_permission_async",
    "requires_role",
    "requires_role_async",
    "requires_scope_async",
    # Request Middleware (runtime enforcement)
    "AuthEnforcementMiddleware",
    "create_auth_middleware",
    # Providers
    "APIKeyProvider",
    "JWTProvider",
    "SessionProvider",
    # OAuth
    "OAuthProvider",
    "OAuthConfig",
    "PKCEChallenge",
    "GitHubOAuthProvider",
    "GoogleOAuthProvider",
    # RBAC
    "RBAC",
]
