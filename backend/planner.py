"""
planner.py

AI Planner for the AML Agent.

Parses natural-language queries, extracts intent/entities/filters,
selects an AML typology, and builds a dynamic execution plan with
human-readable rationale for each tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanStep:
    """A single step in the agent execution plan."""

    tool: str
    reason: str


@dataclass
class PlannerResult:
    """Structured output from the planner stage."""

    query: str
    intent: str
    filters: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, Any] = field(default_factory=dict)
    aml_pattern: str = "GENERAL AML ANALYSIS"
    execution_plan: List[PlanStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "filters": self.filters,
            "entities": self.entities,
            "aml_pattern": self.aml_pattern,
            "execution_plan": [
                {"step": step.tool, "reason": step.reason}
                for step in self.execution_plan
            ],
        }


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: List[tuple] = [
    ("STRUCTURING", [r"\bstructuring\b", r"\bsmurf", r"\bthreshold\b"]),
    ("CUSTOMER_LOOKUP", [r"\bcustomer\b.*\b(suspicious|risky|risk)\b", r"\bis customer\b"]),
    ("TRANSACTION_LOOKUP", [r"\btransaction\b.*\b(id)?\b\s*\d+", r"\btransaction\b.*\b(suspicious|risk)\b"]),
    ("RULE_QUERY", [
        r"\b\d+\+?\s*transactions?\b",
        r"\bunder\b.*\$?\s*\d+",
        r"\bmore than\b.*\btransactions?\b",
        r"\bdaily volume\b",
        r"\brapid\b.*\btransactions?\b",
        r"\bnear\b.*\b(threshold|reporting)\b",
    ]),
    ("TOP_SUSPICIOUS", [r"\btop\b.*\b(suspicious|risk)", r"\bhighest risk\b", r"\bmost suspicious\b"]),
    ("EDA", [r"\banalys", r"\banalyz", r"\bexplore\b", r"\bdataset\b", r"\beda\b", r"\boverview\b", r"\bstatistics\b"]),
]


def detect_intent(query: str) -> str:
    """Classify the analyst's intent from a natural-language query."""
    lowered = query.lower()

    for intent, patterns in _INTENT_PATTERNS:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return intent

    return "GENERAL"


# ---------------------------------------------------------------------------
# Entity & filter extraction
# ---------------------------------------------------------------------------


def extract_entities(query: str) -> Dict[str, Any]:
    """Pull structured entities (IDs, amounts, counts) from the query."""
    entities: Dict[str, Any] = {}
    lowered = query.lower()

    customer_match = re.search(r"customer\s*(?:id)?\s*#?\s*(\d+)", lowered)
    if customer_match:
        entities["customer_id"] = int(customer_match.group(1))

    transaction_match = re.search(r"transaction\s*(?:id)?\s*#?\s*(\d+)", lowered)
    if transaction_match:
        entities["transaction_id"] = int(transaction_match.group(1))

    amount_match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", query)
    if amount_match:
        entities["amount"] = float(amount_match.group(1).replace(",", ""))

    count_match = re.search(r"(\d+)\+?\s*(?:or more\s*)?transactions?", lowered)
    if count_match:
        entities["transaction_count"] = int(count_match.group(1))

    return entities


