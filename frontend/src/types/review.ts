export type ClauseCategory =
  | "Payment"
  | "Confidentiality"
  | "Liability"
  | "Termination"
  | "Warranty"
  | "Intellectual Property"
  | "Indemnity"
  | "Dispute Resolution"
  | "Governing Law"
  | "Insurance"
  | "Data Protection"
  | "Other";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export type ReviewStatus =
  | "NO_MAJOR_DEVIATION"
  | "ATTENTION_REQUIRED"
  | "HUMAN_REVIEW_REQUIRED";

export interface Finding {
  finding_id: string;
  category: ClauseCategory;
  contract_requirement: string;
  reference_requirement: string;
  difference: string;
  risk_level: RiskLevel;
  contract_evidence: string;
  contract_page: number;
  reference_evidence: string;
  reference_page: number;
  is_missing_clause: boolean;
  validated: boolean;
  validation_notes?: string | null;
}

export interface ClassifiedClause {
  clause_id: string;
  category: ClauseCategory;
  text: string;
  page: number;
  confidence: number;
}

export interface ReviewReport {
  status: ReviewStatus;
  summary: string;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  findings: Finding[];
  clauses: ClassifiedClause[];
  disclaimer: string;
}

export interface ReviewResponse {
  id: string;
  status: string;
  result: ReviewReport;
  created_at: string;
}

export interface ReviewListItem {
  id: string;
  status: string;
  created_at: string;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  document_type: "contract" | "reference";
  created_at: string;
}
