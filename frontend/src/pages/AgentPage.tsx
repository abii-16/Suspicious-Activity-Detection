import { FormEvent, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Radio, Send, Terminal } from "lucide-react";
import AgentQueryResult from "@/components/agent/AgentQueryResult";
import ChatMessage from "@/components/ChatMessage";
import TypingIndicator from "@/components/TypingIndicator";
import { query as runAgentQuery, apiErrorMessage } from "@/services/api";
import type { QueryResponse } from "@/types/api";

const SUGGESTED_QUERIES = [
  "Find structuring patterns in the last 30 days",
  "Show top 20 most suspicious transactions",
  "Analyze the dataset and summarize fraud percentage",
  "Find accounts with 10+ transactions under $10,000",
];

interface Turn {
  id: string;
  query: string;
  response?: QueryResponse;
  error?: string;
}

export default function AgentPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function runQuery(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const turnId = crypto.randomUUID();
    setTurns((prev) => [...prev, { id: turnId, query: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const response = await runAgentQuery(trimmed);
      setTurns((prev) =>
        prev.map((t) => (t.id === turnId ? { ...t, response } : t)),
      );
    } catch (err) {
      const message = apiErrorMessage(err);
      setTurns((prev) =>
        prev.map((t) => (t.id === turnId ? { ...t, error: message } : t)),
      );
    } finally {
      setLoading(false);
      requestAnimationFrame(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
      });
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void runQuery(input);
  }

  return (
    <div className="relative flex min-h-[calc(100vh-4rem)] flex-col bg-[radial-gradient(ellipse_at_top,_rgba(59,130,246,0.08)_0%,_transparent_50%)]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:24px_24px] opacity-40" />

      <div className="relative border-b border-navy-700/80 bg-navy-900/40 px-4 py-3 backdrop-blur-sm sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-accent/30 bg-accent/10">
              <Radio className="h-5 w-5 text-accent-light" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100">SOC Investigation Console</p>
              <p className="text-xs text-slate-500">Natural language AML agent · live tool orchestration</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-risk-low/30 bg-risk-low/10 px-3 py-1 text-xs font-medium text-risk-low sm:flex">
            <span className="h-2 w-2 animate-pulse rounded-full bg-risk-low" />
            Agent Ready
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="relative flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-5xl space-y-8">
          {turns.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl border border-dashed border-navy-600 bg-navy-900/40 p-8 text-center"
            >
              <Terminal className="mx-auto mb-4 h-10 w-10 text-accent" />
              <h2 className="text-lg font-semibold text-slate-100">Start an AML investigation</h2>
              <p className="mx-auto mt-2 max-w-lg text-sm text-slate-400">
                Ask in plain English. The agent will detect intent, build an execution plan, run tools,
                and return risk assessments with full audit trail for judges.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {SUGGESTED_QUERIES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => void runQuery(q)}
                    className="rounded-lg border border-navy-600 bg-navy-800/80 px-3 py-2 text-left text-xs text-slate-300 transition hover:border-accent/40 hover:text-accent-light"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          ) : null}

          <AnimatePresence mode="popLayout">
            {turns.map((turn) => (
              <motion.div
                key={turn.id}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <ChatMessage role="user">
                  <p className="text-sm font-medium">{turn.query}</p>
                  <p className="mt-1 text-[10px] uppercase tracking-widest text-slate-500">User Query</p>
                </ChatMessage>

                {!turn.response && !turn.error && loading && turns[turns.length - 1]?.id === turn.id ? (
                  <ChatMessage role="assistant">
                    <TypingIndicator />
                  </ChatMessage>
                ) : null}

                {turn.error ? (
                  <ChatMessage role="assistant">
                    <div className="flex items-start gap-2 text-risk-critical">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                      <div>
                        <p className="text-sm font-medium">Execution failed</p>
                        <p className="mt-1 text-xs text-slate-400">{turn.error}</p>
                      </div>
                    </div>
                  </ChatMessage>
                ) : null}

                {turn.response ? (
                  <ChatMessage role="assistant">
                    <AgentQueryResult data={turn.response} />
                  </ChatMessage>
                ) : null}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      <div className="relative border-t border-navy-700 bg-navy-900/80 px-4 py-4 backdrop-blur-md sm:px-6">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-5xl gap-3">
          <div className="relative flex-1">
            <Terminal className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Find structuring patterns in the last 30 days"
              disabled={loading}
              className="w-full rounded-xl border border-navy-600 bg-navy-950 py-3 pl-10 pr-4 text-sm text-slate-100 placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60"
            />
          </div>
          <motion.button
            type="submit"
            disabled={loading || !input.trim()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white shadow-glow transition disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            Run
          </motion.button>
        </form>
      </div>
    </div>
  );
}
