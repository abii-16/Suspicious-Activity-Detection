import type { ComponentType, ReactNode } from "react";
import { motion } from "framer-motion";
import {
  Clock,
  Crosshair,
  Filter,
  Layers,
  MessageSquare,
  Sparkles,
  Target,
  Timer,
} from "lucide-react";
import ExecutionTimeline from "@/components/ExecutionTimeline";
import ExplanationCard from "@/components/ExplanationCard";
import RecommendationCard from "@/components/RecommendationCard";
import RiskBadge from "@/components/RiskBadge";
import ToolExecutionTimeline from "@/components/ToolExecutionTimeline";
import type { QueryResponse, SuspiciousTransactionRow } from "@/types/api";

interface AgentQueryResultProps {
  data: QueryResponse;
}

function SocSection({
  title,
  icon: Icon,
  children,
  delay = 0,
}: {
  title: string;
  icon: ComponentType<{ className?: string }>;
  children: ReactNode;
  delay?: number;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      className="rounded-xl border border-navy-700/80 bg-navy-950/60 p-4"
    >
      <div className="mb-3 flex items-center gap-2 border-b border-navy-700/80 pb-2">
        <Icon className="h-4 w-4 text-accent" />
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">{title}</h3>
      </div>
      {children}
    </motion.section>
  );
}

function extractTransactions(results: Record<string, unknown>): SuspiciousTransactionRow[] {
  const top = results.top_suspicious_transactions as
    | { transactions?: SuspiciousTransactionRow[] }
    | undefined;
  if (top?.transactions?.length) return top.transactions;

  const risk = results.generate_risk as { transactions?: SuspiciousTransactionRow[] } | undefined;
  if (risk?.transactions?.length) return risk.transactions;

  return [];
}

function formatFilterEntries(
  filters: Record<string, unknown>,
  entities: Record<string, unknown>,
): Array<{ key: string; value: string }> {
  const merged = { ...filters, ...entities };
  return Object.entries(merged)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([key, value]) => ({
      key,
      value: typeof value === "object" ? JSON.stringify(value) : String(value),
    }));
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

export default function AgentQueryResult({ data }: AgentQueryResultProps) {
  const summary = data.execution_summary;
  const planDetail = summary?.execution_plan_detail ?? [];
  const planSteps = summary?.execution_plan ?? data.execution_plan ?? [];
  const toolEntries = summary?.tools_executed ?? [];
  const filterChips = formatFilterEntries(
    summary?.extracted_filters ?? data.filters ?? {},
    summary?.extracted_entities ?? data.entities ?? {},
  );
  const transactions = extractTransactions(data.results);
  const execTime =
    summary?.total_execution_time_ms ?? summary?.total_execution_time_seconds ?? "—";

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
    >
      <SocSection title="User Query" icon={MessageSquare} delay={0.02}>
        <p className="text-sm leading-relaxed text-slate-200">
          {summary?.user_query ?? data.query}
        </p>
      </SocSection>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SocSection title="Detected Intent" icon={Crosshair} delay={0.05}>
          <p className="font-mono text-sm font-semibold text-accent-light">
            {summary?.detected_intent ?? data.intent}
          </p>
        </SocSection>
        <SocSection title="AML Pattern" icon={Target} delay={0.08}>
          <p className="text-sm font-medium text-slate-200">
            {summary?.selected_aml_pattern ?? data.aml_pattern}
          </p>
        </SocSection>
        <SocSection title="Execution Time" icon={Timer} delay={0.11}>
          <p className="font-mono text-lg font-semibold text-slate-100">
            {execTime}
            <span className="ml-1 text-xs font-normal text-slate-500">
              {typeof execTime === "number" ? "s" : ""}
            </span>
          </p>
        </SocSection>
        <SocSection title="Risk Level" icon={Sparkles} delay={0.14}>
          <RiskBadge level={data.risk_level} size="lg" pulse />
        </SocSection>
      </div>

      <SocSection title="Extracted Filters" icon={Filter} delay={0.12}>
        {filterChips.length === 0 ? (
          <p className="text-sm text-slate-500">No structured filters extracted — general analysis.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {filterChips.map(({ key, value }) => (
              <motion.span
                key={key}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="inline-flex items-center gap-2 rounded-lg border border-navy-600 bg-navy-800/80 px-3 py-1.5 font-mono text-xs"
              >
                <span className="text-accent-light">{key}</span>
                <span className="text-slate-400">=</span>
                <span className="text-slate-200">{value}</span>
              </motion.span>
            ))}
          </div>
        )}
      </SocSection>

      <SocSection title="Execution Plan" icon={Layers} delay={0.16}>
        <ExecutionTimeline steps={planSteps} details={planDetail} />
      </SocSection>

      <SocSection title="Tool Execution Timeline" icon={Clock} delay={0.2}>
        <ToolExecutionTimeline tools={toolEntries} />
      </SocSection>

      <div className="grid gap-4 lg:grid-cols-2">
        <RecommendationCard recommendation={data.recommendation} />
        <ExplanationCard explanation={data.explanation} />
      </div>

      {transactions.length > 0 ? (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="overflow-hidden rounded-xl border border-navy-700 bg-navy-900/50"
        >
          <div className="border-b border-navy-700 px-4 py-3">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
              Top Suspicious Transactions
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-navy-700 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2.5 font-medium">Txn ID</th>
                  <th className="px-4 py-2.5 font-medium">Score</th>
                  <th className="px-4 py-2.5 font-medium">Risk</th>
                  <th className="px-4 py-2.5 font-medium">Pattern / Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.slice(0, 10).map((tx, i) => (
                  <motion.tr
                    key={tx.transaction_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + i * 0.04 }}
                    className="border-b border-navy-800/80 hover:bg-navy-800/40"
                  >
                    <td className="px-4 py-2.5 font-mono text-accent-light">{tx.transaction_id}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-300">{tx.risk_score}</td>
                    <td className="px-4 py-2.5">
                      <RiskBadge level={tx.risk_level} size="sm" />
                    </td>
                    <td className="max-w-xs truncate px-4 py-2.5 text-xs text-slate-400">
                      {tx.aml_pattern ?? tx.recommended_action ?? tx.recommendation ?? "—"}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>
      ) : null}
    </motion.div>
  );
}
