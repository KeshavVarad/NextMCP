"""
Tests for specialized authentication error types.

Tests custom exceptions for OAuth, scopes, and manifest violations.
"""

import pytest

from nextmcp.auth.core import AuthContext, Permission, Role
from nextmcp.auth.errors import (
    ManifestViolationError,
    OAuthRequiredError,
    ScopeInsufficientError,
)


class TestOAuthRequiredError:
    """Tests for OAuthRequiredError exception."""

    def test_oauth_required_error_basic(self):
        """Test creating OAuthRequiredError with basic message."""
        error = OAuthRequiredError("OAuth authentication required")

        assert str(error) == "OAuth authentication required"
        assert isinstance(error, Exception)

    def test_oauth_required_error_with_provider(self):
        """Test OAuthRequiredError with provider information."""
        error = OAuthRequiredError(
            "OAuth authentication required",
            provider="github",
            scopes=["read:user", "repo:read"],
        )

        assert error.provider == "github"
        assert error.scopes == ["read:user", "repo:read"]
        assert "OAuth authentication required" in str(error)

    def test_oauth_required_error_with_authorization_url(self):
        """Test OAuthRequiredError with authorization URL."""
        error = OAuthRequiredError(
            "OAuth required",
            provider="google",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth?...",
        )

        assert error.authorization_url == "https://accounts.google.com/o/oauth2/v2/auth?..."
        assert error.provider == "google"

    def test_oauth_required_error_attributes(self):
        """Test all OAuthRequiredError attributes."""
        error = OAuthRequiredError(
            message="Please authenticate",
            provider="github",
            scopes=["repo:write"],
            authorization_url="https://github.com/login/oauth/authorize",
            user_id=None,
        )

        assert error.message == "Please authenticate"
        assert error.provider == "github"
        assert error.scopes == ["repo:write"]
        assert error.authorization_url == "https://github.com/login/oauth/authorize"
        assert error.user_id is None


class TestScopeInsufficientError:
    """Tests for ScopeInsufficientError exception."""

    def test_scope_insufficient_error_basic(self):
        """Test creating ScopeInsufficientError with basic message."""
        error = ScopeInsufficientError("Insufficient OAuth scopes")

        assert str(error) == "Insufficient OAuth scopes"
        assert isinstance(error, Exception)

    def test_scope_insufficient_error_with_required_scopes(self):
        """Test ScopeInsufficientError with required scopes."""
        error = ScopeInsufficientError(
            "Missing required scopes",
            required_scopes=["repo:write", "admin:org"],
            current_scopes=["repo:read"],
        )

        assert error.required_scopes == ["repo:write", "admin:org"]
        assert error.current_scopes == ["repo:read"]
        assert "Missing required scopes" in str(error)

    def test_scope_insufficient_error_with_user_id(self):
        """Test ScopeInsufficientError with user identification."""
        error = ScopeInsufficientError(
            "Need admin scope",
            required_scopes=["admin:all"],
            current_scopes=["read:all"],
            user_id="user123",
        )

        assert error.user_id == "user123"
        assert error.required_scopes == ["admin:all"]

    def test_scope_insufficient_error_missing_context(self):
        """Test ScopeInsufficientError when missing scope data."""
        error = ScopeInsufficientError(
            "Scopes required",
            required_scopes=["write:data"],
            current_scopes=[],
        )

        assert error.required_scopes == ["write:data"]
        assert error.current_scopes == []


