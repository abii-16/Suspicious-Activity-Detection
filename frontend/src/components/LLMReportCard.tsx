import { motion } from "framer-motion";
import { Brain, ChevronRight, Lightbulb, ShieldAlert } from "lucide-react";
import type { LLMInvestigationReport } from "@/types/api";
import ConfidenceMeter from "./ConfidenceMeter";

interface LLMReportCardProps {
  report: LLMInvestigationReport;
  title?: string;
}

// Pretty labels for field keys
const FIELD_LABELS: Record<string, string> = {
  dataset_summary: "Dataset Summary",
  key_statistics: "Key Statistics",
  key_insights: "Key Insights",
  suggested_next_queries: "Suggested Next Queries",
  customer_summary: "Customer Summary",
  risk_score: "Risk Score",
  why_flagged: "Why Flagged",
  recommended_action: "Recommended Action",
  transaction_summary: "Transaction Summary",
  risk_analysis: "Risk Analysis",
  rule_violations: "Rule Violations",
  pattern_found: "Pattern Found",
  evidence: "Supporting Evidence",
  affected_accounts: "Affected Accounts",
  recommendation: "Recommendation",
  screening_summary: "Screening Summary",
  highest_risk_transaction: "Highest Risk Transaction",
  common_patterns: "Common Patterns",
  risk_breakdown: "Risk Breakdown",
  recommended_actions: "Recommended Actions",
  model_summary: "Model Summary",
  dataset_statistics: "Dataset Statistics",
  scoring_analysis: "Scoring Analysis",
  model_insights: "Model Insights",
  explanation_summary: "Explanation Summary",
  risk_factors: "Risk Factors",
  summary: "Summary",
  key_findings: "Key Findings",
  confidence: "Confidence",
};

// Keys that are metadata, not content
const META_KEYS = new Set([
  "available", "model", "inference_time_ms", "intent", "error",
  "aml_pattern", "full_report",
]);

// Which intents show which keys (defines render order too)
const INTENT_KEYS: Record<string, string[]> = {
  DATASET_EXPLORATION:       ["dataset_summary", "key_statistics", "key_insights", "suggested_next_queries"],
  CUSTOMER_INVESTIGATION:    ["customer_summary", "risk_score", "why_flagged", "recommended_action"],
  TRANSACTION_INVESTIGATION: ["transaction_summary", "risk_analysis", "rule_violations", "recommended_action"],
  PATTERN_DETECTION:         ["pattern_found", "evidence", "affected_accounts", "recommendation"],
  TOP_SUSPICIOUS:            ["screening_summary", "highest_risk_transaction", "common_patterns", "risk_breakdown", "recommended_actions"],
  MODEL_ANALYTICS:           ["model_summary", "dataset_statistics", "scoring_analysis", "model_insights"],
  RISK_EXPLANATION:          ["explanation_summary", "risk_factors", "recommended_action"],
  GENERAL:                   ["summary", "key_findings", "recommended_action"],
};

const NA = "Not available from current analysis.";

function isNA(val: unknown): boolean {
  return val === NA || val === null || val === undefined || val === "";
}

function StringField({ label, value, delay }: { label: string; value: string; delay: number }) {
  const na = isNA(value);
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-lg border border-navy-700/80 bg-navy-950/50 p-4"
    >
      <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-accent">{label}</h4>
      <p className={`text-sm leading-relaxed ${na ? "italic text-slate-500" : "text-slate-200"}`}>
        {na ? NA : value}
      </p>
    </motion.div>
  );
}

