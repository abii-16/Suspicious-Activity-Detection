"""
router.py

Execution dispatcher for the AML Agent.

Executes the planner's tool chain, tracks timing, assembles the full
response including planner reasoning, execution summary, and intent-specific
LLM report.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from backend.llm import generate_investigation_report, generate_natural_response, is_llm_available
from backend.planner import PlannerResult, plan_query
from backend.tools import (
    analytics_tool,
    comparison_tool,
    customer_summary,
    filter_data,
    generate_explanation,
    generate_risk,
    investigation_tool,
    knowledge_tool,
    pattern_detection_tool,
    rule_engine,
    run_eda,
    top_suspicious_transactions,
    transaction_summary,
)
from backend.utils import format_duration_ms, safe_json

logger = logging.getLogger(__name__)

ToolFn = Callable[..., Dict[str, Any]]

_TOOL_REGISTRY: Dict[str, ToolFn] = {
    "filter_data": filter_data,
    "run_eda": run_eda,
    "generate_risk": generate_risk,
    "generate_explanation": generate_explanation,
    "rule_engine": rule_engine,
    "customer_summary": customer_summary,
    "transaction_summary": transaction_summary,
    "top_suspicious_transactions": top_suspicious_transactions,
    # specialised tools
    "analytics_tool": analytics_tool,
    "comparison_tool": comparison_tool,
    "investigation_tool": investigation_tool,
    "knowledge_tool": knowledge_tool,
    "pattern_detection_tool": pattern_detection_tool,
}


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def _extract_top_customer_id(top_result: Dict[str, Any]) -> Optional[int]:
    """Pull the account ID of the highest-risk transaction from top_suspicious result."""
    txs = top_result.get("transactions") or []
    if txs:
        return txs[0].get("account")
    return None


def _extract_top_transaction_id(top_result: Dict[str, Any]) -> Optional[int]:
    """Pull the transaction_id of the highest-risk entry from top_suspicious result."""
    txs = top_result.get("transactions") or []
    if txs:
        return txs[0].get("transaction_id")
    return None


def _invoke_tool(
    tool_name: str,
    filters: Dict[str, Any],
    context: Dict[str, Any],
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Dispatch a single tool call, resolving any missing parameters from
    previously executed tool outputs (dynamic tool chaining).
    """
    # ── analytics / comparison / knowledge / pattern tools ───────────────
    if tool_name == "analytics_tool":
        return analytics_tool(
            group_by=context.get("group_by") or filters.get("group_by", "bank"),
            metric=context.get("metric") or filters.get("metric", "suspicious_transactions"),
            top_n=int(context.get("top_n") or filters.get("top_n") or 10),
        )

    if tool_name == "comparison_tool":
        return comparison_tool(
            entity_type=context.get("entity_type") or filters.get("entity_type", "bank"),
            entity_ids=context.get("entity_ids") or filters.get("entity_ids"),
            top_n=int(context.get("top_n") or filters.get("top_n") or 5),
        )

    if tool_name == "knowledge_tool":
        return knowledge_tool(
            topic=context.get("knowledge_topic") or filters.get("knowledge_topic", "overview"),
        )

    if tool_name == "pattern_detection_tool":
        # Extract pattern type from filters or context; default structuring
        ptype = (context.get("pattern_type") or filters.get("pattern_type") or
                 filters.get("aml_pattern", "").lower().replace(" / ", "_").replace(" ", "_").replace("/", "_") or
                 "structuring")
        # Normalise common names
        ptype_map = {"structuring_smurfing": "structuring", "rapid_transaction_pattern": "rapid_transactions",
                     "cross_border_layering": "cross_bank", "large_value_transfer": "high_value"}
        ptype = ptype_map.get(ptype, ptype)
        return pattern_detection_tool(pattern_type=ptype, top_n=20)

    if tool_name == "investigation_tool":
        cid = context.get("customer_id") or filters.get("customer_id")
        tid = context.get("transaction_id") or filters.get("transaction_id")
        bid = context.get("bank_id") or filters.get("bank_id")
        return investigation_tool(customer_id=cid, transaction_id=tid, bank_id=bid)

    # ── customer_summary ────────────────────────────────────────────────
    if tool_name == "customer_summary":
        cid = filters.get("customer_id") or context.get("customer_id")

        # Dynamic resolution: if top_suspicious already ran, use its top account
        if cid is None and "top_suspicious_transactions" in results:
            cid = _extract_top_customer_id(results["top_suspicious_transactions"])
            if cid is not None:
                context["customer_id"] = cid  # propagate for downstream tools
                logger.info("Resolved customer_id=%s from top_suspicious_transactions", cid)

        if cid is None:
            raise ValueError("customer_summary requires a customer_id — not found in query or prior results.")
        return customer_summary(int(cid), {k: v for k, v in filters.items() if k != "customer_id"})

    # ── transaction_summary ──────────────────────────────────────────────
    if tool_name == "transaction_summary":
        tid = filters.get("transaction_id") or context.get("transaction_id")

        # Dynamic resolution: if top_suspicious already ran, use its top transaction
        if tid is None and "top_suspicious_transactions" in results:
            tid = _extract_top_transaction_id(results["top_suspicious_transactions"])
            if tid is not None:
                context["transaction_id"] = tid
                logger.info("Resolved transaction_id=%s from top_suspicious_transactions", tid)

        if tid is None:
            raise ValueError("transaction_summary requires a transaction_id — not found in query or prior results.")
        return transaction_summary(int(tid))

    # ── rule_engine ──────────────────────────────────────────────────────
    if tool_name == "rule_engine":
        return rule_engine(filters)

    # ── generate_explanation ─────────────────────────────────────────────
    if tool_name == "generate_explanation":
        # If a specific transaction was resolved, explain it
        tid = context.get("transaction_id") or filters.get("transaction_id")
        # For customer investigations, use customer-scoped filter
        cid = context.get("customer_id") or filters.get("customer_id")
        if tid is not None:
            try:
                return generate_explanation(transaction_id=int(tid), filters={"customer_id": cid} if cid else {})
            except (TypeError, ValueError):
                pass
        if cid is not None:
            return generate_explanation(filters={"customer_id": cid})
        return generate_explanation(filters=filters)

    # ── generate_risk ────────────────────────────────────────────────────
    if tool_name == "generate_risk":
        # Scope to discovered customer if available
        cid = context.get("customer_id") or filters.get("customer_id")
        if cid is not None:
            return generate_risk({"customer_id": cid})
        return generate_risk(filters)

    # ── top_suspicious_transactions ──────────────────────────────────────
    if tool_name == "top_suspicious_transactions":
        n = context.get("top_n") or filters.get("top_n") or 20
        return top_suspicious_transactions(int(n), {k: v for k, v in filters.items() if k not in ("customer_id", "transaction_id")})

    # ── remaining registry tools ─────────────────────────────────────────
    if tool_name in _TOOL_REGISTRY:
        return _TOOL_REGISTRY[tool_name](filters)

    raise KeyError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------------------------
