"""Markdown and Text Notes Ingester."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Union
from apex_agent.ingest.base import BaseIngester
from apex_agent.models import ContentType, MemoryEvent, SourceType


class NoteIngester(BaseIngester):
    """Ingests Markdown (.md) and text (.txt) personal notes."""

    def can_ingest(self, file_path: Union[str, Path]) -> bool:
        return Path(file_path).suffix.lower() in (".md", ".markdown", ".txt")

    def ingest(self, file_path: Union[str, Path]) -> List[MemoryEvent]:
        p = Path(file_path)
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()

        if not content:
            return []

        file_mtime = datetime.fromtimestamp(p.stat().st_mtime)
        event_id = f"note_{uuid.uuid4().hex[:10]}"
        source_ref = f"note:{p.name}:{file_mtime.strftime('%Y-%m-%d')}"

        return [
            MemoryEvent(
                id=event_id,
                source_type=SourceType.NOTE,
                source_ref=source_ref,
                timestamp=file_mtime,
                content_text=content,
                title=p.stem,
                content_type=ContentType.MARKDOWN if p.suffix.lower() in (".md", ".markdown") else ContentType.TEXT,
                metadata={"filename": p.name, "size_chars": len(content)},
            )
        ]
