export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card animate-pulse space-y-3">
      <div className="h-3 w-1/3 rounded bg-navy-700" />
      <div className="h-8 w-1/2 rounded bg-navy-700" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 rounded bg-navy-800" style={{ width: `${90 - i * 10}%` }} />
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="card animate-pulse">
      <div className="mb-4 h-3 w-1/4 rounded bg-navy-700" />
      <div className="flex h-48 items-end gap-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 rounded-t bg-navy-700"
            style={{ height: `${30 + (i % 4) * 15}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="card animate-pulse space-y-3">
      <div className="h-3 w-1/4 rounded bg-navy-700" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="h-4 flex-1 rounded bg-navy-800" />
          <div className="h-4 w-16 rounded bg-navy-800" />
          <div className="h-4 w-20 rounded bg-navy-800" />
        </div>
      ))}
    </div>
  );
}
