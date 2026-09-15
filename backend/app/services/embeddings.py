"""Lightweight text matching utilities.

This implementation avoids loading a machine-learning embedding model,
which keeps memory usage low during deployment.
"""

import re
from typing import List


def tokenize(text: str) -> set[str]:
    """Convert text into a set of lowercase words."""
    return set(re.findall(r"\b[a-zA-Z0-9]+\b", text.lower()))


def embed_texts(texts: List[str]):
    """
    Lightweight replacement for SentenceTransformer embeddings.

    Kept for compatibility with existing code.
    Actual retrieval is handled by word-overlap matching.
    """
    return texts