import pytest
from pathlib import Path
from apex_agent.memory.pipeline import IngestionPipeline
from apex_agent.memory.search import HybridSearchEngine
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.vector_store import create_vector_store, InMemoryVectorStore
from apex_agent.memory.embedder import Embedder, BGE_SMALL_EN, EMBEDDING_DIM

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_embedder_uses_bge_model():
    """Verify embedder uses BGE-small-en-v1.5 by default."""
    # Test embedding dimension
    assert Embedder.get_embedding_dimension() == 384
    
    # Test that model name is BGE
    assert BGE_SMALL_EN == "BAAI/bge-small-en-v1.5"


def test_vector_store_backends():
    """Test vector store creation with different backends."""
    # In-memory store always works
    store = create_vector_store(backend="memory")
    assert isinstance(store, InMemoryVectorStore)
    
    # Test upsert and search
    test_embedding = [0.1] * 384
    store.upsert("test_id", test_embedding, {"content": "test content"})
    
    results = store.search(test_embedding, limit=5)
    assert len(results) == 1
    assert results[0].chunk_id == "test_id"
    
    # Test count
    assert store.count() == 1
    
    # Test delete
    store.delete("test_id")
    assert store.count() == 0


def test_ingestion_and_hybrid_search(tmp_path):
    """Test multi-modal ingestion and hybrid search with ANN."""
    # Use isolated test database
    db_path = tmp_path / "test_index.db"
    vector_path = tmp_path / "vectors"
    vector_path.mkdir(parents=True, exist_ok=True)
    
    index = SQLiteMemoryIndex(db_path=db_path)
    vector_store = create_vector_store(backend="memory")
    
    pipeline = IngestionPipeline(index=index)
    search_engine = HybridSearchEngine(
        index=index,
        vector_store=vector_store
    )
    
    # 1. Ingest WhatsApp
    wa_events = pipeline.ingest_file(FIXTURES_DIR / "sample_whatsapp.txt")
    assert len(wa_events) > 0
    assert wa_events[0].source_type.value == "whatsapp"

    # 2. Ingest Markdown Notes
    note_events = pipeline.ingest_file(FIXTURES_DIR / "sample_notes.md")
    assert len(note_events) > 0
    assert note_events[0].source_type.value == "note"

    # 3. Ingest Email
    email_events = pipeline.ingest_file(FIXTURES_DIR / "sample_email.eml")
    assert len(email_events) > 0
    assert email_events[0].source_type.value == "email"
    
    # 4. Sync and verify vector store
    # Note: search_engine._sync_chunks_to_vector_store() is called during init
    # But since we passed a fresh vector_store, let's re-sync
    
    # Search across multiple sources
    results = search_engine.search("valuation seed Sequoia")
    assert len(results) > 0
    top = results[0]
    assert "Sequoia" in top.chunk.content or "valuation" in top.chunk.content
    assert "whatsapp" in top.chunk.source_ref.lower()
    assert top.relevance_score > 0.3
    assert top.vector_score > 0.0  # Should have vector component

    # Search email payment terms
    results_terms = search_engine.search("payment terms Net 30")
    assert len(results_terms) > 0
    assert any("Net 30" in r.chunk.content for r in results_terms)

    # Verify hybrid search combines both signals
    stats = search_engine.get_stats()
    assert stats["vector_store_type"] == "InMemoryVectorStore"
    
    print("\n[SUCCESS] All multi-modal ingestion and search tests passed with ANN integration!")


def test_vector_only_search(tmp_path):
    """Test pure vector search capability."""
    db_path = tmp_path / "test_index.db"
    index = SQLiteMemoryIndex(db_path=db_path)
    vector_store = create_vector_store(backend="memory")
    
    pipeline = IngestionPipeline(index=index)
    search_engine = HybridSearchEngine(
        index=index,
        vector_store=vector_store
    )
    
    # Ingest test data
    pipeline.ingest_file(FIXTURES_DIR / "sample_notes.md")
    
    # Test vector-only search
    results = search_engine.vector_only_search("project timeline", limit=5)
    
    # Results should be sorted by vector similarity
    for r in results:
        assert r.bm25_score == 0.0  # Pure vector search
        assert r.vector_score >= 0.0


def test_chunk_retrieval_by_id(tmp_path):
    """Test efficient chunk ID-based retrieval."""
    db_path = tmp_path / "test_index.db"
    index = SQLiteMemoryIndex(db_path=db_path)
    
    from apex_agent.models import Chunk, SourceType
    from datetime import datetime
    
    # Insert test chunks
    test_chunks = [
        Chunk(
            id=f"test_chunk_{i}",
            event_id=f"event_{i}",
            chunk_index=i,
            content=f"Test content number {i}",
            source_type=SourceType.NOTE,
            source_ref="test_ref",
            timestamp=datetime.now(),
            embedding=[0.1] * 384,
        )
        for i in range(5)
    ]
    
    for chunk in test_chunks:
        index.add_chunk(chunk)
    
    # Test get_chunks_by_ids
    fetched = index.get_chunks_by_ids(["test_chunk_0", "test_chunk_2", "test_chunk_4"])
    assert len(fetched) == 3
    assert {c.id for c in fetched} == {"test_chunk_0", "test_chunk_2", "test_chunk_4"}
    
    # Test get_chunk_by_id
    single = index.get_chunk_by_id("test_chunk_1")
    assert single is not None
    assert single.id == "test_chunk_1"
    
    # Test non-existent ID
    none = index.get_chunk_by_id("nonexistent")
    assert none is None


def test_backward_compatibility(tmp_path):
    """Ensure backward compatibility with existing chunk format."""
    from apex_agent.models import Chunk, SourceType
    from datetime import datetime
    import json
    
    db_path = tmp_path / "test_index.db"
    index = SQLiteMemoryIndex(db_path=db_path)
    
    # Create chunk with old-style embedding (from all-MiniLM-L6-v2)
    old_embedding = [0.1] * 384  # 384-dim, same as BGE
    chunk = Chunk(
        id="legacy_chunk",
        event_id="legacy_event",
        chunk_index=0,
        content="Legacy content",
        source_type=SourceType.NOTE,
        source_ref="legacy_ref",
        timestamp=datetime.now(),
        embedding=old_embedding,
        metadata={"legacy": True}
    )
    
    index.add_chunk(chunk)
    
    # Verify retrieval
    fetched = index.get_chunk_by_id("legacy_chunk")
    assert fetched is not None
    assert fetched.embedding == old_embedding
    assert fetched.metadata.get("legacy") is True
    
    # Verify search works
    vector_store = create_vector_store(backend="memory")
    search = HybridSearchEngine(index=index, vector_store=vector_store)
    
    results = search.search("Legacy content")
    assert len(results) > 0


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        test_ingestion_and_hybrid_search(Path(td))
