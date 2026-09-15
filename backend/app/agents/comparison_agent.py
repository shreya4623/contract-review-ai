"""
Policy Comparison Agent.

This agent compares contract clauses against reference-policy clauses.

Important design:
- Numeric requirements are checked deterministically FIRST.
- This ensures cases such as 90 days vs 30 days are always detected correctly.
- OpenAI is used for non-numeric/substantive comparisons when available.
- If OpenAI is unavailable, a deterministic fallback is used.
- Evidence always comes directly from the uploaded documents.
"""

import logging
import re
import uuid
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.review import (
    ClauseCategory,
    ClassifiedClause,
    Finding,
    RiskLevel,
)

from app.services.vector_store import RetrievalHit
from app.services.llm_service import (
    call_structured,
    LLMServiceError,
)

logger = logging.getLogger(__name__)


# ============================================================
# LLM PROMPT
# ============================================================

_SYSTEM_PROMPT = """
You are a contract-review comparison assistant.

Compare one CONTRACT clause against one REFERENCE POLICY clause.

Rules:

1. Identify only substantive deviations.
2. Pay close attention to:
   - number of days
   - notice periods
   - payment periods
   - percentages
   - monetary limits
   - time periods
3. If the contract is consistent with the policy, set has_deviation=false.
4. contract_evidence MUST come directly from the contract text.
5. reference_evidence MUST come directly from the reference text.
6. Never invent evidence.
7. Clearly explain the difference.
8. risk_level must be LOW, MEDIUM, or HIGH.
"""


# ============================================================
# STRUCTURED RESULT
# ============================================================

class ComparisonResult(BaseModel):
    has_deviation: bool
    contract_requirement: str
    reference_requirement: str
    difference: str
    risk_level: RiskLevel
    contract_evidence: str
    reference_evidence: str


# ============================================================
# TEXT HELPERS
# ============================================================

def _normalize(text: str) -> str:
    """Normalize whitespace and lowercase text."""

    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


# ============================================================
# DAY EXTRACTION
# ============================================================

def _extract_days(text: str) -> Optional[int]:
    """
    Extract a number followed by 'day' or 'days'.

    Examples:

        30 days
        90 days
        15 calendar days
        10 business days

    Also handles numbers written as words for the sample documents.
    """

    # First try numeric form.
    match = re.search(
        r"(\d+)\s*(?:calendar\s+|business\s+)?days?",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    # Handle common written numbers.
    number_words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
        "hundred": 100,
    }

    # Search for phrases such as "ninety (90) days".
    for word, value in number_words.items():
        pattern = rf"\b{word}\b\s*(?:\(\s*\d+\s*\))?\s*days?"

        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):
            return value

    return None


# ============================================================
# PERCENTAGE EXTRACTION
# ============================================================

def _extract_percentages(text: str) -> List[float]:
    """Extract percentages such as 1%, 1.5%, 10%."""

    matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*%",
        text,
    )

    return [
        float(value)
        for value in matches
    ]


# ============================================================
# YEAR EXTRACTION
# ============================================================

