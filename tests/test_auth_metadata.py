"""
Tests for Auth Metadata Protocol.

Tests the protocol-level metadata system that allows MCP servers to announce
their authentication requirements to hosts.
"""

import pytest

from nextmcp.protocol.auth_metadata import (
    AUTH_METADATA_SCHEMA,
    AuthFlowType,
    AuthMetadata,
    AuthProviderMetadata,
    AuthRequirement,
)


class TestAuthProviderMetadata:
    """Test AuthProviderMetadata functionality."""

    def test_create_oauth_provider(self):
        """Test creating OAuth provider metadata."""
        provider = AuthProviderMetadata(
            name="google",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["profile", "email"],
            supports_refresh=True,
            supports_pkce=True,
        )

        assert provider.name == "google"
        assert provider.type == "oauth2"
        assert AuthFlowType.OAUTH2_PKCE in provider.flows
        assert provider.supports_refresh is True
        assert "email" in provider.scopes

    def test_provider_to_dict(self):
        """Test serializing provider to dictionary."""
        provider = AuthProviderMetadata(
            name="github",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user"],
        )

        data = provider.to_dict()

        assert data["name"] == "github"
        assert data["type"] == "oauth2"
        assert "oauth2-pkce" in data["flows"]
        assert data["scopes"] == ["repo", "user"]

    def test_api_key_provider(self):
        """Test creating API key provider metadata."""
        provider = AuthProviderMetadata(
            name="custom-api",
            type="api-key",
            flows=[AuthFlowType.API_KEY],
        )

        assert provider.name == "custom-api"
        assert AuthFlowType.API_KEY in provider.flows
        assert provider.supports_pkce is True  # Default


