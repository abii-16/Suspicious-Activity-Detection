export type RiskLevel = string;

export interface ToolExecutionEntry {
  tool: string;
  status: "success" | "error";
  duration_ms: string | number;
  reason?: string;
  error?: string;
}

export interface PlanStepDetail {
  step: string;
  reason: string;
}

export interface ExecutionSummary {
  user_query: string;
  detected_intent: string;
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
  total_execution_time_ms: string | number;
  total_execution_time_seconds?: number;
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
  filters: Record<string, unknown>;
  entities: Record<string, unknown>;
  aml_pattern: string;
  execution_plan: string[];
  tools_executed: string[];
  results: Record<string, unknown>;
  risk_level: RiskLevel;
  explanation: string;
  recommendation: string;
  execution_summary: ExecutionSummary;
}
