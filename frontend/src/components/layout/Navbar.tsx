import { useEffect, useState } from "react";
import { Activity, Brain, Circle, Cpu } from "lucide-react";
import { getHealth } from "@/services/api";

type HealthStatus = "loading" | "online" | "offline";

export default function Navbar() {
  const [status, setStatus] = useState<HealthStatus>("loading");
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [llmAvailable, setLlmAvailable] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const health = await getHealth();
        if (!cancelled) {
          setStatus("online");
          setModelsLoaded(health.models_loaded);
          setLlmAvailable(Boolean(health.llm_available));
        }
      } catch {
        if (!cancelled) {
          setStatus("offline");
          setModelsLoaded(false);
          setLlmAvailable(false);
        }
      }
    }

    void checkHealth();
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
    <header className="flex h-16 flex-wrap items-center justify-between gap-3 border-b border-navy-700 bg-navy-900/60 px-4 py-2 backdrop-blur-md sm:px-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">AI AML Agent</h1>
        <p className="text-xs text-slate-500">Anti-Money Laundering Intelligence Platform</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 rounded-full border border-navy-700 bg-navy-800/80 px-3 py-1.5">
          <Cpu className={`h-3.5 w-3.5 ${modelsLoaded ? "text-risk-low" : "text-slate-500"}`} />
          <span className="text-xs text-slate-400">
            Models {modelsLoaded ? "Loaded" : "—"}
          </span>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-navy-700 bg-navy-800/80 px-3 py-1.5">
          <Brain className={`h-3.5 w-3.5 ${llmAvailable ? "text-accent-light" : "text-slate-500"}`} />
          <span className="text-xs text-slate-400">
            LLM {llmAvailable ? "Groq Ready" : "Fallback"}
          </span>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-navy-700 bg-navy-800/80 px-4 py-2">
          <Activity className={`h-4 w-4 ${statusConfig.color}`} />
          <Circle className={`h-2 w-2 fill-current ${statusConfig.dot}`} />
          <span className={`text-sm font-medium ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
        </div>
      </div>
    </header>
  );
}
