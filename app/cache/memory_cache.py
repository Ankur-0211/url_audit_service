import threading
import time
from typing import Any, Optional


class TTLCache:
    """
    Thread-safe in-memory cache with per-entry TTL.
    Interface (get/set) is intentionally identical to the future
    RedisCache implementation (Task B, SDD §14) so the swap is
    a drop-in replacement with zero changes to audit_service.py.
    """

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            expires_at, value = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None

            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            expires_at = time.monotonic() + ttl_seconds
            self._store[key] = (expires_at, value)


# Single shared instance for the whole app process
audit_cache = TTLCache()