def _extract_years(text: str) -> Optional[int]:
    match = re.search(
        r"(\d+)\s*years?",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return None


# ============================================================
# MONTH EXTRACTION
# ============================================================

def _extract_months(text: str) -> Optional[int]:
    match = re.search(
        r"(\d+)\s*months?",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return None


# ============================================================
# DAY RISK
# ============================================================

def _risk_from_day_gap(
    gap: int,
) -> RiskLevel:
    """
    Determine risk from a day-count difference.

    <= 7 days  -> LOW
    <= 30 days -> MEDIUM
    > 30 days  -> HIGH

    Example:
        90 vs 30 = 60-day gap = HIGH
    """

    if gap <= 7:
        return RiskLevel.LOW

    if gap <= 30:
        return RiskLevel.MEDIUM

    return RiskLevel.HIGH


# ============================================================
# DETERMINISTIC NUMERIC COMPARISON
# ============================================================

def _deterministic_numeric_compare(
    contract_clause: ClassifiedClause,
    reference_hit: RetrievalHit,
) -> Optional[ComparisonResult]:
    """
    Compare numeric requirements before using the LLM.

    This is deliberately executed FIRST.

    Example:

        Contract:
        Payment shall be made within ninety (90) days.

        Reference:
        Payment must be completed within thirty (30) days.

    Result:

        90 days vs 30 days
        60 additional days
        HIGH risk
    """

    contract_text = contract_clause.text
    reference_text = reference_hit.segment.text

    # --------------------------------------------------------
    # DAY COMPARISON
    # --------------------------------------------------------

    contract_days = _extract_days(
        contract_text
    )

    reference_days = _extract_days(
        reference_text
    )

    if (
        contract_days is not None
        and reference_days is not None
        and contract_days != reference_days
    ):

        gap = abs(
            contract_days - reference_days
        )

        if contract_days > reference_days:

            difference = (
                f"The contract requires payment or performance "
                f"within {contract_days} days, while the reference "
                f"policy requires {reference_days} days. "
                f"The contract allows {gap} additional day(s)."
            )

        else:

            difference = (
                f"The contract specifies {contract_days} days, "
                f"while the reference policy specifies "
                f"{reference_days} days. "
                f"This represents a {gap}-day deviation."
            )

        logger.info(
            "Deterministic day comparison detected deviation: "
            "%s days vs %s days",
            contract_days,
            reference_days,
        )

        return ComparisonResult(
            has_deviation=True,

            contract_requirement=contract_text,

            reference_requirement=reference_text,

            difference=difference,

            risk_level=_risk_from_day_gap(
                gap
            ),

            contract_evidence=contract_text,

            reference_evidence=reference_text,
        )

    # --------------------------------------------------------
    # PERCENTAGE COMPARISON
    # --------------------------------------------------------

    contract_percentages = _extract_percentages(
        contract_text
    )

    reference_percentages = _extract_percentages(
        reference_text
    )

    if (
        contract_percentages
        and reference_percentages
    ):

        contract_percentage = (
            contract_percentages[0]
        )

        reference_percentage = (
            reference_percentages[0]
        )

        if (
            contract_percentage
            != reference_percentage
        ):

            difference = abs(
                contract_percentage
                - reference_percentage
            )

            risk = (
                RiskLevel.MEDIUM
                if difference >= 0.5
                else RiskLevel.LOW
            )

            return ComparisonResult(
                has_deviation=True,

                contract_requirement=contract_text,

                reference_requirement=reference_text,

                difference=(
                    f"The contract specifies "
                    f"{contract_percentage}%, while the "
                    f"reference policy specifies "
                    f"{reference_percentage}%, a difference "
                    f"of {difference} percentage point(s)."
                ),

                risk_level=risk,

                contract_evidence=contract_text,

                reference_evidence=reference_text,
            )

    # No numeric difference.
    return None


# ============================================================
# LOCAL FALLBACK
# ============================================================

def _local_compare(
    contract_clause: ClassifiedClause,
    reference_hit: RetrievalHit,
) -> ComparisonResult:
    """
    Local fallback when OpenAI is unavailable.

    Numeric comparison is attempted first.
    """

    numeric_result = _deterministic_numeric_compare(
        contract_clause,
        reference_hit,
    )

    if numeric_result is not None:
        return numeric_result

    contract_text = contract_clause.text
    reference_text = reference_hit.segment.text

    contract_lower = _normalize(
        contract_text
    )

    reference_lower = _normalize(
        reference_text
    )

    category = contract_clause.category

    # --------------------------------------------------------
    # CONFIDENTIALITY YEARS
    # --------------------------------------------------------

    if category == ClauseCategory.CONFIDENTIALITY:

        contract_years = _extract_years(
            contract_text
        )

        reference_years = _extract_years(
            reference_text
        )

        if (
            contract_years is not None
            and reference_years is not None
            and contract_years != reference_years
        ):

            return ComparisonResult(
                has_deviation=True,

                contract_requirement=contract_text,

                reference_requirement=reference_text,

                difference=(
                    f"The contract provides confidentiality "
                    f"protection for {contract_years} years, "
                    f"while the reference policy specifies "
                    f"{reference_years} years."
                ),

                risk_level=RiskLevel.MEDIUM,

                contract_evidence=contract_text,

                reference_evidence=reference_text,
            )

    # --------------------------------------------------------
    # LIABILITY MONTHS
    # --------------------------------------------------------

    if category == ClauseCategory.LIABILITY:

        contract_months = _extract_months(
            contract_text
        )

        reference_months = _extract_months(
            reference_text
        )

        if (
            contract_months is not None
            and reference_months is not None
            and contract_months != reference_months
        ):

            gap = abs(
                contract_months
                - reference_months
            )

            return ComparisonResult(
                has_deviation=True,

                contract_requirement=contract_text,

                reference_requirement=reference_text,

                difference=(
                    f"The contract specifies a "
                    f"{contract_months}-month liability "
                    f"period, while the reference policy "
                    f"specifies {reference_months} months. "
                    f"This represents a {gap}-month deviation."
                ),

                risk_level=RiskLevel.MEDIUM,

                contract_evidence=contract_text,

                reference_evidence=reference_text,
            )

    # --------------------------------------------------------
    # EXACT MATCH
    # --------------------------------------------------------

    if contract_lower == reference_lower:

        return ComparisonResult(
            has_deviation=False,

            contract_requirement=contract_text,

            reference_requirement=reference_text,

            difference="No material deviation detected.",

            risk_level=RiskLevel.LOW,

            contract_evidence=contract_text,

            reference_evidence=reference_text,
        )

    # --------------------------------------------------------
    # CONSERVATIVE DEFAULT
    # --------------------------------------------------------

    return ComparisonResult(
        has_deviation=False,

        contract_requirement=contract_text,

        reference_requirement=reference_text,

        difference=(
            "No material deviation detected by "
            "deterministic comparison."
        ),

        risk_level=RiskLevel.LOW,

        contract_evidence=contract_text,

        reference_evidence=reference_text,
    )


# ============================================================
# MAIN COMPARISON FUNCTION
# ============================================================

def compare_clause(
    contract_clause: ClassifiedClause,
    reference_hit: RetrievalHit,
) -> Optional[ComparisonResult]:
    """
    Compare one contract clause with a reference clause.

    IMPORTANT ORDER:

    1. Deterministic numeric comparison
    2. OpenAI comparison
    3. Local fallback

    This guarantees that important numeric deviations such as
    90 vs 30 days are not missed or incorrectly replaced by
    a percentage-only difference.
    """

    # ========================================================
    # STEP 1 — ALWAYS CHECK NUMBERS LOCALLY
    # ========================================================

    numeric_result = _deterministic_numeric_compare(
        contract_clause,
        reference_hit,
    )

    if numeric_result is not None:

        logger.info(
            "Using deterministic numeric comparison for clause %s.",
            contract_clause.clause_id,
        )

        return numeric_result

    # ========================================================
    # STEP 2 — TRY OPENAI
    # ========================================================

    user_prompt = f"""
Category:
{contract_clause.category.value}

CONTRACT clause:
\"\"\"{contract_clause.text}\"\"\"

REFERENCE POLICY clause:
\"\"\"{reference_hit.segment.text}\"\"\"

Compare the contract against the reference policy.
"""

    try:

        result = call_structured(
            _SYSTEM_PROMPT,
            user_prompt,
            ComparisonResult,
        )

        logger.info(
            "OpenAI comparison succeeded for clause %s.",
            contract_clause.clause_id,
        )

        return result

    except LLMServiceError as exc:

        logger.warning(
            "OpenAI comparison unavailable for clause %s. "
            "Using local fallback. Reason: %s",
            contract_clause.clause_id,
            exc,
        )

        # ====================================================
        # STEP 3 — LOCAL FALLBACK
        # ====================================================

        return _local_compare(
            contract_clause,
            reference_hit,
        )


# ============================================================
# BUILD FINDINGS
# ============================================================

def build_findings(
    contract_clauses: List[ClassifiedClause],
    retrieval_map: dict,
) -> List[Finding]:
    """
    Build Finding objects from contract clauses and
    corresponding reference-policy matches.
    """

    findings: List[Finding] = []

    for clause in contract_clauses:

        # Skip unclassified/irrelevant clauses.
        if clause.category == ClauseCategory.OTHER:
            continue

        # Get retrieved reference clause.
        hit: Optional[RetrievalHit] = (
            retrieval_map.get(
                clause.clause_id
            )
        )

        if hit is None:
            continue

        # Compare contract vs reference.
        result = compare_clause(
            clause,
            hit,
        )

        if result is None:
            continue

        if not result.has_deviation:
            continue

        finding = Finding(
            finding_id=(
                f"finding-{uuid.uuid4().hex[:8]}"
            ),

            category=clause.category,

            contract_requirement=(
                result.contract_requirement
            ),

            reference_requirement=(
                result.reference_requirement
            ),

            difference=result.difference,

            risk_level=result.risk_level,

            contract_evidence=(
                result.contract_evidence
            ),

            contract_page=clause.page,

            reference_evidence=(
                result.reference_evidence
            ),

            reference_page=hit.segment.page,

            is_missing_clause=False,

            validated=False,
        )

        findings.append(
            finding
        )

    logger.info(
        "Comparison agent generated %d finding(s).",
        len(findings),
    )

    return findings