class TestAuthMetadata:
    """Test AuthMetadata functionality."""

    def test_create_empty_metadata(self):
        """Test creating empty auth metadata."""
        metadata = AuthMetadata()

        assert metadata.requirement == AuthRequirement.NONE
        assert len(metadata.providers) == 0
        assert len(metadata.required_scopes) == 0

    def test_create_required_auth(self):
        """Test creating metadata with required auth."""
        metadata = AuthMetadata(
            requirement=AuthRequirement.REQUIRED,
            required_scopes=["profile", "email"],
        )

        assert metadata.requirement == AuthRequirement.REQUIRED
        assert "profile" in metadata.required_scopes
        assert "email" in metadata.required_scopes

    def test_add_provider(self):
        """Test adding a provider."""
        metadata = AuthMetadata()
        metadata.add_provider(
            name="google",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["profile", "email"],
            supports_refresh=True,
        )

        assert len(metadata.providers) == 1
        assert metadata.providers[0].name == "google"
        assert metadata.providers[0].supports_refresh is True

    def test_add_scopes(self):
        """Test adding scopes."""
        metadata = AuthMetadata()

        metadata.add_required_scope("profile")
        metadata.add_required_scope("email")
        metadata.add_optional_scope("drive.readonly")

        assert "profile" in metadata.required_scopes
        assert "email" in metadata.required_scopes
        assert "drive.readonly" in metadata.optional_scopes

    def test_add_permissions(self):
        """Test adding permissions."""
        metadata = AuthMetadata()

        metadata.add_permission("file.read")
        metadata.add_permission("file.write")

        assert "file.read" in metadata.permissions
        assert "file.write" in metadata.permissions

    def test_add_roles(self):
        """Test adding roles."""
        metadata = AuthMetadata()

        metadata.add_role("admin")
        metadata.add_role("user")

        assert "admin" in metadata.roles
        assert "user" in metadata.roles

    def test_to_dict(self):
        """Test serializing to dictionary."""
        metadata = AuthMetadata(
            requirement=AuthRequirement.REQUIRED,
            required_scopes=["profile"],
            supports_multi_user=True,
        )
        metadata.add_provider(
            name="github",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
        )

        data = metadata.to_dict()

        assert data["requirement"] == "required"
        assert "profile" in data["required_scopes"]
        assert data["supports_multi_user"] is True
        assert len(data["providers"]) == 1
        assert data["providers"][0]["name"] == "github"

    def test_from_dict(self):
        """Test deserializing from dictionary."""
        data = {
            "requirement": "required",
            "providers": [
                {
                    "name": "google",
                    "type": "oauth2",
                    "flows": ["oauth2-pkce"],
                    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "scopes": ["profile", "email"],
                    "supports_refresh": True,
                    "supports_pkce": True,
                }
            ],
            "required_scopes": ["profile"],
            "optional_scopes": ["email"],
            "permissions": ["file.read"],
            "supports_multi_user": True,
        }

        metadata = AuthMetadata.from_dict(data)

        assert metadata.requirement == AuthRequirement.REQUIRED
        assert len(metadata.providers) == 1
        assert metadata.providers[0].name == "google"
        assert "profile" in metadata.required_scopes
        assert "email" in metadata.optional_scopes
        assert "file.read" in metadata.permissions
        assert metadata.supports_multi_user is True

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip."""
        original = AuthMetadata(
            requirement=AuthRequirement.REQUIRED,
            required_scopes=["profile", "email"],
            permissions=["file.read", "file.write"],
            supports_multi_user=True,
        )
        original.add_provider(
            name="github",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            scopes=["repo", "user"],
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = AuthMetadata.from_dict(data)

        assert restored.requirement == original.requirement
        assert restored.required_scopes == original.required_scopes
        assert restored.permissions == original.permissions
        assert restored.supports_multi_user == original.supports_multi_user
        assert len(restored.providers) == len(original.providers)
        assert restored.providers[0].name == original.providers[0].name

    def test_validate_valid_metadata(self):
        """Test validating valid metadata."""
        metadata = AuthMetadata(requirement=AuthRequirement.OPTIONAL)
        metadata.add_provider(
            name="google",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
        )

        is_valid, errors = metadata.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_required_auth_without_providers(self):
        """Test validation fails when auth required but no providers."""
        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)

        is_valid, errors = metadata.validate()

        assert is_valid is False
        assert any("no providers" in error.lower() for error in errors)

    def test_validate_oauth_without_urls(self):
        """Test validation fails when OAuth provider missing URLs."""
        metadata = AuthMetadata()
        metadata.add_provider(
            name="google",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            # Missing authorization_url and token_url
        )

        is_valid, errors = metadata.validate()

        assert is_valid is False
        assert any("authorization_url" in error for error in errors)
        assert any("token_url" in error for error in errors)

    def test_validate_scope_conflict(self):
        """Test validation fails when scope is both required and optional."""
        metadata = AuthMetadata()
        metadata.add_required_scope("profile")
        metadata.add_optional_scope("profile")  # Conflict!

        is_valid, errors = metadata.validate()

        assert is_valid is False
        assert any("both required and optional" in error.lower() for error in errors)

    def test_schema_structure(self):
        """Test that JSON schema has expected structure."""
        assert "$schema" in AUTH_METADATA_SCHEMA
        assert "properties" in AUTH_METADATA_SCHEMA
        assert "requirement" in AUTH_METADATA_SCHEMA["properties"]
        assert "providers" in AUTH_METADATA_SCHEMA["properties"]

    def test_multi_provider_metadata(self):
        """Test metadata with multiple providers."""
        metadata = AuthMetadata(requirement=AuthRequirement.REQUIRED)

        metadata.add_provider(
            name="google",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
        )

        metadata.add_provider(
            name="github",
            type="oauth2",
            flows=[AuthFlowType.OAUTH2_PKCE],
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
        )

        assert len(metadata.providers) == 2
        provider_names = [p.name for p in metadata.providers]
        assert "google" in provider_names
        assert "github" in provider_names

    def test_token_refresh_configuration(self):
        """Test token refresh configuration."""
        metadata = AuthMetadata(
            token_refresh_enabled=True,
        )

        assert metadata.token_refresh_enabled is True

        data = metadata.to_dict()
        assert data["token_refresh_enabled"] is True

    def test_session_management_types(self):
        """Test different session management types."""
        for session_type in ["server-side", "client-side", "stateless"]:
            metadata = AuthMetadata(session_management=session_type)
            assert metadata.session_management == session_type

    def test_error_codes_documentation(self):
        """Test error code documentation."""
        metadata = AuthMetadata()
        metadata.error_codes = {
            "auth_required": "Authentication is required to access this resource",
            "insufficient_scopes": "Your token lacks required OAuth scopes",
        }

        data = metadata.to_dict()
        assert "auth_required" in data["error_codes"]
        assert "insufficient_scopes" in data["error_codes"]
