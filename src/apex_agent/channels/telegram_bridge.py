"""Telegram Bot Gateway for Apex Agent.
Allows the founder to interact with Apex Agent directly on Telegram,
trigger autonomous goals, search memory, and receive proactive briefings.
"""

import asyncio
import logging
import os
from typing import Optional
import httpx
from apex_agent.agent.conversation_loop import ConversationalAgent
from apex_agent.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("apex_agent.telegram")


class TelegramApexBridge:
    """Long-polling Telegram Bot daemon running Apex Agent."""

    def __init__(self, token: Optional[str] = None, allowed_user: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN or "8725855304:AAGp1RTU-62RfVwvcUX82EzpYtCSJlqeBjE"
        self.allowed_user = str(allowed_user or TELEGRAM_CHAT_ID or "5590614649")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.sessions = {}  # chat_id -> ConversationalAgent

    def send_text(self, chat_id: str, text: str):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=10) as client:
                res = client.post(url, json=payload)
                if res.status_code != 200:
                    # Fallback plain text if markdown formatting errors
                    payload.pop("parse_mode", None)
                    client.post(url, json=payload)
        except Exception as e:
            logger.error("Error sending telegram message: %s", e)

    def run_polling(self):
        """Polls Telegram for incoming messages and routes to Apex Agent."""
        print(f"🚀 Telegram Apex Agent Bridge is LIVE. Listening for messages from user: {self.allowed_user}...")
        offset = 0

        with httpx.Client(timeout=35) as client:
            while True:
                try:
                    url = f"{self.base_url}/getUpdates?offset={offset}&timeout=25"
                    resp = client.get(url)
                    if resp.status_code != 200:
                        asyncio.run(asyncio.sleep(2))
                        continue

                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        msg = update.get("message", {})
                        from_id = str(msg.get("from", {}).get("id", ""))
                        chat_id = str(msg.get("chat", {}).get("id", ""))
                        text = msg.get("text", "").strip()

                        if not text:
                            continue

                        # Restrict to founder
                        if self.allowed_user and from_id != self.allowed_user:
                            client.post(f"{self.base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "⛔ Unauthorized. This is a private Apex Agent personal assistant."
                            })
                            continue

                        # Initialize or get session for this chat
                        if chat_id not in self.sessions:
                            self.sessions[chat_id] = ConversationalAgent()

                        agent = self.sessions[chat_id]

                        # Send typing indicator
                        client.post(f"{self.base_url}/sendChatAction", json={
                            "chat_id": chat_id,
                            "action": "typing"
                        })

                        # Process with Apex Agent
                        reply = agent.interact(text)
                        self.send_text(chat_id, reply)

                except KeyboardInterrupt:
                    print("\nTelegram Bridge stopped.")
                    break
                except Exception as e:
                    logger.error("Polling error: %s", e)
                    asyncio.run(asyncio.sleep(3))


if __name__ == "__main__":
    bridge = TelegramApexBridge()
    bridge.run_polling()
