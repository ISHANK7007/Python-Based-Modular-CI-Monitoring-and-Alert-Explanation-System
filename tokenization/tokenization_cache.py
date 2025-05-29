from collections import OrderedDict
from typing import Optional
from tokenization.models import TokenizedSegment  # Adjust path if needed


class TokenizationCache:
    """LRU cache for tokenization results to improve performance and avoid redundant parsing."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, TokenizedSegment] = OrderedDict()

    def get(self, key: str) -> Optional[TokenizedSegment]:
        """Retrieve cached tokenization result if available and mark as recently used."""
        value = self.cache.pop(key, None)
        if value is not None:
            self.cache[key] = value  # Re-insert to mark as recently used
        return value

    def set(self, key: str, value: TokenizedSegment) -> None:
        """Store tokenization result in cache with LRU eviction."""
        if key in self.cache:
            self.cache.pop(key)  # Remove to reinsert and mark as recently used
        elif len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # Evict least recently used item
        self.cache[key] = value

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def __len__(self) -> int:
        """Returns current cache size."""
        return len(self.cache)
