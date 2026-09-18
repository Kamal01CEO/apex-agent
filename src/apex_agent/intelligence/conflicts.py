"""Conflict Detection Engine for Contradictory Information Across Sources."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from apex_agent.config import DB_PATH
from apex_agent.llm import llm
from apex_agent.models import Conflict, SearchResult


class ConflictDetector:
    """Identifies contradictory claims across multiple retrieved memory chunks."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def detect_conflicts(self, search_results: List[SearchResult]) -> List[Conflict]:
        """Examines chunks to detect if any contradict each other on facts, dates, prices, or terms."""
        if len(search_results) < 2:
            return []

        # Prepare numbered chunk digests
        snippets = []
        for idx, res in enumerate(search_results[:6]):
            snippets.append(
                f"[Chunk {idx+1}] (Source: {res.chunk.source_ref} | Time: {res.chunk.timestamp.isoformat()})\n"
                f"{res.chunk.content.strip()}"
            )

        prompt = f"""
Analyze the retrieved memory chunks below. Determine if there are ANY DIRECT FACTUAL CONTRADICTIONS
between different sources (e.g. differing dates, meeting times, payment terms, valuations, or deadlines).

Memory Chunks:
{chr(10).join(snippets)}

If there is a conflict, output STRICTLY valid JSON with no markdown wrapping:
{{
  "has_conflict": true,
  "topic": "Short conflict topic (e.g. Payment Terms for Acme Corp)",
  "claim_a": "What source A claims",
  "chunk_a_index": 1,
  "claim_b": "What source B claims",
  "chunk_b_index": 2,
  "explanation": "Why they contradict"
}}

If there are NO direct contradictions, output:
{{
  "has_conflict": false
}}
"""
        messages = [
            {"role": "system", "content": "You are a precise fact-checking detector. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]

        raw = llm.chat_completion(messages, temperature=0.1, max_tokens=600)
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(clean)
            if data.get("has_conflict"):
                idx_a = max(0, min(len(search_results) - 1, data.get("chunk_a_index", 1) - 1))
                idx_b = max(0, min(len(search_results) - 1, data.get("chunk_b_index", 2) - 1))

                res_a = search_results[idx_a]
                res_b = search_results[idx_b]

                conflict = Conflict(
                    id=f"cnf_{uuid.uuid4().hex[:8]}",
                    topic=data.get("topic", "Factual Discrepancy"),
                    claim_a=data.get("claim_a", res_a.chunk.content[:100]),
                    source_a=res_a.chunk.source_ref,
                    timestamp_a=res_a.chunk.timestamp,
                    claim_b=data.get("claim_b", res_b.chunk.content[:100]),
                    source_b=res_b.chunk.source_ref,
                    timestamp_b=res_b.chunk.timestamp,
                    detected_at=datetime.now(),
                    resolution_notes=data.get("explanation"),
                )

                # Persist to database
                self._persist_conflict(conflict)
                return [conflict]
        except Exception:
            pass

        return []

    def _persist_conflict(self, conflict: Conflict):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO conflicts
            (id, topic, claim_a, source_a, timestamp_a, claim_b, source_b, timestamp_b, detected_at, resolved, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conflict.id,
            conflict.topic,
            conflict.claim_a,
            conflict.source_a,
            conflict.timestamp_a.isoformat(),
            conflict.claim_b,
            conflict.source_b,
            conflict.timestamp_b.isoformat(),
            conflict.detected_at.isoformat(),
            1 if conflict.resolved else 0,
            conflict.resolution_notes
        ))
        conn.commit()
        conn.close()

    def get_unresolved_conflicts(self) -> List[dict]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conflicts WHERE resolved = 0 ORDER BY detected_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
