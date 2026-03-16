"""
Persistent caching using SQLite with TTL support.
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Any, Optional
import os
from threading import Lock


class SQLiteCache:
    """
    Thread-safe SQLite cache with time-to-live expiration.
    """

    def __init__(self, db_path: str = ".github_repo_analyzer_cache.db", default_ttl: int = 600):
        """
        Initialize cache.

        Args:
            db_path: Path to SQLite database file
            default_ttl: Default TTL in seconds (10 minutes)
        """
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._lock = Lock()
        self._init_db()

    def _init_db(self):
        """Create cache table if not exists."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at INTEGER NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache (expires_at)")
                conn.commit()
            finally:
                conn.close()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                if row:
                    value_json, expires_at = row
                    if expires_at > int(time.time()):
                        return json.loads(value_json)
                    else:
                        # Expired, delete
                        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                        conn.commit()
                return None
            finally:
                conn.close()

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a cache value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: TTL in seconds (uses default if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = int(time.time()) + ttl
        value_json = json.dumps(value, default=str)

        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, value_json, expires_at)
                )
                conn.commit()
            finally:
                conn.close()

    def delete(self, key: str):
        """Remove a key from cache."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
            finally:
                conn.close()

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute("DELETE FROM cache")
                conn.commit()
            finally:
                conn.close()

    def cleanup_expired(self):
        """Remove expired entries."""
        now = int(time.time())
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                conn.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
                conn.commit()
            finally:
                conn.close()

    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            try:
                cursor = conn.execute("SELECT COUNT(*), MIN(expires_at), MAX(expires_at) FROM cache")
                total, min_exp, max_exp = cursor.fetchone()
                now = int(time.time())
                cursor = conn.execute("SELECT COUNT(*) FROM cache WHERE expires_at > ?", (now,))
                active = cursor.fetchone()[0]
                return {
                    "total_entries": total or 0,
                    "active_entries": active,
                    "expired_entries": (total or 0) - active,
                    "oldest_expiration": datetime.fromtimestamp(min_exp).isoformat() if min_exp else None,
                    "newest_expiration": datetime.fromtimestamp(max_exp).isoformat() if max_exp else None,
                }
            finally:
                conn.close()
