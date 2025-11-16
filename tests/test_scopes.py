"""
Tests for OAuth scope system.

Tests for scope support in AuthContext and scope-based authorization decorators.
"""

import pytest

from nextmcp.auth.core import AuthContext, Permission, Role
from nextmcp.auth.middleware import AuthenticationError, requires_auth_async, requires_scope_async


class TestAuthContextScopes:
    """Tests for scope support in AuthContext."""

    def test_auth_context_with_scopes(self):
        """Test creating AuthContext with scopes."""
        context = AuthContext(
            authenticated=True,
            user_id="user123",
            scopes={"read:data", "write:data"},
        )

        assert context.authenticated is True
        assert context.user_id == "user123"
        assert len(context.scopes) == 2
        assert "read:data" in context.scopes
        assert "write:data" in context.scopes

    def test_auth_context_default_empty_scopes(self):
        """Test that AuthContext has empty scopes by default."""
        context = AuthContext(authenticated=True, user_id="user123")

        assert context.scopes == set()
        assert len(context.scopes) == 0

    def test_has_scope_returns_true_for_existing_scope(self):
        """Test has_scope returns True for scopes that exist."""
        context = AuthContext(
            authenticated=True,
            user_id="user123",
            scopes={"read:data", "write:data", "admin:all"},
        )

        assert context.has_scope("read:data") is True
        assert context.has_scope("write:data") is True
        assert context.has_scope("admin:all") is True

    def test_has_scope_returns_false_for_missing_scope(self):
        """Test has_scope returns False for scopes that don't exist."""
        context = AuthContext(authenticated=True, user_id="user123", scopes={"read:data"})

        assert context.has_scope("write:data") is False
        assert context.has_scope("admin:all") is False
        assert context.has_scope("delete:data") is False

    def test_has_scope_case_sensitive(self):
        """Test that scope checking is case-sensitive."""
        context = AuthContext(authenticated=True, user_id="user123", scopes={"read:data"})

        assert context.has_scope("read:data") is True
        assert context.has_scope("READ:DATA") is False
        assert context.has_scope("Read:Data") is False

    def test_add_scope_single(self):
        """Test adding a single scope to AuthContext."""
        context = AuthContext(authenticated=True, user_id="user123")

        context.add_scope("read:data")

        assert context.has_scope("read:data") is True
        assert len(context.scopes) == 1

    def test_add_scope_multiple(self):
        """Test adding multiple scopes to AuthContext."""
        context = AuthContext(authenticated=True, user_id="user123")

        context.add_scope("read:data")
        context.add_scope("write:data")
        context.add_scope("admin:all")

        assert len(context.scopes) == 3
        assert context.has_scope("read:data") is True
        assert context.has_scope("write:data") is True
        assert context.has_scope("admin:all") is True

    def test_add_scope_duplicate_ignored(self):
        """Test that adding duplicate scopes doesn't create duplicates."""
        context = AuthContext(authenticated=True, user_id="user123")

        context.add_scope("read:data")
        context.add_scope("read:data")  # Duplicate
        context.add_scope("read:data")  # Duplicate

        assert len(context.scopes) == 1
        assert context.has_scope("read:data") is True

    def test_scopes_and_permissions_coexist(self):
        """Test that scopes and permissions can coexist in AuthContext."""
        context = AuthContext(
            authenticated=True,
            user_id="user123",
            permissions={Permission("read:posts"), Permission("write:posts")},
            scopes={"repo:read", "repo:write"},
        )

        # Check permissions
        assert context.has_permission("read:posts") is True
        assert context.has_permission("write:posts") is True

        # Check scopes
        assert context.has_scope("repo:read") is True
        assert context.has_scope("repo:write") is True

        # Verify they're separate
        assert context.has_permission("repo:read") is False  # Not a permission
        assert context.has_scope("read:posts") is False  # Not a scope

    def test_scopes_and_roles_coexist(self):
        """Test that scopes and roles can coexist in AuthContext."""
        context = AuthContext(
            authenticated=True,
            user_id="user123",
            roles={Role("admin"), Role("editor")},
            scopes={"repo:read", "repo:write"},
        )

        # Check roles
        assert context.has_role("admin") is True
        assert context.has_role("editor") is True

        # Check scopes
        assert context.has_scope("repo:read") is True
        assert context.has_scope("repo:write") is True


