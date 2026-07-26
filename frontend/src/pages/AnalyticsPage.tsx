import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="page-container">
      <div className="card flex flex-col items-center justify-center gap-3 py-24 text-center">
        <BarChart3 className="h-12 w-12 text-accent" />
        <h2 className="text-xl font-semibold text-slate-100">Analytics</h2>
        <p className="max-w-md text-sm text-slate-400">
          Dataset overview, fraud statistics, and distribution charts from EDA.
        </p>
      </div>
    </div>
  );
}
