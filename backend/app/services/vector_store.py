"""In-memory FAISS index used to retrieve the most relevant reference-policy
segments for each contract clause.

The index is built fresh per review request (reference policies are small
enough that this is fast and avoids any persistence/staleness concerns). This
keeps the implementation simple, matching the project's "keep it simple"
requirement while still using FAISS + Sentence-Transformers as specified.
"""
from dataclasses import dataclass
from typing import List

import faiss
import numpy as np

from app.services.chunking import TextSegment
from app.services.embeddings import embed_texts


@dataclass
class RetrievalHit:
    segment: TextSegment
    score: float


class ReferenceVectorStore:
    """Wraps a FAISS flat inner-product index over reference-policy segments."""

    def __init__(self, segments: List[TextSegment]):
        self.segments = segments
        self._embeddings = embed_texts([s.text for s in segments])
        dim = self._embeddings.shape[1] if self._embeddings.size else 384
        self.index = faiss.IndexFlatIP(dim)
        if self._embeddings.shape[0] > 0:
            self.index.add(self._embeddings)

    def search(self, query_text: str, top_k: int = 3) -> List[RetrievalHit]:
        if not self.segments:
            return []
        query_vec = embed_texts([query_text])
        k = min(top_k, len(self.segments))
        scores, indices = self.index.search(query_vec, k)
        hits: List[RetrievalHit] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            hits.append(RetrievalHit(segment=self.segments[int(idx)], score=float(score)))
        return hits

    def search_by_category(self, category: str, top_k: int = 3) -> List[RetrievalHit]:
        """Convenience wrapper: use the category name itself as a query, useful
        for detecting reference requirements that have no matching contract
        clause at all (missing-clause detection)."""
        return self.search(category, top_k=top_k)
