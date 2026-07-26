"""
planner.py

Agentic AI Planner for the AML Agent.

Key principle: Never call a tool without satisfying its required parameters.
If a required entity (customer_id, transaction_id) is missing, the planner
inserts a discovery step first — dynamic tool chaining.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PlanStep:
    tool: str
    reason: str


@dataclass
class PlannerThought:
    thought: str
    conclusion: str


@dataclass
class PlannerResult:
    query: str
    intent: str
    intent_label: str
    filters: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, Any] = field(default_factory=dict)
    aml_pattern: str = "General AML Analysis"
    execution_plan: List[PlanStep] = field(default_factory=list)
    reasoning: List[PlannerThought] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "intent_label": self.intent_label,
            "filters": self.filters,
            "entities": self.entities,
            "aml_pattern": self.aml_pattern,
            "reasoning": [
                {"thought": t.thought, "conclusion": t.conclusion}
                for t in self.reasoning
            ],
            "execution_plan": [
                {"step": s.tool, "reason": s.reason}
                for s in self.execution_plan
            ],
        }


# ---------------------------------------------------------------------------
# Intent definitions
# ---------------------------------------------------------------------------

INTENTS = {
    "DATASET_EXPLORATION":       "Dataset Exploration",
    "CUSTOMER_INVESTIGATION":    "Customer Investigation",
    "TRANSACTION_INVESTIGATION": "Transaction Investigation",
    "PATTERN_DETECTION":         "Suspicious Pattern Detection",
    "TOP_SUSPICIOUS":            "Top Suspicious Accounts",
    "MODEL_ANALYTICS":           "Model Analytics",
    "RISK_EXPLANATION":          "Risk Explanation",
    "ANALYTICS_QUERY":           "Analytics Query",
    "COMPARISON":                "Comparison",
    "KNOWLEDGE":                 "Knowledge / Architecture",
    "GENERAL":                   "General Q&A",
}

_INTENT_PATTERNS: List[tuple] = [
    ("DATASET_EXPLORATION", [
        r"\bdataset\b", r"\beda\b", r"\boverview\b", r"\bstatistics\b",
        r"\bhow many\b.*\btransaction", r"\bfraud\b.*\brate\b",
        r"\bexplore\b", r"\bsummar\b.*\bdata",
    ]),
    ("KNOWLEDGE", [
        r"\bhow.{0,10}(work|calculate|compute|built|train)\b",
        r"\bwhat is\b.*\b(xgboost|isolation|risk score|hybrid|aml agent)\b",
        r"\bexplain\b.*\b(model|algorithm|architecture|system|xgboost|isolation)\b",
        r"\bxgboost\b", r"\bisolation forest\b",
        r"\bhybrid ml\b", r"\brisk score\b.*\bcalcul",
        r"\bhow.{0,15}risk score",
        r"\bwhat.*\bfeatures?\b.*\b(use|train|input)\b",
        r"\baml pattern\b.*\btype\b",
    ]),
    ("COMPARISON", [
        r"\bcompare\b.{0,30}\b(customer|bank|currency|account)\b",
        r"\b(bank|customer)\b.{0,15}\bvs\.?\b",
        r"\bdifference\b.{0,20}\b(bank|customer|currency)\b",
        r"\bsid[e\s]*by[- \s]*side\b",
    ]),
    ("ANALYTICS_QUERY", [
        r"\bwhich\b.{0,20}\b(bank|currency|payment|format)\b.{0,20}\b(highest|most|top|lowest)\b",
        r"\b(highest|most|top|lowest)\b.{0,20}\b(bank|currency|payment|format)\b",
        r"\btop\b.{0,10}\b(bank|banks|currencies|formats)\b",
        r"\b(bank|currency|payment format)\b.{0,20}\b(fraud rate|suspicious|risk|transactions)\b",
        r"\bcompare\b.{0,20}\b(bank|currency|payment)\b",
        r"\bmost common\b.{0,20}\b(payment|currency|method)\b",
        r"\banalyze\b.{0,15}\bbank\b",
    ]),
    ("CUSTOMER_INVESTIGATION", [
        r"\bcustomer\s*(?:id)?\s*#?\s*\d+",
        r"\baccount\s*(?:id)?\s*#?\s*\d+",
        r"\binvestigat\b.*\bcustomer\b",
        r"\bcustomer\b.*\brisk\b",
        r"\bprofile\b.*\bcustomer\b",
        r"\bhighest.{0,10}risk.{0,10}customer",
        r"\bmost.{0,10}suspicious.{0,10}customer",
        r"\briskiest\b.*\bcustomer",
        r"\bworst\b.*\bcustomer",
    ]),
    ("TRANSACTION_INVESTIGATION", [
        r"\btransaction\s*(?:id)?\s*#?\s*\d+",
        r"\btransaction\b.*\b(suspicious|risky|flag)\b",
        r"\binvestigat\b.*\btransaction\b",
        r"\bhighest.{0,10}risk.{0,10}transaction",
        r"\bmost.{0,10}suspicious.{0,10}transaction",
        r"\briskiest\b.*\btransaction",
    ]),
    ("PATTERN_DETECTION", [
        r"\bstructuring\b", r"\bsmurf", r"\blayering\b",
        r"\bcross[- ]border\b", r"\brapid\b.*\btransaction",
        r"\bnear\b.*\bthreshold\b", r"\bpattern\b",
        r"\bcurrency\b.*\bconver", r"\bfan[- ]out\b",
        r"\banomaly\b", r"\bunusual\b.*\btransaction",
    ]),
    ("TOP_SUSPICIOUS", [
        r"\btop\b.*\b(suspicious|risk)",
        r"\bhighest\b.*\brisk\b",
        r"\bmost\b.*\bsuspicious\b",
        r"\bmost\b.*\brisky\b",
        r"\bshow\b.*\bsuspicious\b",
        r"\blist\b.*\brisk\b",
    ]),
    ("MODEL_ANALYTICS", [
        r"\bmodel\b.*\bperformance\b",
        r"\bfeature\b.*\bimportance\b",
        r"\baccuracy\b", r"\bfalse\b.*\bpositive\b",
    ]),
    ("RISK_EXPLANATION", [
        r"\bwhy\b.*\bflagged\b", r"\bexplain\b.*\brisk\b",
        r"\bwhat\b.*\bmakes\b.*\bsuspicious\b",
        r"\breason\b.*\bflag\b", r"\bexplain\b.*\bscore\b",
    ]),
]


# ---------------------------------------------------------------------------
# Helpers: query classification
# ---------------------------------------------------------------------------

def _wants_highest_risk_customer(query: str) -> bool:
    lowered = query.lower()
    return bool(re.search(
        r"(highest|most|riskiest|worst|top).{0,15}(risk|suspicious).{0,15}customer"
        r"|customer.{0,15}(highest|most|riskiest|worst|top).{0,15}(risk|suspicious)",
        lowered,
    ))


def _wants_highest_risk_transaction(query: str) -> bool:
    lowered = query.lower()
    return bool(re.search(
        r"(highest|most|riskiest|worst|top).{0,15}(risk|suspicious).{0,15}transaction"
        r"|transaction.{0,15}(highest|most|riskiest|worst|top).{0,15}(risk|suspicious)",
        lowered,
    ))


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

def detect_intent(query: str) -> str:
    lowered = query.lower()
    for intent, patterns in _INTENT_PATTERNS:
        if any(re.search(p, lowered) for p in patterns):
            return intent
    return "GENERAL"


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

def extract_entities(query: str) -> Dict[str, Any]:
    entities: Dict[str, Any] = {}
    lowered = query.lower()

    m = re.search(r"customer\s*(?:id)?\s*#?\s*(\d+)", lowered)
    if m:
        entities["customer_id"] = int(m.group(1))

    m = re.search(r"account\s*(?:id)?\s*#?\s*(\d+)", lowered)
    if m and "customer_id" not in entities:
        entities["customer_id"] = int(m.group(1))

    m = re.search(r"transaction\s*(?:id)?\s*#?\s*(\d+)", lowered)
    if m:
        entities["transaction_id"] = int(m.group(1))

    m = re.search(r"bank\s*(?:id)?\s*#?\s*(\d+)", lowered)
    if m:
        entities["bank_id"] = int(m.group(1))

    # "Bank 70", "Bank 10" style
    if "bank_id" not in entities:
        m = re.search(r"\bbank\s+(\d+)\b", lowered)
        if m:
            entities["bank_id"] = int(m.group(1))

    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", query)
    if m:
        entities["amount"] = float(m.group(1).replace(",", ""))

    m = re.search(r"(\d+)\+?\s*(?:or more\s*)?transactions?", lowered)
    if m:
        entities["transaction_count"] = int(m.group(1))

    m = re.search(r"top\s+(\d+)", lowered)
    if m:
        entities["top_n"] = int(m.group(1))

    # Detect group_by dimension for analytics queries
    if re.search(r"\bcurrenc", lowered):
        entities["group_by"] = "currency"
    elif re.search(r"\bpayment.{0,10}(format|method)\b", lowered):
        entities["group_by"] = "payment_format"
    elif re.search(r"\bbank\b", lowered) and "bank_id" not in entities:
        entities["group_by"] = "bank"

    # Detect metric for analytics queries
    if re.search(r"\bfraud.{0,10}rate\b", lowered):
        entities["metric"] = "fraud_rate"
    elif re.search(r"\bsuspicious\b", lowered):
        entities["metric"] = "suspicious_transactions"
    elif re.search(r"\b(avg|average).{0,10}risk\b", lowered):
        entities["metric"] = "avg_risk_score"
    elif re.search(r"\btransaction.{0,10}count\b|\bmost.{0,10}transaction\b", lowered):
        entities["metric"] = "transaction_count"

    # Detect comparison entity_ids e.g. "compare Bank 10 and Bank 70"
    bank_matches = re.findall(r"\bbank\s+(\d+)\b", lowered)
    if len(bank_matches) >= 2:
        entities["entity_ids"] = [int(x) for x in bank_matches]
        entities["entity_type"] = "bank"

    # Detect knowledge topic
    for topic in ("xgboost", "isolation forest", "risk score", "hybrid ml",
                  "features", "aml patterns", "architecture", "agent"):
        if topic in lowered:
            entities["knowledge_topic"] = topic
            break

    return entities


# ---------------------------------------------------------------------------
# Filter extraction
# ---------------------------------------------------------------------------

def extract_filters(query: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    filters: Dict[str, Any] = dict(entities)
    lowered = query.lower()

    m = re.search(r"last\s+(\d+)\s+days?", lowered)
    if m:
        filters["days"] = int(m.group(1))

    if re.search(r"\bstructuring\b|\bsmurf", lowered):
        filters["aml_pattern"] = "STRUCTURING / SMURFING"
    elif re.search(r"\brapid\b", lowered):
        filters["aml_pattern"] = "RAPID TRANSACTIONS"
    elif re.search(r"\blayering\b|\bcross[- ]border\b", lowered):
        filters["aml_pattern"] = "LAYERING"

    m = re.search(r"under\s+\$?\s*([\d,]+)", lowered)
    if m:
        filters["max_amount"] = float(m.group(1).replace(",", ""))
        filters["amount_threshold"] = filters["max_amount"]

    if "transaction_count" in entities:
        filters["min_transactions_under_amount"] = entities["transaction_count"]

    if re.search(r"\bdaily\b.*\bvolume\b|\bhigh\b.*\bdaily\b", lowered):
        filters["min_daily_volume"] = 50_000
    if re.search(r"\brapid\b.*\btransactions?\b", lowered):
        filters["rapid_transactions"] = True
    if re.search(r"\bnear\b.*\b(threshold|reporting)\b", lowered):
        filters["near_threshold"] = True

    return filters


# ---------------------------------------------------------------------------
# AML pattern
# ---------------------------------------------------------------------------

def detect_aml_pattern(query: str, intent: str, filters: Dict[str, Any]) -> str:
    if filters.get("aml_pattern"):
        return str(filters["aml_pattern"])
    lowered = query.lower()
    if "structuring" in lowered or "smurf" in lowered:
        return "Structuring / Smurfing"
    if "layering" in lowered or "cross-border" in lowered:
        return "Layering"
    if "rapid" in lowered:
        return "Rapid Transaction Pattern"
    if "near threshold" in lowered:
        return "Near Reporting Threshold"
    if intent == "CUSTOMER_INVESTIGATION":
        return "Customer Risk Assessment"
    if intent == "TRANSACTION_INVESTIGATION":
        return "Transaction Risk Assessment"
    if intent == "TOP_SUSPICIOUS":
        return "High-Risk Transaction Screening"
    if intent == "DATASET_EXPLORATION":
        return "Dataset Exploration"
    if intent == "PATTERN_DETECTION":
        return "AML Pattern Detection"
    return "General AML Analysis"


# ---------------------------------------------------------------------------
# Execution plan builder — with dependency resolution
# ---------------------------------------------------------------------------

def build_execution_plan(
    query: str,
    intent: str,
    entities: Dict[str, Any],
    filters: Dict[str, Any],
) -> List[PlanStep]:
    lowered = query.lower()

    # ── COMPARISON ────────────────────────────────────────────────────────
    if intent == "COMPARISON":
        entity_type = entities.get("entity_type", "bank")
        ids = entities.get("entity_ids")
        id_str = f" ({', '.join(str(i) for i in ids)})" if ids else " (top by volume)"
        return [
            PlanStep("comparison_tool",
                     f"Compare {entity_type}s{id_str} side-by-side on risk, fraud rate, and volume."),
        ]

    # ── ANALYTICS QUERY ──────────────────────────────────────────────────
    if intent == "ANALYTICS_QUERY":
        group_by = entities.get("group_by", "bank")
        metric = entities.get("metric", "suspicious_transactions")
        n = entities.get("top_n", 10)
        return [
            PlanStep("analytics_tool",
                     f"Group by {group_by}, compute {metric} for top {n} groups."),
        ]

    # ── COMPARISON ────────────────────────────────────────────────────────
    if intent == "COMPARISON":
        entity_type = entities.get("entity_type", "bank")
        ids = entities.get("entity_ids")
        id_str = f" ({', '.join(str(i) for i in ids)})" if ids else " (top by volume)"
        return [
            PlanStep("comparison_tool",
                     f"Compare {entity_type}s{id_str} side-by-side on risk, fraud rate, and volume."),
        ]

    # ── KNOWLEDGE ─────────────────────────────────────────────────────────
    if intent == "KNOWLEDGE":
        topic = entities.get("knowledge_topic", "overview")
        return [
            PlanStep("knowledge_tool",
                     f"Answer question about '{topic}' from system knowledge base — no ML inference."),
        ]

    # ── DATASET EXPLORATION ──────────────────────────────────────────────
    if intent == "DATASET_EXPLORATION":
        return [
            PlanStep("run_eda", "User asked for dataset statistics — EDA provides rows, fraud %, averages, distributions."),
        ]

    # ── MODEL ANALYTICS ──────────────────────────────────────────────────
    if intent == "MODEL_ANALYTICS":
        return [
            PlanStep("run_eda", "Gather dataset baseline for model analytics."),
            PlanStep("generate_risk", "Show hybrid ML scoring output across the dataset."),
        ]

    # ── CUSTOMER INVESTIGATION ───────────────────────────────────────────
    if intent == "CUSTOMER_INVESTIGATION":
        has_id = "customer_id" in entities
        wants_top = _wants_highest_risk_customer(query)

        if not has_id or wants_top:
            # No customer_id supplied — must discover it first via top suspicious
            return [
                PlanStep(
                    "top_suspicious_transactions",
                    "No customer ID provided. Finding the highest-risk customer by scanning top suspicious transactions.",
                ),
                PlanStep(
                    "customer_summary",
                    "Retrieve full transaction history for the discovered highest-risk customer.",
                ),
                PlanStep(
                    "generate_risk",
                    "Apply ML scoring to that customer's transactions.",
                ),
                PlanStep(
                    "generate_explanation",
                    "Explain why this customer is the highest-risk account.",
                ),
            ]

        # customer_id present — direct investigation
        cid = entities["customer_id"]
        steps: List[PlanStep] = [
            PlanStep("customer_summary", f"Retrieve full transaction history and risk profile for customer {cid}."),
            PlanStep("generate_risk", f"Apply hybrid ML scoring to customer {cid}'s transactions."),
        ]
        if filters.get("rapid_transactions") or filters.get("near_threshold") or filters.get("min_daily_volume"):
            steps.append(PlanStep("rule_engine", "Check deterministic AML rules for this customer's patterns."))
        steps.append(PlanStep("generate_explanation", f"Explain why customer {cid} was flagged using ML + rule signals."))
        return steps

    # ── TRANSACTION INVESTIGATION ─────────────────────────────────────────
    if intent == "TRANSACTION_INVESTIGATION":
        has_id = "transaction_id" in entities
        wants_top = _wants_highest_risk_transaction(query)

        if not has_id or wants_top:
            # No transaction_id supplied — discover it first
            return [
                PlanStep(
                    "top_suspicious_transactions",
                    "No transaction ID provided. Finding the highest-risk transaction first.",
                ),
                PlanStep(
                    "transaction_summary",
                    "Fetch full details for the discovered highest-risk transaction.",
                ),
                PlanStep(
                    "generate_risk",
                    "Cross-check risk score with ML scoring.",
                ),
                PlanStep(
                    "generate_explanation",
                    "Explain all risk indicators for this transaction.",
                ),
            ]

        # transaction_id present — direct investigation
        tid = entities["transaction_id"]
        return [
            PlanStep("transaction_summary", f"Fetch full details, ML scores, and features for transaction {tid}."),
            PlanStep("generate_risk", "Cross-check risk score with current hybrid ML scoring."),
            PlanStep("generate_explanation", f"Explain all risk indicators for transaction {tid}."),
        ]

    # ── PATTERN DETECTION ─────────────────────────────────────────────────
    if intent == "PATTERN_DETECTION":
        # Determine which AML pattern type to detect
        ptype = "structuring"
        if filters.get("rapid_transactions") or "rapid" in lowered:
            ptype = "rapid_transactions"
        elif filters.get("near_threshold") or "threshold" in lowered:
            ptype = "near_threshold"
        elif "cross" in lowered and "bank" in lowered:
            ptype = "cross_bank"
        elif "currency" in lowered:
            ptype = "currency_change"
        elif "layering" in lowered:
            ptype = "cross_bank"
        elif "anomaly" in lowered:
            ptype = "anomaly"
        elif "fan" in lowered:
            ptype = "fan_out"
        elif "high value" in lowered or "high_value" in lowered:
            ptype = "high_value"

        # If rule-based count query, use rule_engine instead
        has_count_rule = filters.get("min_transactions_under_amount") or filters.get("min_daily_volume")
        if has_count_rule:
            return [PlanStep("rule_engine", "Apply deterministic AML rules to find accounts matching count/amount thresholds.")]

        return [
            PlanStep("pattern_detection_tool", f"Detect {ptype} pattern using pre-computed feature flags."),
        ]

    # ── TOP SUSPICIOUS ────────────────────────────────────────────────────
    if intent == "TOP_SUSPICIOUS":
        n = entities.get("top_n", 20)
        return [
            PlanStep("top_suspicious_transactions", f"Return top {n} highest-risk transactions ranked by hybrid ML score."),
            PlanStep("generate_explanation", "Attach human-readable explanations to each flagged transaction."),
        ]

    # ── RISK EXPLANATION ──────────────────────────────────────────────────
    if intent == "RISK_EXPLANATION":
        steps = []
        if entities.get("transaction_id"):
            steps.append(PlanStep("transaction_summary", f"Fetch transaction {entities['transaction_id']} details."))
        elif entities.get("customer_id"):
            steps.append(PlanStep("customer_summary", f"Fetch customer {entities['customer_id']} profile."))
        else:
            # No entity — explain the highest-risk transaction
            steps.append(PlanStep("top_suspicious_transactions", "No entity specified. Fetching highest-risk transaction for explanation."))
        steps.append(PlanStep("generate_risk", "Retrieve ML risk scores as basis for explanation."))
        steps.append(PlanStep("generate_explanation", "Explain risk indicators in detail."))
        return steps

    # ── GENERAL FALLBACK ──────────────────────────────────────────────────
    return [
        PlanStep("run_eda", "Start with dataset overview to understand the data landscape."),
        PlanStep("generate_risk", "Apply hybrid ML scoring to surface high-risk transactions."),
        PlanStep("generate_explanation", "Explain why top-scored transactions were flagged."),
    ]


# ---------------------------------------------------------------------------
# Reasoning thoughts
# ---------------------------------------------------------------------------

def _build_reasoning(
    query: str,
    intent: str,
    entities: Dict[str, Any],
    filters: Dict[str, Any],
    execution_plan: List[PlanStep],
) -> List[PlannerThought]:
    thoughts: List[PlannerThought] = []
    lowered = query.lower()

    thoughts.append(PlannerThought(
        thought=f'Received query: "{query}"',
        conclusion=f"Classified as: {INTENTS.get(intent, intent)}",
    ))

    # Entity check with dependency reasoning
    if entities.get("customer_id"):
        thoughts.append(PlannerThought(
            thought=f"Customer ID {entities['customer_id']} found in query.",
            conclusion="Direct customer lookup — no discovery step needed.",
        ))
    elif entities.get("transaction_id"):
        thoughts.append(PlannerThought(
            thought=f"Transaction ID {entities['transaction_id']} found in query.",
            conclusion="Direct transaction lookup — no discovery step needed.",
        ))
    elif intent == "CUSTOMER_INVESTIGATION":
        thoughts.append(PlannerThought(
            thought="Customer investigation requested but no customer_id in query.",
            conclusion="Will run top_suspicious_transactions first to discover the highest-risk customer ID.",
        ))
    elif intent == "TRANSACTION_INVESTIGATION":
        thoughts.append(PlannerThought(
            thought="Transaction investigation requested but no transaction_id in query.",
            conclusion="Will run top_suspicious_transactions first to discover the highest-risk transaction ID.",
        ))
    else:
        thoughts.append(PlannerThought(
            thought="No specific entity ID in query.",
            conclusion="Operating on dataset-level tools.",
        ))

    # ML needed?
    needs_ml = intent in {"CUSTOMER_INVESTIGATION", "TRANSACTION_INVESTIGATION",
                           "TOP_SUSPICIOUS", "PATTERN_DETECTION", "RISK_EXPLANATION"}
    thoughts.append(PlannerThought(
        thought="Checking if Hybrid ML scoring is required.",
        conclusion="ML scoring included." if needs_ml else "ML scoring not required — skipping.",
    ))

    # Rule engine?
    rule_needed = any([
        filters.get("rapid_transactions"), filters.get("near_threshold"),
        filters.get("min_daily_volume"), filters.get("min_transactions_under_amount"),
        intent == "PATTERN_DETECTION",
    ])
    if rule_needed:
        thoughts.append(PlannerThought(
            thought="Query involves threshold/count/pattern rules.",
            conclusion="Rule engine included in plan.",
        ))

    thoughts.append(PlannerThought(
        thought="All dependencies resolved.",
        conclusion=f"Final plan: {' → '.join(s.tool for s in execution_plan)}",
    ))

    return thoughts


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def plan_query(query: str) -> PlannerResult:
    intent = detect_intent(query)
    entities = extract_entities(query)
    filters = extract_filters(query, entities)
    aml_pattern = detect_aml_pattern(query, intent, filters)
    execution_plan = build_execution_plan(query, intent, entities, filters)
    reasoning = _build_reasoning(query, intent, entities, filters, execution_plan)

    return PlannerResult(
        query=query,
        intent=intent,
        intent_label=INTENTS.get(intent, intent),
        filters=filters,
        entities=entities,
        aml_pattern=aml_pattern,
        execution_plan=execution_plan,
        reasoning=reasoning,
    )


__all__ = [
    "PlanStep",
    "PlannerThought",
    "PlannerResult",
    "INTENTS",
    "detect_intent",
    "extract_entities",
    "extract_filters",
    "detect_aml_pattern",
    "build_execution_plan",
    "plan_query",
]
