"""
Tests for Session Store.

Tests the session storage implementations for OAuth tokens and user data.
"""

import tempfile
import time
from pathlib import Path

import pytest

from nextmcp.session.session_store import (
    FileSessionStore,
    MemorySessionStore,
    SessionData,
)


class TestSessionData:
    """Test SessionData functionality."""

    def test_create_session(self):
        """Test creating session data."""
        session = SessionData(
            user_id="user123",
            access_token="token_abc",
            refresh_token="refresh_xyz",
            scopes=["profile", "email"],
        )

        assert session.user_id == "user123"
        assert session.access_token == "token_abc"
        assert session.refresh_token == "refresh_xyz"
        assert "profile" in session.scopes

    def test_session_not_expired(self):
        """Test session not expired."""
        session = SessionData(
            user_id="user123",
            access_token="token",
            expires_at=time.time() + 3600,  # Expires in 1 hour
        )

        assert session.is_expired() is False

    def test_session_expired(self):
        """Test session is expired."""
        session = SessionData(
            user_id="user123",
            access_token="token",
            expires_at=time.time() - 10,  # Expired 10 seconds ago
        )

        assert session.is_expired() is True

    def test_session_no_expiry(self):
        """Test session with no expiry never expires."""
        session = SessionData(
            user_id="user123",
            access_token="token",
            # No expires_at set
        )

        assert session.is_expired() is False

    def test_needs_refresh(self):
        """Test checking if token needs refresh."""
        # Token expiring in 2 minutes
        session = SessionData(
            user_id="user123",
            access_token="token",
            expires_at=time.time() + 120,
        )

        # Should need refresh (default buffer is 5 minutes)
        assert session.needs_refresh() is True

    def test_does_not_need_refresh(self):
        """Test token doesn't need refresh yet."""
        # Token expiring in 10 minutes
        session = SessionData(
            user_id="user123",
            access_token="token",
            expires_at=time.time() + 600,
        )

        # Should not need refresh (default buffer is 5 minutes)
        assert session.needs_refresh() is False

    def test_custom_refresh_buffer(self):
        """Test custom refresh buffer."""
        # Token expiring in 2 minutes
        session = SessionData(
            user_id="user123",
            access_token="token",
            expires_at=time.time() + 120,
        )

        # With 1 minute buffer, should not need refresh
        assert session.needs_refresh(buffer_seconds=60) is False

        # With 3 minute buffer, should need refresh
        assert session.needs_refresh(buffer_seconds=180) is True

    def test_session_to_dict(self):
        """Test serializing session to dict."""
        session = SessionData(
            user_id="user123",
            access_token="token_abc",
            scopes=["profile", "email"],
            provider="google",
        )

        data = session.to_dict()

        assert data["user_id"] == "user123"
        assert data["access_token"] == "token_abc"
        assert data["scopes"] == ["profile", "email"]
        assert data["provider"] == "google"

    def test_session_from_dict(self):
        """Test deserializing session from dict."""
        data = {
            "user_id": "user123",
            "access_token": "token_abc",
            "refresh_token": "refresh_xyz",
            "scopes": ["profile"],
            "provider": "github",
            "created_at": 1234567890.0,
            "updated_at": 1234567890.0,
            "metadata": {},
            "token_type": "Bearer",
            "expires_at": None,
            "user_info": {},
        }

        session = SessionData.from_dict(data)

        assert session.user_id == "user123"
        assert session.access_token == "token_abc"
        assert session.refresh_token == "refresh_xyz"
        assert "profile" in session.scopes
        assert session.provider == "github"

    def test_session_with_user_info(self):
        """Test session with user information."""
        session = SessionData(
            user_id="user123",
            access_token="token",
            user_info={
                "name": "John Doe",
                "email": "john@example.com",
                "avatar": "https://example.com/avatar.jpg",
            },
        )

        assert session.user_info["name"] == "John Doe"
        assert session.user_info["email"] == "john@example.com"


