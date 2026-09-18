"""Session and Message Persistence Engine (Hermes state.db architecture)."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from apex_agent.config import DB_PATH


class SessionDB:
    """Manages persistent chat sessions, message turns, tool calls, and FTS search."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        cur = conn.cursor()

        # Sessions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata_json TEXT
            );
        """)

        # Messages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls_json TEXT,
                tool_results_json TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
            );
        """)

        # FTS5 for session search
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chat_messages_fts USING fts5(
                content,
                session_id,
                role,
                content='chat_messages',
                content_rowid='rowid'
            );
        """)

        conn.commit()
        conn.close()

    def create_session(self, title: str = "New Session") -> str:
        session_id = f"sess_{uuid.uuid4().hex[:10]}"
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chat_sessions (id, title, created_at, updated_at, metadata_json)
            VALUES (?, ?, ?, ?, '{}')
        """, (session_id, title, now, now))
        conn.commit()
        conn.close()
        return session_id

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*, count(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cur = conn.cursor()

        tc_json = json.dumps(tool_calls) if tool_calls else None
        tr_json = json.dumps(tool_results) if tool_results else None

        cur.execute("""
            INSERT INTO chat_messages (id, session_id, role, content, tool_calls_json, tool_results_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, session_id, role, content, tc_json, tr_json, now))

        # Index in FTS5
        cur.execute("""
            INSERT INTO chat_messages_fts (rowid, content, session_id, role)
            SELECT rowid, content, session_id, role FROM chat_messages WHERE id = ?
        """, (msg_id,))

        # Update session timestamp
        cur.execute("""
            UPDATE chat_sessions SET updated_at = ? WHERE id = ?
        """, (now, session_id))

        conn.commit()
        conn.close()
        return msg_id

    def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, limit))
        rows = cur.fetchall()
        conn.close()

        msgs = []
        for r in rows:
            m = dict(r)
            m["tool_calls"] = json.loads(m["tool_calls_json"]) if m.get("tool_calls_json") else None
            m["tool_results"] = json.loads(m["tool_results_json"]) if m.get("tool_results_json") else None
            msgs.append(m)
        return msgs
