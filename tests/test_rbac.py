"""
Tests for Role-Based Access Control (RBAC) system.

Tests for Permission, Role, and RBAC classes.
"""

import pytest

from nextmcp.auth.core import AuthContext, Permission, Role
from nextmcp.auth.rbac import RBAC, PermissionDeniedError


class TestPermission:
    """Tests for Permission class."""

    def test_permission_creation(self):
        """Test basic permission creation."""
        perm = Permission(name="read:posts", description="Read blog posts")

        assert perm.name == "read:posts"
        assert perm.description == "Read blog posts"
        assert perm.resource is None

    def test_permission_with_resource(self):
        """Test permission with resource."""
        perm = Permission(name="write:posts", resource="posts")

        assert perm.name == "write:posts"
        assert perm.resource == "posts"

    def test_permission_string(self):
        """Test permission string representation."""
        perm = Permission(name="admin:users")
        assert str(perm) == "admin:users"

    def test_permission_hash_and_equality(self):
        """Test permission hashing and equality."""
        perm1 = Permission(name="read:posts")
        perm2 = Permission(name="read:posts")
        perm3 = Permission(name="write:posts")

        assert perm1 == perm2
        assert perm1 != perm3
        assert hash(perm1) == hash(perm2)
        assert hash(perm1) != hash(perm3)

        # Can be used in sets
        perm_set = {perm1, perm2, perm3}
        assert len(perm_set) == 2  # perm1 and perm2 are the same

    def test_permission_matches_exact(self):
        """Test exact permission matching."""
        perm = Permission(name="read:posts")

        assert perm.matches("read:posts") is True
        assert perm.matches("write:posts") is False

    def test_permission_matches_wildcard(self):
        """Test wildcard permission matching."""
        perm_all = Permission(name="*")
        assert perm_all.matches("read:posts") is True
        assert perm_all.matches("anything") is True

        perm_admin = Permission(name="admin:*")
        assert perm_admin.matches("admin:users") is True
        assert perm_admin.matches("admin:posts") is True
        assert perm_admin.matches("read:posts") is False


class TestRole:
    """Tests for Role class."""

    def test_role_creation(self):
        """Test basic role creation."""
        role = Role(name="admin", description="Administrator")

        assert role.name == "admin"
        assert role.description == "Administrator"
        assert len(role.permissions) == 0

    def test_role_string(self):
        """Test role string representation."""
        role = Role(name="editor")
        assert str(role) == "editor"

    def test_role_hash_and_equality(self):
        """Test role hashing and equality."""
        role1 = Role(name="admin")
        role2 = Role(name="admin")
        role3 = Role(name="editor")

        assert role1 == role2
        assert role1 != role3
        assert hash(role1) == hash(role2)

        # Can be used in sets
        role_set = {role1, role2, role3}
        assert len(role_set) == 2

    def test_add_permission(self):
        """Test adding permissions to role."""
        role = Role(name="editor")

        # Add permission object
        perm1 = Permission(name="read:posts")
        role.add_permission(perm1)
        assert perm1 in role.permissions

        # Add permission by name
        role.add_permission("write:posts")
        assert any(p.name == "write:posts" for p in role.permissions)

    def test_has_permission(self):
        """Test checking if role has permission."""
        role = Role(name="editor")
        role.add_permission(Permission(name="read:posts"))
        role.add_permission(Permission(name="write:posts"))

        assert role.has_permission("read:posts") is True
        assert role.has_permission("write:posts") is True
        assert role.has_permission("delete:posts") is False

    def test_has_permission_wildcard(self):
        """Test role with wildcard permissions."""
        role = Role(name="admin")
        role.add_permission(Permission(name="admin:*"))

        assert role.has_permission("admin:users") is True
        assert role.has_permission("admin:posts") is True
        assert role.has_permission("read:posts") is False


