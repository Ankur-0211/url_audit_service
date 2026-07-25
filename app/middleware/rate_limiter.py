import threading
import time
from app.core.config import settings


class SlidingWindowRateLimiter:
    """
    Per-IP sliding window log rate limiter, in-memory.
    Interface designed so a Redis-backed version (Task B, SDD §15)
    is a drop-in replacement.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, client_ip: str) -> tuple[bool, float]:
        """
        Returns (allowed, retry_after_seconds).
        retry_after_seconds is 0 when allowed is True.
        """
        now = time.monotonic()
        window_start = now - self._window_seconds

        with self._lock:
            timestamps = self._requests.get(client_ip, [])
            # Prune anything outside the window
            timestamps = [t for t in timestamps if t > window_start]

            if len(timestamps) >= self._max_requests:
                oldest = timestamps[0]
                retry_after = oldest + self._window_seconds - now
                self._requests[client_ip] = timestamps
                return False, max(retry_after, 0.0)

            timestamps.append(now)
            self._requests[client_ip] = timestamps
            return True, 0.0


rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
