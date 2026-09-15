"""Structured schemas shared by the LangGraph agents and the API layer.

These models are the contract between the LLM output and the rest of the
system: every LLM call that must return structured data is instructed to
produce JSON that validates against one of these models.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ClauseCategory(str, Enum):
    PAYMENT = "Payment"
    CONFIDENTIALITY = "Confidentiality"
    LIABILITY = "Liability"
    TERMINATION = "Termination"
    WARRANTY = "Warranty"
    INTELLECTUAL_PROPERTY = "Intellectual Property"
    INDEMNITY = "Indemnity"
    DISPUTE_RESOLUTION = "Dispute Resolution"
    GOVERNING_LAW = "Governing Law"
    INSURANCE = "Insurance"
    DATA_PROTECTION = "Data Protection"
    OTHER = "Other"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ReviewStatus(str, Enum):
    NO_MAJOR_DEVIATION = "NO_MAJOR_DEVIATION"
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class TextSpan(BaseModel):
    """A snippet of evidence tied back to a specific page of a specific document."""
    text: str = Field(description="Exact supporting sentence copied verbatim from the source document.")
    page: int = Field(description="1-indexed page number the text was found on.")


class ExtractedClause(BaseModel):
    """A single clause pulled out of a document during extraction."""
    clause_id: str
    category: ClauseCategory
    text: str
    page: int


class ClassifiedClause(ExtractedClause):
    """A clause after the classification pass confirms/refines its category."""
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class RetrievedReferenceMatch(BaseModel):
    """Result of FAISS similarity search: the reference clause(s) most relevant
    to a given contract clause."""
    contract_clause_id: str
    reference_clause_id: str
    reference_text: str
    reference_page: int
    similarity_score: float


class Finding(BaseModel):
    """A single detected issue. This is the primary traceability unit required
    by the project spec - every field below must be populated."""
    finding_id: str
    category: ClauseCategory
    contract_requirement: str
    reference_requirement: str
    difference: str
    risk_level: RiskLevel
    contract_evidence: str
    contract_page: int
    reference_evidence: str
    reference_page: int
    is_missing_clause: bool = False
    validated: bool = False
    validation_notes: Optional[str] = None


class MissingClauseFinding(BaseModel):
    """A category required by the reference policy but absent from the contract."""
    category: ClauseCategory
    reference_requirement: str
    reference_evidence: str
    reference_page: int
    risk_level: RiskLevel = RiskLevel.HIGH


class ReviewReport(BaseModel):
    """The final artifact returned to the frontend and persisted to the DB."""
    status: ReviewStatus
    summary: str
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    findings: List[Finding]
    clauses: List[ClassifiedClause]
    disclaimer: str = (
        "This system provides contract-review support and does not constitute "
        "professional legal advice."
    )


class ReviewCreateRequest(BaseModel):
    contract_document_id: str
    reference_document_id: str


class ReviewResponse(BaseModel):
    id: str
    status: str
    result: ReviewReport
    created_at: str


class ReviewListItem(BaseModel):
    id: str
    status: str
    created_at: str
