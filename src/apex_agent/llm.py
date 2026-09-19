"""LLM Client for Apex Agent connecting to active verified gateway on port 8642."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from openai import OpenAI
from apex_agent.config import (
    HERMES_API_BASE_URL,
    HERMES_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_API_KEY,
)

logger = logging.getLogger("apex_agent.llm")


class LLMClient:
    """Multi-provider client for Apex Agent with active gateway primary."""

    def __init__(self):
        self.providers: List[Dict[str, Any]] = [
            {
                "name": "active-gateway-8642",
                "client": OpenAI(base_url=HERMES_API_BASE_URL, api_key=HERMES_API_KEY),
                "model": "hermes-agent",
            },
            {
                "name": "9router-fallback",
                "client": OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY),
                "model": "gc/gemini-2.5-flash",
            },
        ]

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1200,
        preferred_model: Optional[str] = None,
    ) -> str:
        """Runs completion down the fallback chain."""
        errors = []

        candidate_providers = list(self.providers)
        for provider in candidate_providers:
            try:
                response = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=25,
                )
                content = response.choices[0].message.content
                if content and content.strip():
                    return content.strip()
            except Exception as e:
                errors.append(f"{provider['name']}: {str(e)}")
                continue

        logger.error("All LLM providers failed: %s", " | ".join(errors))
        return "I apologize, but all AI synthesis channels are temporarily unreachable. Recalled direct raw chunks will be used."


llm = LLMClient()