# Result summariser
# ---------------------------------------------------------------------------

def _summarise_results(results: Dict[str, Any]) -> Dict[str, str]:
    risk_level = "LOW"
    explanation = "Analysis completed."
    recommendation = "Continue monitoring."

    if "run_eda" in results and len(results) == 1:
        eda = results["run_eda"]
        explanation = (
            f"Dataset contains {eda.get('rows', 0):,} transactions "
            f"with {eda.get('fraud_pct', 0)}% labelled as laundering."
        )
        recommendation = "Use targeted queries to investigate specific patterns."

    if "generate_risk" in results:
        r = results["generate_risk"]
        risk_level = r.get("top_risk_level", risk_level)
        top = (r.get("transactions") or [{}])[0]
        recommendation = top.get("recommendation", recommendation)

    if "customer_summary" in results:
        c = results["customer_summary"]
        if c.get("found"):
            risk_level = c.get("risk_level", risk_level)
            recommendation = c.get("recommendation", recommendation)

    if "transaction_summary" in results:
        t = results["transaction_summary"]
        if t.get("found"):
            risk_level = t.get("risk_level", risk_level)
            recommendation = t.get("recommendation", recommendation)
            explanation = " | ".join(t.get("reasons", []))

    if "top_suspicious_transactions" in results:
        txs = (results["top_suspicious_transactions"].get("transactions") or [])
        if txs:
            risk_level = txs[0].get("risk_level", risk_level)

    if "generate_explanation" in results:
        e = results["generate_explanation"]
        if e.get("explanation"):
            explanation = e["explanation"]
        elif e.get("explanations"):
            explanation = (e["explanations"][0] or {}).get("explanation", explanation)
        elif e.get("reasons"):
            explanation = " | ".join(e["reasons"])

    if "rule_engine" in results:
        r = results["rule_engine"]
        mc = r.get("match_count", 0)
        explanation = f"Rule engine matched {mc} accounts under rule '{r.get('rule_type', 'custom')}'."
        recommendation = "Review matched accounts manually." if mc else "No rule matches — continue monitoring."
        risk_level = "HIGH" if mc else "LOW"

    return {"risk_level": risk_level, "explanation": explanation, "recommendation": recommendation}


