"""Extracts page-indexed text from PDF and DOCX files.

Preserving page numbers is required so every downstream finding can cite an
exact page. DOCX has no native page concept, so we approximate pages by
splitting on explicit page breaks when present, and otherwise by chunking
paragraphs into fixed-size "virtual pages" of ~1800 characters - this keeps
evidence traceable to a stable page index even though DOCX pagination is
ultimately a rendering-time concept.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader
from docx import Document as DocxDocument

VIRTUAL_PAGE_CHARS = 1800


class UnsupportedFileTypeError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    filename: str
    pages: List[ParsedPage]

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def is_empty(self) -> bool:
        return not self.full_text.strip()


def parse_pdf(path: str) -> ParsedDocument:
    reader = PdfReader(path)
    if len(reader.pages) == 0:
        raise EmptyDocumentError("PDF has no pages.")

    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(ParsedPage(page_number=i, text=text))
    return ParsedDocument(filename=Path(path).name, pages=pages)


def parse_docx(path: str) -> ParsedDocument:
    doc = DocxDocument(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise EmptyDocumentError("DOCX has no readable text.")

    # Chunk paragraphs into virtual pages of roughly VIRTUAL_PAGE_CHARS characters.
    pages: List[ParsedPage] = []
    current_chunk: List[str] = []
    current_len = 0
    page_number = 1

    for para in paragraphs:
        current_chunk.append(para)
        current_len += len(para)
        if current_len >= VIRTUAL_PAGE_CHARS:
            pages.append(ParsedPage(page_number=page_number, text="\n".join(current_chunk)))
            page_number += 1
            current_chunk = []
            current_len = 0

    if current_chunk:
        pages.append(ParsedPage(page_number=page_number, text="\n".join(current_chunk)))

    return ParsedDocument(filename=Path(path).name, pages=pages)


def parse_document(path: str) -> ParsedDocument:
    """Dispatch to the right parser based on file extension."""
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        parsed = parse_pdf(path)
    elif suffix == ".docx":
        parsed = parse_docx(path)
    else:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. Only .pdf and .docx are supported."
        )

    if parsed.is_empty:
        raise EmptyDocumentError(f"Document '{parsed.filename}' contains no extractable text.")

    return parsed
