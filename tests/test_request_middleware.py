"""
Tests for Runtime Auth Enforcement Middleware.

Tests the request-level auth enforcement that validates every request.
"""

import pytest

from nextmcp.auth.core import AuthContext, AuthResult
from nextmcp.auth.errors import AuthenticationError, AuthorizationError
from nextmcp.auth.manifest import PermissionManifest
from nextmcp.auth.oauth_providers import GitHubOAuthProvider
from nextmcp.auth.request_middleware import (
    AuthEnforcementMiddleware,
    create_auth_middleware,
)
from nextmcp.protocol.auth_metadata import AuthMetadata, AuthRequirement
from nextmcp.session.session_store import MemorySessionStore, SessionData


class MockAuthProvider:
    """Mock auth provider for testing."""

    def __init__(self, should_succeed=True, user_id="test_user"):
        self.name = "mock"
        self.should_succeed = should_succeed
        self.user_id = user_id
        self.authenticate_called = False

    async def authenticate(self, credentials):
        self.authenticate_called = True

        if not self.should_succeed:
            return AuthResult.failure("Authentication failed")

        context = AuthContext(
            authenticated=True,
            user_id=self.user_id,
            username="testuser",
        )
        context.add_scope("read:data")
        return AuthResult.success_result(context)


@pytest.mark.asyncio
class TestAuthEnforcementMiddleware:
    """Test AuthEnforcementMiddleware functionality."""

    async def test_no_auth_required_passes_through(self):
        """Test request passes through when auth not required."""
        provider = MockAuthProvider()
        metadata = AuthMetadata(requirement=AuthRequirement.NONE)
        middleware = AuthEnforcementMiddleware(provider=provider, metadata=metadata)

        request = {"method": "tools/call", "params": {"name": "test_tool"}}
        handler_called = False

        async def handler(req):
            nonlocal handler_called
            handler_called = True
            return {"success": True}

        result = await middleware(request, handler)

        assert handler_called is True
        assert result["success"] is True
        assert provider.authenticate_called is False  # Should not authenticate

    async def test_optional_auth_without_credentials_passes(self):
        """Test optional auth passes without credentials."""
        provider = MockAuthProvider()
        metadata = AuthMetadata(requirement=AuthRequirement.OPTIONAL)
        middleware = AuthEnforcementMiddleware(provider=provider, metadata=metadata)

        request = {"method": "tools/call", "params": {"name": "test_tool"}}

        async def handler(req):
            return {"success": True}

        result = await middleware(request, handler)

        assert result["success"] is True
        assert provider.authenticate_called is False

    async def test_required_auth_without_credentials_fails(self):
        """Test required auth fails without credentials."""
        provider = MockAuthProvider()
        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(provider=provider, metadata=metadata)

        request = {"method": "tools/call", "params": {"name": "test_tool"}}

        async def handler(req):
            return {"success": True}

        with pytest.raises(AuthenticationError, match="no credentials provided"):
            await middleware(request, handler)

    async def test_successful_authentication(self):
        """Test successful authentication flow."""
        provider = MockAuthProvider(should_succeed=True)
        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(provider=provider, metadata=metadata)

        request = {
            "method": "tools/call",
            "params": {"name": "test_tool"},
            "auth": {"access_token": "valid_token"},
        }

        async def handler(req):
            # Check auth context was injected
            assert "_auth_context" in req
            assert req["_auth_context"].authenticated is True
            return {"success": True}

        result = await middleware(request, handler)

        assert result["success"] is True
        assert provider.authenticate_called is True

    async def test_failed_authentication(self):
        """Test failed authentication."""
        provider = MockAuthProvider(should_succeed=False)
        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(provider=provider, metadata=metadata)

        request = {
            "method": "tools/call",
            "params": {"name": "test_tool"},
            "auth": {"access_token": "invalid_token"},
        }

        async def handler(req):
            return {"success": True}

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await middleware(request, handler)

    async def test_session_store_integration(self):
        """Test integration with session store."""
        provider = MockAuthProvider(should_succeed=True, user_id="user123")
        session_store = MemorySessionStore()
        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(
            provider=provider,
            session_store=session_store,
            metadata=metadata,
        )

        # First request should authenticate and create session
        request = {
            "method": "tools/call",
            "params": {"name": "test_tool"},
            "auth": {
                "access_token": "token123",
                "refresh_token": "refresh123",
            },
        }

        async def handler(req):
            return {"success": True}

        result = await middleware(request, handler)
        assert result["success"] is True

        # Check session was created
        session = session_store.load("user123")
        assert session is not None
        assert session.access_token == "token123"

    async def test_session_reuse(self):
        """Test reusing existing session."""
        provider = MockAuthProvider(should_succeed=True, user_id="user123")
        session_store = MemorySessionStore()

        # Pre-populate session
        session = SessionData(
            user_id="user123",
            access_token="token123",
            scopes=["read:data"],
            user_info={"login": "testuser"},
            provider="mock",
        )
        session_store.save(session)

        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(
            provider=provider,
            session_store=session_store,
            metadata=metadata,
        )

        request = {
            "method": "tools/call",
            "params": {"name": "test_tool"},
            "auth": {"access_token": "token123"},
        }

        async def handler(req):
            # Check auth context from session
            assert "_auth_context" in req
            assert req["_auth_context"].user_id == "user123"
            return {"success": True}

        result = await middleware(request, handler)
        assert result["success"] is True

    async def test_expired_token_rejection(self):
        """Test expired tokens are rejected."""
        import time

        provider = MockAuthProvider()
        session_store = MemorySessionStore()

        # Create expired session
        session = SessionData(
            user_id="user123",
            access_token="expired_token",
            expires_at=time.time() - 10,  # Expired 10 seconds ago
        )
        session_store.save(session)

        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(
            provider=provider,
            session_store=session_store,
            metadata=metadata,
        )

        request = {
            "method": "tools/call",
            "params": {"name": "test_tool"},
            "auth": {"access_token": "expired_token"},
        }

        async def handler(req):
            return {"success": True}

        with pytest.raises(AuthenticationError, match="expired"):
            await middleware(request, handler)

    async def test_scope_enforcement(self):
        """Test required scopes are enforced."""
        provider = MockAuthProvider(should_succeed=True)
        metadata = AuthMetadata(
            requirement=AuthRequirement.REQUIRED,
            required_scopes=["write:data"],  # Requires write scope
        )
        middleware = AuthEnforcementMiddleware(provider=provider, metadata=metadata)

        request = {
            "method": "tools/call",
            "params": {"name": "test_tool"},
            "auth": {"access_token": "token"},
        }

        async def handler(req):
            return {"success": True}

        # Provider only gives "read:data" scope, should fail
        with pytest.raises(AuthorizationError, match="Missing required scopes"):
            await middleware(request, handler)

    async def test_manifest_enforcement(self):
        """Test permission manifest is enforced."""
        from nextmcp.auth.errors import ManifestViolationError

        provider = MockAuthProvider(should_succeed=True)
        manifest = PermissionManifest()
        manifest.define_tool_permission("admin_tool", roles=["admin"])

        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(
            provider=provider,
            metadata=metadata,
            manifest=manifest,
        )

        request = {
            "method": "tools/call",
            "params": {"name": "admin_tool"},
            "auth": {"access_token": "token"},
        }

        async def handler(req):
            return {"success": True}

        # User doesn't have admin role, should fail
        with pytest.raises(ManifestViolationError):
            await middleware(request, handler)

    async def test_manifest_allows_authorized_user(self):
        """Test manifest allows authorized user."""

        class AdminProvider(MockAuthProvider):
            async def authenticate(self, credentials):
                context = AuthContext(
                    authenticated=True,
                    user_id="admin_user",
                    username="admin",
                )
                context.add_role("admin")
                return AuthResult.success_result(context)

        provider = AdminProvider()
        manifest = PermissionManifest()
        manifest.define_tool_permission("admin_tool", roles=["admin"])

        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(
            provider=provider,
            metadata=metadata,
            manifest=manifest,
        )

        request = {
            "method": "tools/call",
            "params": {"name": "admin_tool"},
            "auth": {"access_token": "token"},
        }

        async def handler(req):
            return {"success": True}

        result = await middleware(request, handler)
        assert result["success"] is True

    async def test_non_tool_request_allowed(self):
        """Test non-tool requests are allowed without auth checks."""
        provider = MockAuthProvider()
        manifest = PermissionManifest()
        manifest.define_tool_permission("protected_tool", roles=["admin"])

        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)
        middleware = AuthEnforcementMiddleware(
            provider=provider,
            metadata=metadata,
            manifest=manifest,
        )

        # Request without tool name (e.g., server info request)
        request = {
            "method": "server/info",
            "auth": {"access_token": "token"},
        }

        async def handler(req):
            return {"success": True}

        result = await middleware(request, handler)
        assert result["success"] is True


