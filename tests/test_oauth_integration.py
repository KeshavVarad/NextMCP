"""
OAuth Integration Tests - Requires Real Credentials

These tests perform actual OAuth flows with GitHub and Google.
They are skipped by default and require:
1. OAuth app credentials (client ID and secret)
2. Pre-obtained access tokens (for testing authenticated endpoints)

Setup Instructions:
See: docs/OAUTH_TESTING_SETUP.md

Run these tests with:
    pytest tests/test_oauth_integration.py -v -m integration

Or skip them (default):
    pytest  # automatically skips integration tests
"""

import os

import pytest

from nextmcp.auth import GitHubOAuthProvider, GoogleOAuthProvider

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# ============================================================================
# CONFIGURATION - Tests skip if these environment variables are not set
# ============================================================================

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")  # Pre-obtained for testing

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN")  # Pre-obtained for testing
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")  # For refresh tests

# Skip conditions
skip_github_no_creds = pytest.mark.skipif(
    not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET,
    reason="GitHub OAuth credentials not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET",
)

skip_github_no_token = pytest.mark.skipif(
    not GITHUB_ACCESS_TOKEN,
    reason="GitHub access token not configured. Set GITHUB_ACCESS_TOKEN",
)

skip_google_no_creds = pytest.mark.skipif(
    not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET,
    reason="Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET",
)

skip_google_no_token = pytest.mark.skipif(
    not GOOGLE_ACCESS_TOKEN,
    reason="Google access token not configured. Set GOOGLE_ACCESS_TOKEN",
)

skip_google_no_refresh = pytest.mark.skipif(
    not GOOGLE_REFRESH_TOKEN,
    reason="Google refresh token not configured. Set GOOGLE_REFRESH_TOKEN",
)


# ============================================================================
# GITHUB OAUTH INTEGRATION TESTS
# ============================================================================


class TestGitHubOAuthIntegration:
    """Integration tests for GitHub OAuth provider."""

    @skip_github_no_creds
    def test_github_authorization_url_generation(self):
        """
        Test generating real GitHub authorization URL.

        This test verifies the authorization URL is correctly formatted
        and can be used to start the OAuth flow.
        """
        provider = GitHubOAuthProvider(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
            scope=["read:user", "repo"],
        )

        auth_data = provider.generate_authorization_url()

        # Verify structure
        assert "url" in auth_data
        assert "state" in auth_data
        assert "verifier" in auth_data

        # Verify URL format
        url = auth_data["url"]
        assert url.startswith("https://github.com/login/oauth/authorize")
        assert f"client_id={GITHUB_CLIENT_ID}" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "scope=read%3Auser+repo" in url or "scope=read:user+repo" in url

        print(f"\n✓ GitHub authorization URL generated successfully")
        print(f"  URL: {url[:80]}...")
        print(f"  State: {auth_data['state']}")

    @skip_github_no_creds
    @skip_github_no_token
    @pytest.mark.asyncio
    async def test_github_get_user_info(self):
        """
        Test retrieving user info from GitHub with real access token.

        Requires: GITHUB_ACCESS_TOKEN environment variable

        To get a token, see: docs/OAUTH_TESTING_SETUP.md
        """
        provider = GitHubOAuthProvider(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
        )

        # Get user info using access token
        user_info = await provider.get_user_info(GITHUB_ACCESS_TOKEN)

        # Verify response structure
        assert "id" in user_info
        assert "login" in user_info

        print(f"\n✓ GitHub user info retrieved successfully")
        print(f"  User ID: {user_info.get('id')}")
        print(f"  Username: {user_info.get('login')}")
        print(f"  Name: {user_info.get('name', 'N/A')}")
        print(f"  Email: {user_info.get('email', 'N/A')}")

    @skip_github_no_creds
    @skip_github_no_token
    @pytest.mark.asyncio
    async def test_github_authentication_with_token(self):
        """
        Test full GitHub authentication flow with access token.

        This tests the authenticate() method which would normally be
        called after the OAuth flow completes.
        """
        provider = GitHubOAuthProvider(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
        )

        # Authenticate with access token
        result = await provider.authenticate({
            "access_token": GITHUB_ACCESS_TOKEN,
            "scopes": ["read:user", "repo"],
        })

        # Verify authentication success
        assert result.success is True
        assert result.context is not None
        assert result.context.authenticated is True
        assert result.context.user_id is not None

        # Verify scopes were added
        assert len(result.context.scopes) > 0

        print(f"\n✓ GitHub authentication successful")
        print(f"  User ID: {result.context.user_id}")
        print(f"  Username: {result.context.username}")
        print(f"  Scopes: {list(result.context.scopes)}")
        print(f"  Permissions: {[p.name for p in result.context.permissions]}")

    @skip_github_no_creds
    @pytest.mark.asyncio
    async def test_github_invalid_token_handling(self):
        """
        Test that invalid tokens are properly rejected.

        This ensures error handling works correctly.
        """
        provider = GitHubOAuthProvider(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
        )

        # Try to authenticate with invalid token
        result = await provider.authenticate({
            "access_token": "invalid_token_12345",
            "scopes": ["read:user"],
        })

        # Should fail gracefully
        assert result.success is False
        assert result.error is not None

        print(f"\n✓ Invalid GitHub token correctly rejected")
        print(f"  Error: {result.error}")


