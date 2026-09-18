"""Interactive Agent Runtime with Tool-Based Memory Retrieval & Anti-Hallucination."""

from typing import Any, Dict, List
from apex_agent.agent.tools import MemoryAgentTools
from apex_agent.intelligence.guard import AntiHallucinationGuard
from apex_agent.llm import llm
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.search import HybridSearchEngine
from apex_agent.memory.store import MarkdownMemoryStore


class MemoryAgentRuntime:
    """Core autonomous agent runtime executing grounded query answering and continuous memory."""

    def __init__(self, index: SQLiteMemoryIndex = None):
        self.index = index or SQLiteMemoryIndex()
        self.tools = MemoryAgentTools(index=self.index)
        self.search_engine = HybridSearchEngine(index=self.index)
        self.guard = AntiHallucinationGuard()
        self.store = MarkdownMemoryStore()

    def ask(self, user_query: str) -> str:
        """Processes a query: Hybrid Search -> Conflict Check -> Anti-Hallucination Grounded Synthesis."""
        # 1. Hybrid search for relevant context
        search_results = self.search_engine.search(user_query, limit=6)

        # 2. Synthesize verified response with anti-hallucination guard
        answer = self.guard.synthesize_answer(user_query, search_results, llm)

        # 3. Log interaction to daily journal
        self.store.append_daily_log(
            f"Query: `{user_query}` | Returned {len(search_results)} sources with top confidence: `{search_results[0].confidence.value if search_results else 'NONE'}`"
        )

        return answer
