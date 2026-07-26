export type RiskLevel = string;

export interface ToolExecutionEntry {
  tool: string;
  status: "success" | "error" | "fallback";
  duration_ms: string | number;
  reason?: string;
  error?: string;
  model?: string | null;
}

export interface PlanStepDetail {
  step: string;
  reason: string;
}

export interface PlannerThought {
  thought: string;
  conclusion: string;
}

export interface ExecutionSummary {
  user_query: string;
  detected_intent: string;
  intent_label?: string;
  extracted_filters: Record<string, unknown>;
  extracted_entities: Record<string, unknown>;
  selected_aml_pattern: string;
  execution_plan: string[];
  execution_plan_detail: PlanStepDetail[];
  tools_executed: ToolExecutionEntry[];
  tool_selection_rationale?: Array<{
    tool: string;
    reason: string;
    executed: boolean;
  }>;
  planner_reasoning?: PlannerThought[];
  total_execution_time_ms: string | number;
  total_execution_time_seconds?: number;
  llm_available?: boolean;
  llm_inference_time_ms?: string | number;
  pipeline?: string[];
}

export interface LLMInvestigationReport {
  // metadata
  available?: boolean;
  model?: string | null;
  inference_time_ms?: number;
  error?: string;
  intent?: string;
  // shared optional chips
  aml_pattern?: string;
  recommended_action?: string;
  recommendation?: string;
  confidence?: string;
  // DATASET_EXPLORATION
  dataset_summary?: string;
  key_statistics?: string;
  key_insights?: string[];
  suggested_next_queries?: string[];
  // CUSTOMER_INVESTIGATION
  customer_summary?: string;
  risk_score?: string;
  why_flagged?: string;
  // TRANSACTION_INVESTIGATION
  transaction_summary?: string;
  risk_analysis?: string;
  rule_violations?: string;
  // PATTERN_DETECTION
  pattern_found?: string;
  evidence?: string;
  affected_accounts?: string;
  // TOP_SUSPICIOUS
  screening_summary?: string;
  highest_risk_transaction?: string;
  common_patterns?: string;
  risk_breakdown?: string;
  recommended_actions?: string;
  // MODEL_ANALYTICS
  model_summary?: string;
  dataset_statistics?: string;
  scoring_analysis?: string;
  model_insights?: string[];
  // RISK_EXPLANATION
  explanation_summary?: string;
  risk_factors?: string[];
  // GENERAL
  summary?: string;
  key_findings?: string[];
  // legacy (kept for fallback compat)
  full_report?: string;
  analyst_note?: string;
}

export interface SuspiciousTransactionRow {
  transaction_id: number;
  account?: number;
  amount_paid?: number;
  risk_score: number;
  risk_level: RiskLevel;
  aml_pattern?: string;
  recommendation?: string;
  recommended_action?: string;
  xgb_score?: number;
}

export interface QueryResponse {
  query: string;
  intent: string;
  intent_label?: string;
  filters: Record<string, unknown>;
  entities: Record<string, unknown>;
  aml_pattern: string;
  execution_plan: string[];
  tools_executed: string[];
  results: Record<string, unknown>;
  risk_level: RiskLevel;
  risk_score?: number;
  explanation: string;
  recommendation: string;
  natural_response?: string;
  planner_reasoning?: Array<{ thought: string; conclusion: string }>;
  investigation_report?: LLMInvestigationReport;
  execution_summary: ExecutionSummary;
}

export interface HealthResponse {
  status: string;
  models_loaded: boolean;
  llm_available?: boolean;
}

export interface DashboardStats {
  total_transactions: number;
  high_risk_count: number;
  critical_risk_count: number;
  average_risk_score: number;
  flagged_pct: number;
  risk_distribution: Record<string, number>;
  risk_trend: Array<{
    month: number;
    avg_risk_score: number;
    transaction_count: number;
    high_risk_count?: number;
  }>;
  top_banks: Record<string, number>;
  currency_distribution: Record<string, number>;
  payment_format_distribution: Record<string, number>;
  top_suspicious_transactions: SuspiciousTransactionRow[];
}

export interface EdaResponse {
  rows: number;
  columns: string[];
  fraud_pct: number;
  average_amount: number;
  average_amount_formatted?: string;
  top_banks: Record<string, number>;
  top_payment_formats: Record<string, number>;
  currency_distribution: Record<string, number>;
  statistics?: Record<string, unknown>;
}

export interface CustomerResponse {
  customer_id: number;
  found: boolean;
  message?: string;
  transaction_count?: number;
  total_amount_sent?: number;
  total_amount_received?: number;
  max_risk_score?: number;
  risk_level?: RiskLevel;
  high_risk_pct?: number;
  suspicious_transactions?: number;
  recommendation?: string;
  recent_transactions?: Record<string, unknown>[];
  llm_analysis?: LLMInvestigationReport;
}

export interface TransactionResponse {
  transaction_id: number;
  found: boolean;
  message?: string;
  account?: number;
  counterparty?: number;
  amount_paid?: number;
  from_bank?: number;
  to_bank?: number;
  payment_currency?: number;
  payment_format?: number;
  xgb_score?: number;
  isolation_anomaly?: boolean;
  isolation_score?: number;
  risk_score?: number;
  risk_level?: RiskLevel;
  aml_pattern?: string;
  actual_label?: number;
  reasons?: string[];
  recommendation?: string;
  features?: Record<string, unknown>;
  llm_analysis?: LLMInvestigationReport;
}
