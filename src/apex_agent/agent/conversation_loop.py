"""Conversational Multi-Turn Agent Loop for Apex Agent with Autonomous Tool Actions."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI

from apex_agent.agent.action_tools import ActionTools
from apex_agent.agent.session_db import SessionDB
from apex_agent.config import (
    HERMES_API_BASE_URL,
    HERMES_API_KEY,
    MEMORY_MD_PATH,
)

logger = logging.getLogger("apex_agent.conversation")


class ConversationalAgent:
    """Apex Agent: Autonomous Chief of Staff executing real actions on demand."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_db = SessionDB()
        self.tools = ActionTools()
        self.session_id = session_id or self.session_db.create_session(title="Interactive Chat")

        self.client = OpenAI(base_url=HERMES_API_BASE_URL, api_key=HERMES_API_KEY)
        self.model = "hermes-agent"

    def _build_system_prompt(self) -> str:
        durable_facts = ""
        if MEMORY_MD_PATH.exists():
            durable_facts = MEMORY_MD_PATH.read_text(encoding="utf-8")[:1500]

        return f"""
You are APEX AGENT — an autonomous personal memory assistant and chief of staff for Kamal (founder of ApexArcGlobal).
Speak directly, concisely, and factually. No corporate fluff.

## Operating Principles
- Never invent facts. Base statements strictly on verified recalled memory data.
- Always cite your sources with `[Source: type:ref:timestamp]` syntax.
- When an action is requested (send cold outreach, save memory, schedule meeting, improve email, set follow-up cron), confirm the action taken and present the outcome clearly.

## Apex Agent's Own Durable Memory
{durable_facts}
"""

    def interact(self, user_input: str, on_tool_call: Optional[Callable[[str, dict], None]] = None) -> str:
        """Processes one conversational turn with autonomous tool routing and memory synthesis."""
        self.session_db.add_message(self.session_id, role="user", content=user_input)
        low = user_input.lower()
        actions_taken = []

        # 1. Lead Generation / Scraping Tool
        if any(w in low for w in ("scrape", "find leads", "prospect discovery", "make client list")):
            ind = "Enterprise SaaS & AI Infrastructure"
            if "logistics" in low: ind = "Logistics"
            elif "edtech" in low: ind = "EdTech"
            if on_tool_call: on_tool_call("scrape_web_leads", {"industry": ind})
            res = self.tools.execute_tool("scrape_web_leads", {"industry": ind})
            actions_taken.append(res)

        # 2. Cold Outreach Sending Tool
        if any(w in low for w in ("cold outreach", "send email to", "outreach mail", "pitch")):
            target_name = "Alexandr Wang" if "alex" in low else "Ali Ghodsi" if "ali" in low else "Arjun Mehta"
            company = "Scale AI" if "alex" in low else "Databricks" if "ali" in low else "NexFlow AI"
            email = "alex@scale.com" if "alex" in low else "ali@databricks.com" if "ali" in low else "arjun@nexflow.ai"
            pain = "production AI employee integration and workflow reliability"
            if on_tool_call: on_tool_call("send_cold_outreach", {"prospect_name": target_name, "company": company, "email": email})
            res = self.tools.execute_tool("send_cold_outreach", {
                "prospect_name": target_name,
                "company": company,
                "email": email,
                "pain_point": pain,
                "custom_hook": f"Following up on {company}'s enterprise AI scaling benchmarks."
            })
            actions_taken.append(res)

        # 3. Autonomous Memory Save (WhatsApp or user notes)
        if any(w in low for w in ("save", "remember this", "whatsapp conversation", "store this")):
            sender = "Rahul Sequoia" if "rahul" in low else "Sarah" if "sarah" in low else "Founder Partner"
            stype = "whatsapp" if "whatsapp" in low else "note"
            if on_tool_call: on_tool_call("auto_save_memory", {"source_type": stype, "sender": sender})
            res = self.tools.execute_tool("auto_save_memory", {
                "source_type": stype,
                "sender": sender,
                "content": user_input,
                "topic": "Real-time Captured Interaction"
            })
            actions_taken.append(res)

        # 4. Schedule Follow-up Cron Watchdog
        if any(w in low for w in ("cron", "follow up", "check if mail reply", "unanswered")):
            lead = "Ali Ghodsi" if "ali" in low else "Arjun Mehta"
            email = "ali@databricks.com" if "ali" in low else "arjun@nexflow.ai"
            if on_tool_call: on_tool_call("schedule_followup_cron", {"lead_name": lead, "email": email})
            res = self.tools.execute_tool("schedule_followup_cron", {
                "lead_name": lead,
                "email": email,
                "days_delay": 2,
                "strategy": "Automated reply-check watchdog + objection addressing"
            })
            actions_taken.append(res)

        # 5. Self-Improvement Engine (Diagnose & Improve unreplied emails)
        if any(w in low for w in ("improve", "why didn't", "no reply", "improve mail")):
            lead = "Ali Ghodsi" if "ali" in low else "Alexandr Wang"
            if on_tool_call: on_tool_call("analyze_and_improve_outreach", {"lead_name": lead})
            res = self.tools.execute_tool("analyze_and_improve_outreach", {
                "lead_name": lead,
                "reason_unanswered": "First pitch was too long with no immediate risk-free trial offer"
            })
            actions_taken.append(res)

        # 6. Meeting Scheduling & Calendar
        if any(w in low for w in ("schedule", "calendar", "meeting", "google meet")):
            participant = "Rahul Sequoia" if "rahul" in low else "Sarah Jenkins" if "sarah" in low else "Client Partner"
            dt_str = "2026-09-23 15:00 IST"
            if on_tool_call: on_tool_call("calendar_schedule_meeting", {"participant": participant, "date_time": dt_str})
            res = self.tools.execute_tool("calendar_schedule_meeting", {
                "title": f"Strategic Partnership Call with {participant}",
                "participant": participant,
                "date_time": dt_str,
                "duration_minutes": 30
            })
            actions_taken.append(res)

        # 7. Memory Search
        memory_context = ""
        results = self.tools.search_engine.search(user_input, limit=4)
        if results and results[0].relevance_score > 0.15:
            if on_tool_call: on_tool_call("memory_search", {"query": user_input})
            memory_context = "\n".join([
                f"[Source: {r.chunk.source_ref} ({r.confidence.value}) | {r.chunk.timestamp.strftime('%Y-%m-%d')}]:\n{r.chunk.content.strip()}"
                for r in results
            ])

        # 8. Formulate Response
        prompt = f"User Request: {user_input}\n"
        if memory_context:
            prompt += f"\n<recalled-memory-data>\n{memory_context}\n</recalled-memory-data>\n"
        if actions_taken:
            prompt += f"\n<actions-executed-autonomously>\n" + "\n".join(actions_taken) + "\n</actions-executed-by-apex>\n"

        prompt += "\nRespond as Apex Agent directly to Kamal. Summarize the actions executed cleanly and provide exact next steps."

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
                timeout=25,
            )
            reply = resp.choices[0].message.content or ""
        except Exception:
            action_summary = "\n".join(actions_taken) if actions_taken else "Actions evaluated."
            reply = f"**Apex Agent Action Report:**\n\n{action_summary}\n\n*Recalled Memory Context:*\n{memory_context[:300]}"

        self.session_db.add_message(
            self.session_id,
            role="assistant",
            content=reply,
            tool_calls=[{"actions": actions_taken}] if actions_taken else None,
        )

        return reply
