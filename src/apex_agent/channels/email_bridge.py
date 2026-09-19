"""Email Bridge utilizing tszaks/ghub for Gmail Multi-Account Browser OAuth & Sending."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class GhubEmailBridge:
    """Invokes ghub MCP server for Gmail browser authentication and automated email dispatch."""

    def __init__(self):
        self.ghub_dir = Path(__file__).resolve().parent.parent.parent / "integrations" / "ghub"
        self.entry_point = self.ghub_dir / "dist" / "index.js"

    def is_configured(self) -> bool:
        return self.entry_point.exists()

    def get_status(self) -> Dict[str, Any]:
        """Returns status of ghub Gmail MCP server."""
        return {
            "status": "active" if self.entry_point.exists() else "not_built",
            "provider": "tszaks/ghub (Gmail Multi-Account OAuth)",
            "path": str(self.entry_point)
        }
