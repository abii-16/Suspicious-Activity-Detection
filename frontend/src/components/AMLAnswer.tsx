import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import RiskBadge from "@/components/RiskBadge";
import AgentDebugPanel from "@/components/AgentDebugPanel";
import type { QueryResponse } from "@/types/api";

interface AMLAnswerProps {
  data: QueryResponse;
}

export default function AMLAnswer({ data }: AMLAnswerProps) {
  const [showDebug, setShowDebug] = useState(false);
  const text = data.natural_response || data.explanation || data.recommendation;

  return (
    <div className="space-y-3">
      {/* Natural language answer */}
      <div className="prose prose-invert prose-sm max-w-none text-slate-200">
        <ReactMarkdown
          components={{
            p: ({ children }) => (
              <p className="mb-2 leading-relaxed text-slate-200">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-slate-100">{children}</strong>
            ),
            ul: ({ children }) => (
              <ul className="my-2 ml-4 space-y-1 text-slate-200">{children}</ul>
            ),
            li: ({ children }) => (
              <li className="flex items-start gap-2">
                <ChevronRight className="mt-1 h-3 w-3 shrink-0 text-accent" />
                <span>{children}</span>
              </li>
            ),
          }}
        >
          {text}
        </ReactMarkdown>
      </div>

      {/* Risk badge inline if available */}
      {data.risk_level && data.risk_level !== "LOW" ? (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Risk Level:</span>
          <RiskBadge level={data.risk_level} size="sm" />
          {data.risk_score != null ? (
            <span className="font-mono text-xs text-slate-500">
              score {data.risk_score.toFixed(4)}
            </span>
          ) : null}
        </div>
      ) : null}

      {/* Collapsible debug panel */}
      <div>
        <button
          type="button"
          onClick={() => setShowDebug((v) => !v)}
          className="flex items-center gap-1.5 text-[11px] text-slate-600 transition hover:text-slate-400"
        >
          {showDebug ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          Show Agent Reasoning
        </button>

        <AnimatePresence>
          {showDebug ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="mt-3 overflow-hidden"
            >
              <AgentDebugPanel data={data} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
