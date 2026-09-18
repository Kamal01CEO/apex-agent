"""Anti-Hallucination Guard, Strict Context Fencing, and Grounded Synthesis."""

from typing import List, Optional
from apex_agent.intelligence.conflicts import ConflictDetector
from apex_agent.models import ConfidenceLevel, Conflict, SearchResult


class AntiHallucinationGuard:
    """Ensures answers are grounded ONLY in verified recalled chunks with explicit source citations.
    Implements Hermes context fencing (<memory-context>) and strict refusal protocol.
    """

    def __init__(self):
        self.conflict_detector = ConflictDetector()

    def format_fenced_context(self, results: List[SearchResult]) -> str:
        """Fences memory chunks to supply grounded context."""
        if not results:
            return ""

        blocks = []
        for idx, r in enumerate(results, 1):
            blocks.append(
                f"--- Memory Record {idx} ---\n"
                f"Source: {r.chunk.source_ref}\n"
                f"Date: {r.chunk.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                f"Content:\n{r.chunk.content.strip()}\n"
            )

        return "\n\n".join(blocks)

    def evaluate_grounding(self, results: List[SearchResult]) -> ConfidenceLevel:
        """Evaluates overall confidence of the retrieval bundle."""
        if not results:
            return ConfidenceLevel.NO_MATCH

        # Check if any chunk has strong relevance or match
        for r in results:
            if r.confidence in (ConfidenceLevel.EXACT_MATCH, ConfidenceLevel.SEMANTIC_MATCH):
                return r.confidence
            if r.relevance_score > 0.25:
                return ConfidenceLevel.SEMANTIC_MATCH

        top = results[0]
        if top.relevance_score > 0.15:
            return ConfidenceLevel.WEAK_MATCH

        return ConfidenceLevel.NO_MATCH

    def synthesize_answer(self, query: str, results: List[SearchResult], llm_client) -> str:
        """Synthesizes the final verified response or executes the refusal protocol."""
        confidence = self.evaluate_grounding(results)

        # 1. Refusal Protocol if no match or negative scores
        if confidence == ConfidenceLevel.NO_MATCH or not results:
            return (
                "❌ **Information Not Found in Memory**\n\n"
                f"I searched across your ingested WhatsApp messages, emails, notes, and documents, "
                f"but found no record regarding: *\"{query}\"*.\n\n"
                "*(Anti-Hallucination Protocol active: I will not guess or extrapolate unverified facts.)*"
            )

        # 2. Check for contradictions/conflicts across sources
        conflicts = self.conflict_detector.detect_conflicts(results)

        fenced_context = self.format_fenced_context(results)

        user_prompt = f"""
You are answering a question based ONLY on the verified personal memory records provided below.
Do not use prior external knowledge. Do not use tools. Extract the answer directly from these records.

QUESTION:
{query}

MEMORY RECORDS:
{fenced_context}

INSTRUCTIONS:
1. Answer the question directly and factually using ONLY the facts above.
2. For every fact mentioned, cite the exact source in parentheses, like `[Source: whatsapp:sample_whatsapp.txt:Rahul:2026-09-15]`.
3. If the answer is not contained in the records above, say exactly: "Information Not Found in Memory".
"""
        if conflicts:
            conflict_warning = "\n\nNOTE: A discrepancy was detected between sources:\n"
            for c in conflicts:
                conflict_warning += (
                    f"- Conflict Topic: {c.topic}\n"
                    f"  Source A ({c.source_a}): {c.claim_a}\n"
                    f"  Source B ({c.source_b}): {c.claim_b}\n"
                )
            user_prompt += conflict_warning + "\nPlease explicitly state both conflicting claims."

        messages = [
            {"role": "user", "content": user_prompt}
        ]

        answer = llm_client.chat_completion(messages, temperature=0.1, max_tokens=800)

        # Prepend conflict alert banner if present
        if conflicts:
            banner = "⚠️ **DISCREPANCY DETECTED BETWEEN SOURCES**\n\n"
            for c in conflicts:
                banner += (
                    f"• **{c.topic}**:\n"
                    f"  - **{c.source_a}**: \"{c.claim_a}\"\n"
                    f"  - **{c.source_b}**: \"{c.claim_b}\"\n"
                    f"  *(Explanation: {c.resolution_notes})*\n\n"
                )
            banner += "---\n\n"
            answer = banner + answer

        return answer
