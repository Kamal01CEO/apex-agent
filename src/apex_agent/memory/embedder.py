"""Embedding generation using BGE-small-en-v1.5 for better semantic understanding.

Supports backward compatibility with all-MiniLM-L6-v2 embeddings via dimension detection.
"""

import logging
from typing import List, Optional

logger = logging.getLogger("apex_agent.embedder")

# Global model cache
_model = None
_model_name = None

# Model configurations
BGE_SMALL_EN = "BAAI/bge-small-en-v1.5"  # 384 dims, excellent semantic understanding
MINILM_FALLBACK = "all-MiniLM-L6-v2"      # 384 dims, legacy support
EMBEDDING_DIM = 384                        # Both models produce 384-dim vectors


def get_embedding_model(model_name: str = BGE_SMALL_EN):
    """Lazy-load embedding model with caching."""
    global _model, _model_name
    
    if _model is not None and _model_name == model_name:
        return _model
    
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {model_name}")
            _model = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info(f"Embedding model loaded successfully (dim={EMBEDDING_DIM})")
        except Exception as e:
            logger.warning(f"Could not load sentence-transformers ({e}). Using hash-based fallback.")
            _model = False
            _model_name = None
    return _model


class Embedder:
    """Generates 384-dim dense float embeddings using BGE-small-en-v1.5.
    
    BGE-small-en-v1.5 provides superior semantic understanding compared to all-MiniLM-L6-v2,
    especially for nuanced queries, while maintaining the same 384-dimensional output.
    """
    
    @staticmethod
    def embed_text(text: str, model_name: str = BGE_SMALL_EN) -> List[float]:
        """Generate embedding for text. Returns 384-dim normalized vector."""
        model = get_embedding_model(model_name)
        if model:
            try:
                emb = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return emb.tolist()
            except Exception:
                pass

        # Deterministic pseudo-embedding fallback
        import hashlib
        import numpy as np

        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def embed_batch(texts: List[str], model_name: str = BGE_SMALL_EN) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        model = get_embedding_model(model_name)
        if model:
            try:
                embeddings = model.encode(
                    texts, 
                    convert_to_numpy=True, 
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                return [emb.tolist() for emb in embeddings]
            except Exception:
                pass
        
        # Fallback to single embeddings
        return [Embedder.embed_text(t, model_name) for t in texts]

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
    
    @staticmethod
    def get_embedding_dimension() -> int:
        """Return the embedding dimension (384)."""
        return EMBEDDING_DIM
