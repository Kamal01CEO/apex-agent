"""Semantic caching to avoid repeated LLM calls for similar queries."""

import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
from apex_agent.memory.embedder import Embedder

logger = logging.getLogger("apex_agent.cache")


class SemanticCache:
    """LRU cache with semantic similarity matching for query deduplication."""

    def __init__(self, max_size: int = 200, similarity_threshold: float = 0.92, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: OrderedDict[str, Tuple[float, Dict[str, Any], datetime]] = OrderedDict()
        self._embeddings: Dict[str, list] = {}
        self._lock = threading.RLock()

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Check if semantically similar query exists in cache."""
        with self._lock:
            query_emb = Embedder.embed_text_cached(query)
            now = datetime.now()

            # Check for similar cached queries
            for cached_query, (score, result, timestamp) in list(self._cache.items()):
                # Check TTL
                if now - timestamp > self.ttl:
                    self._evict(cached_query)
                    continue

                # Check semantic similarity
                if cached_query in self._embeddings:
                    cached_emb = self._embeddings[cached_query]
                    similarity = Embedder.cosine_similarity(query_emb, cached_emb)

                    if similarity >= self.similarity_threshold:
                        # Move to end (most recently used)
                        self._cache.move_to_end(cached_query)
                        logger.debug("Cache hit: similarity=%.3f for query='%s'", similarity, query[:50])
                        return result

            return None

    def set(self, query: str, result: Dict[str, Any]):
        """Store query result in cache."""
        with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self.max_size:
                self._evict_oldest()

            query_emb = Embedder.embed_text_cached(query)
            self._cache[query] = (0.0, result, datetime.now())
            self._embeddings[query] = list(query_emb)

    def _evict(self, query: str):
        """Remove specific query from cache."""
        self._cache.pop(query, None)
        self._embeddings.pop(query, None)

    def _evict_oldest(self):
        """Evict the least recently used entry."""
        if self._cache:
            oldest_query = next(iter(self._cache))
            self._evict(oldest_query)

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._embeddings.clear()

    def stats(self) -> Dict[str, int]:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "embeddings_stored": len(self._embeddings),
        }
