"""
Tests for Permission Manifest system.

Tests for declarative security definitions using manifests.
"""

import tempfile
from pathlib import Path

import pytest

from nextmcp.auth.core import AuthContext, Permission, Role
from nextmcp.auth.manifest import PermissionManifest, ScopeDefinition, ToolPermission


class TestScopeDefinition:
    """Tests for ScopeDefinition dataclass."""

    def test_scope_definition_creation(self):
        """Test creating a ScopeDefinition."""
        scope = ScopeDefinition(
            name="read:data",
            description="Read access to data",
            oauth_mapping={"github": ["repo:read"], "google": ["drive.readonly"]},
        )

        assert scope.name == "read:data"
        assert scope.description == "Read access to data"
        assert scope.oauth_mapping["github"] == ["repo:read"]
        assert scope.oauth_mapping["google"] == ["drive.readonly"]

    def test_scope_definition_minimal(self):
        """Test creating ScopeDefinition with minimal fields."""
        scope = ScopeDefinition(name="write:data", description="Write data")

        assert scope.name == "write:data"
        assert scope.description == "Write data"
        assert scope.oauth_mapping == {}

    def test_scope_definition_no_description(self):
        """Test ScopeDefinition with empty description."""
        scope = ScopeDefinition(name="delete:data", description="")

        assert scope.name == "delete:data"
        assert scope.description == ""


class TestToolPermission:
    """Tests for ToolPermission dataclass."""

    def test_tool_permission_creation(self):
        """Test creating a ToolPermission."""
        tool = ToolPermission(
            tool_name="query_database",
            permissions=["read:data"],
            scopes=["db.query.read"],
            roles=["viewer", "editor"],
            description="Execute database queries",
            dangerous=False,
        )

        assert tool.tool_name == "query_database"
        assert tool.permissions == ["read:data"]
        assert tool.scopes == ["db.query.read"]
        assert tool.roles == ["viewer", "editor"]
        assert tool.description == "Execute database queries"
        assert tool.dangerous is False

    def test_tool_permission_minimal(self):
        """Test ToolPermission with minimal fields."""
        tool = ToolPermission(tool_name="simple_tool")

        assert tool.tool_name == "simple_tool"
        assert tool.permissions == []
        assert tool.scopes == []
        assert tool.roles == []
        assert tool.description == ""
        assert tool.dangerous is False

    def test_tool_permission_dangerous_flag(self):
        """Test ToolPermission with dangerous flag."""
        tool = ToolPermission(tool_name="delete_all", dangerous=True)

        assert tool.dangerous is True


class TestPermissionManifest:
    """Tests for PermissionManifest class."""

    def test_manifest_initialization(self):
        """Test creating an empty PermissionManifest."""
        manifest = PermissionManifest()

        assert manifest.scopes == {}
        assert manifest.tools == {}

    def test_define_scope(self):
        """Test defining a scope in the manifest."""
        manifest = PermissionManifest()

        scope = manifest.define_scope(
            name="read:data", description="Read data", oauth_mapping={"github": ["repo:read"]}
        )

        assert isinstance(scope, ScopeDefinition)
        assert scope.name == "read:data"
        assert "read:data" in manifest.scopes
        assert manifest.scopes["read:data"] == scope

    def test_define_multiple_scopes(self):
        """Test defining multiple scopes."""
        manifest = PermissionManifest()

        manifest.define_scope("read:data", "Read data")
        manifest.define_scope("write:data", "Write data")
        manifest.define_scope("delete:data", "Delete data")

        assert len(manifest.scopes) == 3
        assert "read:data" in manifest.scopes
        assert "write:data" in manifest.scopes
        assert "delete:data" in manifest.scopes

    def test_define_tool_permission(self):
        """Test defining a tool permission."""
        manifest = PermissionManifest()

        tool = manifest.define_tool_permission(
            tool_name="query_db",
            permissions=["read:data"],
            scopes=["db.query.read"],
            roles=["viewer"],
        )

        assert isinstance(tool, ToolPermission)
        assert tool.tool_name == "query_db"
        assert "query_db" in manifest.tools
        assert manifest.tools["query_db"] == tool

    def test_define_multiple_tool_permissions(self):
        """Test defining multiple tool permissions."""
        manifest = PermissionManifest()

        manifest.define_tool_permission("tool1", permissions=["read"])
        manifest.define_tool_permission("tool2", scopes=["scope1"])
        manifest.define_tool_permission("tool3", roles=["admin"])

        assert len(manifest.tools) == 3
        assert "tool1" in manifest.tools
        assert "tool2" in manifest.tools
        assert "tool3" in manifest.tools

    def test_load_from_dict(self):
        """Test loading manifest from dictionary."""
        manifest = PermissionManifest()

        data = {
            "scopes": [
                {
                    "name": "read:data",
                    "description": "Read data",
                    "oauth_mapping": {"github": ["repo:read"]},
                },
                {"name": "write:data", "description": "Write data"},
            ],
            "tools": {
                "query_db": {
                    "permissions": ["read:data"],
                    "scopes": ["db.query.read"],
                    "roles": ["viewer"],
                    "description": "Query database",
                    "dangerous": False,
                },
                "delete_data": {
                    "permissions": ["delete:data"],
                    "scopes": ["db.delete"],
                    "roles": ["admin"],
                    "dangerous": True,
                },
            },
        }

        manifest.load_from_dict(data)

        # Check scopes loaded
        assert len(manifest.scopes) == 2
        assert "read:data" in manifest.scopes
        assert "write:data" in manifest.scopes
        assert manifest.scopes["read:data"].oauth_mapping["github"] == ["repo:read"]

        # Check tools loaded
        assert len(manifest.tools) == 2
        assert "query_db" in manifest.tools
        assert "delete_data" in manifest.tools
        assert manifest.tools["query_db"].permissions == ["read:data"]
        assert manifest.tools["delete_data"].dangerous is True

    def test_load_from_dict_empty(self):
        """Test loading empty manifest."""
        manifest = PermissionManifest()
        manifest.load_from_dict({})

        assert len(manifest.scopes) == 0
        assert len(manifest.tools) == 0

    def test_load_from_dict_scopes_only(self):
        """Test loading manifest with only scopes."""
        manifest = PermissionManifest()

        data = {"scopes": [{"name": "read:data", "description": "Read"}]}

        manifest.load_from_dict(data)

        assert len(manifest.scopes) == 1
        assert len(manifest.tools) == 0

    def test_load_from_dict_tools_only(self):
        """Test loading manifest with only tools."""
        manifest = PermissionManifest()

        data = {"tools": {"tool1": {"permissions": ["read"]}}}

        manifest.load_from_dict(data)

        assert len(manifest.scopes) == 0
        assert len(manifest.tools) == 1

    def test_to_dict(self):
        """Test exporting manifest to dictionary."""
        manifest = PermissionManifest()

        manifest.define_scope("read:data", "Read", {"github": ["repo:read"]})
        manifest.define_tool_permission("query", permissions=["read:data"], dangerous=False)

        result = manifest.to_dict()

        assert "scopes" in result
        assert "tools" in result
        assert len(result["scopes"]) == 1
        assert len(result["tools"]) == 1
        assert result["scopes"][0]["name"] == "read:data"
        assert "query" in result["tools"]

    def test_to_dict_empty(self):
        """Test exporting empty manifest."""
        manifest = PermissionManifest()
        result = manifest.to_dict()

        assert result == {"scopes": [], "tools": {}}


