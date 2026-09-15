"""LangGraph workflow implementing the required pipeline:

START -> parse -> extract_classify -> retrieve -> compare -> detect_risk
       -> reviewer_validate -> END

Each node receives and returns a partial WorkflowState dict, which is
LangGraph's standard state-reducer pattern. Any exception raised inside a
node is caught by the node itself and stored in `state["error"]`, and every
downstream node short-circuits if `error` is already set - this keeps a
single bad document from crashing the whole request and instead surfaces a
clean error to the API layer.
"""
import logging
from typing import Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from app.agents.parser_agent import parse_and_segment
from app.agents.clause_agent import extract_and_classify
from app.agents.comparison_agent import build_findings
from app.agents.risk_agent import apply_deterministic_rules, detect_missing_clauses
from app.agents.reviewer_agent import (
    validate_findings,
    determine_overall_status,
    build_clause_lookup,
)
from app.schemas.review import ClassifiedClause, ClauseCategory, Finding, ReviewReport, RiskLevel
from app.services.vector_store import ReferenceVectorStore, RetrievalHit
from app.services.chunking import TextSegment

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    contract_path: str
    reference_path: str
    contract_segments: List[TextSegment]
    reference_segments: List[TextSegment]
    contract_clauses: List[ClassifiedClause]
    reference_clauses: List[ClassifiedClause]
    retrieval_map: Dict[str, RetrievalHit]
    findings: List[Finding]
    report: Optional[ReviewReport]
    error: Optional[str]


def node_parse(state: WorkflowState) -> WorkflowState:
    try:
        contract_segments = parse_and_segment(state["contract_path"])
        reference_segments = parse_and_segment(state["reference_path"])
        return {"contract_segments": contract_segments, "reference_segments": reference_segments}
    except Exception as exc:  # noqa: BLE001 - surface any parse error to the API cleanly
        logger.exception("Parsing failed")
        return {"error": f"Document parsing failed: {exc}"}


def node_extract_classify(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return {}
    try:
        contract_clauses = extract_and_classify(state["contract_segments"])
        reference_clauses = extract_and_classify(state["reference_segments"])
        return {"contract_clauses": contract_clauses, "reference_clauses": reference_clauses}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Classification failed")
        return {"error": f"Clause classification failed: {exc}"}


def node_retrieve(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return {}
    try:
        reference_clauses = [c for c in state["reference_clauses"] if c.category != ClauseCategory.OTHER]
        reference_segments = [
            TextSegment(segment_id=c.clause_id, text=c.text, page=c.page) for c in reference_clauses
        ]
        store = ReferenceVectorStore(reference_segments)

        retrieval_map: Dict[str, RetrievalHit] = {}
        # Prefer same-category matches; fall back to best global match.
        by_category: Dict[ClauseCategory, List[TextSegment]] = {}
        for seg, clause in zip(reference_segments, reference_clauses):
            by_category.setdefault(clause.category, []).append(seg)

        for clause in state["contract_clauses"]:
            if clause.category == ClauseCategory.OTHER:
                continue

            same_category_segments = by_category.get(clause.category, [])
            if same_category_segments:
                local_store = ReferenceVectorStore(same_category_segments)
                hits = local_store.search(clause.text, top_k=1)
            else:
                hits = store.search(clause.text, top_k=1)

            if hits:
                retrieval_map[clause.clause_id] = hits[0]

        return {"retrieval_map": retrieval_map}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Retrieval failed")
        return {"error": f"Policy retrieval failed: {exc}"}


def node_compare(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return {}
    try:
        findings = build_findings(state["contract_clauses"], state["retrieval_map"])
        return {"findings": findings}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Comparison failed")
        return {"error": f"Policy comparison failed: {exc}"}


def node_detect_risk(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return {}
    try:
        findings = apply_deterministic_rules(state["findings"])
        missing = detect_missing_clauses(state["contract_clauses"], state["reference_clauses"])
        return {"findings": findings + missing}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Risk detection failed")
        return {"error": f"Risk detection failed: {exc}"}


def node_reviewer_validate(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return {}
    try:
        contract_lookup = build_clause_lookup(state["contract_clauses"])
        reference_lookup = build_clause_lookup(state["reference_clauses"])
        findings = validate_findings(state["findings"], contract_lookup, reference_lookup)

        status = determine_overall_status(findings)
        high = sum(1 for f in findings if f.risk_level == RiskLevel.HIGH)
        medium = sum(1 for f in findings if f.risk_level == RiskLevel.MEDIUM)
        low = sum(1 for f in findings if f.risk_level == RiskLevel.LOW)

        summary = (
            f"Reviewed {len(state['contract_clauses'])} contract clause(s) against the reference "
            f"policy. Found {len(findings)} issue(s): {high} high, {medium} medium, {low} low risk."
        )

        report = ReviewReport(
            status=status,
            summary=summary,
            high_risk_count=high,
            medium_risk_count=medium,
            low_risk_count=low,
            findings=findings,
            clauses=state["contract_clauses"],
        )
        return {"report": report, "findings": findings}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reviewer validation failed")
        return {"error": f"Reviewer validation failed: {exc}"}


def build_workflow():
    graph = StateGraph(WorkflowState)

    graph.add_node("parse", node_parse)
    graph.add_node("extract_classify", node_extract_classify)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("compare", node_compare)
    graph.add_node("detect_risk", node_detect_risk)
    graph.add_node("reviewer_validate", node_reviewer_validate)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "extract_classify")
    graph.add_edge("extract_classify", "retrieve")
    graph.add_edge("retrieve", "compare")
    graph.add_edge("compare", "detect_risk")
    graph.add_edge("detect_risk", "reviewer_validate")
    graph.add_edge("reviewer_validate", END)

    return graph.compile()


_compiled_workflow = None


def get_workflow():
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = build_workflow()
    return _compiled_workflow


def run_review_workflow(contract_path: str, reference_path: str) -> WorkflowState:
    """Entry point used by the /reviews API route."""
    workflow = get_workflow()
    initial_state: WorkflowState = {"contract_path": contract_path, "reference_path": reference_path}
    final_state = workflow.invoke(initial_state)
    return final_state
