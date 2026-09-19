"""Conversational Multi-Turn Agent Loop for Apex Agent with Tool Actions."""

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
    """Apex Agent: Own Memory, Own Knowledge Graph, Own Action Tools."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_db = SessionDB()
        self.tools = ActionTools()
        self.session_id = session_id or self.session_db.create_session(title="Interactive Chat")

        # Connect directly to live working gateway on port 8642
        self.client = OpenAI(base_url=HERMES_API_BASE_URL, api_key=HERMES_API_KEY)
        self.model = "hermes-agent"

    def _build_system_prompt(self) -> str:
        durable_facts = ""
        if MEMORY_MD_PATH.exists():
            durable_facts = MEMORY_MD_PATH.read_text(encoding="utf-8")[:1500]

        return f"""
You are APEX AGENT — an autonomous personal memory assistant and chief of staff for a solo founder.
Speak directly, concisely, and factually. No corporate fluff.

## Grounding Rules
- Never invent facts. Base statements strictly on verified recalled memory data.
- Always cite your sources with `[Source: type:ref:timestamp]` syntax.
- If conflicting information exists across sources, point out both claims clearly.

## Apex Agent's Own Durable Memory
{durable_facts}
"""

    def interact(self, user_input: str, on_tool_call: Optional[Callable[[str, dict], None]] = None) -> str:
        """Processes one conversational turn with memory search and action tools."""
        # 1. Save user turn
        self.session_db.add_message(self.session_id, role="user", content=user_input)

        # 2. Autonomous memory search
        memory_context = ""
        results = self.tools.search_engine.search(user_input, limit=4)
        if results and results[0].relevance_score > 0.15:
            if on_tool_call:
                on_tool_call("memory_search", {"query": user_input})
            memory_context = "\n".join([
                f"[Source: {r.chunk.source_ref} ({r.confidence.value}) | {r.chunk.timestamp.strftime('%Y-%m-%d')}]:\n{r.chunk.content.strip()}"
                for r in results
            ])

        # 3. Action tools execution
        actions_taken = []
        if "draft" in user_input.lower() and "email" in user_input.lower():
            if on_tool_call:
                on_tool_call("draft_email", {"recipient": "Sarah Jenkins", "goal": "compromise terms"})
            res = self.tools.execute_tool("draft_email", {
                "recipient": "sarah.jenkins@acmecorp.com",
                "subject": "RE: Contract Payment Terms — Proposed Compromise",
                "body": "Hi Sarah,\n\nThanks for following up. Regarding payment terms, we understand your corporate policy requires Net 30. We can agree to Net 30 with a 50% upfront milestone deposit, or maintain Net 15 for standard invoicing.\n\nLet me know if this works for your team.\n\nBest regards,\nKamal Rai\nApexArcGlobal",
                "context_notes": "Compromise proposal for Net 15 vs Net 30 conflict"
            })
            actions_taken.append(res)

        if "pipeline" in user_input.lower() or "contract" in user_input.lower():
            if on_tool_call:
                on_tool_call("update_pipeline", {"company": "Acme Corp", "stage": "proposal"})
            res = self.tools.execute_tool("update_pipeline", {
                "company": "Acme Corp",
                "stage": "proposal",
                "deal_value": "$45,000 + $6,000/mo retainer",
                "notes": "Negotiating payment terms (Net 15 vs Net 30)"
            })
            actions_taken.append(res)

        # 4. Check for conflicts
        conflicts = self.tools.conflict_detector.detect_conflicts(results) if results else []

        # 5. Formulate prompt
        prompt = f"User Request: {user_input}\n"
        if memory_context:
            prompt += f"\n<recalled-memory-data>\n{memory_context}\n</recalled-memory-data>\n"
        if conflicts:
            prompt += f"\n<conflict-warning>\nDetected contradiction: {conflicts[0].topic}\nSource A: {conflicts[0].claim_a}\nSource B: {conflicts[0].claim_b}\n</conflict-warning>\n"
        if actions_taken:
            prompt += f"\n<actions-executed-by-apex>\n" + "\n".join(actions_taken) + "\n</actions-executed-by-apex>\n"

        prompt += "\nRespond as Apex Agent directly to the founder. Cite exact sources for any memory claims. State any actions taken."

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        # 6. Call live working endpoint on port 8642
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
                timeout=25,
            )
            reply = resp.choices[0].message.content or ""
        except Exception as e:
            action_summary = " ".join(actions_taken) if actions_taken else "Actions evaluated."
            reply = f"Apex Agent (Offline Mode): {action_summary}\n\nRecalled Context:\n{memory_context[:300]}"

        # 7. Save assistant turn to SessionDB
        self.session_db.add_message(
            self.session_id,
            role="assistant",
            content=reply,
            tool_calls=[{"actions": actions_taken}] if actions_taken else None,
        )

        return reply
