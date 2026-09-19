"""Live Gmail Integration for Outbound Cold Outreach and Inbound Monitoring."""

import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import imaplib
import logging
import smtplib
import ssl
from typing import Any, Dict, List, Optional
from apex_agent.config import GMAIL_USER, GMAIL_APP_PASSWORD

logger = logging.getLogger("apex_agent.email")


class LiveGmailBridge:
    """Sends real emails via Gmail SMTP and checks inbound replies via Gmail IMAP."""

    def __init__(self, user: str = GMAIL_USER, password: str = GMAIL_APP_PASSWORD):
        self.user = user
        self.password = password.replace(" ", "")

    def send_email(self, to_email: str, subject: str, body_text: str) -> Dict[str, Any]:
        """Sends a real email through Gmail SMTP."""
        if not self.user or not self.password:
            return {"status": "error", "message": "Gmail credentials not configured."}

        msg = MIMEMultipart()
        msg["From"] = f"Kamal Rai <{self.user}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.user, self.password)
                server.sendmail(self.user, to_email, msg.as_string())
            return {
                "status": "success",
                "message": f"Real email successfully dispatched to {to_email} via Gmail SMTP.",
                "from": self.user,
                "to": to_email,
                "subject": subject
            }
        except Exception as e:
            logger.error("Gmail SMTP error: %s", e)
            return {"status": "error", "message": f"SMTP Error: {str(e)}"}

    def fetch_recent_replies(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Connects via IMAP to check recent unread or inbound messages."""
        if not self.user or not self.password:
            return []

        messages = []
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.user, self.password)
            mail.select("inbox")

            status, data = mail.search(None, "ALL")
            mail_ids = data[0].split()

            # Take latest 'limit' messages
            for i in reversed(mail_ids[-limit:]):
                status, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg.get("Subject", ""))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")
                        from_sender = msg.get("From", "")

                        messages.append({
                            "from": from_sender,
                            "subject": subject,
                            "date": msg.get("Date", "")
                        })
            mail.close()
            mail.logout()
        except Exception as e:
            logger.error("Gmail IMAP error: %s", e)

        return messages
