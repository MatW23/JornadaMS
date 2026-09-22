"""Small in-process login limiter for single-instance deployments."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    """Limit failed login attempts by independent client keys.

    This protects the local development/single-instance deployment. A multi-worker
    production deployment must enforce the same policy at the gateway or in Redis.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, keys: list[str]) -> int | None:
        """Return remaining block time when any key is currently blocked."""

        now = monotonic()
        with self._lock:
            retry_after = 0
            for key in keys:
                attempts = self._attempts.get(key)
                if attempts is None:
                    continue
                self._discard_expired(attempts, now)
                if len(attempts) >= self.max_attempts and attempts:
                    retry_after = max(
                        retry_after,
                        int(self.window_seconds - (now - attempts[0])) + 1,
                    )
            return retry_after or None

    def record_failure(self, keys: list[str]) -> None:
        """Record one failed attempt for each independent key."""

        now = monotonic()
        with self._lock:
            for key in keys:
                attempts = self._attempts[key]
                self._discard_expired(attempts, now)
                attempts.append(now)

    def clear(self, keys: list[str]) -> None:
        """Clear counters after a successful authentication."""

        with self._lock:
            for key in keys:
                self._attempts.pop(key, None)

    def _discard_expired(self, attempts: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
