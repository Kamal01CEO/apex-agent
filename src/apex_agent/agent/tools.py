"""Tool definitions for the Apex Memory Agent runtime."""

from typing import Any, Dict, List, Optional
from apex_agent.intelligence.conflicts import ConflictDetector
from apex_agent.intelligence.entities import EntityGraphEngine
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.pipeline import IngestionPipeline
from apex_agent.memory.search import HybridSearchEngine


class MemoryAgentTools:
    """Provides tools to search memory, traverse knowledge graphs, inspect conflicts, and ingest files."""

    def __init__(self, index: SQLiteMemoryIndex = None):
        self.index = index or SQLiteMemoryIndex()
        self.search_engine = HybridSearchEngine(index=self.index)
        self.graph_engine = EntityGraphEngine()
        self.conflict_detector = ConflictDetector()
        self.pipeline = IngestionPipeline(index=self.index)

    def memory_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches multi-modal memory for facts, conversations, and records."""
        results = self.search_engine.search(query, limit=limit)
        return [
            {
                "content": r.chunk.content,
                "source_ref": r.chunk.source_ref,
                "source_type": r.chunk.source_type.value,
                "timestamp": r.chunk.timestamp.isoformat(),
                "confidence": r.confidence.value,
                "relevance": round(r.relevance_score, 3)
            }
            for r in results
        ]

    def entity_lookup(self, entity_name: str) -> Dict[str, Any]:
        """Looks up an entity (person, company, project) and its relationship graph."""
        return self.graph_engine.get_entity_context(entity_name)

    def list_conflicts(self) -> List[Dict[str, Any]]:
        """Returns all unresolved discrepancies and conflicting information across sources."""
        return self.conflict_detector.get_unresolved_conflicts()

    def ingest_path(self, path: str) -> Dict[str, Any]:
        """Ingests a file or document into memory."""
        events = self.pipeline.ingest_file(path)
        return {
            "status": "success",
            "file": path,
            "events_count": len(events),
            "sources": [e.source_ref for e in events]
        }
