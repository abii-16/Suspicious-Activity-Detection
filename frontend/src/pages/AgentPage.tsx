import { FormEvent, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Bot, Send, Shield, User } from "lucide-react";
import AMLAnswer from "@/components/AMLAnswer";
import TypingIndicator from "@/components/TypingIndicator";
import { query as runAgentQuery, apiErrorMessage } from "@/services/api";
import type { QueryResponse } from "@/types/api";

const SUGGESTED = [
  "Analyze the dataset",
  "Show top 20 suspicious transactions",
  "Find structuring patterns",
  "Investigate transaction 0",
  "Find accounts with rapid transactions",
];

interface Turn {
  id: string;
  query: string;
  response?: QueryResponse;
  error?: string;
}

// What we send back to the backend for context resolution
type HistoryEntry = {
  query: string;
  entities?: Record<string, unknown>;
  natural_response?: string;
};

export default function AgentPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keep a compact history for context resolution
  const historyRef = useRef<HistoryEntry[]>([]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function runQuery(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const id = crypto.randomUUID();
    setTurns((prev) => [...prev, { id, query: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const response = await runAgentQuery(trimmed, historyRef.current);

      // Persist this turn in history for follow-up context
      historyRef.current = [
        ...historyRef.current.slice(-6), // keep last 6 turns
        {
          query: trimmed,
          entities: response.entities as Record<string, unknown>,
          natural_response: response.natural_response,
        },
      ];

      setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, response } : t)));
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, error: apiErrorMessage(err) } : t)),
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void runQuery(input);
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col bg-navy-950">
      {/* Subtle grid background */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.02)_1px,transparent_1px)] bg-[size:32px_32px]" />

      {/* Chat area */}
      <div className="relative flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-3xl space-y-6">

          {/* Empty state */}
          {turns.length === 0 && !loading ? (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center pt-16 text-center"
            >
              <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-accent/30 bg-accent/10">
                <Shield className="h-8 w-8 text-accent-light" />
              </div>
              <h2 className="text-xl font-semibold text-slate-100">AML Investigation Assistant</h2>
              <p className="mt-2 max-w-md text-sm text-slate-400">
                Ask anything about your transaction data. I'll investigate, analyze patterns,
                and explain risk assessments in plain English.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-2">
                {SUGGESTED.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => void runQuery(q)}
                    className="rounded-lg border border-navy-600 bg-navy-800/60 px-4 py-2 text-sm text-slate-300 transition hover:border-accent/50 hover:bg-navy-800 hover:text-slate-100"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          ) : null}

          {/* Conversation turns */}
          <AnimatePresence initial={false}>
            {turns.map((turn, idx) => (
              <motion.div
                key={turn.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-4"
              >
                {/* User message */}
                <div className="flex justify-end gap-3">
                  <div className="max-w-lg rounded-2xl rounded-tr-sm border border-accent/25 bg-accent/10 px-4 py-3 text-sm text-slate-100">
                    {turn.query}
                  </div>
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-accent/30 bg-accent/20">
                    <User className="h-4 w-4 text-accent-light" />
                  </div>
                </div>

                {/* Assistant message or loading */}
                <div className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-navy-600 bg-navy-800">
                    <Bot className="h-4 w-4 text-accent" />
                  </div>
                  <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-navy-700 bg-navy-900/90 px-4 py-3">
                    {/* Loading */}
                    {!turn.response && !turn.error && loading && idx === turns.length - 1 ? (
                      <TypingIndicator />
                    ) : null}

                    {/* Error */}
                    {turn.error ? (
                      <div className="flex items-start gap-2 text-risk-critical">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                        <div>
                          <p className="text-sm font-medium">Something went wrong</p>
                          <p className="mt-0.5 text-xs text-slate-400">{turn.error}</p>
                        </div>
                      </div>
                    ) : null}

                    {/* Answer */}
                    {turn.response ? (
                      <AMLAnswer data={turn.response} />
                    ) : null}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Scroll anchor */}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="relative border-t border-navy-700 bg-navy-900/80 px-4 py-4 backdrop-blur-md sm:px-6">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-end gap-3">
          <div className="flex-1">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void runQuery(input);
                }
              }}
              placeholder="Ask about transactions, customers, patterns…"
              disabled={loading}
              autoComplete="off"
              className="w-full rounded-xl border border-navy-600 bg-navy-950 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/50 disabled:opacity-60"
            />
          </div>
          <motion.button
            type="submit"
            disabled={loading || !input.trim()}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent text-white shadow-glow transition disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </motion.button>
        </form>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] text-slate-600">
          AI AML Agent · Powered by Hybrid ML + Groq LLaMA 3.3
        </p>
      </div>
    </div>
  );
}
