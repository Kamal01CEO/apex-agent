"""Email (.eml / RFC-822) Ingester."""

import email
from email import policy
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Union
from apex_agent.ingest.base import BaseIngester
from apex_agent.models import ContentType, MemoryEvent, SourceType


class EmailIngester(BaseIngester):
    """Ingests raw email files extracting headers, subject, sender, and clean body."""

    def can_ingest(self, file_path: Union[str, Path]) -> bool:
        return Path(file_path).suffix.lower() in (".eml", ".msg")

    def ingest(self, file_path: Union[str, Path]) -> List[MemoryEvent]:
        p = Path(file_path)
        with open(p, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        subject = msg.get("Subject", "No Subject")
        sender = msg.get("From", "Unknown Sender")
        recipient = msg.get("To", "")
        date_str = msg.get("Date")

        ts = datetime.now()
        if date_str:
            try:
                parsed_dt = email.utils.parsedate_to_datetime(date_str)
                if parsed_dt:
                    ts = parsed_dt.replace(tzinfo=None)
            except Exception:
                pass

        # Extract plain text content
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
            if not body:
                # Fallback to HTML conversion if no plaintext
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        body = part.get_content()
                        break
        else:
            body = msg.get_content()

        body_clean = str(body).strip()
        event_id = f"eml_{uuid.uuid4().hex[:10]}"
        source_ref = f"email:{sender}:{subject[:30]}:{ts.strftime('%Y-%m-%d')}"

        return [
            MemoryEvent(
                id=event_id,
                source_type=SourceType.EMAIL,
                source_ref=source_ref,
                timestamp=ts,
                content_text=f"Subject: {subject}\nFrom: {sender}\nTo: {recipient}\n\n{body_clean}",
                sender=sender,
                recipient=recipient,
                title=subject,
                content_type=ContentType.TEXT,
                metadata={"subject": subject, "from": sender, "to": recipient, "file": p.name},
                thread_id=msg.get("Message-ID", p.name),
            )
        ]
