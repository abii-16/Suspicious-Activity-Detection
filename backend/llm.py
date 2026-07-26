"""
llm.py

Groq LLM integration — strict data-grounded, intent-specific reports.

Hard constraints:
- Only values explicitly present in tool output are mentioned.
- Missing fields are omitted entirely (not filled with "not available").
- No inference, no opinions, no invented context.
- Each intent has a unique prompt and a unique response schema.
- Max 1024 tokens, temperature 0.1 for minimal creativity.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils import safe_json

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

_groq_client: Optional[Any] = None
_client_checked = False


def _get_api_key() -> Optional[str]:
    return os.getenv("GROQ_API_KEY", "").strip() or None


def get_groq_client() -> Optional[Any]:
    global _groq_client, _client_checked
    if _client_checked:
        return _groq_client
    _client_checked = True
    api_key = _get_api_key()
    if not api_key:
        logger.warning("GROQ_API_KEY not set — LLM reports disabled.")
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
        logger.info("Groq client initialised (model=%s).", GROQ_MODEL)
    except Exception as exc:
        logger.error("Failed to initialise Groq client: %s", exc)
        _groq_client = None
    return _groq_client


def is_llm_available() -> bool:
    return get_groq_client() is not None


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an AML data analyst. Your only job is to summarize numbers and facts from tool outputs.

ABSOLUTE RULES:
1. Only state values that appear explicitly in the TOOL DATA block.
2. Do not infer, interpret, or add context beyond what the data shows.
3. Do not say things like "this is concerning" or "this is high" unless the data explicitly labels it.
4. If a field is absent from TOOL DATA, omit that section entirely. Do not write "not available".
5. Use bullet points. Be concise. No paragraphs longer than 2 sentences.
6. Respond with valid JSON only. No markdown fences. No text outside the JSON."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_ran(results: Dict[str, Any], tool: str) -> bool:
    v = results.get(tool)
    return v is not None and not (isinstance(v, dict) and v.get("error"))


def _j(data: Any, limit: int = 3000) -> str:
    return json.dumps(safe_json(data), indent=2, default=str)[:limit]


def _strip(d: Dict[str, Any], exclude: List[str]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if k not in exclude and v is not None}


# ---------------------------------------------------------------------------
# Intent-specific prompt builders
# ---------------------------------------------------------------------------

def _build_dataset_prompt(ctx: Dict[str, Any]) -> str:
    eda = ctx["results"].get("run_eda", {})

    # Only pass the fields that are actually present and non-null
    data = {k: v for k, v in {
        "total_rows":                    eda.get("total_rows"),
        "total_columns":                 eda.get("total_columns"),
        "fraud_percentage":              eda.get("fraud_percentage"),
        "total_laundering_transactions": eda.get("total_laundering_transactions"),
        "average_amount_formatted":      eda.get("average_amount_formatted"),
        "amount_min":                    eda.get("amount_min"),
        "amount_max_formatted":          eda.get("amount_max_formatted"),
        "amount_median":                 eda.get("amount_median"),
        "top_banks":                     eda.get("top_banks") or {},
        "top_currencies":                eda.get("top_currencies") or {},
        "payment_formats":               eda.get("payment_formats") or {},
        "risk_distribution":             eda.get("risk_distribution") or {},
        "top_fraud_bank":                eda.get("top_fraud_bank"),
        "dataset_summary":               eda.get("dataset_summary"),
    }.items() if v is not None and v != {} and v != []}

    # Build concrete suggested queries from actual bank IDs in the data
    top_bank_ids = list((eda.get("top_banks") or {}).keys())[:3]
    bank_queries = [f"Analyze Bank {b}" for b in top_bank_ids]
    suggested = [
        "Show top 20 most suspicious transactions",
        "Find structuring patterns in transactions",
        "Find accounts with rapid transactions",
    ] + bank_queries

    return f"""User query: "{ctx['query']}"
Executed tool: run_eda

TOOL DATA:
{_j(data)}

