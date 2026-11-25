import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """Thread-safe in-memory TTL cache for external API responses."""

    def __init__(self, default_ttl_seconds: int = 600) -> None:
        self._default_ttl = max(0, default_ttl_seconds)
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if self._default_ttl <= 0:
            self._misses += 1
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            expires_at, value = entry
            if now >= expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = self._default_ttl if ttl_seconds is None else max(0, ttl_seconds)
        if ttl <= 0:
            return
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._store[key] = (expires_at, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
            }
