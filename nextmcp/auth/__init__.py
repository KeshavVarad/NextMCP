"""
Authentication and authorization for NextMCP.

This module provides a comprehensive auth system inspired by next-auth,
adapted for the Model Context Protocol (MCP).
"""

from nextmcp.auth.core import (
    AuthContext,
    AuthProvider,
    AuthResult,
    Permission,
    Role,
)
from nextmcp.auth.middleware import (
    requires_auth,
    requires_auth_async,
    requires_permission,
    requires_permission_async,
    requires_role,
    requires_role_async,
)
from nextmcp.auth.providers import (
    APIKeyProvider,
    JWTProvider,
    SessionProvider,
)
from nextmcp.auth.rbac import RBAC, PermissionDeniedError

__all__ = [
    # Core
    "AuthContext",
    "AuthProvider",
    "AuthResult",
    "Permission",
    "Role",
    # Middleware
    "requires_auth",
    "requires_auth_async",
    "requires_permission",
    "requires_permission_async",
    "requires_role",
    "requires_role_async",
    # Providers
    "APIKeyProvider",
    "JWTProvider",
    "SessionProvider",
    # RBAC
    "RBAC",
    "PermissionDeniedError",
]
