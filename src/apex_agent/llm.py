"""LLM Client with silent cascading fallback and zero-downtime tolerance."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from openai import OpenAI
from apex_agent.config import (
    HERMES_API_BASE_URL,
    HERMES_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_API_KEY,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_API_KEY,
)

logger = logging.getLogger("apex_agent.llm")


class LLMClient:
    """Cascading multi-model client.
    1. Primary: Hermes Live Gateway Brain (instant, authenticated)
    2. Fallback: 9router OpenRouter
    3. Fallback: Local llama-server
    """

    def __init__(self):
        self.providers: List[Dict[str, Any]] = [
            {
                "name": "hermes-live-gateway",
                "client": OpenAI(base_url=HERMES_API_BASE_URL, api_key=HERMES_API_KEY),
                "model": "hermes-agent",
            },
            {
                "name": "9router-gemini",
                "client": OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY),
                "model": "gc/gemini-2.5-flash",
            },
            {
                "name": "local-qwen",
                "client": OpenAI(base_url=LOCAL_LLM_BASE_URL, api_key=LOCAL_LLM_API_KEY),
                "model": "qwen3-8b",
            },
        ]

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1200,
        preferred_model: Optional[str] = None,
    ) -> str:
        """Runs completion down the fallback chain silently."""
        errors = []

        candidate_providers = list(self.providers)
        if preferred_model:
            candidate_providers.insert(
                0,
                {
                    "name": f"preferred-{preferred_model}",
                    "client": OpenAI(base_url=HERMES_API_BASE_URL, api_key=HERMES_API_KEY),
                    "model": preferred_model,
                }
            )

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