Summarize ONLY the numbers from TOOL DATA above. Do not add interpretations.
Return JSON with exactly these keys (omit a key if data is absent):
{{
  "dataset_summary": "One sentence using total_rows, total_columns, fraud_percentage from data",
  "key_statistics": "Bullet list: state each numeric value exactly as given — total rows, fraud %, avg amount, laundering count",
  "key_insights": ["3 observations that directly quote numbers from the data — no opinions"],
  "suggested_next_queries": {json.dumps(suggested)}
}}"""


def _build_customer_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    cust = _strip(results.get("customer_summary", {}), ["recent_transactions", "found"])
    risk_txs = (results.get("generate_risk", {}).get("transactions") or [])[:3] if _tool_ran(results, "generate_risk") else []
    expl = results.get("generate_explanation", {}) if _tool_ran(results, "generate_explanation") else {}
    rule = results.get("rule_engine", {}) if _tool_ran(results, "rule_engine") else {}

    data: Dict[str, Any] = {}
    if cust: data["customer"] = cust
    if risk_txs: data["top_risk_transactions"] = risk_txs
    if expl.get("reasons"): data["flag_reasons"] = expl["reasons"]
    if rule.get("match_count"): data["rule_matches"] = {"rule_type": rule.get("rule_type"), "match_count": rule.get("match_count"), "top_matches": (rule.get("matches") or [])[:3]}

    is_suspicious = cust.get("is_suspicious", False)
    suspicious_count = cust.get("suspicious_transactions", 0)
    high_risk_pct = cust.get("high_risk_pct", 0)
    level = str(cust.get("risk_level", "LOW")).upper()

    if not is_suspicious or (suspicious_count == 0 and high_risk_pct == 0 and level not in ("HIGH", "CRITICAL")):
        risk_instruction = (
            "suspicious_transactions=0 and high_risk_pct=0. "
            "Do NOT say the customer was flagged. "
            "Omit the why_flagged key entirely. "
            "The recommended_action should be: 'Continue standard monitoring.'"
        )
    elif level in ("HIGH", "CRITICAL"):
        risk_instruction = (
            f"The customer has {suspicious_count} suspicious transactions and {high_risk_pct}% high-risk activity. "
            "Describe the specific risk indicators from top_risk_reasons/flag_reasons. "
            "Recommend escalation or manual review."
        )
    else:
        risk_instruction = (
            f"The customer shows some risk indicators (risk_level={level}, suspicious_transactions={suspicious_count}). "
            "Describe what was found without overstating the risk. Recommend continued monitoring."
        )

    return f"""User query: "{ctx['query']}"
Executed tools: {', '.join(t for t in ['customer_summary','generate_risk','generate_explanation','rule_engine'] if _tool_ran(results, t))}

TOOL DATA:
{_j(data)}

Risk instruction: {risk_instruction}

Summarize ONLY what is in TOOL DATA. Follow the risk instruction above exactly.
Return JSON with exactly these keys (omit key if data absent):
{{
  "customer_summary": "State customer_id, transaction_count, total_amount_sent, risk_level — exact values",
  "risk_score": "State max_risk_score and risk_level exactly as in data",
  "why_flagged": "ONLY include if is_suspicious=true. Bullet list from top_risk_reasons/flag_reasons — copy exact strings. If not suspicious, omit this key entirely.",
  "recommended_action": "Copy exact recommendation string from customer data. If LOW risk with no suspicious activity, say: Continue standard monitoring."
}}"""


def _build_transaction_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    tx = _strip(results.get("transaction_summary", {}), ["features", "found"]) if _tool_ran(results, "transaction_summary") else {}
    risk_txs = (results.get("generate_risk", {}).get("transactions") or [])[:2] if _tool_ran(results, "generate_risk") else []
    expl = results.get("generate_explanation", {}) if _tool_ran(results, "generate_explanation") else {}

    data: Dict[str, Any] = {}
    if tx: data["transaction"] = tx
    if risk_txs: data["ml_scores"] = risk_txs
    if expl.get("reasons"): data["flag_reasons"] = expl["reasons"]

    return f"""User query: "{ctx['query']}"
Executed tools: {', '.join(t for t in ['transaction_summary','generate_risk','generate_explanation'] if _tool_ran(results, t))}

TOOL DATA:
{_j(data)}

