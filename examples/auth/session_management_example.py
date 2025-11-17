"""
Session Management Example

This example demonstrates advanced session management features:
- Manual session creation and management
- Session inspection and monitoring
- Token refresh workflows
- Session cleanup strategies
- Custom session metadata

This is useful for understanding how sessions work internally and for
building custom session management logic.

Run this example:
    python examples/auth/session_management_example.py
"""

import asyncio
import time
from pathlib import Path

from nextmcp.session import (
    FileSessionStore,
    MemorySessionStore,
    SessionData,
)


async def main():
    """Run session management demonstrations."""
    print("\n" + "=" * 70)
    print("NextMCP Session Management Examples")
    print("=" * 70 + "\n")

    # ========================================================================
    # Example 1: Basic Session Operations
    # ========================================================================

    print("📋 Example 1: Basic Session Operations")
    print("-" * 70)

    # Create session store (using memory for demo)
    session_store = MemorySessionStore()

    # Create a session
    session = SessionData(
        user_id="user123",
        access_token="ya29.a0ATi6K2example_access_token",
        refresh_token="1//01example_refresh_token",
        expires_at=time.time() + 3600,  # Expires in 1 hour
        scopes=["openid", "email", "profile"],
        user_info={
            "email": "user@example.com",
            "name": "John Doe",
            "picture": "https://example.com/photo.jpg",
        },
        provider="google",
    )

    # Save session
    session_store.save(session)
    print(f"✓ Created session for user: {session.user_id}")
    print(f"  Provider: {session.provider}")
    print(f"  Scopes: {', '.join(session.scopes)}")
    print(f"  Expires: in {int((session.expires_at - time.time()) / 60)} minutes")

    # Load session
    loaded = session_store.load("user123")
    print(f"\n✓ Loaded session for user: {loaded.user_id}")
    print(f"  Email: {loaded.user_info.get('email')}")
    print(f"  Name: {loaded.user_info.get('name')}")

    # ========================================================================
    # Example 2: Token Expiration Handling
    # ========================================================================

    print("\n\n📋 Example 2: Token Expiration Handling")
    print("-" * 70)

    # Create session expiring soon
    expiring_session = SessionData(
        user_id="user456",
        access_token="token_expires_soon",
        expires_at=time.time() + 120,  # Expires in 2 minutes
        scopes=["profile"],
        provider="google",
    )

    session_store.save(expiring_session)

    # Check expiration
    print(f"Token expired? {expiring_session.is_expired()}")
    print(f"Needs refresh (5 min buffer)? {expiring_session.needs_refresh()}")
    print(f"Needs refresh (1 min buffer)? {expiring_session.needs_refresh(buffer_seconds=60)}")

    # Create already-expired session
    expired_session = SessionData(
        user_id="user789",
        access_token="token_expired",
        expires_at=time.time() - 10,  # Expired 10 seconds ago
        scopes=["profile"],
        provider="google",
    )

    session_store.save(expired_session)

    print(f"\nExpired token check: {expired_session.is_expired()}")

    # Clean up expired sessions
    cleaned = session_store.cleanup_expired()
    print(f"\n✓ Cleaned up {cleaned} expired session(s)")
    print(f"  Remaining sessions: {len(session_store.list_users())}")

    # ========================================================================
    # Example 3: Updating Tokens (Refresh Flow)
    # ========================================================================

    print("\n\n📋 Example 3: Updating Tokens (Refresh Flow)")
    print("-" * 70)

    # Simulate token refresh
    print("Simulating token refresh for user123...")

    # Load existing session
    session = session_store.load("user123")
    old_token = session.access_token

    # Update with new tokens (simulating OAuth refresh)
    session_store.update_tokens(
        user_id="user123",
        access_token="ya29.a0NEW_ACCESS_TOKEN_after_refresh",
        refresh_token="1//01NEW_REFRESH_TOKEN",
        expires_in=3600,  # New expiration (1 hour from now)
    )

    # Verify update
    updated = session_store.load("user123")
    print(f"✓ Token refreshed")
    print(f"  Old token: {old_token[:20]}...")
    print(f"  New token: {updated.access_token[:20]}...")
    print(f"  Expires in: {int((updated.expires_at - time.time()) / 60)} minutes")

    # ========================================================================
    # Example 4: Custom Session Metadata
    # ========================================================================

    print("\n\n📋 Example 4: Custom Session Metadata")
    print("-" * 70)

    # Create session with custom metadata
    session_with_metadata = SessionData(
        user_id="poweruser",
        access_token="token_with_metadata",
        scopes=["admin"],
        provider="google",
        metadata={
            "subscription": "premium",
            "preferences": {
                "theme": "dark",
                "notifications": True,
            },
            "usage_stats": {
                "requests_today": 42,
                "last_request": time.time(),
            },
            "roles": ["admin", "developer"],
        },
    )

    session_store.save(session_with_metadata)

    # Retrieve and use metadata
    loaded = session_store.load("poweruser")
    print("✓ Session with custom metadata:")
    print(f"  Subscription: {loaded.metadata.get('subscription')}")
    print(f"  Theme: {loaded.metadata.get('preferences', {}).get('theme')}")
    print(f"  Roles: {loaded.metadata.get('roles')}")
    print(f"  Requests today: {loaded.metadata.get('usage_stats', {}).get('requests_today')}")

    # ========================================================================
    # Example 5: File-Based Session Persistence
    # ========================================================================

    print("\n\n📋 Example 5: File-Based Session Persistence")
    print("-" * 70)

    # Create file-based session store
    file_store = FileSessionStore(".example_sessions")

    # Create sessions
    for i in range(3):
        session = SessionData(
            user_id=f"file_user_{i}",
            access_token=f"token_{i}",
            scopes=["profile"],
            provider="google",
            user_info={"email": f"user{i}@example.com"},
        )
        file_store.save(session)

    print(f"✓ Created {len(file_store.list_users())} file-based sessions")
    print(f"  Storage location: {file_store.directory.absolute()}")

    # List files
    files = list(file_store.directory.glob("session_*.json"))
    print(f"  Files created: {len(files)}")
    for file in files:
        print(f"    - {file.name}")

    # Test persistence across instances
    file_store2 = FileSessionStore(".example_sessions")
    users = file_store2.list_users()
    print(f"\n✓ Loaded {len(users)} sessions from disk (different instance)")

    # Cleanup
    file_store.clear_all()
    print(f"✓ Cleaned up file-based sessions")

    # ========================================================================
    # Example 6: Multi-User Session Management
    # ========================================================================

    print("\n\n📋 Example 6: Multi-User Session Management")
    print("-" * 70)

    # Create sessions for multiple users
    users = [
        ("alice", "google", ["email", "profile"]),
        ("bob", "github", ["read:user", "repo"]),
        ("charlie", "google", ["email", "profile", "drive.readonly"]),
        ("diana", "github", ["read:user"]),
    ]

    store = MemorySessionStore()

    for user_id, provider, scopes in users:
        session = SessionData(
            user_id=user_id,
            access_token=f"token_{user_id}",
            scopes=scopes,
            provider=provider,
            user_info={"username": user_id},
        )
        store.save(session)

    print(f"✓ Created {len(store.list_users())} user sessions")

    # Group by provider
    google_users = []
    github_users = []

    for user_id in store.list_users():
        session = store.load(user_id)
        if session.provider == "google":
            google_users.append(user_id)
        else:
            github_users.append(user_id)

    print(f"\n  Google users: {google_users}")
    print(f"  GitHub users: {github_users}")

    # ========================================================================
    # Example 7: Session Monitoring
    # ========================================================================

    print("\n\n📋 Example 7: Session Monitoring")
    print("-" * 70)

    # Create mix of sessions with different states
    monitoring_store = MemorySessionStore()

    # Active session
    active = SessionData(
        user_id="active_user",
        access_token="token_active",
        expires_at=time.time() + 3600,
        scopes=["profile"],
        provider="google",
    )
    monitoring_store.save(active)

    # Expiring soon
    expiring = SessionData(
        user_id="expiring_user",
        access_token="token_expiring",
        expires_at=time.time() + 120,  # 2 minutes
        scopes=["profile"],
        provider="google",
    )
    monitoring_store.save(expiring)

    # Expired
    expired = SessionData(
        user_id="expired_user",
        access_token="token_expired",
        expires_at=time.time() - 10,
        scopes=["profile"],
        provider="google",
    )
    monitoring_store.save(expired)

    # Monitor sessions
    all_users = monitoring_store.list_users()
    print(f"Total sessions: {len(all_users)}")

    active_count = 0
    expiring_count = 0
    expired_count = 0

    for user_id in all_users:
        session = monitoring_store.load(user_id)
        if session.is_expired():
            expired_count += 1
            print(f"  ❌ {user_id}: Expired")
        elif session.needs_refresh():
            expiring_count += 1
            print(f"  ⚠️  {user_id}: Expiring soon")
        else:
            active_count += 1
            print(f"  ✓ {user_id}: Active")

    print(f"\nSummary:")
    print(f"  Active: {active_count}")
    print(f"  Expiring soon: {expiring_count}")
    print(f"  Expired: {expired_count}")

    # ========================================================================
    # Cleanup
    # ========================================================================

    print("\n\n📋 Cleanup")
    print("-" * 70)

    # Clean up example session directory
    if Path(".example_sessions").exists():
        import shutil

        shutil.rmtree(".example_sessions")
        print("✓ Removed example session directory")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