class TestAuthContext:
    """Tests for AuthContext class."""

    def test_auth_context_creation(self):
        """Test basic auth context creation."""
        context = AuthContext(authenticated=True, user_id="user123", username="alice")

        assert context.authenticated is True
        assert context.user_id == "user123"
        assert context.username == "alice"
        assert len(context.roles) == 0
        assert len(context.permissions) == 0

    def test_add_role(self):
        """Test adding roles to context."""
        context = AuthContext(authenticated=True, user_id="user123")

        # Add role object
        role1 = Role(name="admin")
        context.add_role(role1)
        assert role1 in context.roles

        # Add role by name
        context.add_role("editor")
        assert any(r.name == "editor" for r in context.roles)

    def test_add_permission(self):
        """Test adding permissions to context."""
        context = AuthContext(authenticated=True, user_id="user123")

        # Add permission object
        perm1 = Permission(name="read:posts")
        context.add_permission(perm1)
        assert perm1 in context.permissions

        # Add permission by name
        context.add_permission("write:posts")
        assert any(p.name == "write:posts" for p in context.permissions)

    def test_has_role(self):
        """Test checking if context has role."""
        context = AuthContext(authenticated=True, user_id="user123")
        context.add_role(Role(name="admin"))
        context.add_role(Role(name="editor"))

        assert context.has_role("admin") is True
        assert context.has_role("editor") is True
        assert context.has_role("viewer") is False

    def test_has_permission_direct(self):
        """Test checking direct permissions."""
        context = AuthContext(authenticated=True, user_id="user123")
        context.add_permission(Permission(name="read:posts"))

        assert context.has_permission("read:posts") is True
        assert context.has_permission("write:posts") is False

    def test_has_permission_from_role(self):
        """Test checking permissions from roles."""
        # Create role with permissions
        editor_role = Role(name="editor")
        editor_role.add_permission(Permission(name="read:posts"))
        editor_role.add_permission(Permission(name="write:posts"))

        # Create context with role
        context = AuthContext(authenticated=True, user_id="user123")
        context.add_role(editor_role)

        assert context.has_permission("read:posts") is True
        assert context.has_permission("write:posts") is True
        assert context.has_permission("delete:posts") is False


