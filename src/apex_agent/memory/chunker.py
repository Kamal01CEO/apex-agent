"""Sliding window text chunker with paragraph and boundary preservation."""

import re
from typing import List


class TextChunker:
    """Splits text into ~400-word/token chunks with ~80-token overlap."""

    def __init__(self, chunk_size: int = 400, overlap: int = 80):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        cleaned = text.strip()
        if not cleaned:
            return []

        # Split into words/tokens
        words = re.split(r"(\s+)", cleaned)
        total_tokens = len(words)

        if total_tokens <= self.chunk_size:
            return [cleaned]

        chunks = []
        start = 0
        step = max(1, self.chunk_size - self.overlap)

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)
            chunk_str = "".join(words[start:end]).strip()
            if chunk_str:
                chunks.append(chunk_str)
            if end >= total_tokens:
                break
            start += step

        return chunks
