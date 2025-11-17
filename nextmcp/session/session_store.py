"""
Session store implementations for NextMCP.

Provides pluggable session storage for OAuth tokens, user identity,
and session state. Supports multiple backends (memory, file, Redis, etc.).
"""

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """
    Session data stored for each user.

    Contains OAuth tokens, user information, and session metadata.
    """

    user_id: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: float | None = None  # Unix timestamp
    scopes: list[str] = field(default_factory=list)
    user_info: dict[str, Any] = field(default_factory=dict)
    provider: str | None = None  # OAuth provider name
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)  # Custom data

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """
        Check if token needs refreshing.

        Args:
            buffer_seconds: Refresh if expiring within this many seconds (default 5 min)

        Returns:
            True if token should be refreshed
        """
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - buffer_seconds)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create SessionData from dictionary."""
        return cls(**data)


class SessionStore(ABC):
    """
    Abstract base class for session storage.

    Subclasses implement different storage backends (memory, file, Redis, etc.).
    """

    @abstractmethod
    def save(self, session: SessionData) -> None:
        """
        Save session data.

        Args:
            session: Session data to save
        """
        pass

    @abstractmethod
    def load(self, user_id: str) -> SessionData | None:
        """
        Load session data for a user.

        Args:
            user_id: User identifier

        Returns:
            SessionData if found, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """
        Delete session data for a user.

        Args:
            user_id: User identifier

        Returns:
            True if session was deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, user_id: str) -> bool:
        """
        Check if session exists for a user.

        Args:
            user_id: User identifier

        Returns:
            True if session exists
        """
        pass

    @abstractmethod
    def list_users(self) -> list[str]:
        """
        List all user IDs with active sessions.

        Returns:
            List of user IDs
        """
        pass

    @abstractmethod
    def clear_all(self) -> int:
        """
        Clear all sessions.

        Returns:
            Number of sessions deleted
        """
        pass

    def update_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
    ) -> None:
        """
        Update tokens for an existing session.

        Args:
            user_id: User identifier
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_in: Token expiration in seconds (optional)
        """
        session = self.load(user_id)
        if not session:
            raise ValueError(f"No session found for user: {user_id}")

        session.access_token = access_token
        if refresh_token:
            session.refresh_token = refresh_token
        if expires_in:
            session.expires_at = time.time() + expires_in
        session.updated_at = time.time()

        self.save(session)


class MemorySessionStore(SessionStore):
    """
    In-memory session storage.

    Sessions are stored in RAM and lost when the process restarts.
    Useful for development and testing.

    Thread-safe with locking.
    """

    def __init__(self):
        """Initialize memory session store."""
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.RLock()

    def save(self, session: SessionData) -> None:
        """Save session to memory."""
        with self._lock:
            session.updated_at = time.time()
            self._sessions[session.user_id] = session
            logger.debug(f"Saved session for user: {session.user_id}")

    def load(self, user_id: str) -> SessionData | None:
        """Load session from memory."""
        with self._lock:
            session = self._sessions.get(user_id)
            if session:
                logger.debug(f"Loaded session for user: {user_id}")
            return session

    def delete(self, user_id: str) -> bool:
        """Delete session from memory."""
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
                logger.debug(f"Deleted session for user: {user_id}")
                return True
            return False

    def exists(self, user_id: str) -> bool:
        """Check if session exists in memory."""
        with self._lock:
            return user_id in self._sessions

    def list_users(self) -> list[str]:
        """List all user IDs in memory."""
        with self._lock:
            return list(self._sessions.keys())

    def clear_all(self) -> int:
        """Clear all sessions from memory."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            logger.info(f"Cleared {count} sessions from memory")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove expired sessions from memory.

        Returns:
            Number of expired sessions removed
        """
        with self._lock:
            expired = [
                user_id
                for user_id, session in self._sessions.items()
                if session.is_expired()
            ]
            for user_id in expired:
                del self._sessions[user_id]
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            return len(expired)


class FileSessionStore(SessionStore):
    """
    File-based session storage.

    Sessions are stored as JSON files in a directory.
    Persists across process restarts.

    Thread-safe with locking.
    """

    def __init__(self, directory: str | Path = ".nextmcp_sessions"):
        """
        Initialize file session store.

        Args:
            directory: Directory to store session files (default: .nextmcp_sessions)
        """
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        logger.info(f"File session store initialized at: {self.directory}")

    def _get_path(self, user_id: str) -> Path:
        """Get file path for user session."""
        # Sanitize user_id for filename (replace invalid chars)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.directory / f"session_{safe_id}.json"

    def save(self, session: SessionData) -> None:
        """Save session to file."""
        with self._lock:
            session.updated_at = time.time()
            path = self._get_path(session.user_id)
            try:
                with open(path, "w") as f:
                    json.dump(session.to_dict(), f, indent=2)
                logger.debug(f"Saved session for user: {session.user_id}")
            except Exception as e:
                logger.error(f"Failed to save session for {session.user_id}: {e}")
                raise

    def load(self, user_id: str) -> SessionData | None:
        """Load session from file."""
        with self._lock:
            path = self._get_path(user_id)
            if not path.exists():
                return None

            try:
                with open(path) as f:
                    data = json.load(f)
                session = SessionData.from_dict(data)
                logger.debug(f"Loaded session for user: {user_id}")
                return session
            except Exception as e:
                logger.error(f"Failed to load session for {user_id}: {e}")
                return None

    def delete(self, user_id: str) -> bool:
        """Delete session file."""
        with self._lock:
            path = self._get_path(user_id)
            if path.exists():
                try:
                    path.unlink()
                    logger.debug(f"Deleted session for user: {user_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to delete session for {user_id}: {e}")
                    return False
            return False

    def exists(self, user_id: str) -> bool:
        """Check if session file exists."""
        with self._lock:
            return self._get_path(user_id).exists()

    def list_users(self) -> list[str]:
        """List all user IDs with session files."""
        with self._lock:
            users = []
            for path in self.directory.glob("session_*.json"):
                try:
                    with open(path) as f:
                        data = json.load(f)
                        users.append(data["user_id"])
                except Exception as e:
                    logger.warning(f"Failed to read session file {path}: {e}")
            return users

    def clear_all(self) -> int:
        """Delete all session files."""
        with self._lock:
            count = 0
            for path in self.directory.glob("session_*.json"):
                try:
                    path.unlink()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to delete session file {path}: {e}")
            logger.info(f"Cleared {count} sessions from file store")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove expired session files.

        Returns:
            Number of expired sessions removed
        """
        with self._lock:
            count = 0
            for path in self.directory.glob("session_*.json"):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    session = SessionData.from_dict(data)
                    if session.is_expired():
                        path.unlink()
                        count += 1
                except Exception as e:
                    logger.warning(f"Failed to check/delete expired session {path}: {e}")
            if count:
                logger.info(f"Cleaned up {count} expired sessions from file store")
            return count
