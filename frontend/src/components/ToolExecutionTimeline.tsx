import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { ToolExecutionEntry } from "@/types/api";

interface ToolExecutionTimelineProps {
  tools: ToolExecutionEntry[];
}

export default function ToolExecutionTimeline({ tools }: ToolExecutionTimelineProps) {
  if (tools.length === 0) {
    return <p className="text-sm text-slate-500">No tools were executed.</p>;
  }

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-stretch gap-0">
        {tools.map((entry, index) => {
          const success = entry.status === "success";
          const isLast = index === tools.length - 1;

          return (
            <div key={`${entry.tool}-${index}`} className="flex items-stretch">
              <motion.div
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.35 + index * 0.1, duration: 0.35 }}
                className={`relative flex w-52 flex-col rounded-xl border p-4 shadow-card ${
                  success
                    ? "border-risk-low/40 bg-navy-800/80"
                    : "border-risk-critical/40 bg-risk-critical/5"
                }`}
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <span className="font-mono text-xs font-semibold text-slate-100">{entry.tool}</span>
                  {success ? (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-risk-low" />
                  ) : (
                    <AlertCircle className="h-5 w-5 shrink-0 text-risk-critical" />
                  )}
                </div>
                {entry.reason ? (
                  <p className="mb-3 flex-1 text-[11px] leading-relaxed text-slate-500">{entry.reason}</p>
                ) : null}
                <div className="mt-auto flex items-center justify-between border-t border-navy-700 pt-2 text-[10px] uppercase tracking-wide text-slate-500">
                  <span className={success ? "text-risk-low" : "text-risk-critical"}>
                    {entry.status}
                  </span>
                  <span>{entry.duration_ms} ms</span>
                </div>
                {entry.error ? (
                  <p className="mt-2 text-[11px] text-risk-critical">{entry.error}</p>
                ) : null}
              </motion.div>

              {!isLast ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 + index * 0.1 }}
                  className="flex w-8 items-center justify-center self-center sm:w-12"
                  aria-hidden
                >
                  <div className="h-0.5 w-full bg-gradient-to-r from-risk-low/60 to-accent/40" />
                </motion.div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
