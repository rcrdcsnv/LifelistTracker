# utils/cache.py
from collections import OrderedDict
from typing import TypeVar, Generic, Optional

K = TypeVar('K')
V = TypeVar('V')


class LRUCache(Generic[K, V]):
    """Simple LRU cache implementation"""

    def __init__(self, capacity: int):
        self.cache: OrderedDict[K, V] = OrderedDict()
        self.capacity = capacity

    def get(self, key: K) -> Optional[V]:
        """Get item from cache, updating its position in LRU order"""
        if key not in self.cache:
            return None

        # Move to end (most recently used)
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def put(self, key: K, value: V) -> None:
        """Add or update item in cache"""
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            # Remove oldest item
            self.cache.popitem(last=False)

        self.cache[key] = value

    def __contains__(self, key: K) -> bool:
        return key in self.cache

    def __getitem__(self, key: K) -> V:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __len__(self) -> int:
        return len(self.cache)