def _extract_risk_score(results: Dict[str, Any]) -> Optional[float]:
    if "generate_risk" in results:
        txs = results["generate_risk"].get("transactions") or []
        if txs:
            return txs[0].get("risk_score")
    if "transaction_summary" in results:
        t = results["transaction_summary"]
        if t.get("found"):
            return t.get("risk_score")
    if "customer_summary" in results:
        c = results["customer_summary"]
        if c.get("found"):
            return c.get("max_risk_score")
    if "top_suspicious_transactions" in results:
        txs = results["top_suspicious_transactions"].get("transactions") or []
        if txs:
            return txs[0].get("risk_score")
    return None


# ---------------------------------------------------------------------------
# Execution summary builder
# ---------------------------------------------------------------------------

def _build_execution_summary(
    planner: PlannerResult,
    tools_executed: List[Dict[str, Any]],
    total_seconds: float,
) -> Dict[str, Any]:
    rationale = [
        {
            "tool": s.tool,
            "reason": s.reason,
            "executed": any(e["tool"] == s.tool for e in tools_executed),
        }
        for s in planner.execution_plan
    ]

    return safe_json({
        "user_query": planner.query,
        "detected_intent": planner.intent,
        "intent_label": planner.intent_label,
        "extracted_filters": planner.filters,
        "extracted_entities": planner.entities,
        "selected_aml_pattern": planner.aml_pattern,
        "execution_plan": [s.tool for s in planner.execution_plan],
        "execution_plan_detail": [{"step": s.tool, "reason": s.reason} for s in planner.execution_plan],
        "tools_executed": tools_executed,
        "tool_selection_rationale": rationale,
        "planner_reasoning": [
            {"thought": t.thought, "conclusion": t.conclusion}
            for t in planner.reasoning
        ],
        "total_execution_time_ms": format_duration_ms(total_seconds),
        "total_execution_time_seconds": round(total_seconds, 4),
    })


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

