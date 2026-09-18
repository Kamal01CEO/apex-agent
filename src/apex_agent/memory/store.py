"""Curated Markdown Store and Daily Memory Logs."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from apex_agent.config import DATA_DIR, MEMORY_MD_PATH


class MarkdownMemoryStore:
    """Manages MEMORY.md and daily logs (memory/YYYY-MM-DD.md)."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.memory_md = MEMORY_MD_PATH
        self.logs_dir = data_dir / "memory"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_memory_md()

    def _ensure_memory_md(self):
        if not self.memory_md.exists():
            default_content = (
                "# MEMORY.md — Curated Core Memory\n"
                "*Maintained by Apex Agent. Stores durable facts, decisions, and standing goals.*\n\n"
                "## Principal\n"
                "- Name: Founder / Operator\n"
                "- Focus: AI Infrastructure & Automation\n\n"
                "## Core Standing Facts\n"
                "- System operates in local-first mode with multi-modal memory indexing.\n"
            )
            self.memory_md.write_text(default_content, encoding="utf-8")

    def read_core_memory(self) -> str:
        """Reads durable core facts from MEMORY.md."""
        if self.memory_md.exists():
            return self.memory_md.read_text(encoding="utf-8")
        return ""

    def append_daily_log(self, entry: str, timestamp: Optional[datetime] = None):
        """Appends an event/note to today's log file."""
        ts = timestamp or datetime.now()
        date_str = ts.strftime("%Y-%m-%d")
        time_str = ts.strftime("%H:%M:%S")
        log_file = self.logs_dir / f"{date_str}.md"

        if not log_file.exists():
            header = f"# Daily Activity Log — {date_str}\n\n"
            log_file.write_text(header, encoding="utf-8")

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"- `[{time_str}]` {entry.strip()}\n")
