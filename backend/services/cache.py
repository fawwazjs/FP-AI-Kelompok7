from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, *, max_items: int, ttl_seconds: int) -> None:
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._items.get(key)
        if entry is None:
            return None

        if monotonic() >= entry.expires_at:
            self._items.pop(key, None)
            return None

        return entry.value

    def set(self, key: str, value: T) -> None:
        self._prune_expired()
        if len(self._items) >= self.max_items:
            oldest_key = min(self._items, key=lambda item_key: self._items[item_key].expires_at)
            self._items.pop(oldest_key, None)

        self._items[key] = CacheEntry(
            value=value,
            expires_at=monotonic() + self.ttl_seconds,
        )

    def _prune_expired(self) -> None:
        now = monotonic()
        expired_keys = [key for key, entry in self._items.items() if now >= entry.expires_at]
        for key in expired_keys:
            self._items.pop(key, None)
