"""Vector store using LanceDB for fast ANN search with local persistence."""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("apex_agent.vector_store")

# Lazy imports to avoid startup cost
_lancedb = None
_table = None


def _get_lancedb():
    """Lazy load LanceDB."""
    global _lancedb
    if _lancedb is None:
        try:
            import lancedb
            _lancedb = lancedb
        except ImportError:
            logger.warning("LanceDB not installed. Run: pip install lancedb")
            _lancedb = False
    return _lancedb


class LanceDBVectorStore:
    """Fast vector similarity search using LanceDB (local, no server needed)."""

    def __init__(self, db_path: Path, table_name: str = "memory_chunks"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.table_name = table_name
        self._db = None
        self._table = None

    def _connect(self):
        """Connect to LanceDB database."""
        if self._db is None:
            lancedb = _get_lancedb()
            if lancedb:
                try:
                    self._db = lancedb.connect(str(self.db_path))
                    # Open or create table
                    try:
                        self._table = self._db.open_table(self.table_name)
                    except Exception:
                        # Table doesn't exist yet
                        self._table = None
                except Exception as e:
                    logger.error("Failed to connect to LanceDB: %s", e)
                    self._db = False
        return self._db is not None and self._db is not False

    def create_table(self, sample_embedding: List[float]):
        """Create the vector table with proper schema."""
        lancedb = _get_lancedb()
        if not lancedb or not self._db:
            return False
        
        try:
            import pyarrow as pa
            
            # Define schema
            dim = len(sample_embedding)
            schema = pa.schema([
                ("id", pa.string()),
                ("content", pa.string()),
                ("source_ref", pa.string()),
                ("source_type", pa.string()),
                ("timestamp", pa.string()),
                ("embedding", pa.list_(pa.float32(), list_size=dim)),
            ])
            
            # Create empty table
            self._db.create_table(self.table_name, schema=schema, mode="overwrite")
            self._table = self._db.open_table(self.table_name)
            logger.info("Created LanceDB table '%s' with %d-dim vectors", self.table_name, dim)
            return True
        except Exception as e:
            logger.error("Failed to create LanceDB table: %s", e)
            return False

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Add chunks with embeddings to the vector store."""
        if not chunks:
            return True
        
        if not self._connect():
            return False
        
        if self._table is None and chunks:
            # Create table with first chunk's embedding dimension
            sample_emb = chunks[0].get("embedding", [])
            if sample_emb:
                self.create_table(sample_emb)
        
        if self._table is None:
            return False
        
        try:
            import pyarrow as pa
            
            # Prepare data
            data = {
                "id": [c.get("id", "") for c in chunks],
                "content": [c.get("content", "")[:2000] for c in chunks],  # Limit content length
                "source_ref": [c.get("source_ref", "") for c in chunks],
                "source_type": [c.get("source_type", "") for c in chunks],
                "timestamp": [c.get("timestamp", "") for c in chunks],
                "embedding": [c.get("embedding", []) for c in chunks],
            }
            
            table = pa.table(data)
            self._table.add(table)
            return True
        except Exception as e:
            logger.error("Failed to add chunks to LanceDB: %s", e)
            return False

    def search(self, query_embedding: List[float], limit: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        """Search for similar vectors using ANN."""
        if not self._connect() or self._table is None:
            return []
        
        try:
            # Build query
            query = self._table.search(query_embedding).limit(limit)
            
            # Apply filters if provided
            if filters:
                # LanceDB supports SQL-like where clauses
                where_clauses = []
                if "source_type" in filters:
                    where_clauses.append(f"source_type = '{filters['source_type']}'")
                if where_clauses:
                    query = query.where(" AND ".join(where_clauses))
            
            results = query.to_pandas()
            
            # Convert to list of dicts
            matches = []
            for _, row in results.iterrows():
                matches.append({
                    "id": row.get("id", ""),
                    "content": row.get("content", ""),
                    "source_ref": row.get("source_ref", ""),
                    "source_type": row.get("source_type", ""),
                    "timestamp": row.get("timestamp", ""),
                    "distance": row.get("_distance", 0.0),
                })
            
            return matches
        except Exception as e:
            logger.error("LanceDB search failed: %s", e)
            return []

    def delete_by_ids(self, chunk_ids: List[str]) -> bool:
        """Delete chunks by IDs."""
        if not self._connect() or self._table is None:
            return False
        
        try:
            self._table.delete(f"id IN {chunk_ids}")
            return True
        except Exception as e:
            logger.error("Failed to delete from LanceDB: %s", e)
            return False

    def clear(self) -> bool:
        """Clear all vectors from the table."""
        if not self._connect() or self._table is None:
            return False
        
        try:
            self._table.delete("true")
            return True
        except Exception as e:
            logger.error("Failed to clear LanceDB: %s", e)
            return False

    def count(self) -> int:
        """Return total number of vectors."""
        if not self._connect() or self._table is None:
            return 0
        
        try:
            return len(self._table.to_pandas())
        except Exception:
            return 0
