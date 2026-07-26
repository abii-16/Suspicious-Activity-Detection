"""
router.py

Execution dispatcher for the AML Agent.

Receives a planner result, invokes only the required tools, tracks timing,
and assembles the final API response including a judge-friendly
``execution_summary``.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from backend.planner import PlannerResult, plan_query
from backend.tools import (
    customer_summary,
    filter_data,
    generate_explanation,
    generate_risk,
    rule_engine,
    run_eda,
    top_suspicious_transactions,
    transaction_summary,
)
from backend.utils import format_duration_ms, safe_json

logger = logging.getLogger(__name__)

ToolFn = Callable[..., Dict[str, Any]]

# Maps planner tool names → callable (router holds no AML/ML logic)
_TOOL_REGISTRY: Dict[str, ToolFn] = {
    "filter_data": filter_data,
    "run_eda": run_eda,
    "generate_risk": generate_risk,
    "generate_explanation": generate_explanation,
    "rule_engine": rule_engine,
    "customer_summary": customer_summary,
    "transaction_summary": transaction_summary,
    "top_suspicious_transactions": top_suspicious_transactions,
}


def _invoke_tool(
    tool_name: str,
    filters: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Dispatch a single tool call with appropriate arguments."""
    if tool_name == "customer_summary":
        customer_id = filters.get("customer_id") or context.get("customer_id")
        if customer_id is None:
            raise ValueError("customer_summary requires a customer_id entity.")
        return customer_summary(int(customer_id), filters)

    if tool_name == "transaction_summary":
        transaction_id = filters.get("transaction_id") or context.get("transaction_id")
        if transaction_id is None:
            raise ValueError("transaction_summary requires a transaction_id entity.")
        return transaction_summary(int(transaction_id), filters)

    if tool_name == "rule_engine":
        return rule_engine(filters)

    if tool_name == "generate_explanation":
        transaction_id = filters.get("transaction_id")
        if transaction_id is not None:
            return generate_explanation(transaction_id=int(transaction_id), filters=filters)
        return generate_explanation(filters=filters)

    if tool_name in {"run_eda", "generate_risk", "filter_data", "top_suspicious_transactions"}:
        return _TOOL_REGISTRY[tool_name](filters)

    raise KeyError(f"Unknown tool: {tool_name}")


def _build_execution_summary(
    planner_result: PlannerResult,
    tools_executed: List[Dict[str, Any]],
    total_seconds: float,
) -> Dict[str, Any]:
    """
    Build a demo-friendly execution trace for hackathon judges.

    Surfaces the full reasoning chain: what was understood, what was
    planned, what ran, and why.
    """
    tool_selection_rationale = [
        {
            "tool": step.tool,
            "reason": step.reason,
            "executed": any(entry["tool"] == step.tool for entry in tools_executed),
        }
        for step in planner_result.execution_plan
    ]

    return safe_json(
        {
            "user_query": planner_result.query,
            "detected_intent": planner_result.intent,
            "extracted_filters": planner_result.filters,
            "extracted_entities": planner_result.entities,
            "selected_aml_pattern": planner_result.aml_pattern,
            "execution_plan": [step.tool for step in planner_result.execution_plan],
            "execution_plan_detail": [
                {"step": step.tool, "reason": step.reason}
                for step in planner_result.execution_plan
            ],
            "tools_executed": tools_executed,
            "tool_selection_rationale": tool_selection_rationale,
            "total_execution_time_ms": format_duration_ms(total_seconds),
            "total_execution_time_seconds": round(total_seconds, 4),
        }
    )