Summarize ONLY what is in TOOL DATA.
Return JSON with exactly these keys (omit key if data absent):
{{
  "transaction_summary": "State transaction_id, amount_paid, account, from_bank, to_bank — exact values",
  "risk_analysis": "State xgb_score, isolation_anomaly, risk_score, risk_level — exact values only",
  "rule_violations": "Bullet list from flag_reasons — copy exact strings",
  "recommended_action": "Copy exact recommendation string from transaction data"
}}"""


def _build_pattern_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    rule = results.get("rule_engine", {}) if _tool_ran(results, "rule_engine") else {}
    risk_txs = (results.get("generate_risk", {}).get("transactions") or [])[:5] if _tool_ran(results, "generate_risk") else []
    filt = results.get("filter_data", {}) if _tool_ran(results, "filter_data") else {}
    expl = results.get("generate_explanation", {}) if _tool_ran(results, "generate_explanation") else {}

    data: Dict[str, Any] = {}
    if filt: data["filter_scope"] = {"filtered_rows": filt.get("filtered_rows"), "filters_applied": filt.get("filters_applied")}
    if rule: data["rule_engine"] = {"rule_type": rule.get("rule_type"), "match_count": rule.get("match_count"), "top_matches": (rule.get("matches") or [])[:5]}
    if risk_txs: data["top_risk_transactions"] = risk_txs
    if expl.get("reasons"): data["flag_reasons"] = expl["reasons"]

    return f"""User query: "{ctx['query']}"
AML pattern: {ctx.get('aml_pattern', 'unknown')}
Executed tools: {', '.join(t for t in ['filter_data','rule_engine','generate_risk','generate_explanation'] if _tool_ran(results, t))}

TOOL DATA:
{_j(data)}

Summarize ONLY what is in TOOL DATA.
Return JSON with exactly these keys (omit key if data absent):
{{
  "pattern_found": "State rule_type and aml_pattern — exact values from data",
  "evidence": "Bullet list: state match_count, top account IDs and their counts — exact numbers",
  "affected_accounts": "State exact match_count number from rule_engine data",
  "recommendation": "State the recommendation based on risk_level in data"
}}"""


def _build_top_suspicious_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    top = results.get("top_suspicious_transactions", {})
    transactions = (top.get("transactions") or [])[:10]
    expl = results.get("generate_explanation", {}) if _tool_ran(results, "generate_explanation") else {}
    expls = (expl.get("explanations") or [])[:5]

    # Compute risk breakdown from actual data
    counts: Dict[str, int] = {}
    for t in transactions:
        lvl = str(t.get("risk_level", "UNKNOWN"))
        counts[lvl] = counts.get(lvl, 0) + 1

    scores = [t.get("risk_score", 0) for t in transactions if t.get("risk_score") is not None]
    score_range = f"{min(scores):.4f} – {max(scores):.4f}" if scores else "N/A"
    top1 = transactions[0] if transactions else {}

    data = {
        "total_returned": top.get("count", len(transactions)),
        "score_range": score_range,
        "risk_breakdown": counts,
        "top_transaction": {"transaction_id": top1.get("transaction_id"), "risk_score": top1.get("risk_score"), "risk_level": top1.get("risk_level"), "account": top1.get("account"), "aml_pattern": top1.get("aml_pattern")},
        "all_transactions": transactions,
        "explanations": expls,
    }

    return f"""User query: "{ctx['query']}"
Executed tools: top_suspicious_transactions{', generate_explanation' if expls else ''}

TOOL DATA:
{_j(data, 5000)}

Summarize ONLY what is in TOOL DATA. State exact numbers.
Return JSON with exactly these keys:
{{
  "screening_summary": "State total_returned and score_range exactly from data",
  "highest_risk_transaction": "State transaction_id, risk_score, risk_level, account — exact values",
  "common_patterns": "Bullet list of aml_pattern values from all_transactions — only patterns that actually appear",
  "risk_breakdown": "State exact counts per risk_level from risk_breakdown field",
  "recommended_actions": "State the recommended action for the highest risk_level found"
}}"""


def _build_analytics_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    eda = _strip(results.get("run_eda", {}), ["statistics", "columns"]) if _tool_ran(results, "run_eda") else {}
    risk = results.get("generate_risk", {}) if _tool_ran(results, "generate_risk") else {}

    data: Dict[str, Any] = {}
    if eda: data["eda"] = {k: v for k, v in eda.items() if k not in ("top_banks_legacy",)}
    if risk: data["model_output"] = {"scored_count": risk.get("scored_count"), "top_risk_level": risk.get("top_risk_level"), "sample_scores": (risk.get("transactions") or [])[:3]}

    return f"""User query: "{ctx['query']}"
Executed tools: {', '.join(t for t in ['run_eda','generate_risk'] if _tool_ran(results, t))}

TOOL DATA:
{_j(data)}

