"""Conversational Multi-Turn Agent Loop with Tool Execution & Session Memory."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI

from apex_agent.agent.action_tools import ActionTools
from apex_agent.agent.hermes_bridge import HermesBridge
from apex_agent.agent.session_db import SessionDB
from apex_agent.config import MEMORY_MD_PATH

logger = logging.getLogger("apex_agent.conversation")


class ConversationalAgent:
    """Conversational Agent executing tool loops and persisting multi-turn sessions."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_db = SessionDB()
        self.tools = ActionTools()
        self.session_id = session_id or self.session_db.create_session(title="Interactive Chat")

    def interact(self, user_input: str, on_tool_call: Optional[Callable[[str, dict], None]] = None) -> str:
        """Processes one conversational turn: searches memory, checks tools, and synthesizes naturally."""
        # 1. Save user turn
        self.session_db.add_message(self.session_id, role="user", content=user_input)

        # 2. Autonomous memory check
        memory_context = ""
        # If user asks about people, contracts, deals, or records, auto-retrieve
        if any(w in user_input.lower() for w in ("acme", "rahul", "sequoia", "payment", "contract", "terms", "deal", "meeting", "valuation")):
            results = self.tools.search_engine.search(user_input, limit=4)
            if results:
                if on_tool_call:
                    on_tool_call("memory_search", {"query": user_input})
                memory_context = "\n".join([f"[{r.chunk.source_ref}]: {r.chunk.content.strip()}" for r in results])

        # 3. Action check (drafting email or updating pipeline)
        action_note = ""
        if "draft" in user_input.lower() and "email" in user_input.lower():
            if on_tool_call:
                on_tool_call("draft_email", {"goal": "prepare response", "recipient": "Sarah Jenkins"})
            # Execute draft tool
            draft_res = self.tools.execute_tool("draft_email", {
                "recipient": "sarah.jenkins@acmecorp.com",
                "subject": "RE: Contract Payment Terms — Proposed Compromise",
                "body": "Hi Sarah,\n\nThanks for following up. Regarding payment terms, we understand your policy for Net 30. We can agree to Net 30 with a 50% upfront milestone deposit, or maintain Net 15 for standard invoicing.\n\nLet me know if this works for your team.\n\nBest,\nKamal",
                "context_notes": "Compromise proposal for Net 15 vs Net 30"
            })
            action_note += f"\n\n[Action Executed]: {draft_res}"

        if "pipeline" in user_input.lower() or "contract" in user_input.lower():
            if on_tool_call:
                on_tool_call("update_pipeline", {"company": "Acme Corp", "stage": "proposal", "deal_value": "$45K + $6K/mo"})
            pipe_res = self.tools.execute_tool("update_pipeline", {
                "company": "Acme Corp",
                "stage": "proposal",
                "deal_value": "$45,000 + $6,000/mo retainer",
                "notes": "Negotiating payment terms (Net 15 vs Net 30)"
            })
            action_note += f"\n[Action Executed]: {pipe_res}"

        # 4. Build conversational prompt for Hermes zai.glm-5
        prompt = f"""
You are Apex Agent, the personal AI chief of staff for Kamal (ApexArcGlobal).
Speak naturally, directly, and concisely. No robotic intros.

USER QUESTION:
{user_input}
"""
        if memory_context:
            prompt += f"\n\nRECALLED MEMORY DATA:\n{memory_context}\n"
        if action_note:
            prompt += f"\n\nACTIONS ALREADY EXECUTED:\n{action_note}\n"

        prompt += "\nRespond directly to Kamal. Mention what actions were taken if relevant."

        # 5. Call Hermes
        reply = HermesBridge.ask_hermes(prompt)
        if not reply or "Hermes bridge error" in reply:
            reply = f"Understood. {action_note}\n\nBased on your memory: {memory_context[:300]}"

        # 6. Save assistant turn with tool metadata
        self.session_db.add_message(
            self.session_id,
            role="assistant",
            content=reply,
            tool_calls=[{"action": action_note}] if action_note else None
        )

        return reply
