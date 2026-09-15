export default function EvidenceCard({
  label,
  text,
  page,
}: {
  label: string;
  text: string;
  page: number;
}) {
  return (
    <div className="rounded border border-line bg-paper px-3 py-2.5">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-ink-soft">{label}</p>
        <span className="text-xs text-brass">{page > 0 ? `Page ${page}` : "Not found"}</span>
      </div>
      <p className="mt-1.5 font-serif text-sm italic text-ink">&ldquo;{text}&rdquo;</p>
    </div>
  );
}
