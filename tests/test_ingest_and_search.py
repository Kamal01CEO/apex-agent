import pytest
from pathlib import Path
from apex_agent.memory.pipeline import IngestionPipeline
from apex_agent.memory.search import HybridSearchEngine
from apex_agent.memory.index import SQLiteMemoryIndex

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_ingestion_and_hybrid_search(tmp_path):
    # Use isolated test database
    db_path = tmp_path / "test_index.db"
    index = SQLiteMemoryIndex(db_path=db_path)
    pipeline = IngestionPipeline(index=index)
    search_engine = HybridSearchEngine(index=index, use_ann=False)  # Use brute-force for testing

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

    # 4. Search across multiple sources
    results = search_engine.search("valuation seed Sequoia")
    assert len(results) > 0
    top = results[0]
    assert "Sequoia" in top.chunk.content or "valuation" in top.chunk.content
    assert "whatsapp" in top.chunk.source_ref.lower()
    assert top.relevance_score > 0.3

    # Search email payment terms
    results_terms = search_engine.search("payment terms Net 30")
    assert len(results_terms) > 0
    assert any("Net 30" in r.chunk.content for r in results_terms)

    print("\n[SUCCESS] All multi-modal ingestion and search tests passed with source provenance!")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        test_ingestion_and_hybrid_search(Path(td))