def _summarise_results(results: Dict[str, Any]) -> Dict[str, str]:
    """Derive top-level risk_level, explanation, and recommendation."""
    risk_level_value = "LOW"
    explanation = "Analysis completed."
    recommendation = "Continue monitoring."

    if "generate_risk" in results:
        risk_data = results["generate_risk"]
        risk_level_value = risk_data.get("top_risk_level", risk_level_value)
        top_tx = (risk_data.get("transactions") or [{}])[0]
        recommendation = top_tx.get("recommendation", recommendation)

    if "customer_summary" in results:
        customer = results["customer_summary"]
        if customer.get("found"):
            risk_level_value = customer.get("risk_level", risk_level_value)
            recommendation = customer.get("recommendation", recommendation)

    if "transaction_summary" in results:
        tx = results["transaction_summary"]
        if tx.get("found"):
            risk_level_value = tx.get("risk_level", risk_level_value)
            recommendation = tx.get("recommendation", recommendation)
            explanation = " | ".join(tx.get("reasons", []))

    if "top_suspicious_transactions" in results:
        top = results["top_suspicious_transactions"]
        txs = top.get("transactions") or []
        if txs:
            risk_level_value = txs[0].get("risk_level", risk_level_value)

    if "generate_explanation" in results:
        expl = results["generate_explanation"]
        if expl.get("explanation"):
            explanation = expl["explanation"]
        elif expl.get("explanations"):
            explanation = expl["explanations"][0].get("explanation", explanation)
        elif expl.get("reasons"):
            explanation = " | ".join(expl["reasons"])

    if "rule_engine" in results:
        rule_data = results["rule_engine"]
        match_count = rule_data.get("match_count", 0)
        explanation = (
            f"Rule engine matched {match_count} accounts under rule "
            f"'{rule_data.get('rule_type', 'custom')}'."
        )
        recommendation = (
            "Review matched accounts manually."
            if match_count
            else "No rule matches — continue monitoring."
        )
        risk_level_value = "HIGH" if match_count else "LOW"

    if "run_eda" in results and len(results) == 1:
        eda = results["run_eda"]
        explanation = (
            f"Dataset contains {eda.get('rows', 0):,} transactions "
            f"with {eda.get('fraud_pct', 0)}% labelled as laundering."
        )
        recommendation = "Use targeted queries to investigate specific patterns."

    return {
        "risk_level": risk_level_value,
        "explanation": explanation,
        "recommendation": recommendation,
    }


def execute_plan(planner_result: PlannerResult) -> Dict[str, Any]:
    """
    Execute the planner's tool chain and return the full query response.

    Args:
        planner_result: Output from ``plan_query``.

    Returns:
        JSON-serialisable response including ``execution_summary``.
    """
    started = time.perf_counter()
    results: Dict[str, Any] = {}
    tools_executed: List[Dict[str, Any]] = []
    context = dict(planner_result.entities)

    for step in planner_result.execution_plan:
        tool_started = time.perf_counter()
        tool_name = step.tool

        try:
            logger.info("Executing tool: %s", tool_name)
            output = _invoke_tool(tool_name, planner_result.filters, context)
            elapsed = time.perf_counter() - tool_started

            results[tool_name] = output
            tools_executed.append(
                safe_json(
                    {
                        "tool": tool_name,
                        "status": "success",
                        "duration_ms": format_duration_ms(elapsed),
                        "reason": step.reason,
                    }
                )
            )
        except Exception as exc:
            elapsed = time.perf_counter() - tool_started
            logger.exception("Tool %s failed", tool_name)
            tools_executed.append(
                safe_json(
                    {
                        "tool": tool_name,
                        "status": "error",
                        "duration_ms": format_duration_ms(elapsed),
                        "reason": step.reason,
                        "error": str(exc),
                    }
                )
            )
            results[tool_name] = {"error": str(exc)}

    total_seconds = time.perf_counter() - started
    summary_fields = _summarise_results(results)

    response = {
        "query": planner_result.query,
        "intent": planner_result.intent,
        "filters": planner_result.filters,
        "entities": planner_result.entities,
        "aml_pattern": planner_result.aml_pattern,
        "execution_plan": [step.tool for step in planner_result.execution_plan],
        "tools_executed": [entry["tool"] for entry in tools_executed],
        "results": results,
        "risk_level": summary_fields["risk_level"],
        "explanation": summary_fields["explanation"],
        "recommendation": summary_fields["recommendation"],
        "execution_summary": _build_execution_summary(
            planner_result,
            tools_executed,
            total_seconds,
        ),
    }

    return safe_json(response)


def handle_query(query: str) -> Dict[str, Any]:
    """End-to-end entry point: plan → execute → respond."""
    planner_result = plan_query(query)
    return execute_plan(planner_result)


__all__ = ["execute_plan", "handle_query"]
