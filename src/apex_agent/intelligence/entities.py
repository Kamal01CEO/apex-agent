"""Entity Extraction and Relationship Graph Engine."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from apex_agent.config import DB_PATH
from apex_agent.llm import llm
from apex_agent.models import Chunk, Entity, Relationship


class EntityGraphEngine:
    """Extracts entities and relationships from chunks and builds an interconnected knowledge graph.
    
    NOTE: Entity extraction is disabled by default (runs on-demand only) as it's LLM-expensive.
    Enable with extract_on_chunk=True in pipeline.
    """

    def __init__(self, db_path=DB_PATH, auto_extract: bool = False):
        self.db_path = str(db_path)
        self.auto_extract = auto_extract  # Disabled by default to save LLM costs

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def extract_and_store_from_chunk(self, chunk: Chunk) -> Dict[str, List]:
        """Uses LLM to extract entities and connections from a chunk."""
        prompt = f"""
You are a precise entity extraction system for a personal memory assistant.
Extract all relevant entities and relationships from the text below.

Source Provenance: {chunk.source_ref} ({chunk.source_type.value})
Timestamp: {chunk.timestamp.isoformat()}
Text:
\"\"\"{chunk.content}\"\"\"

Output STRICTLY valid JSON with no markdown wrapping and no explanation:
{{
  "entities": [
    {{"name": "Entity Name", "type": "person|org|topic|event|deal", "attributes": {{"key": "value"}}}}
  ],
  "relationships": [
    {{"entity_a": "Entity Name A", "entity_b": "Entity Name B", "relation": "relationship_type", "context": "brief reason/quote"}}
  ]
}}
"""
        messages = [
            {"role": "system", "content": "You are a factual knowledge graph extractor. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]

        raw = llm.chat_completion(messages, temperature=0.1, max_tokens=800)

        # Parse JSON
        clean_json = raw.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        extracted_entities = []
        extracted_relationships = []

        try:
            data = json.loads(clean_json)
            extracted_entities = data.get("entities", [])
            extracted_relationships = data.get("relationships", [])
        except Exception:
            # Fallback heuristic rule extraction if LLM formatting fails
            pass

        # Persist into SQLite
        conn = self._get_connection()
        cur = conn.cursor()

        stored_entities = []
        for e in extracted_entities:
            name = e.get("name", "").strip()
            etype = e.get("type", "topic").strip().lower()
            attrs = json.dumps(e.get("attributes", {}))
            if not name:
                continue

            ent_id = f"ent_{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO entities (id, name, type, aliases_json, attributes_json, first_seen, last_seen, mention_count)
                VALUES (?, ?, ?, '[]', ?, ?, ?, 1)
                ON CONFLICT(name) DO UPDATE SET
                    last_seen=excluded.last_seen,
                    mention_count=mention_count + 1
            """, (ent_id, name, etype, attrs, chunk.timestamp.isoformat(), chunk.timestamp.isoformat()))
            stored_entities.append(name)

        stored_rel_ids = []
        for r in extracted_relationships:
            ea = r.get("entity_a", "").strip()
            eb = r.get("entity_b", "").strip()
            rel = r.get("relation", "connected_to").strip()
            ctx = r.get("context", chunk.content[:150]).strip()
            if not ea or not eb:
                continue

            rel_id = f"rel_{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO relationships (id, entity_a, entity_b, relation_type, context, source_ref, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (rel_id, ea, eb, rel, ctx, chunk.source_ref, chunk.timestamp.isoformat()))
            stored_rel_ids.append(rel_id)

        conn.commit()
        conn.close()

        return {"entities": stored_entities, "relationships": stored_rel_ids}

    def get_entity_context(self, entity_name: str) -> Dict[str, any]:
        """Traverses knowledge graph around an entity."""
        conn = self._get_connection()
        cur = conn.cursor()

        # Fetch entity info
        cur.execute("SELECT * FROM entities WHERE name LIKE ?", (f"%{entity_name}%",))
        entity_rows = cur.fetchall()

        # Fetch relationships
        cur.execute("""
            SELECT * FROM relationships
            WHERE entity_a LIKE ? OR entity_b LIKE ?
            ORDER BY timestamp DESC
        """, (f"%{entity_name}%", f"%{entity_name}%"))
        rel_rows = cur.fetchall()

        conn.close()

        entities = [dict(r) for r in entity_rows]
        relationships = [dict(r) for r in rel_rows]

        return {
            "query": entity_name,
            "entities": entities,
            "relationships": relationships
        }
