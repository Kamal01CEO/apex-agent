"""Vector database layer using Qdrant (primary) or LanceDB (fallback) for fast ANN search.

Provides efficient approximate nearest neighbor search over dense embeddings,
replacing the slow in-memory cosine similarity computation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger("apex_agent.vector_store")

# Embedding dimension (BGE-small-en-v1.5 and MiniLM both produce 384-dim)
VECTOR_DIM = 384


@dataclass
class VectorMatch:
    """Result from vector similarity search."""
    chunk_id: str
    score: float
    payload: Dict[str, Any]


class VectorStore:
    """Abstract interface for vector databases."""
    
    def upsert(self, chunk_id: str, embedding: List[float], payload: Dict[str, Any]):
        """Insert or update a vector with metadata."""
        raise NotImplementedError
    
    def upsert_batch(self, items: List[Tuple[str, List[float], Dict[str, Any]]]):
        """Batch insert/update vectors."""
        for chunk_id, embedding, payload in items:
            self.upsert(chunk_id, embedding, payload)
    
    def search(self, query_vector: List[float], limit: int = 10, min_score: float = 0.0) -> List[VectorMatch]:
        """Find nearest neighbors by cosine similarity."""
        raise NotImplementedError
    
    def delete(self, chunk_id: str):
        """Remove a vector by ID."""
        raise NotImplementedError
    
    def count(self) -> int:
        """Return total number of vectors."""
        raise NotImplementedError
    
    def close(self):
        """Clean up resources."""
        pass


class QdrantVectorStore(VectorStore):
    """Qdrant-based vector store for production-grade ANN search.
    
    Qdrant provides:
    - Fast HNSW-based ANN search
    - Persistent storage
    - Filtering support
    - Great performance for 100K+ vectors
    """
    
    def __init__(self, collection_name: str = "apex_chunks", db_path: Optional[Path] = None):
        self.collection_name = collection_name
        self.db_path = db_path
        self._client = None
        self._initialized = False
        
    def _get_client(self):
        """Lazy initialization of Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http.models import Distance, VectorParams
                
                # Use local file-based storage for simplicity
                storage_path = str(self.db_path) if self.db_path else ":memory:"
                self._client = QdrantClient(path=storage_path if storage_path != ":memory:" else None)
                
                # Create collection if not exists
                collections = self._client.get_collections().collections
                collection_names = [c.name for c in collections]
                
                if self.collection_name not in collection_names:
                    from qdrant_client.http.models import Distance, VectorParams
                    self._client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=VECTOR_DIM,
                            distance=Distance.Cosine
                        )
                    )
                    logger.info(f"Created Qdrant collection '{self.collection_name}'")
                
                self._initialized = True
                logger.info(f"Qdrant vector store initialized at {storage_path}")
                
            except ImportError:
                logger.warning("qdrant-client not installed. Falling back to LanceDB.")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant: {e}")
                raise
        
        return self._client
    
    def upsert(self, chunk_id: str, embedding: List[float], payload: Dict[str, Any]):
        """Insert or update a vector with metadata."""
        from qdrant_client.http.models import PointStruct
        
        client = self._get_client()
        client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )
    
    def upsert_batch(self, items: List[Tuple[str, List[float], Dict[str, Any]]]):
        """Batch insert/update vectors for efficiency."""
        from qdrant_client.http.models import PointStruct
        
        client = self._get_client()
        points = [
            PointStruct(id=chunk_id, vector=embedding, payload=payload)
            for chunk_id, embedding, payload in items
        ]
        
        if points:
            client.upsert(
                collection_name=self.collection_name,
                points=points
            )
    
    def search(self, query_vector: List[float], limit: int = 10, min_score: float = 0.0) -> List[VectorMatch]:
        """Find nearest neighbors by cosine similarity."""
        client = self._get_client()
        
        results = client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=min_score
        )
        
        return [
            VectorMatch(
                chunk_id=str(hit.id),
                score=hit.score,
                payload=hit.payload or {}
            )
            for hit in results
        ]
    
    def delete(self, chunk_id: str):
        """Remove a vector by ID."""
        client = self._get_client()
        client.delete(
            collection_name=self.collection_name,
            points_selector=[chunk_id]
        )
    
    def count(self) -> int:
        """Return total number of vectors."""
        client = self._get_client()
        info = client.get_collection(self.collection_name)
        return info.points_count if info else 0


