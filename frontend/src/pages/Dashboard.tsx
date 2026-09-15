import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import { listReviews, extractErrorMessage } from "../services/api";
import type { ReviewListItem } from "../types/review";

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

export default function Dashboard() {
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listReviews()
      .then(setReviews)
      .catch((err) => setError(extractErrorMessage(err, "Could not load reviews.")))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-2xl font-semibold text-ink">Reviews</h1>
            <p className="mt-1 text-sm text-ink-soft">Past contract reviews for your account.</p>
          </div>
          <Link
            to="/upload"
            className="rounded bg-ink px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            New review
          </Link>
        </div>

        {loading && <p className="text-sm text-ink-soft">Loading…</p>}
        {error && <p className="text-sm text-risk-high">{error}</p>}

        {!loading && !error && reviews.length === 0 && (
          <div className="rounded-md border border-dashed border-line bg-white px-6 py-16 text-center">
            <p className="text-ink">No reviews yet.</p>
            <p className="mt-1 text-sm text-ink-soft">Upload a contract and reference policy to get started.</p>
            <Link
              to="/upload"
              className="mt-4 inline-block rounded bg-ink px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              Start a review
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {reviews.map((review) => (
            <Link
              key={review.id}
              to={`/reviews/${review.id}`}
              className="flex items-center justify-between rounded-md border border-line bg-white px-5 py-4 transition-colors hover:border-brass-light"
            >
              <div>
                <p className="font-medium text-ink">Review {review.id.slice(0, 8)}</p>
                <p className="text-sm text-ink-soft">
                  {new Date(review.created_at).toLocaleString()}
                </p>
              </div>
              <span className={`rounded px-3 py-1 text-xs font-medium ${STATUS_STYLES[review.status] ?? ""}`}>
                {STATUS_LABELS[review.status] ?? review.status}
              </span>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