class TestManifestViolationError:
    """Tests for ManifestViolationError exception."""

    def test_manifest_violation_error_basic(self):
        """Test creating ManifestViolationError with basic message."""
        error = ManifestViolationError("Manifest access denied")

        assert str(error) == "Manifest access denied"
        assert isinstance(error, Exception)

    def test_manifest_violation_error_with_tool_name(self):
        """Test ManifestViolationError with tool name."""
        error = ManifestViolationError(
            "Access denied to tool",
            tool_name="delete_database",
        )

        assert error.tool_name == "delete_database"
        assert "Access denied to tool" in str(error)

    def test_manifest_violation_error_with_requirements(self):
        """Test ManifestViolationError with requirement details."""
        error = ManifestViolationError(
            "Missing required role",
            tool_name="admin_panel",
            required_roles=["admin", "superuser"],
            required_permissions=["admin:all"],
            required_scopes=["admin:full"],
        )

        assert error.tool_name == "admin_panel"
        assert error.required_roles == ["admin", "superuser"]
        assert error.required_permissions == ["admin:all"]
        assert error.required_scopes == ["admin:full"]

    def test_manifest_violation_error_with_user_context(self):
        """Test ManifestViolationError with user context."""
        error = ManifestViolationError(
            "Unauthorized access attempt",
            tool_name="sensitive_operation",
            user_id="user456",
            auth_context=AuthContext(
                authenticated=True,
                user_id="user456",
                username="testuser",
            ),
        )

        assert error.user_id == "user456"
        assert error.auth_context is not None
        assert error.auth_context.user_id == "user456"

    def test_manifest_violation_error_all_attributes(self):
        """Test ManifestViolationError with all attributes."""
        context = AuthContext(authenticated=True, user_id="user789")
        context.add_role(Role("viewer"))

        error = ManifestViolationError(
            message="Complete denial",
            tool_name="dangerous_tool",
            required_roles=["admin"],
            required_permissions=["write:all"],
            required_scopes=["full:access"],
            user_id="user789",
            auth_context=context,
        )

        assert error.message == "Complete denial"
        assert error.tool_name == "dangerous_tool"
        assert error.required_roles == ["admin"]
        assert error.required_permissions == ["write:all"]
        assert error.required_scopes == ["full:access"]
        assert error.user_id == "user789"
        assert error.auth_context == context


class TestErrorHierarchy:
    """Tests for error type hierarchy and inheritance."""

    def test_all_errors_are_exceptions(self):
        """Test that all error types inherit from Exception."""
        oauth_error = OAuthRequiredError("test")
        scope_error = ScopeInsufficientError("test")
        manifest_error = ManifestViolationError("test")

        assert isinstance(oauth_error, Exception)
        assert isinstance(scope_error, Exception)
        assert isinstance(manifest_error, Exception)

    def test_error_messages_are_strings(self):
        """Test that all errors convert to string properly."""
        errors = [
            OAuthRequiredError("OAuth needed"),
            ScopeInsufficientError("Scope missing"),
            ManifestViolationError("Manifest violation"),
        ]

        for error in errors:
            assert isinstance(str(error), str)
            assert len(str(error)) > 0

    def test_errors_can_be_raised_and_caught(self):
        """Test that errors can be raised and caught."""
        with pytest.raises(OAuthRequiredError) as exc_info:
            raise OAuthRequiredError("Test OAuth error")
        assert "Test OAuth error" in str(exc_info.value)

        with pytest.raises(ScopeInsufficientError) as exc_info:
            raise ScopeInsufficientError("Test scope error")
        assert "Test scope error" in str(exc_info.value)

        with pytest.raises(ManifestViolationError) as exc_info:
            raise ManifestViolationError("Test manifest error")
        assert "Test manifest error" in str(exc_info.value)


class TestErrorUsagePatterns:
    """Tests for common error usage patterns."""

    def test_oauth_error_for_missing_token(self):
        """Test using OAuthRequiredError when access token is missing."""
        error = OAuthRequiredError(
            "Access token required for this operation",
            provider="github",
            scopes=["repo:read"],
            authorization_url="https://github.com/login/oauth/authorize?client_id=...",
        )

        assert error.provider == "github"
        assert "repo:read" in error.scopes

    def test_scope_error_for_insufficient_permissions(self):
        """Test using ScopeInsufficientError when scopes are insufficient."""
        error = ScopeInsufficientError(
            "This operation requires write access",
            required_scopes=["repo:write"],
            current_scopes=["repo:read"],
            user_id="user123",
        )

        assert "repo:write" in error.required_scopes
        assert "repo:read" in error.current_scopes

    def test_manifest_error_for_tool_access_denial(self):
        """Test using ManifestViolationError when tool access is denied."""
        context = AuthContext(authenticated=True, user_id="user456")
        context.add_role(Role("viewer"))

        error = ManifestViolationError(
            "Tool requires admin role",
            tool_name="delete_all_users",
            required_roles=["admin"],
            user_id="user456",
            auth_context=context,
        )

        assert error.tool_name == "delete_all_users"
        assert "admin" in error.required_roles