class TestManifestAccessControl:
    """Tests for manifest-based access control."""

    def test_check_tool_access_no_restrictions(self):
        """Test tool access when tool is not in manifest."""
        manifest = PermissionManifest()
        context = AuthContext(authenticated=True, user_id="user1")

        allowed, error = manifest.check_tool_access("unknown_tool", context)

        assert allowed is True
        assert error is None

    def test_check_tool_access_with_role_success(self):
        """Test tool access with required role - success."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("admin_tool", roles=["admin"])

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_role(Role("admin"))

        allowed, error = manifest.check_tool_access("admin_tool", context)

        assert allowed is True
        assert error is None

    def test_check_tool_access_with_role_failure(self):
        """Test tool access with required role - missing role."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("admin_tool", roles=["admin"])

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_role(Role("viewer"))

        allowed, error = manifest.check_tool_access("admin_tool", context)

        assert allowed is False
        assert error is not None
        assert "admin" in error

    def test_check_tool_access_with_permission_success(self):
        """Test tool access with required permission - success."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("read_tool", permissions=["read:data"])

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_permission(Permission("read:data"))

        allowed, error = manifest.check_tool_access("read_tool", context)

        assert allowed is True
        assert error is None

    def test_check_tool_access_with_permission_failure(self):
        """Test tool access with required permission - missing permission."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("write_tool", permissions=["write:data"])

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_permission(Permission("read:data"))

        allowed, error = manifest.check_tool_access("write_tool", context)

        assert allowed is False
        assert error is not None
        assert "write:data" in error

    def test_check_tool_access_with_scope_success(self):
        """Test tool access with required scope - success."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("oauth_tool", scopes=["repo:read"])

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_scope("repo:read")

        allowed, error = manifest.check_tool_access("oauth_tool", context)

        assert allowed is True
        assert error is None

    def test_check_tool_access_with_scope_failure(self):
        """Test tool access with required scope - missing scope."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("oauth_tool", scopes=["repo:write"])

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_scope("repo:read")

        allowed, error = manifest.check_tool_access("oauth_tool", context)

        assert allowed is False
        assert error is not None
        assert "repo:write" in error

    def test_check_tool_access_multiple_requirements_any_match(self):
        """Test tool access with multiple requirements - any one matches."""
        manifest = PermissionManifest()
        manifest.define_tool_permission(
            "multi_tool", permissions=["read:data", "write:data", "admin:all"]
        )

        context = AuthContext(authenticated=True, user_id="user1")
        context.add_permission(Permission("write:data"))  # Has one of the required permissions

        allowed, error = manifest.check_tool_access("multi_tool", context)

        assert allowed is True
        assert error is None

    def test_check_tool_access_combined_role_and_permission(self):
        """Test tool access with both role and permission requirements."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("combined_tool", roles=["editor"], permissions=["edit:data"])

        # Has role but not permission
        context1 = AuthContext(authenticated=True, user_id="user1")
        context1.add_role(Role("editor"))

        allowed, error = manifest.check_tool_access("combined_tool", context1)
        # Should fail because missing permission
        assert allowed is False

        # Has both role and permission
        context2 = AuthContext(authenticated=True, user_id="user2")
        context2.add_role(Role("editor"))
        context2.add_permission(Permission("edit:data"))

        allowed, error = manifest.check_tool_access("combined_tool", context2)
        assert allowed is True

    def test_check_tool_access_all_three_types(self):
        """Test tool access requiring role, permission, AND scope."""
        manifest = PermissionManifest()
        manifest.define_tool_permission(
            "strict_tool", roles=["admin"], permissions=["admin:all"], scopes=["admin:full"]
        )

        # Missing all three
        context1 = AuthContext(authenticated=True, user_id="user1")
        allowed, _ = manifest.check_tool_access("strict_tool", context1)
        assert allowed is False

        # Has role only
        context2 = AuthContext(authenticated=True, user_id="user2")
        context2.add_role(Role("admin"))
        allowed, _ = manifest.check_tool_access("strict_tool", context2)
        assert allowed is False  # Still needs permission AND scope

        # Has all three
        context3 = AuthContext(authenticated=True, user_id="user3")
        context3.add_role(Role("admin"))
        context3.add_permission(Permission("admin:all"))
        context3.add_scope("admin:full")
        allowed, _ = manifest.check_tool_access("strict_tool", context3)
        assert allowed is True


class TestManifestYAMLLoading:
    """Tests for loading manifests from YAML files."""

    def test_load_from_yaml_file(self):
        """Test loading manifest from YAML file."""
        manifest = PermissionManifest()

        yaml_content = """
