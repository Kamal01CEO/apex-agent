"""SQLite Hybrid Storage Engine with FTS5 and Vector persistence."""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional
from apex_agent.config import DB_PATH
from apex_agent.memory.embedder import Embedder
from apex_agent.models import Chunk, MemoryEvent, SourceType


class SQLiteMemoryIndex:
    """Manages raw chunks, FTS5 full-text index, entity tables, and conflicts."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cur = conn.cursor()

        # 1. Main Chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT,
                embedding_json TEXT
            );
        """)

        # 2. FTS5 Virtual Table for BM25 Keyword Search
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                source_ref,
                source_type,
                content='chunks',
                content_rowid='rowid'
            );
        """)

        # 3. Entities table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                aliases_json TEXT,
                attributes_json TEXT,
                first_seen TEXT,
                last_seen TEXT,
                mention_count INTEGER DEFAULT 1
            );
        """)

        # 4. Relationships table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                entity_a TEXT NOT NULL,
                entity_b TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                context TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                confidence REAL DEFAULT 1.0
            );
        """)

        # 5. Conflicts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conflicts (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                claim_a TEXT NOT NULL,
                source_a TEXT NOT NULL,
                timestamp_a TEXT NOT NULL,
                claim_b TEXT NOT NULL,
                source_b TEXT NOT NULL,
                timestamp_b TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolution_notes TEXT
            );
        """)

        conn.commit()
        conn.close()

    def add_chunk(self, chunk: Chunk):
        conn = self._get_connection()
        cur = conn.cursor()

        embedding_str = json.dumps(chunk.embedding) if chunk.embedding else None
        meta_str = json.dumps(chunk.metadata)

        cur.execute("""
            INSERT OR REPLACE INTO chunks
            (id, event_id, chunk_index, content, source_type, source_ref, timestamp, metadata_json, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk.id,
            chunk.event_id,
            chunk.chunk_index,
            chunk.content,
            chunk.source_type.value,
            chunk.source_ref,
            chunk.timestamp.isoformat(),
            meta_str,
            embedding_str,
        ))

        # Update FTS index
        cur.execute("""
            INSERT INTO chunks_fts (rowid, content, source_ref, source_type)
            SELECT rowid, content, source_ref, source_type FROM chunks WHERE id = ?
        """, (chunk.id,))

        conn.commit()
        conn.close()

    def search_keyword(self, query: str, limit: int = 20) -> List[Chunk]:
        """Performs FTS5 BM25 search."""
        conn = self._get_connection()
        cur = conn.cursor()

        # Sanitize query for FTS5 (remove special characters)
        sanitized = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
        if not sanitized:
            return []

        # Use FTS prefix match
        fts_query = " OR ".join([f"{term}*" for term in sanitized.split() if len(term) > 1])
        if not fts_query:
            fts_query = sanitized

        try:
            cur.execute("""
                SELECT c.id, c.event_id, c.chunk_index, c.content, c.source_type, c.source_ref,
                       c.timestamp, c.metadata_json, c.embedding_json, bm25(chunks_fts) as rank
                FROM chunks_fts f
                JOIN chunks c ON c.rowid = f.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))

            rows = cur.fetchall()
            results = []
            for r in rows:
                emb = json.loads(r["embedding_json"]) if r["embedding_json"] else None
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                results.append(
                    Chunk(
                        id=r["id"],
                        event_id=r["event_id"],
                        chunk_index=r["chunk_index"],
                        content=r["content"],
                        source_type=SourceType(r["source_type"]),
                        source_ref=r["source_ref"],
                        timestamp=datetime.fromisoformat(r["timestamp"]),
                        metadata=meta,
                        embedding=emb,
                    )
                )
            return results
        except Exception as e:
            return []
        finally:
            conn.close()

    def get_all_chunks(self, limit: int = 500) -> List[Chunk]:
        """Retrieves chunks for vector similarity ranking."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM chunks ORDER BY rowid DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        chunks = []
        for r in rows:
            emb = json.loads(r["embedding_json"]) if r["embedding_json"] else None
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            chunks.append(
                Chunk(
                    id=r["id"],
                    event_id=r["event_id"],
                    chunk_index=r["chunk_index"],
                    content=r["content"],
                    source_type=SourceType(r["source_type"]),
                    source_ref=r["source_ref"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    metadata=meta,
                    embedding=emb,
                )
            )
        conn.close()
        return chunks

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        """Retrieve specific chunks by their IDs."""
        if not chunk_ids:
            return []
        
        conn = self._get_connection()
        cur = conn.cursor()
        
        placeholders = ",".join("?" * len(chunk_ids))
        cur.execute(
            f"SELECT * FROM chunks WHERE id IN ({placeholders})",
            chunk_ids
        )
        rows = cur.fetchall()
        
        chunks = []
        for r in rows:
            emb = json.loads(r["embedding_json"]) if r["embedding_json"] else None
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            chunks.append(
                Chunk(
                    id=r["id"],
                    event_id=r["event_id"],
                    chunk_index=r["chunk_index"],
                    content=r["content"],
                    source_type=SourceType(r["source_type"]),
                    source_ref=r["source_ref"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    metadata=meta,
                    embedding=emb,
                )
            )
        conn.close()
        return chunks

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieve a single chunk by ID."""
        chunks = self.get_chunks_by_ids([chunk_id])
        return chunks[0] if chunks else None
