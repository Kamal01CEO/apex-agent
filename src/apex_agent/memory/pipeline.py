"""Unified Ingestion Pipeline: Ingest -> Chunk -> Embed -> Index -> Entity Graph."""

import uuid
from pathlib import Path
from typing import List, Union
from apex_agent.ingest.email import EmailIngester
from apex_agent.ingest.notes import NoteIngester
from apex_agent.ingest.pdf import PDFIngester
from apex_agent.ingest.whatsapp import WhatsAppIngester
from apex_agent.intelligence.entities import EntityGraphEngine
from apex_agent.memory.chunker import TextChunker
from apex_agent.memory.embedder import Embedder
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.store import MarkdownMemoryStore
from apex_agent.models import Chunk, MemoryEvent


class IngestionPipeline:
    """Dispatches raw files to ingesters, generates embeddings, extracts entities, and saves to index."""

    def __init__(self, index: SQLiteMemoryIndex = None):
        self.index = index or SQLiteMemoryIndex()
        self.chunker = TextChunker(chunk_size=350, overlap=60)
        self.store = MarkdownMemoryStore()
        self.graph_engine = EntityGraphEngine()
        self.ingesters = [
            WhatsAppIngester(),
            PDFIngester(),
            EmailIngester(),
            NoteIngester(),
        ]

    def ingest_file(self, file_path: Union[str, Path]) -> List[MemoryEvent]:
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        # Find matching ingester
        matched_ingester = None
        for ing in self.ingesters:
            if ing.can_ingest(p):
                matched_ingester = ing
                break

        if not matched_ingester:
            matched_ingester = NoteIngester()

        events = matched_ingester.ingest(p)

        # Process each event into chunks & store in index + knowledge graph
        for event in events:
            text_chunks = self.chunker.chunk_text(event.content_text)
            for idx, text in enumerate(text_chunks):
                chunk_id = f"chk_{uuid.uuid4().hex[:12]}"
                emb = Embedder.embed_text(text)
                chunk = Chunk(
                    id=chunk_id,
                    event_id=event.id,
                    chunk_index=idx,
                    content=text,
                    source_type=event.source_type,
                    source_ref=event.source_ref,
                    timestamp=event.timestamp,
                    metadata=event.metadata,
                    embedding=emb,
                )
                self.index.add_chunk(chunk)

                # Extract entities & relationships for the knowledge graph
                try:
                    self.graph_engine.extract_and_store_from_chunk(chunk)
                except Exception:
                    pass

            # Log to daily memory file
            self.store.append_daily_log(
                f"Ingested `{event.source_type.value}` from `{p.name}` ({len(text_chunks)} chunks indexed: `{event.source_ref}`)"
            )

        return events