Summarize ONLY what is in TOOL DATA.
Return JSON with exactly these keys (omit key if data absent):
{{
  "model_summary": "State what the hybrid XGBoost + Isolation Forest scored — exact scored_count and top_risk_level",
  "dataset_statistics": "Bullet list of exact numeric values: total_rows, fraud_percentage, average_amount",
  "scoring_analysis": "Bullet list: scored_count, top_risk_level, sample score values — exact from data",
  "model_insights": ["2-3 direct observations quoting numbers from data only"]
}}"""


def _build_explanation_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    expl = results.get("generate_explanation", {}) if _tool_ran(results, "generate_explanation") else {}
    risk_txs = (results.get("generate_risk", {}).get("transactions") or [])[:3] if _tool_ran(results, "generate_risk") else []
    tx = _strip(results.get("transaction_summary", {}), ["features", "found"]) if _tool_ran(results, "transaction_summary") else {}
    cust = _strip(results.get("customer_summary", {}), ["recent_transactions", "found"]) if _tool_ran(results, "customer_summary") else {}

    data: Dict[str, Any] = {}
    if expl: data["explanation"] = _strip(expl, [])
    if risk_txs: data["risk_scores"] = risk_txs
    if tx: data["transaction"] = tx
    if cust: data["customer"] = cust

    return f"""User query: "{ctx['query']}"
Executed tools: {', '.join(t for t in ['generate_explanation','generate_risk','transaction_summary','customer_summary'] if _tool_ran(results, t))}

TOOL DATA:
{_j(data)}

Summarize ONLY what is in TOOL DATA.
Return JSON with exactly these keys (omit key if data absent):
{{
  "explanation_summary": "One sentence stating what was flagged using exact values from data",
  "risk_factors": ["Copy exact strings from explanation.reasons — do not paraphrase"],
  "recommended_action": "Copy exact recommendation string from data"
}}"""


def _build_general_prompt(ctx: Dict[str, Any]) -> str:
    results = ctx["results"]
    ran = [t for t in ["run_eda", "generate_risk", "generate_explanation"] if _tool_ran(results, t)]

    data: Dict[str, Any] = {}
    if _tool_ran(results, "run_eda"):
        eda = results["run_eda"]
        data["eda"] = {k: v for k, v in eda.items() if k not in ("statistics", "columns", "top_banks_legacy") and v is not None}
    if _tool_ran(results, "generate_risk"):
        data["top_risks"] = (results["generate_risk"].get("transactions") or [])[:5]
    if _tool_ran(results, "generate_explanation"):
        data["explanation"] = _strip(results["generate_explanation"], [])

    return f"""User query: "{ctx['query']}"
Executed tools: {', '.join(ran) or 'none'}

TOOL DATA:
{_j(data)}

