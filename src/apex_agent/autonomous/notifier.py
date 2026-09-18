"""Proactive notifications via Telegram and local terminal."""

import logging
from typing import Optional
import httpx
from apex_agent.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("apex_agent.notifier")


class TelegramNotifier:
    """Delivers proactive alerts, morning briefings, and conflict warnings."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID

    def send_message(self, text: str) -> bool:
        """Sends message to Telegram or falls back cleanly to stdout/logger."""
        if not self.token or not self.chat_id:
            # Fallback to local terminal notification
            print(f"\n[PROACTIVE NOTIFICATION]\n{text}\n")
            return True

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            with httpx.Client(timeout=10) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return True
                else:
                    logger.warning("Telegram API error: %s", res.text)
                    print(f"\n[TELEGRAM FALLBACK]\n{text}\n")
                    return False
        except Exception as e:
            logger.error("Failed to deliver Telegram notification: %s", e)
            print(f"\n[TELEGRAM FALLBACK EXCEPTION]\n{text}\n")
            return False
