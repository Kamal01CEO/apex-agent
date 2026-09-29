"""Hybrid Search Engine combining FTS5 BM25 and Vector ANN Search."""

import logging
from typing import Dict, List, Optional
from apex_agent.memory.embedder import Embedder
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.vector_store import LanceDBVectorStore
from apex_agent.models import Chunk, ConfidenceLevel, SearchResult, SourceType
from apex_agent.config import DATA_DIR, DB_PATH
from pathlib import Path

logger = logging.getLogger("apex_agent.search")


class HybridSearchEngine:
    """Executes 70% vector ANN + 30% BM25 hybrid ranking over multi-modal chunks."""

    def __init__(self, index: Optional[SQLiteMemoryIndex] = None, use_ann: bool = True):
        self.index = index or SQLiteMemoryIndex()
        self.use_ann = use_ann
        self._vector_store = None
        
        if self.use_ann:
            try:
                vector_db_path = DATA_DIR / "vectors"
                self._vector_store = LanceDBVectorStore(db_path=vector_db_path)
                logger.info("Initialized LanceDB vector store at %s", vector_db_path)
            except Exception as e:
                logger.warning("Failed to initialize vector store, using fallback: %s", e)
                self._vector_store = None

    def ensure_vectors_indexed(self):
        """Sync existing chunks to vector store if not already indexed."""
        if not self._vector_store:
            return
        
        # Check if already indexed
        if self._vector_store.count() > 0:
            logger.debug("Vector store already has %d vectors", self._vector_store.count())
            return
        
        logger.info("Indexing existing chunks to vector store...")
        chunks = self.index.get_all_chunks(limit=10000)
        
        if not chunks:
            return
        
        # Batch embed and add
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Prepare data for vector store
            vec_chunks = []
            for c in batch:
                if c.embedding:
                    vec_chunks.append({
                        "id": c.id,
                        "content": c.content,
                        "source_ref": c.source_ref,
                        "source_type": c.source_type.value,
                        "timestamp": c.timestamp.isoformat() if c.timestamp else "",
                        "embedding": c.embedding,
                    })
            
            if vec_chunks:
                success = self._vector_store.add_chunks(vec_chunks)
                if success:
                    logger.debug("Indexed batch of %d chunks", len(vec_chunks))
        
        logger.info("Finished indexing %d chunks to vector store", len(chunks))

    def search(
        self,
        query: str,
        limit: int = 8,
        vector_weight: float = 0.70,
        bm25_weight: float = 0.30,
        source_type_filter: Optional[List[SourceType]] = None,
    ) -> List[SearchResult]:
        if not query.strip():
            return []

        # Ensure vectors are indexed
        if self._vector_store and self._vector_store.count() == 0:
            self.ensure_vectors_indexed()

        # 1. BM25 keyword search
        bm25_chunks = self.index.search_keyword(query, limit=limit * 3)
        bm25_map: Dict[str, float] = {}
        total_bm25 = len(bm25_chunks)
        for rank, chunk in enumerate(bm25_chunks):
            score = 1.0 - (rank / max(1, total_bm25))
            bm25_map[chunk.id] = max(0.1, score)

        # 2. Vector search (ANN via LanceDB or fallback)
        query_vec = Embedder.embed_text_cached(query)
        
        vector_map: Dict[str, float] = {}
        chunk_pool: Dict[str, Chunk] = {}
        
        for c in bm25_chunks:
            chunk_pool[c.id] = c

        if self._vector_store and self.use_ann:
            # Fast ANN search
            try:
                ann_results = self._vector_store.search(
                    query_embedding=list(query_vec),
                    limit=limit * 2
                )
                
                # Get full chunk objects for ANN results
                for idx, match in enumerate(ann_results):
                    chunk_id = match.get("id")
                    if chunk_id:
                        # Fetch chunk from SQLite
                        chunks = self.index.search_keyword(chunk_id, limit=1)
                        if chunks:
                            chunk_pool[chunk_id] = chunks[0]
                        # Distance to similarity ( LanceDB returns distance, convert)
                        distance = match.get("distance", 0.0)
                        similarity = max(0.0, 1.0 - (distance / 2.0))  # Normalize
                        vector_map[chunk_id] = similarity
            except Exception as e:
                logger.warning("ANN search failed, falling back to brute-force: %s", e)
                self._vector_store = None
        
        # Fallback: brute-force vector search
        if not self._vector_store or not vector_map:
            all_chunks = self.index.get_all_chunks(limit=300)
            for c in all_chunks:
                if c.embedding:
                    sim = Embedder.cosine_similarity(query_vec, c.embedding)
                    vector_map[c.id] = sim
                    chunk_pool[c.id] = c

        # 3. Combine scores
        combined_results: List[SearchResult] = []

        for cid, chunk in chunk_pool.items():
            if source_type_filter and chunk.source_type not in source_type_filter:
                continue

            v_score = vector_map.get(cid, 0.0)
            b_score = bm25_map.get(cid, 0.0)

            final_score = (vector_weight * v_score) + (bm25_weight * b_score)

            # Determine confidence level
            if b_score > 0.6 or (v_score > 0.85 and b_score > 0.2):
                conf = ConfidenceLevel.EXACT_MATCH
            elif v_score > 0.75 or (v_score > 0.65 and b_score > 0.3):
                conf = ConfidenceLevel.SEMANTIC_MATCH
            elif v_score > 0.50 or b_score > 0.2:
                conf = ConfidenceLevel.WEAK_MATCH
            else:
                conf = ConfidenceLevel.NO_MATCH

            combined_results.append(
                SearchResult(
                    chunk=chunk,
                    relevance_score=final_score,
                    confidence=conf,
                    bm25_score=b_score,
                    vector_score=v_score,
                )
            )

        combined_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return combined_results[:limit]

    def search_keywords_only(self, query: str, limit: int = 10) -> List[SearchResult]:
        """BM25-only search for exact keyword matching."""
        bm25_chunks = self.index.search_keyword(query, limit=limit)
        
        results = []
        for rank, chunk in enumerate(bm25_chunks):
            results.append(SearchResult(
                chunk=chunk,
                relevance_score=1.0 - (rank / max(1, len(bm25_chunks))),
                confidence=ConfidenceLevel.EXACT_MATCH,
                bm25_score=1.0,
                vector_score=0.0,
            ))
        
        return results

    def search_semantic_only(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Pure semantic search using vector similarity only."""
        if not self._vector_store:
            logger.warning("Vector store not available for semantic-only search")
            return []
        
        query_vec = Embedder.embed_text_cached(query)
        ann_results = self._vector_store.search(
            query_embedding=list(query_vec),
            limit=limit
        )
        
        results = []
        for match in ann_results:
            chunk_id = match.get("id")
            chunks = self.index.search_keyword(chunk_id, limit=1)
            if chunks:
                distance = match.get("distance", 0.0)
                similarity = max(0.0, 1.0 - (distance / 2.0))
                
                results.append(SearchResult(
                    chunk=chunks[0],
                    relevance_score=similarity,
                    confidence=ConfidenceLevel.SEMANTIC_MATCH if similarity > 0.5 else ConfidenceLevel.WEAK_MATCH,
                    bm25_score=0.0,
                    vector_score=similarity,
                ))
        
        return results