# ============================================================================
# GOOGLE OAUTH INTEGRATION TESTS
# ============================================================================


class TestGoogleOAuthIntegration:
    """Integration tests for Google OAuth provider."""

    @skip_google_no_creds
    def test_google_authorization_url_generation(self):
        """
        Test generating real Google authorization URL.

        This test verifies the authorization URL includes required parameters
        for Google OAuth with offline access (refresh tokens).
        """
        provider = GoogleOAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scope=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
        )

        auth_data = provider.generate_authorization_url()

        # Verify structure
        assert "url" in auth_data
        assert "state" in auth_data
        assert "verifier" in auth_data

        # Verify URL format
        url = auth_data["url"]
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert f"client_id={GOOGLE_CLIENT_ID}" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "access_type=offline" in url  # Important for refresh tokens
        assert "prompt=consent" in url

        print(f"\n✓ Google authorization URL generated successfully")
        print(f"  URL: {url[:80]}...")
        print(f"  State: {auth_data['state']}")
        print(f"  Includes offline access: Yes")

    @skip_google_no_creds
    @skip_google_no_token
    @pytest.mark.asyncio
    async def test_google_get_user_info(self):
        """
        Test retrieving user info from Google with real access token.

        Requires: GOOGLE_ACCESS_TOKEN environment variable

        To get a token, see: docs/OAUTH_TESTING_SETUP.md
        """
        provider = GoogleOAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        # Get user info using access token
        user_info = await provider.get_user_info(GOOGLE_ACCESS_TOKEN)

        # Verify response structure (Google's userinfo endpoint)
        assert "sub" in user_info  # Google user ID
        assert "email" in user_info or "name" in user_info

        print(f"\n✓ Google user info retrieved successfully")
        print(f"  User ID: {user_info.get('sub')}")
        print(f"  Email: {user_info.get('email', 'N/A')}")
        print(f"  Name: {user_info.get('name', 'N/A')}")
        print(f"  Picture: {user_info.get('picture', 'N/A')[:50]}...")

    @skip_google_no_creds
    @skip_google_no_token
    @pytest.mark.asyncio
    async def test_google_authentication_with_token(self):
        """
        Test full Google authentication flow with access token.

        This tests the authenticate() method which would normally be
        called after the OAuth flow completes.
        """
        provider = GoogleOAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        # Authenticate with access token
        result = await provider.authenticate({
            "access_token": GOOGLE_ACCESS_TOKEN,
            "scopes": [
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
            ],
        })

        # Verify authentication success
        assert result.success is True
        assert result.context is not None
        assert result.context.authenticated is True
        assert result.context.user_id is not None

        # Verify scopes were added
        assert len(result.context.scopes) > 0

        print(f"\n✓ Google authentication successful")
        print(f"  User ID: {result.context.user_id}")
        print(f"  Username: {result.context.username}")
        print(f"  Scopes: {list(result.context.scopes)}")
        print(f"  Permissions: {[p.name for p in result.context.permissions]}")

    @skip_google_no_creds
    @skip_google_no_refresh
    @pytest.mark.asyncio
    async def test_google_token_refresh(self):
        """
        Test refreshing an expired access token.

        Requires: GOOGLE_REFRESH_TOKEN environment variable

        This tests the token refresh flow, which is unique to Google OAuth
        (with offline access).
        """
        provider = GoogleOAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        # Refresh the token
        token_data = await provider.refresh_access_token(GOOGLE_REFRESH_TOKEN)

        # Verify token response
        assert "access_token" in token_data
        assert "expires_in" in token_data
        assert "token_type" in token_data

        print(f"\n✓ Google token refresh successful")
        print(f"  New access token: {token_data['access_token'][:20]}...")
        print(f"  Expires in: {token_data['expires_in']} seconds")
        print(f"  Token type: {token_data['token_type']}")

    @skip_google_no_creds
    @pytest.mark.asyncio
    async def test_google_invalid_token_handling(self):
        """
        Test that invalid tokens are properly rejected.

        This ensures error handling works correctly.
        """
        provider = GoogleOAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        # Try to authenticate with invalid token
        result = await provider.authenticate({
            "access_token": "invalid_token_12345",
            "scopes": ["https://www.googleapis.com/auth/userinfo.profile"],
        })

        # Should fail gracefully
        assert result.success is False
        assert result.error is not None

        print(f"\n✓ Invalid Google token correctly rejected")
        print(f"  Error: {result.error}")

    @skip_google_no_creds
    @pytest.mark.asyncio
    async def test_google_invalid_refresh_token_handling(self):
        """
        Test that invalid refresh tokens are properly rejected.
        """
        provider = GoogleOAuthProvider(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        # Try to refresh with invalid token
        with pytest.raises(ValueError, match="Token refresh failed"):
            await provider.refresh_access_token("invalid_refresh_token_12345")

        print(f"\n✓ Invalid refresh token correctly rejected")


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

def test_show_setup_instructions():
    """
    Display setup instructions when integration tests are run.

    This is always shown to help users understand what's needed.
    """
    print("\n" + "=" * 70)
    print("OAUTH INTEGRATION TESTS - SETUP REQUIRED")
    print("=" * 70)
    print("\nThese tests require OAuth credentials and access tokens.")
    print("\nQuick Start:")
    print("  1. See docs/OAUTH_TESTING_SETUP.md for detailed instructions")
    print("  2. Run: python examples/auth/oauth_token_helper.py")
    print("  3. Set environment variables with your tokens")
    print("\nRequired Environment Variables:")
    print("  GitHub Tests:")
    print("    - GITHUB_CLIENT_ID")
    print("    - GITHUB_CLIENT_SECRET")
    print("    - GITHUB_ACCESS_TOKEN (for authenticated tests)")
    print("\n  Google Tests:")
    print("    - GOOGLE_CLIENT_ID")
    print("    - GOOGLE_CLIENT_SECRET")
    print("    - GOOGLE_ACCESS_TOKEN (for authenticated tests)")
    print("    - GOOGLE_REFRESH_TOKEN (for refresh tests)")
    print("\nCurrent Status:")
    print(f"  GitHub credentials: {'✓ Set' if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET else '✗ Not set'}")
    print(f"  GitHub token: {'✓ Set' if GITHUB_ACCESS_TOKEN else '✗ Not set'}")
    print(f"  Google credentials: {'✓ Set' if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET else '✗ Not set'}")
    print(f"  Google token: {'✓ Set' if GOOGLE_ACCESS_TOKEN else '✗ Not set'}")
    print(f"  Google refresh: {'✓ Set' if GOOGLE_REFRESH_TOKEN else '✗ Not set'}")
    print("\n" + "=" * 70)
