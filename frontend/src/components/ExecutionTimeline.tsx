import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import type { PlanStepDetail } from "@/types/api";

interface ExecutionTimelineProps {
  steps: string[];
  details?: PlanStepDetail[];
}

export default function ExecutionTimeline({ steps, details }: ExecutionTimelineProps) {
  if (steps.length === 0) {
    return (
      <p className="text-sm text-slate-500">No execution plan generated.</p>
    );
  }

  const reasonFor = (tool: string, index: number) =>
    details?.find((d) => d.step === tool)?.reason ??
    details?.[index]?.reason ??
    "Planned agent step";

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-start gap-0 px-1">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          return (
            <div key={`${step}-${index}`} className="flex items-start">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.12, duration: 0.4 }}
                className="flex w-44 flex-col items-center text-center sm:w-52"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: index * 0.12 + 0.08, type: "spring", stiffness: 260 }}
                  className="relative z-10 flex h-11 w-11 items-center justify-center rounded-full border-2 border-accent bg-navy-900 font-mono text-sm font-bold text-accent-light shadow-glow"
                >
                  {index + 1}
                </motion.div>
                <p className="mt-3 font-mono text-xs font-semibold text-accent-light">{step}</p>
                <p className="mt-1 line-clamp-3 px-1 text-[11px] leading-snug text-slate-500">
                  {reasonFor(step, index)}
                </p>
              </motion.div>

              {!isLast ? (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: index * 0.12 + 0.2, duration: 0.45 }}
                  className="mt-5 flex w-16 items-center origin-left sm:w-24"
                  aria-hidden
                >
                  <div className="h-0.5 flex-1 bg-gradient-to-r from-accent to-accent/30" />
                  <ChevronRight className="-ml-1 h-4 w-4 shrink-0 text-accent/60" />
                </motion.div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
