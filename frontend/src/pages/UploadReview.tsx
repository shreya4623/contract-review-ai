import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import FileUpload from "../components/FileUpload";
import { uploadDocument, createReview, extractErrorMessage } from "../services/api";

const STEPS = [
  "Extracting document",
  "Identifying clauses",
  "Comparing policies",
  "Detecting risks",
  "Validating evidence",
];

type StepStatus = "done" | "active" | "pending";

export default function UploadReview() {
  const navigate = useNavigate();
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  function stepStatus(index: number): StepStatus {
    if (index < activeStep) return "done";
    if (index === activeStep) return "active";
    return "pending";
  }

  async function handleStartReview() {
    if (!contractFile || !referenceFile) return;
    setError(null);
    setIsProcessing(true);
    setActiveStep(0);

    // Advance the visual step indicator while the backend workflow runs.
    // The backend executes the pipeline as a single synchronous call; this
    // gives the user a sense of progress through the documented stages.
    timerRef.current = setInterval(() => {
      setActiveStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 1800);

    try {
      const contractDoc = await uploadDocument(contractFile, "contract");
      const referenceDoc = await uploadDocument(referenceFile, "reference");
      const review = await createReview(contractDoc.id, referenceDoc.id);

      if (timerRef.current) clearInterval(timerRef.current);
      setActiveStep(STEPS.length);
      navigate(`/reviews/${review.id}`);
    } catch (err) {
      if (timerRef.current) clearInterval(timerRef.current);
      setIsProcessing(false);
      setError(extractErrorMessage(err, "The review could not be completed. Please try again."));
    }
  }

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="font-serif text-2xl font-semibold text-ink">New review</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Upload the contract to review and the reference policy to compare it against.
        </p>

        <div className="mt-8 space-y-6 rounded-md border border-line bg-white p-6">
          <FileUpload
            label="Contract"
            helperText="The agreement you want reviewed."
            file={contractFile}
            onFileSelected={setContractFile}
          />
          <FileUpload
            label="Reference policy"
            helperText="Your organization's template or policy to compare against."
            file={referenceFile}
            onFileSelected={setReferenceFile}
          />

          {error && <p className="text-sm text-risk-high">{error}</p>}

          <button
            onClick={handleStartReview}
            disabled={!contractFile || !referenceFile || isProcessing}
            className="w-full rounded bg-ink py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {isProcessing ? "Running review…" : "Run review"}
          </button>
        </div>

        {isProcessing && (
          <div className="mt-6 rounded-md border border-line bg-white p-6">
            <p className="mb-4 text-sm font-medium text-ink">Processing</p>
            <ul className="space-y-3">
              {STEPS.map((step, index) => {
                const status = stepStatus(index);
                return (
                  <li key={step} className="flex items-center gap-3 text-sm">
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                        status === "done"
                          ? "bg-risk-low text-white"
                          : status === "active"
                          ? "border-2 border-brass text-brass"
                          : "border border-line text-ink-soft"
                      }`}
                    >
                      {status === "done" ? "✓" : status === "active" ? "●" : "○"}
                    </span>
                    <span className={status === "pending" ? "text-ink-soft" : "text-ink"}>{step}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <p className="mt-6 text-xs text-ink-soft">
          This system provides contract-review support and does not constitute professional legal advice.
        </p>
      </main>
    </div>
  );
}
