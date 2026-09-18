"""PDF Document Ingester using pdfplumber."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Union
import pdfplumber
from apex_agent.ingest.base import BaseIngester
from apex_agent.models import ContentType, MemoryEvent, SourceType


class PDFIngester(BaseIngester):
    """Ingests PDF documents preserving page-level provenance."""

    def can_ingest(self, file_path: Union[str, Path]) -> bool:
        return Path(file_path).suffix.lower() == ".pdf"

    def ingest(self, file_path: Union[str, Path]) -> List[MemoryEvent]:
        p = Path(file_path)
        events: List[MemoryEvent] = []
        file_mtime = datetime.fromtimestamp(p.stat().st_mtime)

        with pdfplumber.open(p) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                clean_text = text.strip()
                if not clean_text:
                    continue

                event_id = f"pdf_{uuid.uuid4().hex[:10]}"
                source_ref = f"pdf:{p.name}:page_{idx}"
                events.append(
                    MemoryEvent(
                        id=event_id,
                        source_type=SourceType.PDF,
                        source_ref=source_ref,
                        timestamp=file_mtime,
                        content_text=clean_text,
                        title=f"{p.name} - Page {idx}",
                        content_type=ContentType.PDF,
                        metadata={"filename": p.name, "page": idx, "total_pages": len(pdf.pages)},
                    )
                )
        return events