function ListField({ label, items, delay }: { label: string; items: string[]; delay: number }) {
  const allNA = items.every(isNA);
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-lg border border-navy-700/80 bg-navy-950/50 p-4"
    >
      <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-accent">{label}</h4>
      {allNA ? (
        <p className="text-sm italic text-slate-500">{NA}</p>
      ) : (
        <ul className="space-y-1.5">
          {items.filter((i) => !isNA(i)).map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
              <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
              {item}
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}

function renderField(key: string, value: unknown, delay: number) {
  const label = FIELD_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  if (key === "confidence" && typeof value === "string") {
    return (
      <motion.div
        key={key}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay }}
        className="rounded-lg border border-navy-700/80 bg-navy-950/50 p-4"
      >
        <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-accent">{label}</h4>
        <ConfidenceMeter confidence={value} />
      </motion.div>
    );
  }

  if (Array.isArray(value)) {
    return <ListField key={key} label={label} items={value as string[]} delay={delay} />;
  }

  return <StringField key={key} label={label} value={String(value ?? "")} delay={delay} />;
}

export default function LLMReportCard({ report, title }: LLMReportCardProps) {
  const intent = (report.intent as string) || "GENERAL";
  const keys = INTENT_KEYS[intent] ?? INTENT_KEYS["GENERAL"];

  const intentLabel: Record<string, string> = {
    DATASET_EXPLORATION: "Dataset Exploration",
    CUSTOMER_INVESTIGATION: "Customer Investigation",
    TRANSACTION_INVESTIGATION: "Transaction Investigation",
    PATTERN_DETECTION: "Pattern Detection",
    TOP_SUSPICIOUS: "Top Suspicious",
    MODEL_ANALYTICS: "Model Analytics",
    RISK_EXPLANATION: "Risk Explanation",
    GENERAL: "General Analysis",
  };

  const displayTitle = title ?? `AI Investigator · ${intentLabel[intent] ?? intent}`;

  // Partition keys: full-width vs two-column
  const fullWidthKeys = ["key_insights", "suggested_next_queries", "evidence", "model_insights", "risk_factors", "key_findings"];
  const halfKeys = keys.filter((k) => !fullWidthKeys.includes(k));
  const fullKeys = keys.filter((k) => fullWidthKeys.includes(k));

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-xl border border-accent/20 bg-gradient-to-br from-navy-900/90 to-navy-950/90"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-navy-700 px-4 py-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-accent-light" />
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">
            {displayTitle}
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {report.model ? (
            <span className="rounded-full border border-navy-600 bg-navy-800 px-2 py-0.5 font-mono text-[10px] text-slate-400">
              {report.model}
            </span>
          ) : null}
          {(report.inference_time_ms as number) != null ? (
            <span className="text-[10px] text-slate-500">{report.inference_time_ms} ms</span>
          ) : null}
          {!report.available ? (
            <span className="rounded-full border border-risk-medium/40 bg-risk-medium/10 px-2 py-0.5 text-[10px] text-risk-medium">
              Fallback
            </span>
          ) : null}
        </div>
      </div>

      {/* Meta chips */}
      {(report.aml_pattern || report.recommended_action || report.recommendation) ? (
        <div className="flex flex-wrap gap-2 border-b border-navy-800 px-4 py-2">
          {report.aml_pattern && !isNA(report.aml_pattern) ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-navy-700 bg-navy-800/60 px-3 py-1">
              <ShieldAlert className="h-3 w-3 text-risk-high" />
              <span className="text-xs text-slate-300">{report.aml_pattern}</span>
            </div>
          ) : null}
          {(report.recommended_action || report.recommendation) &&
          !isNA(report.recommended_action ?? "") ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-navy-700 bg-navy-800/60 px-3 py-1">
              <Lightbulb className="h-3 w-3 text-risk-medium" />
              <span className="text-xs text-slate-300">
                {report.recommended_action ?? report.recommendation}
              </span>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Body — only render keys defined for this intent */}
      <div className="space-y-3 p-4">
        {/* Two-column grid for scalar fields */}
        {halfKeys.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {halfKeys.map((key, i) => {
              const val = (report as Record<string, unknown>)[key];
              if (META_KEYS.has(key)) return null;
              return renderField(key, val, 0.04 + i * 0.04);
            })}
          </div>
        ) : null}

        {/* Full-width for lists */}
        {fullKeys.map((key, i) => {
          const val = (report as Record<string, unknown>)[key];
          if (META_KEYS.has(key)) return null;
          return renderField(key, val, 0.1 + i * 0.05);
        })}
      </div>
    </motion.section>
  );
}
