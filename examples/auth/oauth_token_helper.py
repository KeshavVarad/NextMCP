"""
OAuth Token Helper Script

This script helps you obtain OAuth access tokens for testing integration tests.
It provides an interactive workflow to:
1. Generate authorization URLs
2. Handle OAuth callbacks
3. Exchange codes for tokens
4. Display environment variables to set

Usage:
    # Interactive mode - prompts for provider
    python examples/auth/oauth_token_helper.py

    # Specify provider
    python examples/auth/oauth_token_helper.py --provider github
    python examples/auth/oauth_token_helper.py --provider google

    # Manual mode (no callback server)
    python examples/auth/oauth_token_helper.py --provider github --manual
"""

import argparse
import asyncio
import os
import sys
import webbrowser
from urllib.parse import parse_qs, urlparse

from nextmcp.auth import GitHubOAuthProvider, GoogleOAuthProvider


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_step(number, text):
    """Print a step number and description."""
    print(f"\n📍 Step {number}: {text}")
    print("-" * 70)


def print_success(text):
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print an error message."""
    print(f"✗ ERROR: {text}")


def print_warning(text):
    """Print a warning message."""
    print(f"⚠️  WARNING: {text}")


def print_info(text):
    """Print an info message."""
    print(f"ℹ️  {text}")


async def run_callback_server(state, verifier):
    """
    Run a simple HTTP server to handle OAuth callback.

    Returns the authorization code or None if failed.
    """
    from aiohttp import web

    code_container = {"code": None, "error": None}

    async def oauth_callback(request):
        """Handle OAuth callback."""
        # Get code from query parameters
        code = request.query.get("code")
        error = request.query.get("error")
        callback_state = request.query.get("state")

        if error:
            code_container["error"] = error
            return web.Response(
                text=f"❌ Authorization failed: {error}\n\nYou can close this window.",
                content_type="text/plain",
            )

        if not code:
            code_container["error"] = "No authorization code received"
            return web.Response(
                text="❌ No authorization code received\n\nYou can close this window.",
                content_type="text/plain",
            )

        if callback_state != state:
            code_container["error"] = "State mismatch - possible CSRF attack"
            return web.Response(
                text="❌ Security error: State mismatch\n\nYou can close this window.",
                content_type="text/plain",
            )

        code_container["code"] = code

        return web.Response(
            text="✅ Authorization successful!\n\nYou can close this window and return to the terminal.",
            content_type="text/plain",
        )

    # Create and start server
    app = web.Application()
    app.router.add_get("/oauth/callback", oauth_callback)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)

    print_info("Starting local callback server on http://localhost:8080")
    print_info("Waiting for authorization...")

    await site.start()

    # Wait for callback (with timeout)
    timeout = 300  # 5 minutes
    for _ in range(timeout):
        if code_container["code"] or code_container["error"]:
            break
        await asyncio.sleep(1)

    # Cleanup
    await runner.cleanup()

    if code_container["error"]:
        print_error(code_container["error"])
        return None

    return code_container["code"]


async def get_github_token(client_id, client_secret, manual_mode=False):
    """
    Interactive workflow to get GitHub access token.

    Args:
        client_id: GitHub OAuth app client ID
        client_secret: GitHub OAuth app client secret
        manual_mode: If True, don't start callback server

    Returns:
        Access token or None
    """
    print_header("GITHUB OAUTH TOKEN HELPER")

    provider = GitHubOAuthProvider(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8080/oauth/callback",
        scope=["read:user", "repo"],
    )

    print_step(1, "Generating authorization URL")
    auth_data = provider.generate_authorization_url()
    url = auth_data["url"]
    state = auth_data["state"]
    verifier = auth_data["verifier"]

    print_success("Authorization URL generated")
    print(f"\n📋 Authorization URL:")
    print(f"   {url}\n")

    if manual_mode:
        print_step(2, "Manual authorization")
        print("Please visit the URL above and authorize the application.")
        print("\nAfter authorization, you'll be redirected to:")
        print("  http://localhost:8080/oauth/callback?code=CODE&state=STATE")
        print("\nCopy the 'code' parameter from the URL and paste it below:")

        code = input("\n🔑 Enter authorization code: ").strip()
        if not code:
            print_error("No code provided")
            return None
    else:
        print_step(2, "Opening browser for authorization")
        print("Your browser will open automatically...")
        print("Please authorize the application in your browser.")

        # Open browser
        webbrowser.open(url)

        # Start callback server
        code = await run_callback_server(state, verifier)
        if not code:
            print_error("Failed to get authorization code")
            return None

    print_success(f"Authorization code received: {code[:20]}...")

    print_step(3, "Exchanging code for access token")
    try:
        token_data = await provider.exchange_code_for_token(
            code=code,
            state=state,
            verifier=verifier,
        )

        access_token = token_data["access_token"]
        print_success("Access token obtained!")

        print_step(4, "Testing token with GitHub API")
        user_info = await provider.get_user_info(access_token)
        print_success(f"Token works! Authenticated as: {user_info.get('login')}")

        # Display results
        print_header("GITHUB TOKEN OBTAINED SUCCESSFULLY")
        print(f"\n✅ Access Token: {access_token}")
        print(f"✅ Token Type: {token_data.get('token_type', 'bearer')}")
        print(f"✅ Scope: {token_data.get('scope', 'N/A')}")

        print("\n📋 Set these environment variables:")
        print(f"   export GITHUB_CLIENT_ID=\"{client_id}\"")
        print(f"   export GITHUB_CLIENT_SECRET=\"{client_secret}\"")
        print(f"   export GITHUB_ACCESS_TOKEN=\"{access_token}\"")

        print("\n💾 Or add to .env file:")
        print(f"   GITHUB_CLIENT_ID={client_id}")
        print(f"   GITHUB_CLIENT_SECRET={client_secret}")
        print(f"   GITHUB_ACCESS_TOKEN={access_token}")

        return access_token

    except Exception as e:
        print_error(f"Token exchange failed: {e}")
        return None


async def get_google_token(client_id, client_secret, manual_mode=False):
    """
    Interactive workflow to get Google access token and refresh token.

    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        manual_mode: If True, don't start callback server

    Returns:
        Tuple of (access_token, refresh_token) or (None, None)
    """
    print_header("GOOGLE OAUTH TOKEN HELPER")

    provider = GoogleOAuthProvider(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8080/oauth/callback",
        scope=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
    )

    print_step(1, "Generating authorization URL with offline access")
    auth_data = provider.generate_authorization_url()
    url = auth_data["url"]
    state = auth_data["state"]
    verifier = auth_data["verifier"]

    print_success("Authorization URL generated")
    print(f"\n📋 Authorization URL:")
    print(f"   {url}\n")
    print_info("Note: This includes 'access_type=offline' for refresh tokens")

    if manual_mode:
        print_step(2, "Manual authorization")
        print("Please visit the URL above and authorize the application.")
        print("\nAfter authorization, you'll be redirected to:")
        print("  http://localhost:8080/oauth/callback?code=CODE&state=STATE")
        print("\nCopy the 'code' parameter from the URL and paste it below:")

        code = input("\n🔑 Enter authorization code: ").strip()
        if not code:
            print_error("No code provided")
            return None, None
    else:
        print_step(2, "Opening browser for authorization")
        print("Your browser will open automatically...")
        print("Please sign in and authorize the application.")

        # Open browser
        webbrowser.open(url)

        # Start callback server
        code = await run_callback_server(state, verifier)
        if not code:
            print_error("Failed to get authorization code")
            return None, None

    print_success(f"Authorization code received: {code[:20]}...")

    print_step(3, "Exchanging code for access and refresh tokens")
    try:
        token_data = await provider.exchange_code_for_token(
            code=code,
            state=state,
            verifier=verifier,
        )

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        print_success("Tokens obtained!")

        if not refresh_token:
            print_warning("No refresh token received - you may need to revoke access and try again")
            print_info("Refresh tokens are only issued on first authorization or with prompt=consent")

        print_step(4, "Testing token with Google API")
        user_info = await provider.get_user_info(access_token)
        print_success(f"Token works! Authenticated as: {user_info.get('email', 'Unknown')}")

        # Display results
        print_header("GOOGLE TOKENS OBTAINED SUCCESSFULLY")
        print(f"\n✅ Access Token: {access_token[:50]}...")
        print(f"✅ Token Type: {token_data.get('token_type', 'Bearer')}")
        print(f"✅ Expires In: {token_data.get('expires_in', 'Unknown')} seconds")
        print(f"✅ Scope: {token_data.get('scope', 'N/A')}")

        if refresh_token:
            print(f"✅ Refresh Token: {refresh_token[:50]}...")
        else:
            print(f"⚠️  Refresh Token: Not issued")

        print("\n📋 Set these environment variables:")
        print(f"   export GOOGLE_CLIENT_ID=\"{client_id}\"")
        print(f"   export GOOGLE_CLIENT_SECRET=\"{client_secret}\"")
        print(f"   export GOOGLE_ACCESS_TOKEN=\"{access_token}\"")
        if refresh_token:
            print(f"   export GOOGLE_REFRESH_TOKEN=\"{refresh_token}\"")

        print("\n💾 Or add to .env file:")
        print(f"   GOOGLE_CLIENT_ID={client_id}")
        print(f"   GOOGLE_CLIENT_SECRET={client_secret}")
        print(f"   GOOGLE_ACCESS_TOKEN={access_token}")
        if refresh_token:
            print(f"   GOOGLE_REFRESH_TOKEN={refresh_token}")

        return access_token, refresh_token

    except Exception as e:
        print_error(f"Token exchange failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OAuth Token Helper - Obtain tokens for integration testing"
    )
    parser.add_argument(
        "--provider",
        choices=["github", "google"],
        help="OAuth provider (github or google)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Manual mode (no callback server, paste code manually)",
    )

    args = parser.parse_args()

    # Welcome message
    print_header("OAUTH TOKEN HELPER FOR INTEGRATION TESTING")
    print("\nThis script helps you obtain OAuth access tokens for testing.")
    print("You'll need OAuth app credentials from GitHub or Google.")
    print("\nFor setup instructions, see: docs/OAUTH_TESTING_SETUP.md")

    # Determine provider
    provider = args.provider
    if not provider:
        print("\n🔧 Select OAuth Provider:")
        print("  1. GitHub")
        print("  2. Google")
        choice = input("\nEnter choice (1 or 2): ").strip()

        if choice == "1":
            provider = "github"
        elif choice == "2":
            provider = "google"
        else:
            print_error("Invalid choice")
            sys.exit(1)

    # Get credentials
    if provider == "github":
        client_id = os.getenv("GITHUB_CLIENT_ID") or input("\n🔑 GitHub Client ID: ").strip()
        client_secret = os.getenv("GITHUB_CLIENT_SECRET") or input("🔑 GitHub Client Secret: ").strip()

        if not client_id or not client_secret:
            print_error("Client ID and Secret are required")
            print_info("Get them from: https://github.com/settings/developers")
            sys.exit(1)

        asyncio.run(get_github_token(client_id, client_secret, args.manual))

    elif provider == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID") or input("\n🔑 Google Client ID: ").strip()
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or input("🔑 Google Client Secret: ").strip()

        if not client_id or not client_secret:
            print_error("Client ID and Secret are required")
            print_info("Get them from: https://console.cloud.google.com")
            sys.exit(1)

        asyncio.run(get_google_token(client_id, client_secret, args.manual))

    print("\n" + "=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Copy the export commands above and run them in your terminal")
    print("2. Or add them to your .env file and run: export $(cat .env | xargs)")
    print("3. Run integration tests: pytest tests/test_oauth_integration.py -v -m integration")
    print("=" * 70)


if __name__ == "__main__":
    main()