class MockAuthProvider:
    """Mock auth provider for testing."""

    async def authenticate(self, credentials):
        from nextmcp.auth.core import AuthResult

        if credentials.get("valid"):
            context = AuthContext(
                authenticated=True,
                user_id="user123",
                scopes=set(credentials.get("scopes", [])),
            )
            return AuthResult.success_result(context)
        return AuthResult.failure("Invalid credentials")


class TestRequiresScopeDecorator:
    """Tests for @requires_scope_async decorator."""

    @pytest.mark.asyncio
    async def test_requires_scope_single_scope_success(self):
        """Test @requires_scope_async with single scope - success case."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("read:data")
        async def protected_function(auth: AuthContext):
            return f"Success for {auth.user_id}"

        # Call with valid credentials including required scope
        result = await protected_function(auth={"valid": True, "scopes": ["read:data"]})

        assert result == "Success for user123"

    @pytest.mark.asyncio
    async def test_requires_scope_single_scope_failure(self):
        """Test @requires_scope_async with single scope - missing scope."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("write:data")
        async def protected_function(auth: AuthContext):
            return f"Success for {auth.user_id}"

        # Call with valid credentials but missing required scope
        with pytest.raises(Exception) as exc_info:
            await protected_function(auth={"valid": True, "scopes": ["read:data"]})

        # Should raise an error about insufficient scopes
        assert "scope" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_requires_scope_multiple_scopes_any_matches(self):
        """Test @requires_scope_async with multiple scopes - any one matches."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("read:data", "write:data", "admin:all")
        async def protected_function(auth: AuthContext):
            return f"Success for {auth.user_id}"

        # User has write:data (one of the required scopes)
        result = await protected_function(auth={"valid": True, "scopes": ["write:data"]})
        assert result == "Success for user123"

        # User has admin:all (another required scope)
        result = await protected_function(auth={"valid": True, "scopes": ["admin:all"]})
        assert result == "Success for user123"

    @pytest.mark.asyncio
    async def test_requires_scope_multiple_scopes_none_match(self):
        """Test @requires_scope_async with multiple scopes - none match."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("read:data", "write:data", "admin:all")
        async def protected_function(auth: AuthContext):
            return f"Success for {auth.user_id}"

        # User has different scope
        with pytest.raises(Exception):
            await protected_function(auth={"valid": True, "scopes": ["other:scope"]})

    @pytest.mark.asyncio
    async def test_requires_scope_with_multiple_user_scopes(self):
        """Test @requires_scope_async when user has multiple scopes."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("write:data")
        async def protected_function(auth: AuthContext):
            return f"Success for {auth.user_id}"

        # User has multiple scopes including the required one
        result = await protected_function(
            auth={"valid": True, "scopes": ["read:data", "write:data", "admin:all"]}
        )
        assert result == "Success for user123"

    @pytest.mark.asyncio
    async def test_requires_scope_preserves_function_metadata(self):
        """Test that @requires_scope_async preserves function metadata."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("read:data")
        async def my_function(auth: AuthContext):
            """My function docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My function docstring."

    @pytest.mark.asyncio
    async def test_requires_scope_without_auth_decorator_fails(self):
        """Test that @requires_scope_async requires @requires_auth_async."""

        @requires_scope_async("read:data")
        async def unprotected_function(param: str):
            return f"Result: {param}"

        # Should fail because first argument is not AuthContext
        with pytest.raises(AuthenticationError, match="requires_scope_async must be used with"):
            await unprotected_function("test")

    @pytest.mark.asyncio
    async def test_requires_scope_stacking_multiple_decorators(self):
        """Test stacking multiple @requires_scope_async decorators."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("read:data")
        @requires_scope_async("write:data")
        async def protected_function(auth: AuthContext):
            return f"Success for {auth.user_id}"

        # User must have both scopes
        result = await protected_function(
            auth={"valid": True, "scopes": ["read:data", "write:data"]}
        )
        assert result == "Success for user123"

        # Missing one scope should fail
        with pytest.raises(Exception):
            await protected_function(auth={"valid": True, "scopes": ["read:data"]})

    @pytest.mark.asyncio
    async def test_requires_scope_with_sync_function(self):
        """Test @requires_scope_async works with sync functions too."""
        provider = MockAuthProvider()

        @requires_auth_async(provider=provider)
        @requires_scope_async("read:data")
        def sync_protected_function(auth: AuthContext):
            return f"Sync success for {auth.user_id}"

        # Wrapper is async even if decorated function is sync
        result = await sync_protected_function(auth={"valid": True, "scopes": ["read:data"]})
        assert result == "Sync success for user123"


