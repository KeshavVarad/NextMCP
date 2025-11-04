#!/usr/bin/env python3
"""
JWT Token Generator

Utility to generate JWT tokens for testing the auth_jwt example.

Usage:
    python generate_token.py --user admin --role admin
    python generate_token.py --user alice --role user
    python generate_token.py --user bob --role viewer --expires 7200
"""

import argparse

from nextmcp.auth import JWTProvider

# Must match the secret in server.py
SECRET_KEY = "your-secret-key-change-in-production"


def main():
    parser = argparse.ArgumentParser(description="Generate JWT tokens for testing")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--role", required=True, help="User role (admin, user, viewer)")
    parser.add_argument(
        "--expires", type=int, default=3600, help="Token expiration in seconds (default: 3600)"
    )

    args = parser.parse_args()

    # Map roles to permissions
    role_permissions = {
        "admin": ["read:*", "write:*", "delete:*"],
        "user": ["read:posts", "write:own_posts"],
        "viewer": ["read:posts"],
    }

    permissions = role_permissions.get(args.role, ["read:posts"])

    # Create JWT provider
    provider = JWTProvider(secret_key=SECRET_KEY)

    # Generate token
    token = provider.create_token(
        user_id=f"user_{args.user}",
        roles=[args.role],
        permissions=permissions,
        username=args.user,
        expires_in=args.expires,
    )

    print("=" * 60)
    print("JWT Token Generated")
    print("=" * 60)
    print()
    print(f"User:        {args.user}")
    print(f"Role:        {args.role}")
    print(f"Permissions: {', '.join(permissions)}")
    print(f"Expires in:  {args.expires} seconds ({args.expires/3600:.1f} hours)")
    print()
    print("Token:")
    print("-" * 60)
    print(token)
    print("-" * 60)
    print()
    print("Usage in your client:")
    print('  auth={"token": "' + token[:20] + '..."}')
    print()
    print("To decode the token, visit: https://jwt.io")
    print("=" * 60)


if __name__ == "__main__":
    main()
