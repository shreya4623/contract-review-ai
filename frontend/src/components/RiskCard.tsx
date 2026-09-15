import type { Finding } from "../types/review";
import EvidenceCard from "./EvidenceCard";

const RISK_STYLES: Record<string, { text: string; bg: string; label: string }> = {
  HIGH: { text: "text-risk-high", bg: "bg-risk-high-bg", label: "High risk" },
  MEDIUM: { text: "text-risk-medium", bg: "bg-risk-medium-bg", label: "Medium risk" },
  LOW: { text: "text-risk-low", bg: "bg-risk-low-bg", label: "Low risk" },
};

export default function RiskCard({ finding }: { finding: Finding }) {
  const risk = RISK_STYLES[finding.risk_level];

  return (
    <div className="rounded-md border border-line bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3">
        <div className="flex items-center gap-3">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${risk.bg} ${risk.text}`}>
            {risk.label}
          </span>
          <span className="font-serif text-base font-semibold text-ink">{finding.category}</span>
          {finding.is_missing_clause && (
            <span className="rounded border border-line px-2 py-0.5 text-xs text-ink-soft">
              Missing clause
            </span>
          )}
        </div>
        <span
          className={`text-xs ${
            finding.validated ? "text-risk-low" : "text-risk-medium"
          }`}
        >
          {finding.validated ? "Evidence verified" : "Needs human review"}
        </span>
      </div>

      <div className="grid gap-4 px-5 py-4 sm:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-soft">Contract requirement</p>
          <p className="mt-1 text-sm text-ink">{finding.contract_requirement}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-soft">Reference requirement</p>
          <p className="mt-1 text-sm text-ink">{finding.reference_requirement}</p>
        </div>
      </div>

      <div className="border-t border-line px-5 py-4">
        <p className="text-xs uppercase tracking-wide text-ink-soft">Difference</p>
        <p className="mt-1 text-sm text-ink">{finding.difference}</p>
      </div>

      <div className="grid gap-4 border-t border-line px-5 py-4 sm:grid-cols-2">
        <EvidenceCard label="Contract evidence" text={finding.contract_evidence} page={finding.contract_page} />
        <EvidenceCard label="Reference evidence" text={finding.reference_evidence} page={finding.reference_page} />
      </div>

      {finding.validation_notes && (
        <div className="border-t border-line bg-paper px-5 py-2.5 text-xs text-ink-soft">
          {finding.validation_notes}
        </div>
      )}
    </div>
  );
}
