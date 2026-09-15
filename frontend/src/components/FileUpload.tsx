import { useRef, useState } from "react";

interface FileUploadProps {
  label: string;
  helperText: string;
  file: File | null;
  onFileSelected: (file: File) => void;
}

const ACCEPTED_TYPES = [".pdf", ".docx"];

export default function FileUpload({ label, helperText, file, onFileSelected }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function validateAndSet(candidate: File) {
    const lower = candidate.name.toLowerCase();
    if (!ACCEPTED_TYPES.some((ext) => lower.endsWith(ext))) {
      setError("Only PDF or DOCX files are accepted.");
      return;
    }
    setError(null);
    onFileSelected(candidate);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) validateAndSet(dropped);
  }

  return (
    <div>
      <p className="mb-1 font-serif text-base font-semibold text-ink">{label}</p>
      <p className="mb-3 text-sm text-ink-soft">{helperText}</p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-10 text-center transition-colors ${
          isDragging ? "border-brass bg-brass/5" : "border-line hover:border-brass-light"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const selected = e.target.files?.[0];
            if (selected) validateAndSet(selected);
          }}
        />
        {file ? (
          <div>
            <p className="font-medium text-ink">{file.name}</p>
            <p className="mt-1 text-xs text-ink-soft">{(file.size / 1024).toFixed(0)} KB &middot; click to replace</p>
          </div>
        ) : (
          <div>
            <p className="text-ink">Drop a file here, or click to browse</p>
            <p className="mt-1 text-xs text-ink-soft">PDF or DOCX, up to 15MB</p>
          </div>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-risk-high">{error}</p>}
    </div>
  );
}