def extract_filters(query: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    """Derive operational filters from the query and extracted entities."""
    filters: Dict[str, Any] = dict(entities)
    lowered = query.lower()

    days_match = re.search(r"last\s+(\d+)\s+days?", lowered)
    if days_match:
        filters["days"] = int(days_match.group(1))

    if "customer_id" in entities:
        filters["customer_id"] = entities["customer_id"]
    if "transaction_id" in entities:
        filters["transaction_id"] = entities["transaction_id"]

    if re.search(r"\bstructuring\b|\bsmurf", lowered):
        filters["aml_pattern"] = "STRUCTURING / SMURFING"
    elif re.search(r"\brapid\b", lowered):
        filters["aml_pattern"] = "RAPID TRANSACTIONS"
    elif re.search(r"\blayering\b|\bcross[- ]border\b", lowered):
        filters["aml_pattern"] = "LAYERING"

    under_match = re.search(r"under\s+\$?\s*([\d,]+)", lowered)
    if under_match:
        filters["max_amount"] = float(under_match.group(1).replace(",", ""))
        filters["amount_threshold"] = filters["max_amount"]

    if "transaction_count" in entities:
        filters["min_transactions_under_amount"] = entities["transaction_count"]

    if re.search(r"\bdaily volume\b|\bhigh daily\b", lowered):
        filters["min_daily_volume"] = 50_000
    if re.search(r"\brapid\b.*\btransactions?\b", lowered):
        filters["rapid_transactions"] = True
    if re.search(r"\bnear\b.*\b(threshold|reporting)\b", lowered):
        filters["near_threshold"] = True

    return filters


def detect_aml_pattern(query: str, intent: str, filters: Dict[str, Any]) -> str:
    """Select the AML typology most relevant to the query."""
    if filters.get("aml_pattern"):
        return str(filters["aml_pattern"])

    lowered = query.lower()

    if intent == "STRUCTURING" or "structuring" in lowered or "smurf" in lowered:
        return "Structuring / Smurfing"
    if "layering" in lowered or "cross-border" in lowered:
        return "Layering"
    if "rapid" in lowered:
        return "Rapid Transaction Pattern"
    if intent == "RULE_QUERY":
        if filters.get("near_threshold"):
            return "Near Reporting Threshold"
        if filters.get("rapid_transactions"):
            return "Rapid Transaction Pattern"
        if filters.get("min_transactions_under_amount") or filters.get("max_amount"):
            return "Structuring / Smurfing"
        return "Rule-Based Pattern Detection"
    if intent == "CUSTOMER_LOOKUP":
        return "Customer Risk Assessment"
    if intent == "TOP_SUSPICIOUS":
        return "High-Risk Transaction Screening"
    if intent == "EDA":
        return "Dataset Exploration"
    return "General AML Analysis"


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def _plan_for_structuring(filters: Dict[str, Any]) -> List[PlanStep]:
    days_note = f" (last {filters['days']} days)" if filters.get("days") else ""
    return [
        PlanStep(
            tool="filter_data",
            reason=f"Scope the dataset to structuring-relevant transactions{days_note}.",
        ),
        PlanStep(
            tool="generate_risk",
            reason="Score filtered transactions with the hybrid XGBoost + Isolation Forest model.",
        ),
        PlanStep(
            tool="generate_explanation",
            reason="Produce analyst-readable reasons for flagged structuring behaviour.",
        ),
    ]


def _plan_for_rule_query(filters: Dict[str, Any]) -> List[PlanStep]:
    if filters.get("rapid_transactions"):
        reason = "Query asks for rapid-transaction behaviour — solvable with deterministic rules."
    elif filters.get("near_threshold"):
        reason = "Query targets near-threshold activity — no ML required."
    elif filters.get("min_daily_volume"):
        reason = "Query targets high daily volume — aggregation rules are sufficient."
    else:
        reason = (
            "Query specifies transaction-count thresholds — "
            "answerable with the rule engine only (no ML needed)."
        )

    return [PlanStep(tool="rule_engine", reason=reason)]


def _plan_for_customer_lookup(filters: Dict[str, Any]) -> List[PlanStep]:
    customer_id = filters.get("customer_id", "unknown")
    return [
        PlanStep(
            tool="customer_summary",
            reason=f"Retrieve transaction history and exposure for customer {customer_id}.",
        ),
        PlanStep(
            tool="generate_risk",
            reason="Evaluate highest-risk activity for this customer's account.",
        ),
        PlanStep(
            tool="generate_explanation",
            reason="Summarise why the customer's activity may be suspicious.",
        ),
    ]


def _plan_for_transaction_lookup(filters: Dict[str, Any]) -> List[PlanStep]:
    tx_id = filters.get("transaction_id", "unknown")
    return [
        PlanStep(
            tool="transaction_summary",
            reason=f"Fetch full details for transaction {tx_id}.",
        ),
        PlanStep(
            tool="generate_explanation",
            reason="Explain risk indicators for this specific transaction.",
        ),
    ]


def _plan_for_top_suspicious(filters: Dict[str, Any]) -> List[PlanStep]:
    return [
        PlanStep(
            tool="top_suspicious_transactions",
            reason="Return pre-ranked highest-risk transactions from the hybrid model.",
        ),
        PlanStep(
            tool="generate_explanation",
            reason="Attach human-readable explanations to the top flagged cases.",
        ),
    ]


def _plan_for_eda(filters: Dict[str, Any]) -> List[PlanStep]:
    return [
        PlanStep(
            tool="run_eda",
            reason="Provide dataset overview statistics for the judge demo.",
        ),
    ]


def _plan_for_general(filters: Dict[str, Any]) -> List[PlanStep]:
    return [
        PlanStep(
            tool="run_eda",
            reason="Start with dataset overview to orient the analysis.",
        ),
        PlanStep(
            tool="generate_risk",
            reason="Apply hybrid ML scoring to surface high-risk transactions.",
        ),
        PlanStep(
            tool="generate_explanation",
            reason="Explain why top-scored transactions were flagged.",
        ),
    ]


def build_execution_plan(intent: str, filters: Dict[str, Any]) -> List[PlanStep]:
    """Map intent to the minimal set of tools required."""
    builders = {
        "STRUCTURING": _plan_for_structuring,
        "RULE_QUERY": _plan_for_rule_query,
        "CUSTOMER_LOOKUP": _plan_for_customer_lookup,
        "TRANSACTION_LOOKUP": _plan_for_transaction_lookup,
        "TOP_SUSPICIOUS": _plan_for_top_suspicious,
        "EDA": _plan_for_eda,
    }
    builder = builders.get(intent, _plan_for_general)
    return builder(filters)


def plan_query(query: str) -> PlannerResult:
    """
    Full planner pipeline: intent → entities → filters → AML pattern → plan.

    Args:
        query: Natural-language AML analyst question.

    Returns:
        PlannerResult ready for the router dispatcher.
    """
    intent = detect_intent(query)
    entities = extract_entities(query)
    filters = extract_filters(query, entities)
    aml_pattern = detect_aml_pattern(query, intent, filters)
    execution_plan = build_execution_plan(intent, filters)

    return PlannerResult(
        query=query,
        intent=intent,
        filters=filters,
        entities=entities,
        aml_pattern=aml_pattern,
        execution_plan=execution_plan,
    )


__all__ = [
    "PlanStep",
    "PlannerResult",
    "detect_intent",
    "extract_entities",
    "extract_filters",
    "detect_aml_pattern",
    "build_execution_plan",
    "plan_query",
]