scopes:
  - name: "read:data"
    description: "Read access"
    oauth_mapping:
      github: ["repo:read"]
  - name: "write:data"
    description: "Write access"

tools:
  query_tool:
    scopes: ["read:data"]
    permissions: ["read:db"]
    description: "Query database"
  write_tool:
    scopes: ["write:data"]
    dangerous: true
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            manifest.load_from_yaml(yaml_path)

            assert len(manifest.scopes) == 2
            assert "read:data" in manifest.scopes
            assert "write:data" in manifest.scopes

            assert len(manifest.tools) == 2
            assert "query_tool" in manifest.tools
            assert "write_tool" in manifest.tools
            assert manifest.tools["write_tool"].dangerous is True

        finally:
            Path(yaml_path).unlink()

    def test_load_from_yaml_invalid_file(self):
        """Test loading from non-existent YAML file raises error."""
        manifest = PermissionManifest()

        with pytest.raises(FileNotFoundError):
            manifest.load_from_yaml("/nonexistent/file.yaml")


class TestManifestEdgeCases:
    """Tests for edge cases in manifest handling."""

    def test_scope_with_special_characters(self):
        """Test scopes with special characters."""
        manifest = PermissionManifest()

        manifest.define_scope("https://api.example.com/read", "URL scope")
        manifest.define_scope("admin:*", "Wildcard scope")

        assert len(manifest.scopes) == 2

    def test_tool_with_empty_requirements(self):
        """Test tool with all empty requirement lists."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("open_tool", permissions=[], scopes=[], roles=[])

        context = AuthContext(authenticated=True, user_id="user1")
        allowed, error = manifest.check_tool_access("open_tool", context)

        # Should allow access since no requirements
        assert allowed is True
        assert error is None

    def test_manifest_overwrite_scope(self):
        """Test that redefining a scope overwrites it."""
        manifest = PermissionManifest()

        manifest.define_scope("data:read", "First description")
        manifest.define_scope("data:read", "Second description")

        assert len(manifest.scopes) == 1
        assert manifest.scopes["data:read"].description == "Second description"

    def test_manifest_overwrite_tool(self):
        """Test that redefining a tool overwrites it."""
        manifest = PermissionManifest()

        manifest.define_tool_permission("tool1", permissions=["old"])
        manifest.define_tool_permission("tool1", permissions=["new"])

        assert len(manifest.tools) == 1
        assert manifest.tools["tool1"].permissions == ["new"]

    def test_to_dict_round_trip(self):
        """Test that to_dict and load_from_dict are inverses."""
        manifest1 = PermissionManifest()

        manifest1.define_scope("read", "Read", {"gh": ["repo:read"]})
        manifest1.define_tool_permission("tool1", permissions=["read"], dangerous=True)

        # Export to dict
        data = manifest1.to_dict()

        # Load into new manifest
        manifest2 = PermissionManifest()
        manifest2.load_from_dict(data)

        # Should be equivalent
        assert len(manifest2.scopes) == len(manifest1.scopes)
        assert len(manifest2.tools) == len(manifest1.tools)
        assert "read" in manifest2.scopes
        assert "tool1" in manifest2.tools
        assert manifest2.tools["tool1"].dangerous is True
