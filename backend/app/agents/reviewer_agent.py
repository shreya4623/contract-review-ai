"""Reviewer / Validation Agent.

This is the final safeguard against hallucinated evidence: every finding's
`contract_evidence` and `reference_evidence` strings are checked against the
ACTUAL text of the source clause they claim to come from. A finding is only
marked `validated=True` if both sides pass. Findings that fail validation are
still returned (never silently dropped) but flagged `HUMAN_REVIEW_REQUIRED`
material and excluded from automated risk counts, so a human always sees them.
"""
import difflib
import re
from typing import Dict, List

from app.schemas.review import ClassifiedClause, Finding, ReviewStatus, RiskLevel

SIMILARITY_THRESHOLD = 0.55


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _best_sentence_similarity(evidence: str, source_text: str) -> float:
    """Highest similarity ratio between the evidence string and any
    substring-sized window of the source text."""
    norm_evidence = _normalize(evidence)
    norm_source = _normalize(source_text)

    if not norm_evidence:
        return 0.0
    if norm_evidence in norm_source:
        return 1.0

    # Compare against sentence-like chunks of the source for a fairer ratio
    # than comparing against the whole (much longer) source text.
    sentences = re.split(r"(?<=[.;])\s+", source_text)
    best = 0.0
    for sentence in sentences:
        ratio = difflib.SequenceMatcher(None, norm_evidence, _normalize(sentence)).ratio()
        best = max(best, ratio)

    # Also compare against the whole text in case the evidence spans sentences.
    best = max(best, difflib.SequenceMatcher(None, norm_evidence, norm_source).ratio())
    return best


def validate_findings(
    findings: List[Finding],
    contract_clauses_by_page: Dict[int, str],
    reference_clauses_by_page: Dict[int, str],
) -> List[Finding]:
    for finding in findings:
        if finding.is_missing_clause:
            # Contract-side "evidence" is a fixed absence statement, not a quote -
            # nothing to verify there. Only check the reference-side quote.
            ref_source = reference_clauses_by_page.get(finding.reference_page, "")
            ref_score = _best_sentence_similarity(finding.reference_evidence, ref_source)
            finding.validated = ref_score >= SIMILARITY_THRESHOLD
            finding.validation_notes = (
                "Reference evidence verified against source page."
                if finding.validated
                else "Could not verify reference evidence against the source document; flagged for human review."
            )
            continue

        contract_source = contract_clauses_by_page.get(finding.contract_page, "")
        reference_source = reference_clauses_by_page.get(finding.reference_page, "")

        contract_score = _best_sentence_similarity(finding.contract_evidence, contract_source)
        reference_score = _best_sentence_similarity(finding.reference_evidence, reference_source)

        if contract_score < SIMILARITY_THRESHOLD:
            # Fall back to the full clause text rather than an unverifiable quote.
            finding.contract_evidence = contract_source[:400] or finding.contract_evidence
        if reference_score < SIMILARITY_THRESHOLD:
            finding.reference_evidence = reference_source[:400] or finding.reference_evidence

        finding.validated = contract_score >= SIMILARITY_THRESHOLD and reference_score >= SIMILARITY_THRESHOLD
        finding.validation_notes = (
            "Both evidence quotes verified against source documents."
            if finding.validated
            else "Evidence quote could not be exactly matched; original clause text substituted for safety."
        )

    return findings


def determine_overall_status(findings: List[Finding]) -> ReviewStatus:
    unvalidated = [f for f in findings if not f.validated]
    high = [f for f in findings if f.risk_level == RiskLevel.HIGH]
    medium = [f for f in findings if f.risk_level == RiskLevel.MEDIUM]

    if unvalidated or high:
        return ReviewStatus.HUMAN_REVIEW_REQUIRED
    if medium:
        return ReviewStatus.ATTENTION_REQUIRED
    return ReviewStatus.NO_MAJOR_DEVIATION


def build_clause_lookup(clauses: List[ClassifiedClause]) -> Dict[int, str]:
    """Map page -> concatenated clause text, used to verify evidence quotes."""
    lookup: Dict[int, str] = {}
    for clause in clauses:
        lookup[clause.page] = lookup.get(clause.page, "") + " " + clause.text
    return lookup