class TestRBAC:
    """Tests for RBAC system."""

    def test_rbac_initialization(self):
        """Test RBAC initialization."""
        rbac = RBAC()

        assert len(rbac.list_roles()) == 0
        assert len(rbac.list_permissions()) == 0

    def test_define_permission(self):
        """Test defining permissions."""
        rbac = RBAC()

        perm = rbac.define_permission("read:posts", "Read blog posts")

        assert perm.name == "read:posts"
        assert perm.description == "Read blog posts"
        assert rbac.get_permission("read:posts") == perm

    def test_define_role(self):
        """Test defining roles."""
        rbac = RBAC()

        role = rbac.define_role("admin", "Administrator")

        assert role.name == "admin"
        assert role.description == "Administrator"
        assert rbac.get_role("admin") == role

    def test_assign_permission_to_role(self):
        """Test assigning permissions to roles."""
        rbac = RBAC()

        rbac.define_permission("read:posts")
        rbac.define_role("viewer")

        rbac.assign_permission_to_role("viewer", "read:posts")

        role = rbac.get_role("viewer")
        assert role.has_permission("read:posts") is True

    def test_assign_permission_auto_create(self):
        """Test auto-creating permission when assigning to role."""
        rbac = RBAC()
        rbac.define_role("editor")

        # Assign permission that doesn't exist yet (should auto-create)
        rbac.assign_permission_to_role("editor", "write:posts")

        role = rbac.get_role("editor")
        assert role.has_permission("write:posts") is True
        assert rbac.get_permission("write:posts") is not None

    def test_assign_permission_invalid_role(self):
        """Test assigning permission to non-existent role."""
        rbac = RBAC()

        with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
            rbac.assign_permission_to_role("nonexistent", "read:posts")

    def test_list_roles_and_permissions(self):
        """Test listing all roles and permissions."""
        rbac = RBAC()

        rbac.define_role("admin")
        rbac.define_role("editor")
        rbac.define_permission("read:posts")
        rbac.define_permission("write:posts")

        assert len(rbac.list_roles()) == 2
        assert len(rbac.list_permissions()) == 2

    def test_check_permission(self):
        """Test checking permissions on auth context."""
        rbac = RBAC()

        # Create role with permission
        rbac.define_role("editor")
        rbac.define_permission("write:posts")
        rbac.assign_permission_to_role("editor", "write:posts")

        # Create auth context with role
        context = AuthContext(authenticated=True, user_id="user123")
        context.add_role(rbac.get_role("editor"))

        assert rbac.check_permission(context, "write:posts") is True
        assert rbac.check_permission(context, "delete:posts") is False

    def test_check_permission_not_authenticated(self):
        """Test permission check fails when not authenticated."""
        rbac = RBAC()

        context = AuthContext(authenticated=False)

        assert rbac.check_permission(context, "any:permission") is False

    def test_check_role(self):
        """Test checking roles on auth context."""
        rbac = RBAC()
        rbac.define_role("admin")

        context = AuthContext(authenticated=True, user_id="user123")
        context.add_role(rbac.get_role("admin"))

        assert rbac.check_role(context, "admin") is True
        assert rbac.check_role(context, "editor") is False

    def test_require_permission_success(self):
        """Test requiring permission succeeds when granted."""
        rbac = RBAC()
        rbac.define_permission("read:posts")

        context = AuthContext(authenticated=True, user_id="user123")
        context.add_permission(rbac.get_permission("read:posts"))

        # Should not raise
        rbac.require_permission(context, "read:posts")

    def test_require_permission_denied(self):
        """Test requiring permission raises when not granted."""
        rbac = RBAC()

        context = AuthContext(authenticated=True, user_id="user123")

        with pytest.raises(PermissionDeniedError, match="Permission 'write:posts' required"):
            rbac.require_permission(context, "write:posts")

    def test_require_role_success(self):
        """Test requiring role succeeds when granted."""
        rbac = RBAC()
        rbac.define_role("admin")

        context = AuthContext(authenticated=True, user_id="user123")
        context.add_role(rbac.get_role("admin"))

        # Should not raise
        rbac.require_role(context, "admin")

    def test_require_role_denied(self):
        """Test requiring role raises when not granted."""
        rbac = RBAC()

        context = AuthContext(authenticated=True, user_id="user123")

        with pytest.raises(PermissionDeniedError, match="Role 'admin' required"):
            rbac.require_role(context, "admin")

    def test_load_from_config(self):
        """Test loading RBAC configuration from dict."""
        rbac = RBAC()

        config = {
            "permissions": [
                {"name": "read:posts", "description": "Read posts"},
                {"name": "write:posts", "description": "Write posts"},
                {"name": "delete:posts", "description": "Delete posts"},
            ],
            "roles": [
                {
                    "name": "viewer",
                    "description": "Read-only access",
                    "permissions": ["read:posts"],
                },
                {
                    "name": "editor",
                    "description": "Can edit content",
                    "permissions": ["read:posts", "write:posts"],
                },
                {
                    "name": "admin",
                    "description": "Full access",
                    "permissions": ["read:posts", "write:posts", "delete:posts"],
                },
            ],
        }

        rbac.load_from_config(config)

        # Check permissions loaded
        assert len(rbac.list_permissions()) == 3
        assert rbac.get_permission("read:posts") is not None

        # Check roles loaded
        assert len(rbac.list_roles()) == 3

        # Check role permissions
        viewer = rbac.get_role("viewer")
        assert viewer.has_permission("read:posts") is True
        assert viewer.has_permission("write:posts") is False

        editor = rbac.get_role("editor")
        assert editor.has_permission("read:posts") is True
        assert editor.has_permission("write:posts") is True
        assert editor.has_permission("delete:posts") is False

        admin = rbac.get_role("admin")
        assert admin.has_permission("read:posts") is True
        assert admin.has_permission("write:posts") is True
        assert admin.has_permission("delete:posts") is True

    def test_to_dict(self):
        """Test exporting RBAC configuration to dict."""
        rbac = RBAC()

        rbac.define_permission("read:posts", "Read posts")
        rbac.define_permission("write:posts", "Write posts")

        rbac.define_role("viewer", "Read-only")
        rbac.assign_permission_to_role("viewer", "read:posts")

        rbac.define_role("editor", "Can edit")
        rbac.assign_permission_to_role("editor", "read:posts")
        rbac.assign_permission_to_role("editor", "write:posts")

        config = rbac.to_dict()

        assert "permissions" in config
        assert "roles" in config
        assert len(config["permissions"]) == 2
        assert len(config["roles"]) == 2

        # Check permission in export
        perm_names = [p["name"] for p in config["permissions"]]
        assert "read:posts" in perm_names
        assert "write:posts" in perm_names

        # Check role in export
        editor_role = next(r for r in config["roles"] if r["name"] == "editor")
        assert "read:posts" in editor_role["permissions"]
        assert "write:posts" in editor_role["permissions"]


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError exception."""

    def test_error_creation(self):
        """Test creating permission denied error."""
        error = PermissionDeniedError("Access denied", required="admin:users", user_id="user123")

        assert str(error) == "Access denied"
        assert error.required == "admin:users"
        assert error.user_id == "user123"

    def test_error_without_details(self):
        """Test error without required/user_id details."""
        error = PermissionDeniedError("Access denied")

        assert str(error) == "Access denied"
        assert error.required is None
        assert error.user_id is None
