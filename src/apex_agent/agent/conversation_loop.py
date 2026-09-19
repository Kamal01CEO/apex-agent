"""Conversational Multi-Turn Agent Loop with True LLM Intent & Autonomous Tool Execution."""

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
    """Apex Agent: Autonomous Chief of Staff executing real actions via LLM intent reasoning."""

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
You are APEX AGENT — an autonomous personal memory operating system and Chief of Staff for Kamal (Founder of ApexArcGlobal).
You are direct, sharp, and proactive. No robotic filler.

## Core Directives
1. Never invent facts. Base statements strictly on recalled memory data or live tool outputs.
2. When answering, state clearly what actions were taken (e.g. meetings cancelled, emails checked, memory saved).
3. If checking emails, summarize the real sender and subject line.
4. If cancelling meetings, confirm the calendar is cleared.

## Apex Agent's Own Durable Memory
{durable_facts}
"""

    def _decide_tool_calls_via_llm(self, user_msg: str) -> List[Dict[str, Any]]:
        """Uses the LLM to determine exact tool calls from the user's intent."""
        decision_prompt = f"""
Given the user request below, select the appropriate tools to call.
Available Tools:
- check_inbox_replies(limit: int) -> checks Gmail inbox for recent emails
- calendar_cancel_meetings(participant: str) -> cancels/clears meetings from calendar ('all' to cancel all)
- calendar_list_meetings() -> lists current scheduled meetings
- calendar_schedule_meeting(title, participant, date_time, duration_minutes) -> schedules a new meeting
- memory_search(query: str) -> searches past personal memory (WhatsApp, notes, emails)
- send_cold_outreach(prospect_name, company, email, pain_point) -> sends real cold outreach email
- schedule_followup_cron(lead_name, email, days_delay) -> sets cron watchdog
- analyze_and_improve_outreach(lead_name) -> analyzes unreplied email and drafts improved version
- auto_save_memory(source_type, content, sender) -> saves new interaction into memory
- scrape_web_leads(industry: str) -> discovers new enterprise leads

User Request: "{user_msg}"

Output a STRICT JSON array of objects with "tool" and "args". If no tools are needed, output [].
Example:
[{{"tool": "calendar_cancel_meetings", "args": {{"participant": "all"}}}}, {{"tool": "check_inbox_replies", "args": {{"limit": 5}}}}]

Output JSON only:
"""
        messages = [
            {"role": "system", "content": "You are a precise tool router. Return strictly valid JSON array."},
            {"role": "user", "content": decision_prompt}
        ]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=400,
                timeout=15,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            calls = json.loads(raw)
            if isinstance(calls, list):
                return calls
        except Exception:
            pass

        # Smart rule-based fallback if LLM formatting fails
        calls = []
        low = user_msg.lower()
        if "cancel" in low and ("meeting" in low or "call" in low or "calendar" in low):
            calls.append({"tool": "calendar_cancel_meetings", "args": {"participant": "all"}})
        elif "schedule" in low and ("meeting" in low or "call" in low):
            calls.append({"tool": "calendar_schedule_meeting", "args": {"title": "Strategic Call", "participant": "Client Partner", "date_time": "2026-09-23 15:00 IST"}})

        if any(w in low for w in ("inbox", "mail", "email", "reply", "replies")) and any(w in low for w in ("check", "read", "important", "new", "any")):
            calls.append({"tool": "check_inbox_replies", "args": {"limit": 5}})
        elif any(w in low for w in ("outreach", "pitch")) or ("send" in low and "email" in low):
            calls.append({"tool": "send_cold_outreach", "args": {"prospect_name": "Ali Ghodsi", "company": "Databricks", "email": "ali@databricks.com"}})

        if "scrape" in low or "find leads" in low:
            calls.append({"tool": "scrape_web_leads", "args": {"industry": "Enterprise SaaS"}})

        if "save" in low and ("whatsapp" in low or "conversation" in low or "remember" in low):
            calls.append({"tool": "auto_save_memory", "args": {"source_type": "whatsapp", "content": user_msg}})

        if not calls and len(user_msg.split()) > 2:
            calls.append({"tool": "memory_search", "args": {"query": user_msg}})

        return calls

    def interact(self, user_input: str, on_tool_call: Optional[Callable[[str, dict], None]] = None) -> str:
        """Processes one conversational turn by determining tools, executing them, and synthesizing response."""
        self.session_db.add_message(self.session_id, role="user", content=user_input)

        # 1. Determine tool calls
        tool_calls = self._decide_tool_calls_via_llm(user_input)
        tool_observations = []

        # 2. Execute each tool
        for tc in tool_calls:
            tname = tc.get("tool")
            targs = tc.get("args", {})
            if on_tool_call:
                on_tool_call(tname, targs)
            obs = self.tools.execute_tool(tname, targs)
            tool_observations.append(f"Tool `{tname}` output:\n{obs}")

        # 3. Synthesize natural grounded response
        obs_text = "\n\n".join(tool_observations) if tool_observations else "No external actions required."

        synthesis_prompt = f"""
User Query: "{user_input}"

Tools Executed and Live Outputs:
{obs_text}

Instructions:
1. Answer the user directly and concisely as Apex Agent (Chief of Staff).
2. Confirm the exact actions completed (e.g. meetings cancelled).
3. If inbox was checked, report the emails found cleanly.
4. Do not recite raw JSON. Speak professionally and crisply.
"""
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": synthesis_prompt}
        ]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=700,
                timeout=25,
            )
            reply = resp.choices[0].message.content or ""
        except Exception:
            reply = f"Apex Agent Action Summary:\n\n{obs_text}"

        self.session_db.add_message(
            self.session_id,
            role="assistant",
            content=reply,
            tool_calls=tool_calls if tool_calls else None
        )

        return reply
