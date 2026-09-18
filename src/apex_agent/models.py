"""Core data models for Apex Agent."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PDF = "pdf"
    NOTE = "note"
    CALENDAR = "calendar"
    SCREENSHOT = "screenshot"


class ContentType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    IMAGE = "image"
    PDF = "pdf"


class ConfidenceLevel(str, Enum):
    EXACT_MATCH = "exact"       # Direct keyword match in FTS5
    SEMANTIC_MATCH = "semantic" # Strong vector similarity (>0.80)
    WEAK_MATCH = "weak"         # Moderate vector similarity (0.60-0.80)
    NO_MATCH = "none"           # Below threshold or ungrounded


@dataclass
class MemoryEvent:
    """Universal normalized container for any ingested piece of data."""
    id: str
    source_type: SourceType
    source_ref: str                       # e.g., "whatsapp:Rahul:2026-09-15" or "pdf:contract.pdf:p2"
    timestamp: datetime
    content_text: str
    sender: Optional[str] = None
    recipient: Optional[str] = None
    title: Optional[str] = None
    content_type: ContentType = ContentType.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)
    thread_id: Optional[str] = None


@dataclass
class Chunk:
    """A granular retrieval unit indexed in SQLite."""
    id: str
    event_id: str
    chunk_index: int
    content: str
    source_type: SourceType
    source_ref: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Result of hybrid keyword + semantic search with provenance."""
    chunk: Chunk
    relevance_score: float
    confidence: ConfidenceLevel
    bm25_score: float = 0.0
    vector_score: float = 0.0
    matched_entities: List[str] = field(default_factory=list)


@dataclass
class Entity:
    """Extracted person, organization, project, or event."""
    id: str
    name: str
    type: str                           # "person" | "org" | "topic" | "event" | "deal"
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    mention_count: int = 1


@dataclass
class Relationship:
    """Connection between two entities."""
    id: str
    entity_a: str
    entity_b: str
    relation_type: str                  # e.g. "works_at", "discussed", "scheduled_with"
    context: str                        # Sentence or snippet establishing the relationship
    source_ref: str
    timestamp: datetime
    confidence: float = 1.0


@dataclass
class Conflict:
    """Detected contradiction between distinct sources."""
    id: str
    topic: str
    claim_a: str
    source_a: str
    timestamp_a: datetime
    claim_b: str
    source_b: str
    timestamp_b: datetime
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_notes: Optional[str] = None
