import { useEffect, useState } from "react";
import { Activity, Circle } from "lucide-react";

type HealthStatus = "loading" | "online" | "offline";

export default function Navbar() {
  const [status, setStatus] = useState<HealthStatus>("loading");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const response = await fetch("/api/health");
        if (!cancelled) {
          setStatus(response.ok ? "online" : "offline");
        }
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const statusConfig = {
    loading: { color: "text-slate-400", label: "Checking…", dot: "bg-slate-400" },
    online: { color: "text-risk-low", label: "Backend Online", dot: "bg-risk-low" },
    offline: { color: "text-risk-critical", label: "Backend Offline", dot: "bg-risk-critical" },
  }[status];

  return (
    <header className="flex h-16 items-center justify-between border-b border-navy-700 bg-navy-900/60 px-6 backdrop-blur-md">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">AI AML Agent</h1>
        <p className="text-xs text-slate-500">Anti-Money Laundering Intelligence Platform</p>
      </div>

      <div className="flex items-center gap-2 rounded-full border border-navy-700 bg-navy-800/80 px-4 py-2">
        <Activity className={`h-4 w-4 ${statusConfig.color}`} />
        <Circle className={`h-2 w-2 fill-current ${statusConfig.dot}`} />
        <span className={`text-sm font-medium ${statusConfig.color}`}>
          {statusConfig.label}
        </span>
      </div>
    </header>
  );
}
