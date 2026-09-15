import type { ClassifiedClause } from "../types/review";

export default function ClauseTable({ clauses }: { clauses: ClassifiedClause[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-white">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-paper text-xs uppercase tracking-wide text-ink-soft">
            <th className="px-4 py-3 font-medium">Category</th>
            <th className="px-4 py-3 font-medium">Page</th>
            <th className="px-4 py-3 font-medium">Clause text</th>
            <th className="px-4 py-3 font-medium">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {clauses.map((clause) => (
            <tr key={clause.clause_id} className="border-b border-line last:border-0">
              <td className="px-4 py-3 font-medium text-ink">{clause.category}</td>
              <td className="px-4 py-3 text-ink-soft">{clause.page}</td>
              <td className="max-w-md px-4 py-3 text-ink-soft">
                <span className="line-clamp-2">{clause.text}</span>
              </td>
              <td className="px-4 py-3 text-ink-soft">{Math.round(clause.confidence * 100)}%</td>
            </tr>
          ))}
          {clauses.length === 0 && (
            <tr>
              <td colSpan={4} className="px-4 py-6 text-center text-ink-soft">
                No clauses were extracted from the contract.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
