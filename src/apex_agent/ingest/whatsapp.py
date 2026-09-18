"""WhatsApp Chat Export Ingester.
Parses standard iOS and Android exported chat transcripts (.txt).
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Union
from apex_agent.ingest.base import BaseIngester
from apex_agent.models import ContentType, MemoryEvent, SourceType


class WhatsAppIngester(BaseIngester):
    """Parses WhatsApp chat transcripts into conversation-grouped MemoryEvents."""

    # Matches formats:
    # [15/09/26, 14:30:15] Rahul: Hello
    # 15/09/2026, 2:30 pm - Rahul: Hello
    # 9/15/26, 2:30 PM - Rahul: Hello
    PATTERN_1 = re.compile(r"^\[?(\d{1,2}[\/\.]\d{1,2}[\/\.]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[apAP][mM])?)\]?\s*[-:]?\s*([^:]+):\s*(.*)$")

    def can_ingest(self, file_path: Union[str, Path]) -> bool:
        p = Path(file_path)
        if p.suffix.lower() != ".txt":
            return False
        # Sample first 5 lines to confirm WhatsApp format
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for _ in range(10):
                    line = f.readline()
                    if self.PATTERN_1.match(line.strip()):
                        return True
        except Exception:
            return False
        return False

    def ingest(self, file_path: Union[str, Path]) -> List[MemoryEvent]:
        p = Path(file_path)
        events: List[MemoryEvent] = []
        filename = p.name

        current_sender = None
        current_date_str = None
        current_time_str = None
        current_text_lines = []

        def flush_message():
            if current_sender and current_text_lines:
                text = "\n".join(current_text_lines).strip()
                # Omit media omitted messages
                if text and "<Media omitted>" not in text:
                    # Attempt parse date
                    ts = datetime.now()
                    try:
                        clean_dt = f"{current_date_str} {current_time_str}".replace("[", "").replace("]", "")
                        for fmt in ("%d/%m/%y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%y %I:%M %p", "%m/%d/%y %I:%M %p", "%d/%m/%Y %I:%M %p"):
                            try:
                                ts = datetime.strptime(clean_dt, fmt)
                                break
                            except ValueError:
                                pass
                    except Exception:
                        ts = datetime.now()

                    event_id = f"wa_{uuid.uuid4().hex[:10]}"
                    source_ref = f"whatsapp:{filename}:{current_sender}:{ts.strftime('%Y-%m-%d')}"
                    events.append(
                        MemoryEvent(
                            id=event_id,
                            source_type=SourceType.WHATSAPP,
                            source_ref=source_ref,
                            timestamp=ts,
                            content_text=f"{current_sender}: {text}",
                            sender=current_sender,
                            content_type=ContentType.TEXT,
                            metadata={"file": filename, "source": "whatsapp_export"},
                            thread_id=filename,
                        )
                    )

        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.rstrip()
                match = self.PATTERN_1.match(line_str)
                if match:
                    flush_message()
                    current_date_str = match.group(1)
                    current_time_str = match.group(2)
                    current_sender = match.group(3).strip()
                    current_text_lines = [match.group(4).strip()]
                else:
                    if current_text_lines:
                        current_text_lines.append(line_str)

        flush_message()
        return events
