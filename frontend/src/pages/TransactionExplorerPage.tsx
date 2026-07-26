import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Search } from "lucide-react";
import ExplanationCard from "@/components/ExplanationCard";
import LLMReportCard from "@/components/LLMReportCard";
import RecommendationCard from "@/components/RecommendationCard";
import RiskBadge from "@/components/RiskBadge";
import { SkeletonCard } from "@/components/SkeletonLoader";
import { apiErrorMessage, getTransaction } from "@/services/api";
import type { TransactionResponse } from "@/types/api";

export default function TransactionExplorerPage() {
  const [transactionId, setTransactionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TransactionResponse | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    const id = parseInt(transactionId, 10);
    if (Number.isNaN(id) || id < 0) {
      setError("Enter a valid transaction ID.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await getTransaction(id);
      setResult(data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-container space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Transaction Explorer</h2>
        <p className="mt-1 text-sm text-slate-400">
          Inspect hybrid ML scores, rule explanations, and LLM analysis
        </p>
      </div>

      <form onSubmit={handleSearch} className="card flex flex-wrap items-end gap-4">
        <div className="min-w-[200px] flex-1">
          <label htmlFor="transaction-id" className="mb-2 block text-xs font-medium uppercase tracking-widest text-slate-500">
            Transaction ID
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              id="transaction-id"
              type="number"
              min={0}
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              placeholder="e.g. 0"
              className="w-full rounded-xl border border-navy-600 bg-navy-950 py-3 pl-10 pr-4 text-sm text-slate-100 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
        </div>
        <motion.button
          type="submit"
          disabled={loading}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          <Search className="h-4 w-4" />
          Investigate
        </motion.button>
      </form>

      {error ? (
        <div className="card flex items-center gap-3 border-risk-critical/40 text-risk-critical">
          <AlertTriangle className="h-5 w-5" />
          <p className="text-sm">{error}</p>
        </div>
      ) : null}

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : null}

      {result?.found ? (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="card flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">Transaction</p>
              <p className="mt-1 font-mono text-lg text-accent-light">#{result.transaction_id}</p>
              <p className="mt-1 text-sm text-slate-400">
                Account {result.account} → Counterparty {result.counterparty}
              </p>
            </div>
            <RiskBadge level={result.risk_level ?? "LOW"} size="lg" pulse />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Amount Paid", value: `$${result.amount_paid?.toLocaleString()}` },
              { label: "Hybrid Score", value: result.risk_score },
              { label: "XGBoost Score", value: result.xgb_score },
              {
                label: "Isolation Forest",
                value: result.isolation_anomaly ? "Anomaly" : "Normal",
              },
            ].map((stat) => (
              <div key={stat.label} className="card">
                <p className="text-xs uppercase tracking-widest text-slate-500">{stat.label}</p>
                <p className="mt-2 text-xl font-bold text-slate-100">{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="card">
            <h3 className="mb-3 text-sm font-semibold text-slate-200">Transaction Details</h3>
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[
                ["AML Pattern", result.aml_pattern],
                ["From Bank", result.from_bank],
                ["To Bank", result.to_bank],
                ["Payment Currency", result.payment_currency],
                ["Payment Format", result.payment_format],
                ["Actual Label", result.actual_label === 1 ? "Laundering" : "Clean"],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg border border-navy-700 bg-navy-950/50 p-3">
                  <dt className="text-[10px] uppercase tracking-widest text-slate-500">{label}</dt>
                  <dd className="mt-1 text-sm text-slate-200">{value ?? "—"}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <RecommendationCard recommendation={result.recommendation ?? "Continue monitoring."} />
            <ExplanationCard explanation={(result.reasons ?? []).join(" | ")} />
          </div>

          {result.llm_analysis ? (
            <LLMReportCard report={result.llm_analysis} title="LLM Transaction Analysis" />
          ) : null}
        </motion.div>
      ) : null}
    </div>
  );
}
