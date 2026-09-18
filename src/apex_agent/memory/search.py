"""Hybrid Search Engine combining FTS5 BM25 and Vector ANN search.

Combines approximate nearest neighbor (ANN) vector search via Qdrant/LanceDB
with SQLite FTS5 full-text search for optimal retrieval quality.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from apex_agent.config import DATA_DIR
from apex_agent.memory.embedder import Embedder
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.vector_store import VectorStore, create_vector_store, VectorMatch
from apex_agent.models import Chunk, ConfidenceLevel, SearchResult, SourceType

logger = logging.getLogger("apex_agent.search")


class HybridSearchEngine:
    """Executes hybrid search combining vector ANN + BM25 keyword ranking.
    
    Architecture:
    1. Vector Search (fast ANN via Qdrant/LanceDB) - 70% weight
    2. Keyword Search (BM25 via SQLite FTS5) - 30% weight
    3. Combined scoring with configurable weighting
    """
    
    def __init__(
        self,
        index: Optional[SQLiteMemoryIndex] = None,
        vector_store: Optional[VectorStore] = None,
        vector_backend: str = "auto",
        vector_db_path: Optional[Path] = None,
    ):
        """Initialize hybrid search engine.
        
        Args:
            index: SQLite memory index for BM25 and chunks
            vector_store: Pre-configured vector store (optional)
            vector_backend: "qdrant", "lancedb", "memory", or "auto"
            vector_db_path: Path for vector database storage
        """
        self.index = index or SQLiteMemoryIndex()
        
        # Initialize vector store
        if vector_store:
            self.vector_store = vector_store
        else:
            vector_path = vector_db_path or (DATA_DIR / "vectors")
            vector_path.mkdir(parents=True, exist_ok=True)
            self.vector_store = create_vector_store(
                backend=vector_backend,
                db_path=vector_path,
                collection_name="apex_chunks"
            )
        
        # Sync existing chunks to vector store on first init
        self._sync_chunks_to_vector_store()
    
    def _sync_chunks_to_vector_store(self):
        """Load existing chunks from SQLite into vector store."""
        try:
            chunks = self.index.get_all_chunks(limit=1000)
            
            if not chunks:
                logger.info("No existing chunks to sync to vector store")
                return
            
            # Check if vector store is empty
            if self.vector_store.count() > 0:
                logger.info(f"Vector store already has {self.vector_store.count()} vectors, skipping sync")
                return
            
            # Batch upsert chunks with embeddings
            items_to_upsert = []
            for chunk in chunks:
                if chunk.embedding:
                    items_to_upsert.append((
                        chunk.id,
                        chunk.embedding,
                        {
                            "event_id": chunk.event_id,
                            "source_type": chunk.source_type.value,
                            "source_ref": chunk.source_ref,
                            "content": chunk.content[:500],  # Store truncated content for display
                            "timestamp": chunk.timestamp.isoformat(),
                        }
                    ))
            
            if items_to_upsert:
                logger.info(f"Syncing {len(items_to_upsert)} chunks to vector store...")
                self.vector_store.upsert_batch(items_to_upsert)
                logger.info(f"Vector store now contains {self.vector_store.count()} vectors")
        
        except Exception as e:
            logger.warning(f"Failed to sync chunks to vector store: {e}")
    
    def index_chunk(self, chunk: Chunk):
        """Index a new chunk in the vector store.
        
        Call this after adding chunk to SQLite to keep vector store in sync.
        """
        if chunk.embedding:
            self.vector_store.upsert(
                chunk_id=chunk.id,
                embedding=chunk.embedding,
                payload={
                    "event_id": chunk.event_id,
                    "source_type": chunk.source_type.value,
                    "source_ref": chunk.source_ref,
                    "content": chunk.content[:500],
                    "timestamp": chunk.timestamp.isoformat(),
                }
            )
    
    def remove_chunk(self, chunk_id: str):
        """Remove a chunk from the vector store."""
        self.vector_store.delete(chunk_id)
    
    def search(
        self,
        query: str,
        limit: int = 8,
        vector_weight: float = 0.70,
        bm25_weight: float = 0.30,
        source_type_filter: Optional[List[SourceType]] = None,
        min_vector_score: float = 0.0,
    ) -> List[SearchResult]:
        """Execute hybrid search combining vector ANN and BM25.
        
        Args:
            query: Search query text
            limit: Maximum results to return
            vector_weight: Weight for vector similarity scores (default 0.70)
            bm25_weight: Weight for BM25 keyword scores (default 0.30)
            source_type_filter: Optional filter by source types
            min_vector_score: Minimum vector similarity score threshold
        
        Returns:
            List of SearchResult sorted by relevance
        """
        if not query.strip():
            return []
        
        # 1. Keyword search (BM25) via FTS5
        bm25_chunks = self.index.search_keyword(query, limit=limit * 3)
        bm25_scores: Dict[str, float] = {}
        
        # Normalize BM25 ranks to 0.1-1.0 range (rank 1 = 1.0, last rank = 0.1)
        total_bm25 = len(bm25_chunks)
        for rank, chunk in enumerate(bm25_chunks):
            score = 1.0 - (rank / max(1, total_bm25))
            bm25_scores[chunk.id] = max(0.1, score)
        
        # 2. Vector search (ANN) via Qdrant/LanceDB
        query_vector = Embedder.embed_text(query)
        vector_results = self.vector_store.search(
            query_vector=query_vector,
            limit=limit * 4,  # Get more candidates for re-ranking
            min_score=min_vector_score
        )
        
        # Build lookup from vector results
        vector_scores: Dict[str, float] = {}
        for match in vector_results:
            vector_scores[match.chunk_id] = match.score
        
        # 3. Gather all candidate chunk IDs
        candidate_ids: Set[str] = set(bm25_scores.keys()) | set(vector_scores.keys())
        
        # 4. Fetch full chunks for candidates
        chunk_pool: Dict[str, Chunk] = {}
        
        # First, use chunks from BM25 results
        for chunk in bm25_chunks:
            chunk_pool[chunk.id] = chunk
        
        # For vector matches not in BM25, fetch from DB using efficient ID lookup
        missing_ids = [cid for cid in vector_scores if cid not in chunk_pool]
        if missing_ids:
            fetched_chunks = self.index.get_chunks_by_ids(missing_ids)
            for chunk in fetched_chunks:
                chunk_pool[chunk.id] = chunk
        
        # 5. Combine scores with RRN-style fusion
        combined_results: List[SearchResult] = []
        
        for cid in candidate_ids:
            chunk = chunk_pool.get(cid)
            if not chunk:
                continue
            
            # Apply source type filter
            if source_type_filter and chunk.source_type not in source_type_filter:
                continue
            
            v_score = vector_scores.get(cid, 0.0)
            b_score = bm25_scores.get(cid, 0.0)
            
            # Combined weighted score
            final_score = (vector_weight * v_score) + (bm25_weight * b_score)
            
            # Determine confidence level based on both signals
            confidence = self._determine_confidence(v_score, b_score)
            
            combined_results.append(
                SearchResult(
                    chunk=chunk,
                    relevance_score=final_score,
                    confidence=confidence,
                    bm25_score=b_score,
                    vector_score=v_score,
                )
            )
        
        # 6. Sort by combined relevance score
        combined_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return combined_results[:limit]
    
    def _determine_confidence(self, vector_score: float, bm25_score: float) -> ConfidenceLevel:
        """Classify result confidence based on vector and BM25 scores."""
        # Strong BM25 match or strong vector + decent BM25
        if bm25_score > 0.6 or (vector_score > 0.85 and bm25_score > 0.2):
            return ConfidenceLevel.EXACT_MATCH
        
        # Good vector match or combined signals
        elif vector_score > 0.75 or (vector_score > 0.65 and bm25_score > 0.3):
            return ConfidenceLevel.SEMANTIC_MATCH
        
        # Moderate match on either signal
        elif vector_score > 0.50 or bm25_score > 0.2:
            return ConfidenceLevel.WEAK_MATCH
        
        # Low confidence match
        else:
            return ConfidenceLevel.NO_MATCH
    
    def vector_only_search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        source_type_filter: Optional[List[SourceType]] = None,
    ) -> List[SearchResult]:
        """Pure vector ANN search without BM25 component.
        
        Useful for semantic queries where keyword matching is less relevant.
        """
        if not query.strip():
            return []
        
        query_vector = Embedder.embed_text(query)
        matches = self.vector_store.search(query_vector, limit=limit * 2, min_score=min_score)
        
        # Fetch full chunks for matches using efficient ID lookup
        match_ids = [m.chunk_id for m in matches]
        chunks_map: Dict[str, Chunk] = {c.id: c for c in self.index.get_chunks_by_ids(match_ids)}
        
        results: List[SearchResult] = []
        for match in matches:
            chunk = chunks_map.get(match.chunk_id)
            
            if chunk:
                if source_type_filter and chunk.source_type not in source_type_filter:
                    continue
                
                confidence = self._determine_confidence(match.score, 0.0)
                
                results.append(SearchResult(
                    chunk=chunk,
                    relevance_score=match.score,
                    confidence=confidence,
                    vector_score=match.score,
                    bm25_score=0.0,
                ))
        
        return results[:limit]
    
    def get_stats(self) -> Dict:
        """Return statistics about the search engine."""
        return {
            "vector_store_type": type(self.vector_store).__name__,
            "vector_count": self.vector_store.count(),
            "sqlite_chunks": len(self.index.get_all_chunks(limit=10000)),
        }
