"""Splits parsed pages into clause-sized text segments for the LLM to classify.

Contracts are usually organized into numbered clauses/sections. We split on
common clause boundary patterns (numbered headings, blank lines) and fall
back to sentence-grouping when no clear structure exists. Each segment keeps
the page number it came from so evidence stays traceable.
"""
import re
from dataclasses import dataclass
from typing import List

from app.services.document_parser import ParsedDocument

# Matches headings like "1.", "1.1", "Section 4:", "ARTICLE III", "(a)" at line start.
_HEADING_PATTERN = re.compile(
    r"^\s*(\d+(\.\d+)*[\.\)]?|\(?[a-zA-Z]\)|SECTION\s+\d+|ARTICLE\s+[IVXLC]+)\s+",
    re.IGNORECASE,
)

MAX_SEGMENT_CHARS = 1200
MIN_SEGMENT_CHARS = 40


@dataclass
class TextSegment:
    segment_id: str
    text: str
    page: int


def _split_page_into_candidates(text: str) -> List[str]:
    lines = [l for l in text.split("\n") if l.strip()]
    segments: List[str] = []
    current: List[str] = []

    for line in lines:
        if _HEADING_PATTERN.match(line) and current:
            segments.append(" ".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        segments.append(" ".join(current).strip())

    # If heading-based splitting produced one giant blob, fall back to sentence grouping.
    if len(segments) <= 1 and len(text) > MAX_SEGMENT_CHARS:
        sentences = re.split(r"(?<=[.;])\s+", text)
        segments = []
        buf = ""
        for s in sentences:
            if len(buf) + len(s) > MAX_SEGMENT_CHARS and buf:
                segments.append(buf.strip())
                buf = s
            else:
                buf = f"{buf} {s}".strip()
        if buf:
            segments.append(buf.strip())

    return [s for s in segments if len(s) >= MIN_SEGMENT_CHARS]


def chunk_document(doc: ParsedDocument) -> List[TextSegment]:
    """Produce clause-candidate segments, each tagged with its source page."""
    segments: List[TextSegment] = []
    counter = 0

    for page in doc.pages:
        for candidate in _split_page_into_candidates(page.text):
            # Further split overly long candidates so nothing sent to the LLM
            # exceeds MAX_SEGMENT_CHARS.
            for i in range(0, len(candidate), MAX_SEGMENT_CHARS):
                chunk_text = candidate[i : i + MAX_SEGMENT_CHARS].strip()
                if len(chunk_text) < MIN_SEGMENT_CHARS:
                    continue
                counter += 1
                segments.append(
                    TextSegment(segment_id=f"seg-{counter}", text=chunk_text, page=page.page_number)
                )

    return segments