@pytest.mark.asyncio
class TestCreateAuthMiddleware:
    """Test create_auth_middleware helper function."""

    async def test_create_middleware_with_defaults(self):
        """Test creating middleware with default settings."""
        provider = MockAuthProvider()
        middleware = create_auth_middleware(provider=provider)

        assert middleware.provider == provider
        assert middleware.metadata.requirement == AuthRequirement.REQUIRED

    async def test_create_middleware_with_optional_auth(self):
        """Test creating middleware with optional auth."""
        provider = MockAuthProvider()
        middleware = create_auth_middleware(
            provider=provider,
            requirement=AuthRequirement.OPTIONAL,
        )

        assert middleware.metadata.requirement == AuthRequirement.OPTIONAL

    async def test_create_middleware_with_scopes(self):
        """Test creating middleware with required scopes."""
        provider = MockAuthProvider()
        middleware = create_auth_middleware(
            provider=provider,
            required_scopes=["read:repo", "write:repo"],
        )

        assert "read:repo" in middleware.metadata.required_scopes
        assert "write:repo" in middleware.metadata.required_scopes

    async def test_create_middleware_with_session_store(self):
        """Test creating middleware with session store."""
        provider = MockAuthProvider()
        session_store = MemorySessionStore()
        middleware = create_auth_middleware(
            provider=provider,
            session_store=session_store,
        )

        assert middleware.session_store == session_store

    async def test_create_middleware_with_manifest(self):
        """Test creating middleware with permission manifest."""
        provider = MockAuthProvider()
        manifest = PermissionManifest()
        middleware = create_auth_middleware(
            provider=provider,
            manifest=manifest,
        )

        assert middleware.manifest == manifest
