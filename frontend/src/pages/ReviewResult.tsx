import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import RiskCard from "../components/RiskCard";
import ClauseTable from "../components/ClauseTable";
import { getReview, extractErrorMessage } from "../services/api";
import type { ReviewResponse } from "../types/review";

const STATUS_STYLES: Record<string, string> = {
  NO_MAJOR_DEVIATION: "text-risk-low bg-risk-low-bg",
  ATTENTION_REQUIRED: "text-risk-medium bg-risk-medium-bg",
  HUMAN_REVIEW_REQUIRED: "text-risk-high bg-risk-high-bg",
};

const STATUS_LABELS: Record<string, string> = {
  NO_MAJOR_DEVIATION: "No major deviation",
  ATTENTION_REQUIRED: "Attention required",
  HUMAN_REVIEW_REQUIRED: "Human review required",
};

export default function ReviewResult() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"ALL" | "HIGH" | "MEDIUM" | "LOW">("ALL");

  useEffect(() => {
    if (!reviewId) return;
    getReview(reviewId)
      .then(setReview)
      .catch((err) => setError(extractErrorMessage(err, "Could not load this review.")))
      .finally(() => setLoading(false));
  }, [reviewId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-paper">
        <Navbar />
        <p className="mx-auto max-w-5xl px-6 py-10 text-sm text-ink-soft">Loading review…</p>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-paper">
        <Navbar />
        <div className="mx-auto max-w-5xl px-6 py-10">
          <p className="text-sm text-risk-high">{error ?? "Review not found."}</p>
          <Link to="/dashboard" className="mt-4 inline-block text-sm text-brass underline">
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  const { result } = review;
  const findings = result.findings.filter((f) => filter === "ALL" || f.risk_level === filter);

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Link to="/dashboard" className="text-sm text-ink-soft hover:text-ink">
          ← Back to dashboard
        </Link>

        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-serif text-2xl font-semibold text-ink">Review result</h1>
            <p className="mt-1 text-sm text-ink-soft">{result.summary}</p>
          </div>
          <span className={`rounded px-3 py-1.5 text-sm font-medium ${STATUS_STYLES[result.status]}`}>
            {STATUS_LABELS[result.status] ?? result.status}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-4">
          <SummaryStat label="High risk" value={result.high_risk_count} tone="text-risk-high" />
          <SummaryStat label="Medium risk" value={result.medium_risk_count} tone="text-risk-medium" />
          <SummaryStat label="Low risk" value={result.low_risk_count} tone="text-risk-low" />
        </div>

        <div className="mt-10">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-serif text-xl font-semibold text-ink">Findings</h2>
            <div className="flex gap-1 rounded-md border border-line p-1 text-xs">
              {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => setFilter(level)}
                  className={`rounded px-3 py-1 transition-colors ${
                    filter === level ? "bg-ink text-white" : "text-ink-soft hover:text-ink"
                  }`}
                >
                  {level === "ALL" ? "All" : level.charAt(0) + level.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {findings.map((finding) => (
              <RiskCard key={finding.finding_id} finding={finding} />
            ))}
            {findings.length === 0 && (
              <p className="rounded-md border border-dashed border-line bg-white px-6 py-10 text-center text-sm text-ink-soft">
                No findings at this risk level.
              </p>
            )}
          </div>
        </div>

        <div className="mt-10">
          <h2 className="mb-4 font-serif text-xl font-semibold text-ink">Extracted clauses</h2>
          <ClauseTable clauses={result.clauses} />
        </div>

        <p className="mt-10 border-t border-line pt-6 text-xs text-ink-soft">{result.disclaimer}</p>
      </main>
    </div>
  );
}

function SummaryStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-md border border-line bg-white px-5 py-4">
      <p className={`font-serif text-3xl font-semibold ${tone}`}>{value}</p>
      <p className="mt-1 text-sm text-ink-soft">{label}</p>
    </div>
  );
}
