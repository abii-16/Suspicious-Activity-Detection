import { motion } from "framer-motion";
import { Clock, Crosshair, Layers, Sparkles, Target, Timer } from "lucide-react";
import ExecutionTimeline from "@/components/ExecutionTimeline";
import LLMReportCard from "@/components/LLMReportCard";
import PipelineTimeline from "@/components/PipelineTimeline";
import PlannerReasoning from "@/components/PlannerReasoning";
import RiskBadge from "@/components/RiskBadge";
import ToolExecutionTimeline from "@/components/ToolExecutionTimeline";
import type { QueryResponse, SuspiciousTransactionRow } from "@/types/api";

interface Props { data: QueryResponse }

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 border-b border-navy-800 py-2 last:border-0">
      <span className="w-36 shrink-0 text-[10px] uppercase tracking-widest text-slate-500">{label}</span>
      <span className="text-xs text-slate-300">{value}</span>
    </div>
  );
}

function extractTransactions(results: Record<string, unknown>): SuspiciousTransactionRow[] {
  const top = results.top_suspicious_transactions as { transactions?: SuspiciousTransactionRow[] } | undefined;
  if (top?.transactions?.length) return top.transactions;
  const risk = results.generate_risk as { transactions?: SuspiciousTransactionRow[] } | undefined;
  if (risk?.transactions?.length) return risk.transactions;
  return [];
}

export default function AgentDebugPanel({ data }: Props) {
  const summary = data.execution_summary;
  const planDetail = summary?.execution_plan_detail ?? [];
  const planSteps = summary?.execution_plan ?? data.execution_plan ?? [];
  const toolEntries = summary?.tools_executed ?? [];
  const reasoning = data.planner_reasoning ?? summary?.planner_reasoning ?? [];
  const intentLabel = data.intent_label ?? summary?.intent_label ?? data.intent;
  const pipeline = summary?.pipeline ?? ["planner", "router", ...planSteps, "llm", "response"];
  const execTime = summary?.total_execution_time_ms ?? "—";
  const transactions = extractTransactions(data.results);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-4 rounded-xl border border-navy-700/60 bg-navy-950/80 p-4"
    >
      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        Agent Reasoning — Debug View
      </p>

      {/* Quick facts */}
      <div className="rounded-lg border border-navy-800 bg-navy-900/60 p-3">
        <Row label="Detected Intent" value={
          <span className="font-mono text-accent-light">{summary?.detected_intent ?? data.intent}
            {intentLabel && intentLabel !== (summary?.detected_intent ?? data.intent)
              ? <span className="ml-2 text-slate-500">({intentLabel})</span> : null}
          </span>
        } />
        <Row label="AML Pattern" value={summary?.selected_aml_pattern ?? data.aml_pattern} />
        <Row label="Risk Level" value={<RiskBadge level={data.risk_level} size="sm" />} />
        {data.risk_score != null && (
          <Row label="Risk Score" value={<span className="font-mono">{data.risk_score.toFixed(4)}</span>} />
        )}
        <Row label="Execution Time" value={<span className="font-mono">{execTime} ms</span>} />
        {summary?.llm_inference_time_ms != null && (
          <Row label="LLM Inference" value={<span className="font-mono">{summary.llm_inference_time_ms} ms</span>} />
        )}
      </div>

      {/* Extracted entities */}
      {Object.keys(data.entities ?? {}).length > 0 ? (
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            <Crosshair className="h-3 w-3" /> Extracted Entities
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.entities).map(([k, v]) => (
              <span key={k} className="inline-flex items-center gap-1.5 rounded-lg border border-navy-700 bg-navy-800/80 px-2.5 py-1 font-mono text-[11px]">
                <span className="text-accent-light">{k}</span>
                <span className="text-slate-400">=</span>
                <span className="text-slate-200">{String(v)}</span>
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {/* Planner reasoning */}
      {reasoning.length > 0 ? (
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            <Sparkles className="h-3 w-3" /> Planner Reasoning
          </p>
          <PlannerReasoning reasoning={reasoning} intentLabel={intentLabel} />
        </div>
      ) : null}

      {/* Execution plan */}
      <div>
        <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          <Layers className="h-3 w-3" /> Execution Plan
        </p>
        <ExecutionTimeline steps={planSteps} details={planDetail} />
      </div>

      {/* Agent pipeline */}
      <div>
        <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          <Target className="h-3 w-3" /> Agent Pipeline
        </p>
        <PipelineTimeline steps={pipeline} executedTools={data.tools_executed} />
      </div>

      {/* Tool execution timeline */}
      {toolEntries.length > 0 ? (
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            <Clock className="h-3 w-3" /> Tool Execution Timeline
          </p>
          <ToolExecutionTimeline tools={toolEntries} />
        </div>
      ) : null}

      {/* Suspicious transactions table */}
      {transactions.length > 0 ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Top Suspicious Transactions
          </p>
          <div className="overflow-x-auto rounded-lg border border-navy-800">
            <table className="w-full min-w-[500px] text-left text-xs">
              <thead>
                <tr className="border-b border-navy-800 text-[10px] uppercase text-slate-500">
                  <th className="px-3 py-2">Txn ID</th>
                  <th className="px-3 py-2">Score</th>
                  <th className="px-3 py-2">Risk</th>
                  <th className="px-3 py-2">Pattern</th>
                </tr>
              </thead>
              <tbody>
                {transactions.slice(0, 10).map((tx) => (
                  <tr key={tx.transaction_id} className="border-b border-navy-900 hover:bg-navy-800/30">
                    <td className="px-3 py-1.5 font-mono text-accent-light">{tx.transaction_id}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-300">{tx.risk_score}</td>
                    <td className="px-3 py-1.5"><RiskBadge level={tx.risk_level} size="sm" /></td>
                    <td className="max-w-[180px] truncate px-3 py-1.5 text-slate-500">{tx.aml_pattern ?? tx.recommended_action ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* LLM structured report */}
      {data.investigation_report ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Structured Report
          </p>
          <LLMReportCard report={data.investigation_report} />
        </div>
      ) : null}
    </motion.div>
  );
}
