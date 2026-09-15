"""Lightweight reference-policy retrieval.

Uses simple word-overlap similarity instead of FAISS and
Sentence-Transformers so the application can run on low-memory servers.
"""

from dataclasses import dataclass
from typing import List
import re


from app.services.chunking import TextSegment


@dataclass
class RetrievalHit:
    segment: TextSegment
    score: float


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-zA-Z0-9]+\b", text.lower()))


def _similarity(query: str, text: str) -> float:
    query_words = _tokenize(query)
    text_words = _tokenize(text)

    if not query_words or not text_words:
        return 0.0

    intersection = query_words.intersection(text_words)

    return len(intersection) / len(query_words)


class ReferenceVectorStore:
    """Lightweight replacement for the FAISS vector store."""

    def __init__(self, segments: List[TextSegment]):
        self.segments = segments

    def search(
        self,
        query_text: str,
        top_k: int = 3
    ) -> List[RetrievalHit]:

        if not self.segments:
            return []

        scored = []

        for segment in self.segments:
            score = _similarity(query_text, segment.text)

            if score > 0:
                scored.append(
                    RetrievalHit(
                        segment=segment,
                        score=float(score)
                    )
                )

        scored.sort(
            key=lambda hit: hit.score,
            reverse=True
        )

        return scored[:top_k]

    def search_by_category(
        self,
        category: str,
        top_k: int = 3
    ) -> List[RetrievalHit]:
        """Retrieve reference clauses related to a category."""

        return self.search(category, top_k=top_k)