Summarize ONLY what is in TOOL DATA.
Return JSON with exactly these keys (omit key if data absent):
{{
  "summary": "2 sentences stating what tools ran and what they found — exact values only",
  "key_findings": ["2-4 bullet points quoting exact numbers or strings from TOOL DATA"],
  "recommended_action": "Copy exact recommendation string from data if present"
}}"""


# ---------------------------------------------------------------------------
# Intent router
# ---------------------------------------------------------------------------

_PROMPT_BUILDERS = {
    "DATASET_EXPLORATION":       _build_dataset_prompt,
    "CUSTOMER_INVESTIGATION":    _build_customer_prompt,
    "TRANSACTION_INVESTIGATION": _build_transaction_prompt,
    "PATTERN_DETECTION":         _build_pattern_prompt,
    "TOP_SUSPICIOUS":            _build_top_suspicious_prompt,
    "MODEL_ANALYTICS":           _build_analytics_prompt,
    "RISK_EXPLANATION":          _build_explanation_prompt,
}


def _get_user_prompt(ctx: Dict[str, Any]) -> str:
    intent = ctx.get("intent", "GENERAL")
    return _PROMPT_BUILDERS.get(intent, _build_general_prompt)(ctx)


# ---------------------------------------------------------------------------
# Schema — what keys each intent returns (defines frontend render order)
# ---------------------------------------------------------------------------

INTENT_SCHEMA: Dict[str, List[str]] = {
    "DATASET_EXPLORATION":       ["dataset_summary", "key_statistics", "key_insights", "suggested_next_queries"],
    "CUSTOMER_INVESTIGATION":    ["customer_summary", "risk_score", "why_flagged", "recommended_action"],
    "TRANSACTION_INVESTIGATION": ["transaction_summary", "risk_analysis", "rule_violations", "recommended_action"],
    "PATTERN_DETECTION":         ["pattern_found", "evidence", "affected_accounts", "recommendation"],
    "TOP_SUSPICIOUS":            ["screening_summary", "highest_risk_transaction", "common_patterns", "risk_breakdown", "recommended_actions"],
    "MODEL_ANALYTICS":           ["model_summary", "dataset_statistics", "scoring_analysis", "model_insights"],
    "RISK_EXPLANATION":          ["explanation_summary", "risk_factors", "recommended_action"],
    "GENERAL":                   ["summary", "key_findings", "recommended_action"],
}


def _parse_llm_json(content: str) -> Dict[str, Any]:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _apply_schema(parsed: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """
    Keep only the keys for this intent.
    Omit any key whose value is null, empty string, or empty list.
    """
    keys = INTENT_SCHEMA.get(intent, INTENT_SCHEMA["GENERAL"])
    result: Dict[str, Any] = {}
    for key in keys:
        val = parsed.get(key)
        if val is None or val == "" or val == []:
            continue  # omit — do not fill with placeholder text
        result[key] = val
    return result


# ---------------------------------------------------------------------------
# Fallback — built purely from tool outputs, no LLM
# ---------------------------------------------------------------------------

def _fallback_report(ctx: Dict[str, Any], reason: str) -> Dict[str, Any]:
    intent = ctx.get("intent", "GENERAL")
    results = ctx.get("results", {})
    explanation = ctx.get("explanation", "")
    recommendation_str = ctx.get("recommendation", "")
    aml_pattern = ctx.get("aml_pattern", "")
    risk_level_val = ctx.get("risk_level", "LOW")
    risk_score = ctx.get("risk_score")
    score_text = str(risk_score) if risk_score is not None else ""

    base: Dict[str, Any] = {}

    if intent == "DATASET_EXPLORATION":
        eda = results.get("run_eda", {})
        if eda.get("total_rows"):
            base["dataset_summary"] = eda.get("dataset_summary", "")
            stats_parts = []
            if eda.get("total_rows"): stats_parts.append(f"Total rows: {eda['total_rows']:,}")
            if eda.get("fraud_percentage"): stats_parts.append(f"Fraud rate: {eda['fraud_percentage']}%")
            if eda.get("average_amount_formatted"): stats_parts.append(f"Avg amount: {eda['average_amount_formatted']}")
            if eda.get("total_laundering_transactions"): stats_parts.append(f"Laundering transactions: {eda['total_laundering_transactions']:,}")
            base["key_statistics"] = "\n".join(f"- {s}" for s in stats_parts)
            base["key_insights"] = [
                f"{eda.get('total_rows', 0):,} total transactions in dataset",
                f"{eda.get('fraud_percentage', 0)}% flagged as money laundering",
                f"Average transaction amount: {eda.get('average_amount_formatted', '')}",
            ]
            top_banks = list((eda.get("top_banks") or {}).keys())[:3]
            base["suggested_next_queries"] = [
                "Show top 20 most suspicious transactions",
                "Find structuring patterns in transactions",
                "Find accounts with rapid transactions",
            ] + [f"Analyze Bank {b}" for b in top_banks]

    elif intent == "CUSTOMER_INVESTIGATION":
        cust = results.get("customer_summary", {})
        if cust.get("found"):
            base["customer_summary"] = f"Account {cust.get('customer_id')}: {cust.get('transaction_count')} transactions, ${cust.get('total_amount_sent', 0):,.2f} sent."
            if score_text: base["risk_score"] = f"{risk_level_val} (score: {score_text})"
        if explanation: base["why_flagged"] = explanation
        if recommendation_str: base["recommended_action"] = recommendation_str

    elif intent == "TRANSACTION_INVESTIGATION":
        tx = results.get("transaction_summary", {})
        if tx.get("found"):
            base["transaction_summary"] = f"Txn #{tx.get('transaction_id')}: ${tx.get('amount_paid', 0):,.2f} from account {tx.get('account')}."
            base["risk_analysis"] = f"Risk: {risk_level_val}" + (f", score: {score_text}" if score_text else "") + f", XGB: {tx.get('xgb_score', '')}, Isolation: {'anomaly' if tx.get('isolation_anomaly') else 'normal'}."
        if explanation: base["rule_violations"] = explanation
        if recommendation_str: base["recommended_action"] = recommendation_str

    elif intent == "PATTERN_DETECTION":
        rule = results.get("rule_engine", {})
        if aml_pattern: base["pattern_found"] = aml_pattern
        if rule.get("match_count") is not None:
            base["evidence"] = f"Rule engine matched {rule['match_count']} accounts under rule '{rule.get('rule_type')}'."
            base["affected_accounts"] = str(rule["match_count"])
        if recommendation_str: base["recommendation"] = recommendation_str

    elif intent == "TOP_SUSPICIOUS":
        top = results.get("top_suspicious_transactions", {})
        txs = top.get("transactions") or []
        if txs:
            base["screening_summary"] = f"{len(txs)} transactions returned, score range: {txs[-1].get('risk_score', 0):.4f} – {txs[0].get('risk_score', 0):.4f}."
            t1 = txs[0]
            base["highest_risk_transaction"] = f"Txn #{t1.get('transaction_id')}, score {t1.get('risk_score')}, {t1.get('risk_level')}."
            patterns = list({t.get("aml_pattern") for t in txs if t.get("aml_pattern")})
            if patterns: base["common_patterns"] = "\n".join(f"- {p}" for p in patterns)
            counts: Dict[str, int] = {}
            for t in txs:
                lvl = str(t.get("risk_level", "UNKNOWN"))
                counts[lvl] = counts.get(lvl, 0) + 1
            base["risk_breakdown"] = ", ".join(f"{lvl}: {n}" for lvl, n in counts.items())
        if recommendation_str: base["recommended_actions"] = recommendation_str

    else:
        if explanation: base["summary"] = explanation
        if explanation: base["key_findings"] = [explanation]
        if recommendation_str: base["recommended_action"] = recommendation_str

    base.update({"available": False, "model": None, "error": reason, "intent": intent})
    return safe_json(base)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_investigation_report(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a concise, intent-specific report grounded in tool outputs only.
    Never predicts. Never hallucinates.
    """
    client = get_groq_client()
    if client is None:
        return _fallback_report(ctx, "GROQ_API_KEY not configured")

    started = time.perf_counter()
    try:
        user_prompt = _get_user_prompt(ctx)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        content = response.choices[0].message.content or ""
        parsed = _parse_llm_json(content)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        intent = ctx.get("intent", "GENERAL")
        report = _apply_schema(parsed, intent)
        report["available"] = True
        report["model"] = GROQ_MODEL
        report["inference_time_ms"] = elapsed_ms
        report["intent"] = intent

        return safe_json(report)

    except Exception as exc:
        logger.exception("Groq report generation failed")
        fb = _fallback_report(ctx, str(exc))
        fb["inference_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return fb


_NATURAL_SYSTEM = """You are a professional AML (Anti-Money Laundering) investigation assistant.
You answer analyst questions conversationally, like a knowledgeable colleague.

RULES:
1. Answer in 2-5 sentences maximum. Be concise and direct.
2. Use exact numbers and values from the data provided. Never invent them.
3. If a data field is absent, skip it — do not say "not available".
4. Use markdown: **bold** for risk levels and key numbers, bullet lists when listing multiple items.
5. Do not mention internal system names like "Hybrid ML", "XGBoost", "Isolation Forest", "router", or "planner".
6. End with one clear action recommendation if risk data is present.
7. Respond in plain text + markdown only. No JSON.
8. CRITICAL: If is_suspicious=false OR (suspicious_transactions=0 AND high_risk_pct=0 AND risk_level is not HIGH/CRITICAL), 
   do NOT say the customer was "flagged" or "suspicious". 
   Say instead: "no significant AML risk indicators were detected"."""


def _natural_prompt(ctx: Dict[str, Any], report: Dict[str, Any]) -> str:
    """Build the conversational answer prompt from tool results and structured report."""
    intent = ctx.get("intent", "GENERAL")
    results = ctx.get("results", {})

    # Distil key facts from report and results
    facts: Dict[str, Any] = {}

    if intent == "DATASET_EXPLORATION":
        eda = results.get("run_eda", {})
        facts = {k: eda.get(k) for k in ("total_rows", "fraud_percentage", "total_laundering_transactions", "average_amount_formatted", "dataset_summary", "top_fraud_bank") if eda.get(k) is not None}
        facts["suggested_next_queries"] = report.get("suggested_next_queries", [])

    elif intent == "CUSTOMER_INVESTIGATION":
        cust = _strip(results.get("customer_summary", {}), ["recent_transactions", "found", "top_risk_reasons"])
        is_susp = cust.get("is_suspicious", False)
        facts["customer"] = cust
        facts["is_suspicious"] = is_susp
        if is_susp:
            facts["top_risk_reasons"] = results.get("customer_summary", {}).get("top_risk_reasons", [])
            if report.get("why_flagged"):
                facts["why_flagged"] = report["why_flagged"]

    elif intent == "TRANSACTION_INVESTIGATION":
        tx = _strip(results.get("transaction_summary", {}), ["features", "found"])
        facts["transaction"] = tx
        facts["risk_factors"] = (results.get("generate_explanation", {}).get("reasons") or [])

    elif intent == "PATTERN_DETECTION":
        rule = results.get("rule_engine", {})
        facts["rule_type"] = rule.get("rule_type")
        facts["match_count"] = rule.get("match_count")
        facts["top_matches"] = (rule.get("matches") or [])[:3]
        facts["aml_pattern"] = ctx.get("aml_pattern")
        top_risk = (results.get("generate_risk", {}).get("transactions") or [{}])[0]
        facts["top_risk_score"] = top_risk.get("risk_score")
        facts["top_risk_level"] = top_risk.get("risk_level")

    elif intent == "TOP_SUSPICIOUS":
        top = results.get("top_suspicious_transactions", {})
        txs = top.get("transactions") or []
        facts["count"] = top.get("count", len(txs))
        facts["top_transaction"] = txs[0] if txs else {}
        facts["score_range"] = f"{txs[-1].get('risk_score', 0):.4f}–{txs[0].get('risk_score', 0):.4f}" if txs else ""
        counts: Dict[str, int] = {}
        for t in txs: counts[str(t.get("risk_level","?"))] = counts.get(str(t.get("risk_level","?")),0)+1
        facts["risk_breakdown"] = counts
        facts["recommendation"] = (txs[0].get("recommended_action") or ctx.get("recommendation", "")) if txs else ""

    elif intent == "MODEL_ANALYTICS":
        eda = results.get("run_eda", {})
        risk = results.get("generate_risk", {})
        facts = {k: eda.get(k) for k in ("total_rows","fraud_percentage","average_amount_formatted") if eda.get(k) is not None}
        facts["scored_count"] = risk.get("scored_count")
        facts["top_risk_level"] = risk.get("top_risk_level")

    elif intent == "RISK_EXPLANATION":
        facts["reasons"] = (results.get("generate_explanation", {}).get("reasons") or [])
        tx = _strip(results.get("transaction_summary", {}), ["features","found"])
        if tx: facts["transaction"] = tx
        cust = _strip(results.get("customer_summary", {}), ["recent_transactions","found"])
        if cust: facts["customer"] = cust

    else:  # GENERAL
        if _tool_ran(results, "run_eda"):
            eda = results["run_eda"]
            facts["total_rows"] = eda.get("total_rows")
            facts["fraud_percentage"] = eda.get("fraud_percentage")
        if _tool_ran(results, "generate_risk"):
            txs = (results["generate_risk"].get("transactions") or [])[:3]
            if txs: facts["top_risks"] = txs

    hist = ctx.get("conversation_history", [])
    history_block = ""
    if hist:
        lines = []
        for turn in hist[-4:]:
            lines.append(f"User: {turn.get('query','')}")
            if turn.get("natural_response"):
                lines.append(f"Assistant: {turn['natural_response'][:200]}")
        history_block = "\n\nRecent conversation:\n" + "\n".join(lines)

    # Build context-specific instruction
    extra_instruction = ""
    if intent == "CUSTOMER_INVESTIGATION":
        is_susp = facts.get("is_suspicious", False)
        cust_data = facts.get("customer", {})
        susp_tx = cust_data.get("suspicious_transactions", 0)
        high_pct = cust_data.get("high_risk_pct", 0)
        level = str(cust_data.get("risk_level", "LOW")).upper()
        if not is_susp or (susp_tx == 0 and high_pct == 0 and level not in ("HIGH", "CRITICAL")):
            extra_instruction = (
                "\nIMPORTANT: This customer has NO suspicious transactions and NO high-risk activity. "
                "Do NOT say the customer was flagged or is suspicious. "
                "Say the customer was analyzed and no significant AML risk indicators were detected."
            )
        else:
            extra_instruction = (
                f"\nIMPORTANT: This customer HAS suspicious indicators (suspicious_transactions={susp_tx}, "
                f"high_risk_pct={high_pct}%, risk_level={level}). "
                "Mention the specific risk reasons from top_risk_reasons."
            )

    return f"""User asked: "{ctx['query']}"{history_block}

Data from analysis tools:
{_j(facts, 2000)}

Write a natural, conversational response (2-5 sentences).{extra_instruction}
Use exact values from the data above.
Be like a knowledgeable AML colleague answering a direct question."""


def _fallback_natural(ctx: Dict[str, Any]) -> str:
    """Build a natural response from raw tool outputs without LLM."""
    intent = ctx.get("intent", "GENERAL")
    results = ctx.get("results", {})
    risk_level_val = ctx.get("risk_level", "LOW")
    risk_score = ctx.get("risk_score")
    recommendation_str = ctx.get("recommendation", "")
    explanation = ctx.get("explanation", "")

    if intent == "DATASET_EXPLORATION":
        eda = results.get("run_eda", {})
        rows = eda.get("total_rows", 0)
        fraud = eda.get("fraud_percentage", 0)
        avg = eda.get("average_amount_formatted", "")
        laundering = eda.get("total_laundering_transactions", 0)
        return (
            f"The dataset contains **{rows:,} transactions** across {eda.get('total_columns', 0)} columns. "
            f"**{fraud}%** of transactions ({laundering:,}) are flagged as potential money laundering. "
            f"The average transaction amount is **{avg}**."
        )
    elif intent == "TRANSACTION_INVESTIGATION":
        tx = results.get("transaction_summary", {})
        if tx.get("found"):
            score_str = f" with a hybrid risk score of **{risk_score:.4f}**" if risk_score else ""
            return (
                f"Transaction **#{tx.get('transaction_id')}** has been classified as **{risk_level_val}** risk{score_str}. "
                f"{explanation} "
                f"{recommendation_str}"
            )
    elif intent == "CUSTOMER_INVESTIGATION":
        cust = results.get("customer_summary", {})
        if cust.get("found"):
            is_susp = cust.get("is_suspicious", False)
            score_str = f" (score: **{risk_score:.4f}**)" if risk_score else ""
            if not is_susp:
                return (
                    f"Customer account **{cust.get('customer_id')}** was analyzed. "
                    f"No significant AML risk indicators were detected. "
                    f"The account has **{cust.get('transaction_count', 0)}** transactions with **0** flagged as suspicious. "
                    f"Continued standard monitoring is recommended."
                )
            else:
                reasons = cust.get("top_risk_reasons", [])
                reason_str = (", ".join(reasons[:3]) + ".") if reasons else ""
                return (
                    f"Customer account **{cust.get('customer_id')}** is rated **{risk_level_val}** risk{score_str}. "
                    + (f"Risk indicators include: {reason_str} " if reason_str else "")
                    + f"{recommendation_str}"
                )
    elif intent == "TOP_SUSPICIOUS":
        top = results.get("top_suspicious_transactions", {})
        txs = top.get("transactions") or []
        if txs:
            t1 = txs[0]
            return (
                f"The highest-risk transaction is **#{t1.get('transaction_id')}** with a score of **{t1.get('risk_score')}** (**{t1.get('risk_level')}**). "
                f"Returned {len(txs)} suspicious transactions in total. "
                f"{recommendation_str}"
            )
    elif intent == "PATTERN_DETECTION":
        rule = results.get("rule_engine", {})
        if rule.get("match_count") is not None:
            return (
                f"Detected **{ctx.get('aml_pattern', 'suspicious pattern')}** in **{rule['match_count']} accounts**. "
                f"{recommendation_str}"
            )
    return f"Analysis complete. Risk level: **{risk_level_val}**. {recommendation_str}"


def generate_natural_response(ctx: Dict[str, Any], report: Dict[str, Any]) -> str:
    """
    Generate a ChatGPT-style conversational answer from tool results.
    Falls back to rule-based if LLM is unavailable.
    """
    client = get_groq_client()
    if client is None:
        return _fallback_natural(ctx)
    try:
        prompt = _natural_prompt(ctx, report)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _NATURAL_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Natural response generation failed: %s", exc)
        return _fallback_natural(ctx)


__all__ = [
    "GROQ_MODEL",
    "INTENT_SCHEMA",
    "get_groq_client",
    "is_llm_available",
    "generate_investigation_report",
    "generate_natural_response",
]
