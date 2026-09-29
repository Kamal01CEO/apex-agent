"""Fast embedding generation using BGE-small or Nomic for better semantic understanding."""

import logging
from typing import List, Optional
from functools import lru_cache

logger = logging.getLogger("apex_agent.embedder")

_model = None
_model_name = None


def get_embedding_model():
    """Load BGE-small-en-v1.5 for best local performance, fallback to all-MiniLM-L6-v2."""
    global _model, _model_name
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Try modern BGE model first (better semantic understanding)
            try:
                _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
                _model_name = "bge-small-en-v1.5"
                logger.info("Loaded BGE-small-en-v1.5 embedding model (384-dim)")
            except Exception:
                # Fallback to older but reliable model
                _model = SentenceTransformer("all-MiniLM-L6-v2")
                _model_name = "all-MiniLM-L6-v2"
                logger.info("Loaded all-MiniLM-L6-v2 embedding model (fallback, 384-dim)")
        except Exception as e:
            logger.warning("Could not load sentence-transformers (%s). Using hash-based fallback.", e)
            _model = False
    return _model


def get_model_name() -> str:
    """Return the currently loaded model name."""
    return _model_name or "fallback"


class Embedder:
    """Generates dense float embeddings with caching and batch support."""

    @staticmethod
    @lru_cache(maxsize=500)
    def embed_text_cached(text: str) -> tuple:
        """Cached embedding for repeated queries. Returns tuple for hashability."""
        result = Embedder.embed_text(text)
        return tuple(result)

    @staticmethod
    def embed_text(text: str) -> List[float]:
        """Generate 384-dim dense embedding for a single text."""
        model = get_embedding_model()
        if model:
            try:
                emb = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
                return emb.tolist()
            except Exception:
                pass

        # Deterministic pseudo-embedding fallback
        import hashlib
        import numpy as np

        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(384).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def embed_batch(texts: List[str]) -> List[List[float]]:
        """Batch embedding for efficiency when processing multiple texts."""
        if not texts:
            return []
        
        model = get_embedding_model()
        if model:
            try:
                import numpy as np
                embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
                return [emb.tolist() for emb in embeddings]
            except Exception:
                pass
        
        # Fallback: process individually
        return [Embedder.embed_text(t) for t in texts]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import numpy as np

        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
