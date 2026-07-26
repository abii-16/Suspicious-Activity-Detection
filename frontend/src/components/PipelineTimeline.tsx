import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

const PIPELINE_LABELS: Record<string, string> = {
  planner: "Planner",
  router: "Router",
  hybrid_ml: "Hybrid ML",
  llm: "LLM",
  response: "Final Response",
  filter_data: "Filter Data",
  run_eda: "EDA",
  generate_risk: "Risk Engine",
  generate_explanation: "Explainability",
  rule_engine: "Rule Engine",
  customer_summary: "Customer",
  transaction_summary: "Transaction",
  top_suspicious_transactions: "Top Suspicious",
};

interface PipelineTimelineProps {
  steps: string[];
  executedTools?: string[];
}

export default function PipelineTimeline({ steps, executedTools = [] }: PipelineTimelineProps) {
  if (steps.length === 0) return null;

  const executedSet = new Set(executedTools.map((t) => t.replace("llm_investigation_report", "llm")));

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-start gap-0 px-1">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          const label = PIPELINE_LABELS[step] ?? step;
          const isExecuted =
            step === "planner" ||
            step === "router" ||
            step === "hybrid_ml" ||
            step === "llm" ||
            step === "response" ||
            executedSet.has(step);

          return (
            <div key={`${step}-${index}`} className="flex items-start">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.35 }}
                className="flex w-36 flex-col items-center text-center sm:w-40"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: index * 0.08 + 0.05, type: "spring", stiffness: 260 }}
                  className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 font-mono text-xs font-bold shadow-glow ${
                    isExecuted
                      ? "border-accent bg-accent/20 text-accent-light"
                      : "border-navy-600 bg-navy-900 text-slate-500"
                  }`}
                >
                  {index + 1}
                </motion.div>
                <p
                  className={`mt-2 font-mono text-[11px] font-semibold ${
                    isExecuted ? "text-accent-light" : "text-slate-500"
                  }`}
                >
                  {label}
                </p>
                <p className="mt-0.5 text-[10px] text-slate-600">
                  {isExecuted ? "executed" : "planned"}
                </p>
              </motion.div>

              {!isLast ? (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: index * 0.08 + 0.12, duration: 0.35 }}
                  className="mt-5 flex w-10 items-center origin-left sm:w-14"
                  aria-hidden
                >
                  <div
                    className={`h-0.5 flex-1 ${
                      isExecuted ? "bg-gradient-to-r from-accent to-accent/30" : "bg-navy-700"
                    }`}
                  />
                  <ChevronRight className="-ml-1 h-3.5 w-3.5 shrink-0 text-accent/40" />
                </motion.div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
