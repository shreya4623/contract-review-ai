"""Document Parsing Agent.

Pure, deterministic step (no LLM call): extracts page-indexed text from the
uploaded PDF/DOCX files and splits each into clause-candidate segments. Kept
deterministic on purpose so no evidence can be "invented" before an LLM is
ever involved.
"""
from typing import List

from app.services.document_parser import parse_document
from app.services.chunking import chunk_document, TextSegment


def parse_and_segment(file_path: str) -> List[TextSegment]:
    """Parse a document and return its clause-candidate text segments."""
    parsed = parse_document(file_path)
    return chunk_document(parsed)
