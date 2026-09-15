"""Risk Detection Agent.

Two responsibilities:
1. Deterministic risk re-scoring for findings whose requirements are
   expressed as numbers of days (e.g. payment terms, notice periods, cure
   periods). Numeric comparison is done in plain Python - never by the LLM -
   satisfying the "use deterministic comparison for numerical requirements
   where practical" requirement.
2. Missing-clause detection: any category that appears in the reference
   policy but has no corresponding contract clause is flagged as a HIGH-risk
   missing-clause finding.
"""
import re
import uuid
from typing import Dict, List, Optional, Set

from app.schemas.review import ClassifiedClause, ClauseCategory, Finding, RiskLevel

_DAY_PATTERN = re.compile(r"(\d+)\s*(?:calendar\s+|business\s+)?days?", re.IGNORECASE)


def _extract_days(text: str) -> Optional[int]:
    match = _DAY_PATTERN.search(text)
    return int(match.group(1)) if match else None


def _risk_from_day_gap(gap: int) -> RiskLevel:
    if gap <= 7:
        return RiskLevel.LOW
    if gap <= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def apply_deterministic_rules(findings: List[Finding]) -> List[Finding]:
    """Where both sides of a finding mention a day-count, override the LLM's
    risk_level with a deterministic threshold based on the actual numeric
    gap. This directly implements the spec's worked example (30 -> 90 days
    is a 60-day gap => HIGH)."""
    for finding in findings:
        ref_days = _extract_days(finding.reference_requirement)
        contract_days = _extract_days(finding.contract_requirement)

        if ref_days is not None and contract_days is not None:
            gap = abs(contract_days - ref_days)
            finding.risk_level = _risk_from_day_gap(gap)
            finding.difference = (
                f"{gap} day(s) {'beyond' if contract_days > ref_days else 'short of'} "
                f"policy (reference: {ref_days} days, contract: {contract_days} days)."
            )

    return findings


def detect_missing_clauses(
    contract_clauses: List[ClassifiedClause],
    reference_clauses: List[ClassifiedClause],
) -> List[Finding]:
    contract_categories: Set[ClauseCategory] = {
        c.category for c in contract_clauses if c.category != ClauseCategory.OTHER
    }

    # Group reference clauses by category so we can cite the strongest evidence.
    reference_by_category: Dict[ClauseCategory, ClassifiedClause] = {}
    for clause in reference_clauses:
        if clause.category == ClauseCategory.OTHER:
            continue
        existing = reference_by_category.get(clause.category)
        if existing is None or clause.confidence > existing.confidence:
            reference_by_category[clause.category] = clause

    findings: List[Finding] = []
    for category, ref_clause in reference_by_category.items():
        if category in contract_categories:
            continue
        findings.append(
            Finding(
                finding_id=f"finding-{uuid.uuid4().hex[:8]}",
                category=category,
                contract_requirement="Not present in the contract.",
                reference_requirement=ref_clause.text[:300],
                difference=f"The contract has no {category.value} clause, which the reference policy requires.",
                risk_level=RiskLevel.HIGH,
                contract_evidence="No matching clause found in the contract.",
                contract_page=0,
                reference_evidence=ref_clause.text[:300],
                reference_page=ref_clause.page,
                is_missing_clause=True,
                validated=False,
            )
        )

    return findings
