import { LayoutDashboard } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="page-container">
      <div className="card flex flex-col items-center justify-center gap-3 py-24 text-center">
        <LayoutDashboard className="h-12 w-12 text-accent" />
        <h2 className="text-xl font-semibold text-slate-100">Dashboard</h2>
        <p className="max-w-md text-sm text-slate-400">
          Risk overview, charts, and top suspicious transactions will appear here.
        </p>
      </div>
    </div>
  );
}
