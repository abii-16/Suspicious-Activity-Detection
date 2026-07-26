import { motion } from "framer-motion";
import { Brain, CheckCircle2 } from "lucide-react";

interface Thought {
  thought: string;
  conclusion: string;
}

interface PlannerReasoningProps {
  reasoning: Thought[];
  intentLabel?: string;
}

export default function PlannerReasoning({ reasoning, intentLabel }: PlannerReasoningProps) {
  if (!reasoning?.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-accent/20 bg-navy-950/60 p-4"
    >
      <div className="mb-3 flex items-center gap-2 border-b border-navy-700 pb-2">
        <Brain className="h-4 w-4 text-accent" />
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
          Planner Reasoning
          {intentLabel ? (
            <span className="ml-2 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 font-mono text-[10px] text-accent-light">
              {intentLabel}
            </span>
          ) : null}
        </h3>
      </div>

      <div className="space-y-3">
        {reasoning.map((t, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.07 }}
            className="flex gap-3"
          >
            <div className="flex flex-col items-center gap-1">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-accent/40 bg-accent/10 font-mono text-[10px] font-bold text-accent-light">
                {i + 1}
              </div>
              {i < reasoning.length - 1 && (
                <div className="w-px flex-1 bg-navy-700" />
              )}
            </div>
            <div className="pb-2">
              <p className="text-xs text-slate-400">{t.thought}</p>
              <div className="mt-1 flex items-start gap-1.5">
                <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-risk-low" />
                <p className="text-xs font-medium text-slate-200">{t.conclusion}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
