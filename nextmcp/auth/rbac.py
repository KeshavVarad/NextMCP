"""
Role-Based Access Control (RBAC) system for NextMCP.

This module provides a comprehensive RBAC system for managing roles,
permissions, and access control at the tool level.
"""

import logging
from typing import Any

from nextmcp.auth.core import AuthContext, Permission, Role

logger = logging.getLogger(__name__)


class PermissionDeniedError(Exception):
    """Raised when a user lacks required permissions."""

    def __init__(self, message: str, required: str | None = None, user_id: str | None = None):
        self.required = required
        self.user_id = user_id
        super().__init__(message)


class RBAC:
    """
    Role-Based Access Control system.

    Manages roles, permissions, and provides methods for checking access.
    Can be used standalone or integrated with NextMCP auth system.
    """

    def __init__(self) -> None:
        """Initialize the RBAC system."""
        self._roles: dict[str, Role] = {}
        self._permissions: dict[str, Permission] = {}

    def define_permission(
        self, name: str, description: str = "", resource: str | None = None
    ) -> Permission:
        """
        Define a new permission.

        Args:
            name: Permission name (e.g., "read:posts", "admin:users")
            description: Human-readable description
            resource: Optional resource this permission applies to

        Returns:
            The created Permission object
        """
        permission = Permission(name=name, description=description, resource=resource)
        self._permissions[name] = permission
        logger.debug(f"Defined permission: {name}")
        return permission

    def define_role(self, name: str, description: str = "") -> Role:
        """
        Define a new role.

        Args:
            name: Role name (e.g., "admin", "editor", "viewer")
            description: Human-readable description

        Returns:
            The created Role object
        """
        role = Role(name=name, description=description)
        self._roles[name] = role
        logger.debug(f"Defined role: {name}")
        return role

    def assign_permission_to_role(self, role_name: str, permission_name: str) -> None:
        """
        Assign a permission to a role.

        Args:
            role_name: Name of the role
            permission_name: Name of the permission

        Raises:
            ValueError: If role or permission doesn't exist
        """
        if role_name not in self._roles:
            raise ValueError(f"Role '{role_name}' not found")

        if permission_name not in self._permissions:
            # Auto-create permission if it doesn't exist
            self.define_permission(permission_name)

        role = self._roles[role_name]
        permission = self._permissions[permission_name]
        role.add_permission(permission)
        logger.debug(f"Assigned permission '{permission_name}' to role '{role_name}'")

    def get_role(self, name: str) -> Role | None:
        """Get a role by name."""
        return self._roles.get(name)

    def get_permission(self, name: str) -> Permission | None:
        """Get a permission by name."""
        return self._permissions.get(name)

    def list_roles(self) -> list[Role]:
        """List all defined roles."""
        return list(self._roles.values())

    def list_permissions(self) -> list[Permission]:
        """List all defined permissions."""
        return list(self._permissions.values())

    def check_permission(self, context: AuthContext, permission_name: str) -> bool:
        """
        Check if an auth context has a specific permission.

        Args:
            context: Authentication context
            permission_name: Required permission name

        Returns:
            True if context has the permission, False otherwise
        """
        if not context.authenticated:
            return False

        return context.has_permission(permission_name)

    def check_role(self, context: AuthContext, role_name: str) -> bool:
        """
        Check if an auth context has a specific role.

        Args:
            context: Authentication context
            role_name: Required role name

        Returns:
            True if context has the role, False otherwise
        """
        if not context.authenticated:
            return False

        return context.has_role(role_name)

    def require_permission(self, context: AuthContext, permission_name: str) -> None:
        """
        Require that an auth context has a specific permission.

        Args:
            context: Authentication context
            permission_name: Required permission name

        Raises:
            PermissionDeniedError: If permission is not granted
        """
        if not self.check_permission(context, permission_name):
            raise PermissionDeniedError(
                f"Permission '{permission_name}' required",
                required=permission_name,
                user_id=context.user_id,
            )

    def require_role(self, context: AuthContext, role_name: str) -> None:
        """
        Require that an auth context has a specific role.

        Args:
            context: Authentication context
            role_name: Required role name

        Raises:
            PermissionDeniedError: If role is not granted
        """
        if not self.check_role(context, role_name):
            raise PermissionDeniedError(
                f"Role '{role_name}' required", required=role_name, user_id=context.user_id
            )

    def load_from_config(self, config: dict[str, Any]) -> None:
        """
        Load roles and permissions from configuration.

        Expected format:
        {
            "permissions": [
                {"name": "read:posts", "description": "Read posts"},
                {"name": "write:posts", "description": "Write posts"}
            ],
            "roles": [
                {
                    "name": "editor",
                    "description": "Content editor",
                    "permissions": ["read:posts", "write:posts"]
                }
            ]
        }

        Args:
            config: Configuration dictionary
        """
        # Load permissions
        for perm_config in config.get("permissions", []):
            self.define_permission(
                name=perm_config["name"],
                description=perm_config.get("description", ""),
                resource=perm_config.get("resource"),
            )

        # Load roles
        for role_config in config.get("roles", []):
            role = self.define_role(
                name=role_config["name"], description=role_config.get("description", "")
            )

            # Assign permissions to role
            for perm_name in role_config.get("permissions", []):
                if perm_name not in self._permissions:
                    self.define_permission(perm_name)
                role.add_permission(self._permissions[perm_name])

        logger.info(
            f"Loaded RBAC config: {len(self._roles)} roles, "
            f"{len(self._permissions)} permissions"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Export RBAC configuration as dictionary.

        Returns:
            Dictionary representation of roles and permissions
        """
        return {
            "permissions": [
                {
                    "name": p.name,
                    "description": p.description,
                    "resource": p.resource,
                }
                for p in self._permissions.values()
            ],
            "roles": [
                {
                    "name": r.name,
                    "description": r.description,
                    "permissions": [p.name for p in r.permissions],
                }
                for r in self._roles.values()
            ],
        }