class LanceDBVectorStore(VectorStore):
    """LanceDB-based vector store as lightweight fallback.
    
    LanceDB advantages:
    - Pure Python, easy installation
    - Embedded (no server)
    - Good for smaller datasets (<100K vectors)
    """
    
    def __init__(self, table_name: str = "apex_chunks", db_path: Optional[Path] = None):
        self.table_name = table_name
        self.db_path = db_path or Path(":memory:")
        self._db = None
        self._table = None
    
    def _get_table(self):
        """Lazy initialization of LanceDB table."""
        if self._table is None:
            try:
                import lancedb
                import pyarrow as pa
                
                # Connect to database
                db_uri = str(self.db_path) if str(self.db_path) != ":memory:" else ":memory:"
                self._db = lancedb.connect(db_uri)
                
                # Define schema
                schema = pa.schema([
                    ("chunk_id", pa.string()),
                    ("vector", pa.list_(pa.float32(), VECTOR_DIM)),
                    ("event_id", pa.string()),
                    ("source_type", pa.string()),
                    ("source_ref", pa.string()),
                    ("content", pa.string()),
                    ("timestamp", pa.string()),
                ])
                
                # Create table if not exists
                if self.table_name not in self._db.table_names():
                    self._table = self._db.create_table(self.table_name, schema=schema)
                    logger.info(f"Created LanceDB table '{self.table_name}'")
                else:
                    self._table = self._db.open_table(self.table_name)
                
                logger.info(f"LanceDB vector store initialized at {db_uri}")
                
            except ImportError as e:
                logger.warning(f"lancedb not installed: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize LanceDB: {e}")
                raise
        
        return self._table
    
    def upsert(self, chunk_id: str, embedding: List[float], payload: Dict[str, Any]):
        """Insert or update a vector (LanceDB uses merge_insert for upsert)."""
        import pyarrow as pa
        
        table = self._get_table()
        
        data = {
            "chunk_id": [chunk_id],
            "vector": [embedding],
            "event_id": [payload.get("event_id", "")],
            "source_type": [payload.get("source_type", "")],
            "source_ref": [payload.get("source_ref", "")],
            "content": [payload.get("content", "")],
            "timestamp": [payload.get("timestamp", "")],
        }
        
        table.add(pa.table(data), mode="overwrite")
    
    def search(self, query_vector: List[float], limit: int = 10, min_score: float = 0.0) -> List[VectorMatch]:
        """Find nearest neighbors by cosine similarity."""
        table = self._get_table()
        
        results = table.search(query_vector, vector_column_name="vector").limit(limit).to_pandas()
        
        matches = []
        for _, row in results.iterrows():
            score = 1.0 - row.get("_distance", 0.0)  # LanceDB returns distance, convert to similarity
            if score >= min_score:
                matches.append(VectorMatch(
                    chunk_id=row["chunk_id"],
                    score=score,
                    payload={
                        "event_id": row.get("event_id", ""),
                        "source_type": row.get("source_type", ""),
                        "source_ref": row.get("source_ref", ""),
                        "content": row.get("content", ""),
                        "timestamp": row.get("timestamp", ""),
                    }
                ))
        
        return matches
    
    def delete(self, chunk_id: str):
        """Remove vectors by ID (LanceDB uses delete with filter)."""
        table = self._get_table()
        table.delete(f'chunk_id = "{chunk_id}"')
    
    def count(self) -> int:
        """Return total number of vectors."""
        table = self._get_table()
        return len(table.to_pandas())


class InMemoryVectorStore(VectorStore):
    """Fallback in-memory vector store using numpy.
    
    Used when neither Qdrant nor LanceDB are available.
    Maintains backward compatibility with existing cosine similarity approach.
    """
    
    def __init__(self):
        self._vectors: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
    
    def upsert(self, chunk_id: str, embedding: List[float], payload: Dict[str, Any]):
        self._vectors[chunk_id] = (embedding, payload)
    
    def search(self, query_vector: List[float], limit: int = 10, min_score: float = 0.0) -> List[VectorMatch]:
        """Brute-force cosine similarity search."""
        import numpy as np
        
        scores = []
        query_arr = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query_arr)
        
        if query_norm == 0:
            return []
        
        for chunk_id, (embedding, payload) in self._vectors.items():
            emb_arr = np.array(embedding, dtype=np.float32)
            emb_norm = np.linalg.norm(emb_arr)
            
            if emb_norm == 0:
                continue
            
            similarity = float(np.dot(query_arr, emb_arr) / (query_norm * emb_norm))
            
            if similarity >= min_score:
                scores.append(VectorMatch(chunk_id=chunk_id, score=similarity, payload=payload))
        
        # Sort by score descending
        scores.sort(key=lambda m: m.score, reverse=True)
        return scores[:limit]
    
    def delete(self, chunk_id: str):
        self._vectors.pop(chunk_id, None)
    
    def count(self) -> int:
        return len(self._vectors)


def create_vector_store(
    backend: str = "auto",
    db_path: Optional[Path] = None,
    collection_name: str = "apex_chunks"
) -> VectorStore:
    """Factory function to create appropriate vector store.
    
    Args:
        backend: "qdrant", "lancedb", "memory", or "auto" (try qdrant, fallback to lancedb, then memory)
        db_path: Path for persistent storage (None for in-memory)
        collection_name: Collection/table name
    
    Returns:
        VectorStore instance
    """
    if backend == "auto":
        # Try Qdrant first (best performance)
        try:
            return QdrantVectorStore(collection_name=collection_name, db_path=db_path)
        except ImportError:
            pass
        
        # Try LanceDB next (lighter weight)
        try:
            return LanceDBVectorStore(table_name=collection_name, db_path=db_path)
        except ImportError:
            pass
        
        # Fallback to in-memory
        logger.info("Using in-memory vector store (install qdrant-client or lancedb for persistence)")
        return InMemoryVectorStore()
    
    elif backend == "qdrant":
        return QdrantVectorStore(collection_name=collection_name, db_path=db_path)
    
    elif backend == "lancedb":
        return LanceDBVectorStore(table_name=collection_name, db_path=db_path)
    
    elif backend == "memory":
        return InMemoryVectorStore()
    
    else:
        raise ValueError(f"Unknown vector store backend: {backend}")