def execute_plan(planner: PlannerResult, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    started = time.perf_counter()
    results: Dict[str, Any] = {}
    tools_executed: List[Dict[str, Any]] = []
    context = dict(planner.entities)

    for step in planner.execution_plan:
        t0 = time.perf_counter()
        try:
            logger.info("Executing tool: %s", step.tool)
            output = _invoke_tool(step.tool, planner.filters, context, results)
            elapsed = time.perf_counter() - t0
            results[step.tool] = output
            tools_executed.append(safe_json({
                "tool": step.tool,
                "status": "success",
                "duration_ms": format_duration_ms(elapsed),
                "reason": step.reason,
            }))
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            logger.exception("Tool %s failed", step.tool)
            tools_executed.append(safe_json({
                "tool": step.tool,
                "status": "error",
                "duration_ms": format_duration_ms(elapsed),
                "reason": step.reason,
                "error": str(exc),
            }))
            results[step.tool] = {"error": str(exc)}

    total_seconds = time.perf_counter() - started
    summary_fields = _summarise_results(results)
    execution_summary = _build_execution_summary(planner, tools_executed, total_seconds)

    # Build intent-specific LLM context — only pass non-empty tool results
    llm_context = {
        "query": planner.query,
        "intent": planner.intent,
        "intent_label": planner.intent_label,
        "aml_pattern": planner.aml_pattern,
        "risk_level": summary_fields["risk_level"],
        "risk_score": _extract_risk_score(results),
        "explanation": summary_fields["explanation"],
        "recommendation": summary_fields["recommendation"],
        "results": {k: v for k, v in results.items() if not (isinstance(v, dict) and v.get("error"))},
        "conversation_history": conversation_history or [],
        "execution_summary": {
            "plan": [s.tool for s in planner.execution_plan],
            "intent": planner.intent,
        },
    }

    t_llm = time.perf_counter()
    investigation_report = generate_investigation_report(llm_context)
    natural_response = generate_natural_response(llm_context, investigation_report)
    llm_elapsed = time.perf_counter() - t_llm

    tools_executed.append(safe_json({
        "tool": "llm_investigation_report",
        "status": "success" if investigation_report.get("available") else "fallback",
        "duration_ms": format_duration_ms(llm_elapsed),
        "reason": f"Generate intent-specific LLM report ({planner.intent_label})",
        "model": investigation_report.get("model"),
    }))

    execution_summary["tools_executed"] = tools_executed
    execution_summary["llm_available"] = is_llm_available()
    execution_summary["llm_inference_time_ms"] = investigation_report.get(
        "inference_time_ms", format_duration_ms(llm_elapsed)
    )

    # Pipeline = only tools that actually ran, in execution order, plus fixed bookends
    executed_tool_names = [e["tool"] for e in tools_executed if e["status"] != "error"]
    execution_summary["pipeline"] = [
        "planner",
        "router",
        *[s.tool for s in planner.execution_plan if s.tool in set(executed_tool_names)],
        "llm",
        "response",
    ]

    return safe_json({
        "query": planner.query,
        "intent": planner.intent,
        "intent_label": planner.intent_label,
        "filters": planner.filters,
        "entities": {**planner.entities, **{k: v for k, v in context.items() if k not in planner.entities}},
        "aml_pattern": planner.aml_pattern,
        "execution_plan": [s.tool for s in planner.execution_plan],
        "tools_executed": [e["tool"] for e in tools_executed],
        "results": results,
        "risk_level": summary_fields["risk_level"],
        "risk_score": _extract_risk_score(results),
        "explanation": summary_fields["explanation"],
        "recommendation": summary_fields["recommendation"],
        "natural_response": natural_response,
        "planner_reasoning": [
            {"thought": t.thought, "conclusion": t.conclusion}
            for t in planner.reasoning
        ],
        "investigation_report": investigation_report,
        "execution_summary": execution_summary,
    })


def handle_query(query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Resolve context from conversation history, then plan and execute.
    Supports pronouns like "this customer", "that transaction", "it".
    """
    history = conversation_history or []
    resolved_query = _resolve_context(query, history)
    planner = plan_query(resolved_query)
    return execute_plan(planner, history)


def _resolve_context(query: str, history: List[Dict[str, Any]]) -> str:
    """
    If the user references a previous entity with a pronoun or implicit reference,
    inject the entity ID from the last turn so the planner can extract it.
    """
    if not history:
        return query

    lowered = query.lower()
    # Pronouns that suggest the user is referring to a previous result
    implicit = any(word in lowered for word in (
        "this customer", "that customer", "the customer",
        "this transaction", "that transaction", "the transaction",
        "this account", "that account", "it", "they", "their",
        "same", "above", "previous",
    ))
    if not implicit:
        return query

    # Look back through history for the most recent entity
    for turn in reversed(history):
        entities = turn.get("entities", {})
        cid = entities.get("customer_id")
        tid = entities.get("transaction_id")
        if tid and any(w in lowered for w in ("transaction", "it", "same", "above", "previous")):
            return f"{query} (transaction {tid})"
        if cid and any(w in lowered for w in ("customer", "account", "it", "they", "their", "same", "above")):
            return f"{query} (customer {cid})"

    return query


__all__ = ["execute_plan", "handle_query"]
