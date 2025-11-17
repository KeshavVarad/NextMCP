"""
Permission Manifest system for NextMCP.

This module provides declarative security definitions using manifests,
allowing tools to specify their permission, role, and scope requirements
in a structured YAML/JSON format.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nextmcp.auth.core import AuthContext


@dataclass
class ScopeDefinition:
    """
    Defines an OAuth scope with metadata and provider mappings.

    Scopes can be mapped to provider-specific OAuth scopes for
    multi-provider support (e.g., GitHub repo:read -> Google drive.readonly).
    """

    name: str
    description: str
    oauth_mapping: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Export scope definition to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "oauth_mapping": self.oauth_mapping,
        }


@dataclass
class ToolPermission:
    """
    Defines permission requirements for a tool.

    A tool can require:
    - Permissions: Fine-grained permission strings (e.g., "read:data")
    - Scopes: OAuth scopes (e.g., "repo:read")
    - Roles: Role names (e.g., "admin")

    All requirement types use OR logic within their type,
    but AND logic between types (must satisfy all types that are specified).
    """

    tool_name: str
    permissions: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    description: str = ""
    dangerous: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Export tool permission to dictionary."""
        return {
            "permissions": self.permissions,
            "scopes": self.scopes,
            "roles": self.roles,
            "description": self.description,
            "dangerous": self.dangerous,
        }


class PermissionManifest:
    """
    Permission manifest for declarative security definitions.

    Manifests define:
    1. Scopes: OAuth scope definitions with provider mappings
    2. Tools: Tool permission requirements

    Can be loaded from YAML/JSON files or defined programmatically.
    Used to enforce access control on MCP tools at runtime.
    """

    def __init__(self) -> None:
        """Initialize an empty permission manifest."""
        self.scopes: dict[str, ScopeDefinition] = {}
        self.tools: dict[str, ToolPermission] = {}

    def define_scope(
        self,
        name: str,
        description: str,
        oauth_mapping: dict[str, list[str]] | None = None,
    ) -> ScopeDefinition:
        """
        Define a scope in the manifest.

        Args:
            name: Scope name (e.g., "read:data")
            description: Human-readable description
            oauth_mapping: Provider-specific OAuth scope mappings

        Returns:
            The created ScopeDefinition
        """
        scope = ScopeDefinition(
            name=name,
            description=description,
            oauth_mapping=oauth_mapping or {},
        )
        self.scopes[name] = scope
        return scope

    def define_tool_permission(
        self,
        tool_name: str,
        permissions: list[str] | None = None,
        scopes: list[str] | None = None,
        roles: list[str] | None = None,
        description: str = "",
        dangerous: bool = False,
    ) -> ToolPermission:
        """
        Define permission requirements for a tool.

        Args:
            tool_name: Name of the tool
            permissions: Required permissions (user needs ANY one)
            scopes: Required OAuth scopes (user needs ANY one)
            roles: Required roles (user needs ANY one)
            description: Human-readable description
            dangerous: Whether this tool is dangerous (requires extra confirmation)

        Returns:
            The created ToolPermission
        """
        tool = ToolPermission(
            tool_name=tool_name,
            permissions=permissions or [],
            scopes=scopes or [],
            roles=roles or [],
            description=description,
            dangerous=dangerous,
        )
        self.tools[tool_name] = tool
        return tool

    def load_from_dict(self, data: dict[str, Any]) -> None:
        """
        Load manifest from a dictionary.

        Expected format:
        {
            "scopes": [
                {
                    "name": "read:data",
                    "description": "Read data",
                    "oauth_mapping": {"github": ["repo:read"]}
                }
            ],
            "tools": {
                "query_db": {
                    "permissions": ["read:data"],
                    "scopes": ["db.query.read"],
                    "roles": ["viewer"],
                    "description": "Query database",
                    "dangerous": false
                }
            }
        }

        Args:
            data: Dictionary containing manifest data
        """
        # Load scopes
        for scope_data in data.get("scopes", []):
            self.define_scope(
                name=scope_data["name"],
                description=scope_data.get("description", ""),
                oauth_mapping=scope_data.get("oauth_mapping", {}),
            )

        # Load tools
        for tool_name, tool_data in data.get("tools", {}).items():
            self.define_tool_permission(
                tool_name=tool_name,
                permissions=tool_data.get("permissions", []),
                scopes=tool_data.get("scopes", []),
                roles=tool_data.get("roles", []),
                description=tool_data.get("description", ""),
                dangerous=tool_data.get("dangerous", False),
            )

    def load_from_yaml(self, path: str) -> None:
        """
        Load manifest from a YAML file.

        Args:
            path: Path to YAML file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        import yaml

        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        self.load_from_dict(data or {})

    def to_dict(self) -> dict[str, Any]:
        """
        Export manifest to dictionary.

        Returns:
            Dictionary containing all scopes and tools
        """
        return {
            "scopes": [scope.to_dict() for scope in self.scopes.values()],
            "tools": {name: tool.to_dict() for name, tool in self.tools.items()},
        }

    def check_tool_access(self, tool_name: str, context: AuthContext) -> tuple[bool, str | None]:
        """
        Check if an auth context has access to a tool.

        Logic:
        - If tool not in manifest, allow access (unrestricted)
        - If tool has no requirements, allow access
        - If tool has requirements, must satisfy ALL requirement types (AND)
        - Within each type (roles/permissions/scopes), need ANY one (OR)

        Args:
            tool_name: Name of the tool to check
            context: Authentication context to check

        Returns:
            Tuple of (allowed: bool, error_message: str | None)
        """
        # If tool not defined in manifest, allow access (no restrictions)
        if tool_name not in self.tools:
            return (True, None)

        tool = self.tools[tool_name]

        # If tool has no requirements, allow access
        if not tool.roles and not tool.permissions and not tool.scopes:
            return (True, None)

        # Check each requirement type (AND logic between types)
        # Must satisfy all types that have requirements

        # Check roles (if specified)
        if tool.roles:
            has_required_role = any(context.has_role(role) for role in tool.roles)
            if not has_required_role:
                roles_str = ", ".join(tool.roles)
                return (False, f"One of the following roles required: {roles_str}")

        # Check permissions (if specified)
        if tool.permissions:
            has_required_permission = any(context.has_permission(perm) for perm in tool.permissions)
            if not has_required_permission:
                perms_str = ", ".join(tool.permissions)
                return (False, f"One of the following permissions required: {perms_str}")

        # Check scopes (if specified)
        if tool.scopes:
            has_required_scope = any(context.has_scope(scope) for scope in tool.scopes)
            if not has_required_scope:
                scopes_str = ", ".join(tool.scopes)
                return (False, f"One of the following scopes required: {scopes_str}")

        # All requirements satisfied
        return (True, None)