class TestMemorySessionStore:
    """Test MemorySessionStore functionality."""

    def test_save_and_load_session(self):
        """Test saving and loading a session."""
        store = MemorySessionStore()
        session = SessionData(user_id="user123", access_token="token_abc")

        store.save(session)
        loaded = store.load("user123")

        assert loaded is not None
        assert loaded.user_id == "user123"
        assert loaded.access_token == "token_abc"

    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        store = MemorySessionStore()
        loaded = store.load("nonexistent")

        assert loaded is None

    def test_exists(self):
        """Test checking if session exists."""
        store = MemorySessionStore()
        session = SessionData(user_id="user123", access_token="token")

        assert store.exists("user123") is False

        store.save(session)

        assert store.exists("user123") is True

    def test_delete_session(self):
        """Test deleting a session."""
        store = MemorySessionStore()
        session = SessionData(user_id="user123", access_token="token")

        store.save(session)
        assert store.exists("user123") is True

        deleted = store.delete("user123")
        assert deleted is True
        assert store.exists("user123") is False

    def test_delete_nonexistent_session(self):
        """Test deleting a session that doesn't exist."""
        store = MemorySessionStore()
        deleted = store.delete("nonexistent")

        assert deleted is False

    def test_list_users(self):
        """Test listing all users."""
        store = MemorySessionStore()

        store.save(SessionData(user_id="user1", access_token="token1"))
        store.save(SessionData(user_id="user2", access_token="token2"))
        store.save(SessionData(user_id="user3", access_token="token3"))

        users = store.list_users()

        assert len(users) == 3
        assert "user1" in users
        assert "user2" in users
        assert "user3" in users

    def test_clear_all(self):
        """Test clearing all sessions."""
        store = MemorySessionStore()

        store.save(SessionData(user_id="user1", access_token="token1"))
        store.save(SessionData(user_id="user2", access_token="token2"))

        count = store.clear_all()

        assert count == 2
        assert len(store.list_users()) == 0

    def test_update_tokens(self):
        """Test updating tokens for existing session."""
        store = MemorySessionStore()
        session = SessionData(user_id="user123", access_token="old_token")
        store.save(session)

        store.update_tokens(
            user_id="user123",
            access_token="new_token",
            refresh_token="new_refresh",
            expires_in=3600,
        )

        updated = store.load("user123")
        assert updated.access_token == "new_token"
        assert updated.refresh_token == "new_refresh"
        assert updated.expires_at is not None

    def test_update_tokens_nonexistent_session(self):
        """Test updating tokens for nonexistent session raises error."""
        store = MemorySessionStore()

        with pytest.raises(ValueError, match="No session found"):
            store.update_tokens("nonexistent", "token")

    def test_cleanup_expired(self):
        """Test cleaning up expired sessions."""
        store = MemorySessionStore()

        # Create sessions: one expired, one valid
        store.save(
            SessionData(
                user_id="expired_user",
                access_token="token1",
                expires_at=time.time() - 10,  # Expired
            )
        )
        store.save(
            SessionData(
                user_id="valid_user",
                access_token="token2",
                expires_at=time.time() + 3600,  # Valid
            )
        )

        count = store.cleanup_expired()

        assert count == 1
        assert store.exists("expired_user") is False
        assert store.exists("valid_user") is True

    def test_thread_safety(self):
        """Test thread safety of memory store."""
        import threading

        store = MemorySessionStore()

        def save_session(user_id):
            session = SessionData(user_id=user_id, access_token=f"token_{user_id}")
            store.save(session)

        threads = [threading.Thread(target=save_session, args=(f"user{i}",)) for i in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All sessions should be saved
        assert len(store.list_users()) == 10


class TestFileSessionStore:
    """Test FileSessionStore functionality."""

    def test_save_and_load_session(self):
        """Test saving and loading a session from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            session = SessionData(user_id="user123", access_token="token_abc")

            store.save(session)
            loaded = store.load("user123")

            assert loaded is not None
            assert loaded.user_id == "user123"
            assert loaded.access_token == "token_abc"

    def test_persistence_across_instances(self):
        """Test sessions persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create session in first store instance
            store1 = FileSessionStore(tmpdir)
            session = SessionData(user_id="user123", access_token="token_abc")
            store1.save(session)

            # Load session in second store instance
            store2 = FileSessionStore(tmpdir)
            loaded = store2.load("user123")

            assert loaded is not None
            assert loaded.user_id == "user123"
            assert loaded.access_token == "token_abc"

    def test_file_created(self):
        """Test that session file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            session = SessionData(user_id="user123", access_token="token")

            store.save(session)

            # Check file exists
            files = list(Path(tmpdir).glob("session_*.json"))
            assert len(files) == 1

    def test_sanitized_filename(self):
        """Test that user IDs are sanitized for filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            # User ID with special characters
            session = SessionData(user_id="user@email.com", access_token="token")

            store.save(session)
            loaded = store.load("user@email.com")

            assert loaded is not None
            assert loaded.user_id == "user@email.com"

    def test_load_nonexistent_session(self):
        """Test loading nonexistent session returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            loaded = store.load("nonexistent")

            assert loaded is None

    def test_exists(self):
        """Test checking if session file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            session = SessionData(user_id="user123", access_token="token")

            assert store.exists("user123") is False

            store.save(session)

            assert store.exists("user123") is True

    def test_delete_session(self):
        """Test deleting session file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            session = SessionData(user_id="user123", access_token="token")

            store.save(session)
            deleted = store.delete("user123")

            assert deleted is True
            assert store.exists("user123") is False

    def test_list_users(self):
        """Test listing users from files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)

            store.save(SessionData(user_id="user1", access_token="token1"))
            store.save(SessionData(user_id="user2", access_token="token2"))
            store.save(SessionData(user_id="user3", access_token="token3"))

            users = store.list_users()

            assert len(users) == 3
            assert "user1" in users
            assert "user2" in users
            assert "user3" in users

    def test_clear_all(self):
        """Test clearing all session files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)

            store.save(SessionData(user_id="user1", access_token="token1"))
            store.save(SessionData(user_id="user2", access_token="token2"))

            count = store.clear_all()

            assert count == 2
            assert len(store.list_users()) == 0

    def test_cleanup_expired(self):
        """Test cleaning up expired session files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)

            # Create sessions: one expired, one valid
            store.save(
                SessionData(
                    user_id="expired_user",
                    access_token="token1",
                    expires_at=time.time() - 10,
                )
            )
            store.save(
                SessionData(
                    user_id="valid_user",
                    access_token="token2",
                    expires_at=time.time() + 3600,
                )
            )

            count = store.cleanup_expired()

            assert count == 1
            assert store.exists("expired_user") is False
            assert store.exists("valid_user") is True

    def test_directory_creation(self):
        """Test that store creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir) / "sessions" / "nested"
            store = FileSessionStore(session_dir)

            assert session_dir.exists()
            assert session_dir.is_dir()

    def test_update_timestamps(self):
        """Test that save updates timestamps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileSessionStore(tmpdir)
            session = SessionData(user_id="user123", access_token="token")

            original_time = session.updated_at
            time.sleep(0.01)  # Small delay

            store.save(session)

            loaded = store.load("user123")
            assert loaded.updated_at > original_time
