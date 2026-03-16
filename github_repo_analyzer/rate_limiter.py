"""
GitHub API rate limit monitoring and auto-backoff.
"""

import time
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Monitors GitHub API rate limits and automatically throttles requests when approaching the limit.

    Attributes:
        github_client: Authenticated PyGithub instance
        low_threshold: Remaining requests threshold to trigger wait (default: 100)
        warning_threshold: Remaining requests to log a warning (default: 500)
    """

    def __init__(self, github_client, low_threshold: int = 100, warning_threshold: int = 500):
        self.g = github_client
        self.low_threshold = low_threshold
        self.warning_threshold = warning_threshold
        self.remaining: Optional[int] = None
        self.limit: Optional[int] = None
        self.reset_at: Optional[float] = None
        self.last_updated: Optional[float] = None
        self._logger = logger

    def update(self) -> bool:
        """
        Fetch current rate limit status from GitHub API.

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            limits = self.g.get_rate_limit()
            self.remaining = limits.rate_limit.remaining
            self.limit = limits.rate_limit.limit
            reset_time = limits.rate_limit.reset
            # Convert to timestamp
            if hasattr(reset_time, 'timestamp'):
                self.reset_at = reset_time.replace(tzinfo=timezone.utc).timestamp()
            else:
                self.reset_at = time.time() + 60
            self.last_updated = time.time()
            self._log_current_limits()
            return True
        except Exception as e:
            self._logger.debug(f"Failed to fetch rate limit: {e}")
            return False

    def _log_current_limits(self):
        """Log current rate limit status at appropriate level."""
        if self.remaining is None:
            return
        if self.remaining < self.low_threshold:
            self._logger.warning(
                f"API rate limit low: {self.remaining}/{self.limit} remaining. "
                f"Reset at {self.reset_at - time.time():.0f}s."
            )
        elif self.remaining < self.warning_threshold:
            self._logger.info(
                f"API rate limit: {self.remaining}/{self.limit} remaining. "
                f"Reset at {self.reset_at - time.time():.0f}s."
            )
        else:
            self._logger.debug(f"API rate limit: {self.remaining}/{self.limit} remaining.")

    def check(self, force_update: bool = False):
        """
        Check rate limit and sleep if necessary to avoid hitting limit.

        Args:
            force_update: Force refresh of rate limit data
        """
        if force_update or self.remaining is None or (time.time() - (self.last_updated or 0)) > 60:
            self.update()

        if self.remaining is not None and self.remaining < self.low_threshold:
            sleep_time = self.reset_at - time.time()
            if sleep_time > 0:
                self._logger.warning(
                    f"Approaching rate limit ({self.remaining}/{self.limit}). "
                    f"Sleeping for {sleep_time:.0f} seconds until reset."
                )
                time.sleep(sleep_time + 1)  # add 1 second buffer
                self.update()  # Refresh after sleep

    def consume(self, count: int = 1):
        """
        Consume a number of requests from the remaining pool without actually making an API call.
        Useful for estimating usage before batch operations.
        """
        if self.remaining is not None:
            self.remaining = max(0, self.remaining - count)

    def get_status(self) -> dict:
        """
        Get current rate limit status.

        Returns:
            Dictionary with keys: remaining, limit, reset_at, last_updated
        """
        return {
            'remaining': self.remaining,
            'limit': self.limit,
            'reset_at': self.reset_at,
            'last_updated': self.last_updated,
            'reset_in_seconds': (self.reset_at - time.time()) if self.reset_at else None
        }
