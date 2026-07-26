import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Search, UserSearch } from "lucide-react";
import LLMReportCard from "@/components/LLMReportCard";
import RecommendationCard from "@/components/RecommendationCard";
import RiskBadge from "@/components/RiskBadge";
import { SkeletonCard, SkeletonTable } from "@/components/SkeletonLoader";
import { apiErrorMessage, getCustomer } from "@/services/api";
import type { CustomerResponse } from "@/types/api";

export default function CustomerLookupPage() {
  const [customerId, setCustomerId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CustomerResponse | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    const id = parseInt(customerId, 10);
    if (Number.isNaN(id) || id < 0) {
      setError("Enter a valid customer ID.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await getCustomer(id);
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
        <h2 className="text-2xl font-bold text-slate-100">Customer Lookup</h2>
        <p className="mt-1 text-sm text-slate-400">
          Search by customer account ID for risk profile and LLM analysis
        </p>
      </div>

      <form onSubmit={handleSearch} className="card flex flex-wrap items-end gap-4">
        <div className="min-w-[200px] flex-1">
          <label htmlFor="customer-id" className="mb-2 block text-xs font-medium uppercase tracking-widest text-slate-500">
            Customer ID
          </label>
          <div className="relative">
            <UserSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              id="customer-id"
              type="number"
              min={0}
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="e.g. 436419"
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
          Search
        </motion.button>
      </form>

      {error ? (
        <div className="card flex items-center gap-3 border-risk-critical/40 text-risk-critical">
          <AlertTriangle className="h-5 w-5" />
          <p className="text-sm">{error}</p>
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
          <SkeletonTable />
        </div>
      ) : null}

      {result?.found ? (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Transactions", value: result.transaction_count?.toLocaleString() },
              { label: "Total Sent", value: `$${result.total_amount_sent?.toLocaleString()}` },
              { label: "Total Received", value: `$${result.total_amount_received?.toLocaleString()}` },
              { label: "High Risk %", value: `${result.high_risk_pct}%` },
            ].map((stat) => (
              <div key={stat.label} className="card">
                <p className="text-xs uppercase tracking-widest text-slate-500">{stat.label}</p>
                <p className="mt-2 text-xl font-bold text-slate-100">{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="card flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">Customer Summary</p>
              <p className="mt-1 font-mono text-lg text-accent-light">Account #{result.customer_id}</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs text-slate-500">Max Risk Score</p>
                <p className="font-mono text-lg text-slate-100">{result.max_risk_score}</p>
              </div>
              <RiskBadge level={result.risk_level ?? "LOW"} size="lg" pulse />
            </div>
          </div>

          <RecommendationCard recommendation={result.recommendation ?? "Continue monitoring."} />

          <div className="card overflow-hidden p-0">
            <div className="border-b border-navy-700 px-5 py-3">
              <h3 className="text-sm font-semibold text-slate-200">Recent Transactions</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead>
                  <tr className="border-b border-navy-700 text-xs uppercase text-slate-500">
                    <th className="px-5 py-2.5">Amount Paid</th>
                    <th className="px-5 py-2.5">Risk Level</th>
                    <th className="px-5 py-2.5">Final Score</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.recent_transactions ?? []).slice(0, 10).map((tx, i) => (
                    <tr key={i} className="border-b border-navy-800/80">
                      <td className="px-5 py-2.5 text-slate-300">
                        {String((tx as Record<string, unknown>)["Amount Paid"] ?? "—")}
                      </td>
                      <td className="px-5 py-2.5">
                        <RiskBadge
                          level={String((tx as Record<string, unknown>)["Risk Level"] ?? "LOW")}
                          size="sm"
                        />
                      </td>
                      <td className="px-5 py-2.5 font-mono text-slate-400">
                        {String((tx as Record<string, unknown>)["Final Risk Score"] ?? "—")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {result.llm_analysis ? (
            <LLMReportCard report={result.llm_analysis} title="LLM Customer Analysis" />
          ) : null}
        </motion.div>
      ) : null}
    </div>
  );
}