class TestScopeIntegrationWithOAuth:
    """Tests for scope integration with OAuth providers."""

    @pytest.mark.asyncio
    async def test_oauth_provider_adds_scopes_to_context(self):
        """Test that OAuth providers correctly add scopes to AuthContext."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from nextmcp.auth.oauth import OAuthConfig, OAuthProvider

        class TestOAuthProvider(OAuthProvider):
            async def get_user_info(self, access_token):
                return {"id": "123", "login": "testuser"}

            def get_additional_auth_params(self):
                return {}

            def extract_user_id(self, user_info):
                return str(user_info["id"])

        config = OAuthConfig(
            client_id="test_client",
            token_url="https://test.com/token",
        )

        provider = TestOAuthProvider(config)

        # Authenticate with scopes
        credentials = {
            "access_token": "test_token",
            "scopes": ["repo:read", "repo:write", "user:email"],
        }

        result = await provider.authenticate(credentials)

        assert result.success is True
        assert result.context is not None

        # Verify scopes were added as permissions (current behavior)
        assert result.context.has_permission("repo:read") is True
        assert result.context.has_permission("repo:write") is True
        assert result.context.has_permission("user:email") is True

    @pytest.mark.asyncio
    async def test_oauth_with_scope_decorator(self):
        """Test OAuth authentication with scope-based access control."""
        from unittest.mock import AsyncMock

        from nextmcp.auth.oauth import OAuthConfig, OAuthProvider

        class TestOAuthProvider(OAuthProvider):
            async def get_user_info(self, access_token):
                return {"id": "123", "login": "testuser"}

            def get_additional_auth_params(self):
                return {}

            def extract_user_id(self, user_info):
                return str(user_info["id"])

        config = OAuthConfig(client_id="test_client", token_url="https://test.com/token")
        provider = TestOAuthProvider(config)

        # Override authenticate to return context with actual scopes
        original_auth = provider.authenticate

        async def auth_with_scopes(credentials):
            result = await original_auth(credentials)
            if result.success:
                # Add scopes to context
                for scope in credentials.get("scopes", []):
                    result.context.add_scope(scope)
            return result

        provider.authenticate = auth_with_scopes

        @requires_auth_async(provider=provider)
        @requires_scope_async("repo:read")
        async def read_repos(auth: AuthContext):
            return {"repos": ["repo1", "repo2"], "user": auth.user_id}

        # Test with correct scope
        result = await read_repos(
            auth={"access_token": "token", "scopes": ["repo:read", "user:email"]}
        )
        assert result["user"] == "123"
        assert "repos" in result

        # Test without required scope
        with pytest.raises(Exception):
            await read_repos(auth={"access_token": "token", "scopes": ["user:email"]})


class TestScopeEdgeCases:
    """Tests for edge cases in scope handling."""

    def test_empty_scope_string(self):
        """Test handling of empty scope strings."""
        context = AuthContext(authenticated=True, user_id="user123")

        context.add_scope("")
        # Empty string should still be added (set behavior)
        assert "" in context.scopes
        assert context.has_scope("") is True

    def test_scope_with_special_characters(self):
        """Test scopes with special characters."""
        context = AuthContext(
            authenticated=True,
            user_id="user123",
            scopes={
                "read:data",
                "write:data:all",
                "admin:*",
                "https://www.googleapis.com/auth/drive",
            },
        )

        assert context.has_scope("read:data") is True
        assert context.has_scope("write:data:all") is True
        assert context.has_scope("admin:*") is True
        assert context.has_scope("https://www.googleapis.com/auth/drive") is True

    def test_scope_immutability_through_set(self):
        """Test that scopes set is properly managed."""
        context = AuthContext(authenticated=True, user_id="user123")

        # Add scopes
        context.add_scope("scope1")
        context.add_scope("scope2")

        # Direct set manipulation should work
        context.scopes.add("scope3")

        assert len(context.scopes) == 3
        assert context.has_scope("scope3") is True
