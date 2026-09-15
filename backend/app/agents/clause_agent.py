"""
Clause Extraction + Classification Agent.

Primary mode:
    Uses OpenAI to classify document segments.

Fallback mode:
    If OpenAI is unavailable, quota is exhausted, or the structured
    response fails, deterministic keyword-based classification is used.

The fallback keeps the application usable during demonstrations and
development without changing the original source evidence.
"""

import logging
import re
from typing import List

from pydantic import BaseModel

from app.schemas.review import ClauseCategory, ClassifiedClause
from app.services.chunking import TextSegment
from app.services.llm_service import call_structured, LLMServiceError

logger = logging.getLogger(__name__)

BATCH_SIZE = 12


_SYSTEM_PROMPT = """You are a contract-clause classification assistant.

You will be given a numbered list of text segments extracted from a legal
document.

For EACH segment, assign the single most appropriate clause category from:

Payment
Confidentiality
Liability
Termination
Warranty
Intellectual Property
Indemnity
Dispute Resolution
Governing Law
Insurance
Data Protection
Other

Use Other for:
- document titles
- headers
- definitions-only text
- signatures
- boilerplate
- text that does not substantively belong to one of the listed categories

Do not modify the source text.

Return only:
segment_id
category
confidence

Confidence must be between 0 and 1.
"""


class _ClassificationItem(BaseModel):
    segment_id: str
    category: ClauseCategory
    confidence: float


class _ClassificationBatch(BaseModel):
    classifications: List[_ClassificationItem]


# ---------------------------------------------------------------------
# LOCAL FALLBACK CLASSIFIER
# ---------------------------------------------------------------------

_CATEGORY_RULES = {
    ClauseCategory.PAYMENT: [
        "payment",
        "invoice",
        "paid",
        "payable",
        "late payment",
        "interest",
    ],
    ClauseCategory.CONFIDENTIALITY: [
        "confidential",
        "confidential information",
        "disclose",
        "disclosure",
        "secret",
    ],
    ClauseCategory.LIABILITY: [
        "liability",
        "aggregate liability",
        "liable",
        "damages",
        "fees paid",
    ],
    ClauseCategory.TERMINATION: [
        "termination",
        "terminate",
        "prior written notice",
        "convenience",
    ],
    ClauseCategory.WARRANTY: [
        "warranty",
        "warrants",
        "warrant",
        "professional and workmanlike",
        "industry standards",
    ],
    ClauseCategory.INTELLECTUAL_PROPERTY: [
        "intellectual property",
        "deliverables",
        "owned by",
        "ownership",
        "license",
        "non-exclusive",
        "non-transferable",
        "internal business purposes",
    ],
    ClauseCategory.INDEMNITY: [
        "indemnity",
        "indemnify",
        "indemnification",
        "hold harmless",
        "third-party claims",
    ],
    ClauseCategory.DISPUTE_RESOLUTION: [
        "dispute resolution",
        "dispute",
        "good-faith negotiation",
        "negotiation",
        "senior representatives",
        "litigation",
    ],
    ClauseCategory.GOVERNING_LAW: [
        "governing law",
        "governed by",
        "laws of the state",
        "conflict of laws",
    ],
    ClauseCategory.INSURANCE: [
        "insurance",
        "commercial general liability insurance",
        "coverage",
        "per occurrence",
        "policy limit",
    ],
    ClauseCategory.DATA_PROTECTION: [
        "data protection",
        "privacy laws",
        "personal data",
        "data",
        "technical and organizational measures",
        "privacy",
    ],
}


def _normalize(text: str) -> str:
    """Normalize text for keyword matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _local_classify_segment(
    segment: TextSegment,
) -> _ClassificationItem:
    """
    Deterministically classify a segment using contract/legal keywords.

    The first category with strong matching evidence wins.
    """

    text = _normalize(segment.text)

    scores = {}

    for category, keywords in _CATEGORY_RULES.items():
        score = 0

        for keyword in keywords:
            if keyword in text:
                # Longer phrases are stronger evidence.
                if len(keyword.split()) >= 2:
                    score += 3
                else:
                    score += 1

        scores[category] = score

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score == 0:
        return _ClassificationItem(
            segment_id=segment.segment_id,
            category=ClauseCategory.OTHER,
            confidence=0.20,
        )

    # Convert rule score into a simple confidence score.
    if best_score >= 6:
        confidence = 0.95
    elif best_score >= 4:
        confidence = 0.90
    elif best_score >= 2:
        confidence = 0.82
    else:
        confidence = 0.70

    return _ClassificationItem(
        segment_id=segment.segment_id,
        category=best_category,
        confidence=confidence,
    )


def _local_classify_batch(
    segments: List[TextSegment],
) -> List[_ClassificationItem]:
    """Classify an entire batch locally."""
    return [_local_classify_segment(segment) for segment in segments]


# ---------------------------------------------------------------------
# LLM + FALLBACK
# ---------------------------------------------------------------------


def _classify_batch(
    segments: List[TextSegment],
) -> List[_ClassificationItem]:

    listing = "\n".join(
        f"[{segment.segment_id}] {segment.text}"
        for segment in segments
    )

    user_prompt = (
        "Segments to classify:\n\n"
        f"{listing}"
    )

    try:
        result = call_structured(
            _SYSTEM_PROMPT,
            user_prompt,
            _ClassificationBatch,
        )

        logger.info(
            "OpenAI classification succeeded for %d segment(s).",
            len(segments),
        )

        return result.classifications

    except LLMServiceError as exc:
        # IMPORTANT:
        # Do not convert everything to Other 0%.
        # Use deterministic local classification instead.
        logger.warning(
            "OpenAI classification unavailable. "
            "Using deterministic local fallback. Reason: %s",
            exc,
        )

        return _local_classify_batch(segments)


# ---------------------------------------------------------------------
# PUBLIC FUNCTION
# ---------------------------------------------------------------------


def extract_and_classify(
    segments: List[TextSegment],
) -> List[ClassifiedClause]:
    """
    Classify every document segment.

    Source text and page number always come directly from the parser.
    The classifier never generates replacement clause text.
    """

    classified: List[ClassifiedClause] = []

    for i in range(0, len(segments), BATCH_SIZE):

        batch = segments[i : i + BATCH_SIZE]

        results = _classify_batch(batch)

        result_by_id = {
            result.segment_id: result
            for result in results
        }

        for segment in batch:

            item = result_by_id.get(segment.segment_id)

            if item is None:
                # Extremely safe fallback.
                item = _local_classify_segment(segment)

            category = item.category

            confidence = max(
                0.0,
                min(1.0, float(item.confidence)),
            )

            classified.append(
                ClassifiedClause(
                    clause_id=segment.segment_id,
                    category=category,
                    text=segment.text,
                    page=segment.page,
                    confidence=confidence,
                )
            )

    logger.info(
        "Classified %d segment(s).",
        len(classified),
    )

    return classified