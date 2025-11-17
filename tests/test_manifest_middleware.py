"""
Tests for manifest-middleware integration.

Tests @requires_manifest decorator for enforcing PermissionManifest at runtime.
"""

import pytest

from nextmcp.auth.core import AuthContext, Permission, Role
from nextmcp.auth.errors import ManifestViolationError
from nextmcp.auth.manifest import PermissionManifest
from nextmcp.auth.middleware import requires_auth_async, requires_manifest_async
from nextmcp.auth.providers import APIKeyProvider


class MockAuthProvider(APIKeyProvider):
    """Mock auth provider for testing."""

    def __init__(self, **kwargs):
        # Accept custom valid_keys or use default
        if 'valid_keys' not in kwargs:
            kwargs['valid_keys'] = {"test_key": {"user_id": "user123"}}
        super().__init__(**kwargs)


@pytest.fixture
def auth_provider():
    """Create mock auth provider."""
    return MockAuthProvider()


@pytest.fixture
def simple_manifest():
    """Create a simple permission manifest for testing."""
    manifest = PermissionManifest()

    # Define a tool requiring admin role
    manifest.define_tool_permission(
        tool_name="admin_tool",
        roles=["admin"],
    )

    # Define a tool requiring read permission
    manifest.define_tool_permission(
        tool_name="read_tool",
        permissions=["read:data"],
    )

    # Define a tool requiring OAuth scope
    manifest.define_tool_permission(
        tool_name="oauth_tool",
        scopes=["repo:read"],
    )

    # Define a tool with multiple requirements
    manifest.define_tool_permission(
        tool_name="strict_tool",
        roles=["admin"],
        permissions=["write:data"],
        scopes=["admin:full"],
    )

    return manifest


class TestRequiresManifestAsync:
    """Tests for @requires_manifest_async decorator."""

    @pytest.mark.asyncio
    async def test_manifest_allows_unrestricted_tool(self, auth_provider, simple_manifest):
        """Test that tools not in manifest are allowed."""

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="unrestricted_tool")
        async def unrestricted_tool(auth: AuthContext):
            return f"Success for {auth.user_id}"

        result = await unrestricted_tool(auth={"api_key": "test_key"})
        assert result == "Success for user123"

    @pytest.mark.asyncio
    async def test_manifest_allows_with_required_role(self, auth_provider, simple_manifest):
        """Test manifest allows access when user has required role."""

        # Mock provider that adds admin role
        class AdminAuthProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_role(Role("admin"))
                return result

        admin_provider = AdminAuthProvider(valid_keys={"admin_key": {"user_id": "admin_user"}})

        @requires_auth_async(provider=admin_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="admin_tool")
        async def admin_tool(auth: AuthContext):
            return "Admin action completed"

        result = await admin_tool(auth={"api_key": "admin_key"})
        assert result == "Admin action completed"

    @pytest.mark.asyncio
    async def test_manifest_denies_without_required_role(self, auth_provider, simple_manifest):
        """Test manifest denies access when user lacks required role."""

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="admin_tool")
        async def admin_tool(auth: AuthContext):
            return "Should not reach here"

        with pytest.raises(ManifestViolationError) as exc_info:
            await admin_tool(auth={"api_key": "test_key"})

        assert exc_info.value.tool_name == "admin_tool"
        assert "admin" in exc_info.value.required_roles

    @pytest.mark.asyncio
    async def test_manifest_allows_with_required_permission(self, auth_provider, simple_manifest):
        """Test manifest allows access when user has required permission."""

        # Mock provider that adds read permission
        class ReadAuthProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_permission(Permission("read:data"))
                return result

        read_provider = ReadAuthProvider(valid_keys={"read_key": {"user_id": "read_user"}})

        @requires_auth_async(provider=read_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="read_tool")
        async def read_tool(auth: AuthContext):
            return "Read completed"

        result = await read_tool(auth={"api_key": "read_key"})
        assert result == "Read completed"

    @pytest.mark.asyncio
    async def test_manifest_denies_without_required_permission(self, auth_provider, simple_manifest):
        """Test manifest denies access when user lacks required permission."""

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="read_tool")
        async def read_tool(auth: AuthContext):
            return "Should not reach here"

        with pytest.raises(ManifestViolationError) as exc_info:
            await read_tool(auth={"api_key": "test_key"})

        assert exc_info.value.tool_name == "read_tool"
        assert "read:data" in exc_info.value.required_permissions

    @pytest.mark.asyncio
    async def test_manifest_allows_with_required_scope(self, auth_provider, simple_manifest):
        """Test manifest allows access when user has required scope."""

        # Mock provider that adds OAuth scope
        class OAuthAuthProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_scope("repo:read")
                return result

        oauth_provider = OAuthAuthProvider(valid_keys={"oauth_key": {"user_id": "oauth_user"}})

        @requires_auth_async(provider=oauth_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="oauth_tool")
        async def oauth_tool(auth: AuthContext):
            return "OAuth action completed"

        result = await oauth_tool(auth={"api_key": "oauth_key"})
        assert result == "OAuth action completed"

    @pytest.mark.asyncio
    async def test_manifest_denies_without_required_scope(self, auth_provider, simple_manifest):
        """Test manifest denies access when user lacks required scope."""

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="oauth_tool")
        async def oauth_tool(auth: AuthContext):
            return "Should not reach here"

        with pytest.raises(ManifestViolationError) as exc_info:
            await oauth_tool(auth={"api_key": "test_key"})

        assert exc_info.value.tool_name == "oauth_tool"
        assert "repo:read" in exc_info.value.required_scopes

    @pytest.mark.asyncio
    async def test_manifest_requires_all_requirement_types(self, auth_provider, simple_manifest):
        """Test manifest requires ALL types (role AND permission AND scope)."""

        # Provider with role only
        class RoleOnlyProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_role(Role("admin"))
                return result

        role_provider = RoleOnlyProvider(valid_keys={"key": {"user_id": "user"}})

        @requires_auth_async(provider=role_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="strict_tool")
        async def strict_tool(auth: AuthContext):
            return "Should not reach here"

        # Should fail because missing permission and scope
        with pytest.raises(ManifestViolationError):
            await strict_tool(auth={"api_key": "key"})

    @pytest.mark.asyncio
    async def test_manifest_allows_with_all_requirements(self, auth_provider, simple_manifest):
        """Test manifest allows when user has ALL requirements."""

        # Provider with all requirements
        class FullAuthProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_role(Role("admin"))
                    result.context.add_permission(Permission("write:data"))
                    result.context.add_scope("admin:full")
                return result

        full_provider = FullAuthProvider(valid_keys={"full_key": {"user_id": "full_user"}})

        @requires_auth_async(provider=full_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="strict_tool")
        async def strict_tool(auth: AuthContext):
            return "All requirements met"

        result = await strict_tool(auth={"api_key": "full_key"})
        assert result == "All requirements met"

    @pytest.mark.asyncio
    async def test_manifest_error_contains_user_context(self, auth_provider, simple_manifest):
        """Test ManifestViolationError contains user context."""

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=simple_manifest, tool_name="admin_tool")
        async def admin_tool(auth: AuthContext):
            return "Should not reach here"

        with pytest.raises(ManifestViolationError) as exc_info:
            await admin_tool(auth={"api_key": "test_key"})

        error = exc_info.value
        assert error.user_id == "user123"
        assert error.auth_context is not None
        assert error.auth_context.user_id == "user123"

    @pytest.mark.asyncio
    async def test_manifest_decorator_without_tool_name(self, auth_provider, simple_manifest):
        """Test decorator can infer tool name from function name."""

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=simple_manifest)  # No tool_name specified
        async def read_tool(auth: AuthContext):
            return "Should not reach here"

        # Should use function name "read_tool" and check manifest
        with pytest.raises(ManifestViolationError) as exc_info:
            await read_tool(auth={"api_key": "test_key"})

        assert exc_info.value.tool_name == "read_tool"

    @pytest.mark.asyncio
    async def test_manifest_with_empty_manifest(self, auth_provider):
        """Test decorator with empty manifest (no restrictions)."""
        empty_manifest = PermissionManifest()

        @requires_auth_async(provider=auth_provider)
        @requires_manifest_async(manifest=empty_manifest, tool_name="any_tool")
        async def any_tool(auth: AuthContext):
            return "Allowed"

        result = await any_tool(auth={"api_key": "test_key"})
        assert result == "Allowed"


class TestManifestIntegrationPatterns:
    """Tests for common manifest integration patterns."""

    @pytest.mark.asyncio
    async def test_multiple_tools_with_shared_manifest(self, auth_provider):
        """Test multiple tools sharing a manifest."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("tool1", roles=["editor"])
        manifest.define_tool_permission("tool2", roles=["viewer", "editor"])

        # Provider that adds editor role
        class EditorProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_role(Role("editor"))
                return result

        editor_provider = EditorProvider(valid_keys={"key": {"user_id": "user"}})

        @requires_auth_async(provider=editor_provider)
        @requires_manifest_async(manifest=manifest, tool_name="tool1")
        async def tool1(auth: AuthContext):
            return "Tool 1"

        @requires_auth_async(provider=editor_provider)
        @requires_manifest_async(manifest=manifest, tool_name="tool2")
        async def tool2(auth: AuthContext):
            return "Tool 2"

        # Both should succeed
        assert await tool1(auth={"api_key": "key"}) == "Tool 1"
        assert await tool2(auth={"api_key": "key"}) == "Tool 2"

    @pytest.mark.asyncio
    async def test_manifest_with_wildcard_permission(self, auth_provider):
        """Test manifest with wildcard permission matching."""
        manifest = PermissionManifest()
        manifest.define_tool_permission("data_tool", permissions=["data:read"])

        # Provider that adds wildcard permission
        class WildcardProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_permission(Permission("data:*"))
                return result

        wildcard_provider = WildcardProvider(valid_keys={"key": {"user_id": "user"}})

        @requires_auth_async(provider=wildcard_provider)
        @requires_manifest_async(manifest=manifest, tool_name="data_tool")
        async def data_tool(auth: AuthContext):
            return "Data access granted"

        result = await data_tool(auth={"api_key": "key"})
        assert result == "Data access granted"

    @pytest.mark.asyncio
    async def test_manifest_loaded_from_dict(self, auth_provider):
        """Test manifest loaded from dictionary configuration."""
        manifest = PermissionManifest()
        manifest.load_from_dict({
            "tools": {
                "query_db": {
                    "roles": ["analyst"],
                }
            }
        })

        # Provider with analyst role
        class AnalystProvider(APIKeyProvider):
            async def authenticate(self, credentials):
                result = await super().authenticate(credentials)
                if result.success:
                    result.context.add_role(Role("analyst"))
                return result

        analyst_provider = AnalystProvider(valid_keys={"key": {"user_id": "user"}})

        @requires_auth_async(provider=analyst_provider)
        @requires_manifest_async(manifest=manifest, tool_name="query_db")
        async def query_db(auth: AuthContext):
            return "Query executed"

        result = await query_db(auth={"api_key": "key"})
        assert result == "Query executed"
