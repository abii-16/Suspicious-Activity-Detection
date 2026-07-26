"""Appends the 5 specialised tools to backend/tools.py — run once."""

NEW_CODE = '''

# ===========================================================================
# SPECIALISED ANALYTICS TOOLS
# ===========================================================================

_GROUP_BY_COL = {
    "bank": "From Bank", "from_bank": "From Bank", "to_bank": "To Bank",
    "currency": "Payment Currency", "payment_format": "Payment Format",
    "payment_method": "Payment Format", "risk_level": "Risk Level", "month": "Month",
}


def analytics_tool(group_by="bank", metric="suspicious_transactions", top_n=10, filters=None):
    """
    Group-by analytics. group_by: bank/currency/payment_format/risk_level/month.
    metric: suspicious_transactions/fraud_rate/avg_risk_score/transaction_count/total_amount/high_risk_count
    """
    df = get_risk_predictions_df()
    if filters:
        df = _apply_filters(df, filters)
    col = _GROUP_BY_COL.get(group_by.lower(), group_by)
    if col not in df.columns:
        return safe_json({"error": f"Column not found: {col}"})
    score_col = "Final Risk Score" if "Final Risk Score" in df.columns else None
    agg = {"transaction_count": (TARGET_COLUMN, "count")}
    if TARGET_COLUMN in df.columns:
        agg["suspicious_count"] = (TARGET_COLUMN, "sum")
    if score_col:
        agg["avg_risk_score"] = (score_col, "mean")
        agg["max_risk_score"] = (score_col, "max")
    if "Amount Paid" in df.columns:
        agg["total_amount"] = ("Amount Paid", "sum")
        agg["avg_amount"] = ("Amount Paid", "mean")
    grouped = df.groupby(col).agg(**agg).reset_index()
    if "suspicious_count" in grouped.columns:
        grouped["fraud_rate_pct"] = (
            grouped["suspicious_count"] / grouped["transaction_count"].clip(lower=1) * 100
        ).round(4)
    if "Risk Level" in df.columns:
        hc = (df[df["Risk Level"].isin(["HIGH", "CRITICAL"])]
              .groupby(col).size().reset_index(name="high_risk_count"))
        grouped = grouped.merge(hc, on=col, how="left")
        grouped["high_risk_count"] = grouped["high_risk_count"].fillna(0).astype(int)
    metric_map = {
        "suspicious_transactions": "suspicious_count",
        "fraud_rate": "fraud_rate_pct",
        "avg_risk_score": "avg_risk_score",
        "transaction_count": "transaction_count",
        "total_amount": "total_amount",
        "high_risk_count": "high_risk_count",
    }
    sc = metric_map.get(metric, "suspicious_count")
    if sc not in grouped.columns:
        sc = "transaction_count"
    grouped = grouped.sort_values(sc, ascending=False).head(top_n)
    for c in grouped.select_dtypes(include="float").columns:
        grouped[c] = grouped[c].round(4)
    rows = []
    for _, row in grouped.iterrows():
        r = {group_by: str(row[col])}
        for k in ("transaction_count", "suspicious_count", "fraud_rate_pct",
                  "avg_risk_score", "max_risk_score", "total_amount", "avg_amount", "high_risk_count"):
            if k in row.index and pd.notna(row[k]):
                r[k] = row[k]
        rows.append(safe_json(r))
    top = rows[0] if rows else {}
    tl = top.get(group_by, "N/A")
    if metric == "suspicious_transactions":
        headline = f"{group_by.title()} {tl} has highest suspicious transactions: {int(top.get('suspicious_count', 0)):,}"
    elif metric == "fraud_rate":
        headline = f"{group_by.title()} {tl} has highest fraud rate: {top.get('fraud_rate_pct', 0):.2f}%"
    elif metric == "avg_risk_score":
        headline = f"{group_by.title()} {tl} has highest avg risk score: {top.get('avg_risk_score', 0):.4f}"
    elif metric == "transaction_count":
        headline = f"{group_by.title()} {tl} has most transactions: {int(top.get('transaction_count', 0)):,}"
    elif metric == "total_amount":
        headline = f"{group_by.title()} {tl} has highest total amount: {top.get('total_amount', 0):,.2f}"
    else:
        headline = f"Top {group_by}: {tl}"
    return safe_json({"group_by": group_by, "metric": metric, "top_n": top_n,
                      "headline": headline, "results": rows})


def investigation_tool(customer_id=None, transaction_id=None, bank_id=None):
    """Unified investigation for customer, transaction, or bank."""
    if customer_id is not None:
        return customer_summary(customer_id)
    if transaction_id is not None:
        return transaction_summary(transaction_id)
    if bank_id is not None:
        df = get_risk_predictions_df()
        bank_df = df[df["From Bank"] == bank_id] if "From Bank" in df.columns else df.iloc[0:0]
        if len(bank_df) == 0:
            return {"bank_id": bank_id, "found": False, "message": f"Bank {bank_id} not found."}
        score_col = "Final Risk Score" if "Final Risk Score" in bank_df.columns else None
        total = len(bank_df)
        suspicious = int((bank_df[TARGET_COLUMN] == 1).sum()) if TARGET_COLUMN in bank_df.columns else 0
        fraud_rate = round(suspicious / total * 100, 4) if total else 0.0
        avg_score = round(float(bank_df[score_col].mean()), 4) if score_col else 0.0
        max_score = round(float(bank_df[score_col].max()), 4) if score_col else 0.0
        risk_dist = ({str(k): int(v) for k, v in bank_df["Risk Level"].value_counts().items()}
                     if "Risk Level" in bank_df.columns else {})
        overall_level = ("HIGH" if (fraud_rate > 5 or avg_score > 0.5)
                         else ("MEDIUM" if (fraud_rate > 1 or avg_score > 0.2) else "LOW"))
        return safe_json({"bank_id": bank_id, "found": True, "total_transactions": total,
                          "suspicious_transactions": suspicious, "fraud_rate_pct": fraud_rate,
                          "avg_risk_score": avg_score, "max_risk_score": max_score,
                          "risk_level": overall_level, "risk_distribution": risk_dist,
                          "recommendation": recommendation(overall_level)})
    return {"error": "investigation_tool requires customer_id, transaction_id, or bank_id."}


def pattern_detection_tool(pattern_type="structuring", top_n=20, filters=None):
    """
    Detect AML patterns using pre-computed feature flags.
    pattern_type: structuring, rapid_transactions, cross_bank, currency_change, anomaly, high_value, fan_out
    """
    df = get_risk_predictions_df()
    if filters:
        df = _apply_filters(df, filters)
    score_col = "Final Risk Score" if "Final Risk Score" in df.columns else None
    pattern_map = {
        "structuring":        ("Near_Threshold",  "Structuring / Smurfing"),
        "near_threshold":     ("Near_Threshold",  "Near Reporting Threshold"),
        "rapid_transactions": ("Rapid_5m",        "Rapid Transaction Pattern"),
        "rapid":              ("Rapid_5m",         "Rapid Transaction Pattern"),
        "cross_bank":         ("Cross_Bank",       "Cross-Bank Transfer"),
        "currency_change":    ("Currency_Change",  "Currency Conversion"),
        "high_value":         ("High_Value",       "Large Value Transfer"),
        "anomaly":            ("Isolation Score",  "Isolation Forest Anomaly"),
        "fan_out":            (None,               "Fan-Out Layering"),
    }
    entry = pattern_map.get(pattern_type.lower())
    if not entry:
        return {"error": f"Unknown pattern_type. Options: {list(pattern_map.keys())}"}
    flag_col, pattern_label = entry
    if pattern_type.lower() == "fan_out":
        matched = (df[(df["Rapid_5m"] == 1) & (df["Unique_Receivers"] > 10)]
                   if "Rapid_5m" in df.columns else df.iloc[0:0])
    elif flag_col and flag_col in df.columns:
        matched = df[df[flag_col] == 1]
    else:
        return {"error": f"Feature column '{flag_col}' not available."}
    total_matched = len(matched)
    if total_matched == 0:
        return safe_json({"pattern_type": pattern_type, "pattern_label": pattern_label,
                          "matched_transactions": 0, "matched_accounts": 0,
                          "headline": f"No {pattern_label} transactions found.", "top_transactions": []})
    matched_accounts = int(matched["Account"].nunique()) if "Account" in matched.columns else 0
    top = matched.nlargest(top_n, score_col) if score_col else matched.head(top_n)
    suspicious_count = int((matched[TARGET_COLUMN] == 1).sum()) if TARGET_COLUMN in matched.columns else 0
    fraud_rate = round(suspicious_count / total_matched * 100, 4) if total_matched else 0.0
    avg_score = round(float(matched[score_col].mean()), 4) if score_col else None
    top_records = []
    for idx, row in top.iterrows():
        rec = {"transaction_id": int(idx)}
        if "Account" in row.index: rec["account"] = int(row["Account"])
        if "Amount Paid" in row.index: rec["amount_paid"] = round(float(row["Amount Paid"]), 2)
        if score_col: rec["risk_score"] = round(float(row[score_col]), 4)
        if "Risk Level" in row.index: rec["risk_level"] = str(row["Risk Level"])
        top_records.append(safe_json(rec))
    return safe_json({"pattern_type": pattern_type, "pattern_label": pattern_label,
                      "matched_transactions": total_matched, "matched_accounts": matched_accounts,
                      "suspicious_transactions": suspicious_count, "fraud_rate_pct": fraud_rate,
                      "avg_risk_score": avg_score,
                      "headline": (f"Detected {total_matched:,} {pattern_label} transactions "
                                   f"across {matched_accounts:,} accounts. Fraud rate: {fraud_rate}%."),
                      "top_transactions": top_records})


def comparison_tool(entity_type="bank", entity_ids=None, top_n=5):
    """Side-by-side comparison. entity_type: bank, currency, payment_format, customer."""
    df = get_risk_predictions_df()
    col_map = {"bank": "From Bank", "currency": "Payment Currency",
               "payment_format": "Payment Format", "customer": "Account"}
    col = col_map.get(entity_type.lower())
    if not col or col not in df.columns:
        return {"error": f"Unknown entity_type '{entity_type}'."}
    if entity_ids:
        ids = [int(x) for x in entity_ids]
        subset = df[df[col].isin(ids)]
    else:
        top_ids = df[col].value_counts().head(top_n).index.tolist()
        subset = df[df[col].isin(top_ids)]
    score_col = "Final Risk Score" if "Final Risk Score" in df.columns else None
    agg = {"transaction_count": (TARGET_COLUMN, "count")}
    if TARGET_COLUMN in df.columns:
        agg["suspicious_count"] = (TARGET_COLUMN, "sum")
    if score_col:
        agg["avg_risk_score"] = (score_col, "mean")
        agg["max_risk_score"] = (score_col, "max")
    if "Amount Paid" in df.columns:
        agg["total_amount"] = ("Amount Paid", "sum")
    grouped = subset.groupby(col).agg(**agg).reset_index()
    if "suspicious_count" in grouped.columns:
        grouped["fraud_rate_pct"] = (
            grouped["suspicious_count"] / grouped["transaction_count"].clip(lower=1) * 100
        ).round(4)
    for c in grouped.select_dtypes(include="float").columns:
        grouped[c] = grouped[c].round(4)
    rows = []
    for _, row in grouped.iterrows():
        r = {entity_type: str(row[col])}
        for k in ("transaction_count", "suspicious_count", "fraud_rate_pct",
                  "avg_risk_score", "max_risk_score", "total_amount"):
            if k in row.index and pd.notna(row[k]):
                r[k] = row[k]
        rows.append(safe_json(r))
    rows.sort(key=lambda x: x.get("avg_risk_score") or x.get("fraud_rate_pct") or 0, reverse=True)
    return safe_json({"entity_type": entity_type, "compared_entities": len(rows),
                      "comparison": rows,
                      "highest_risk": rows[0] if rows else {},
                      "lowest_risk": rows[-1] if rows else {}})


def knowledge_tool(topic="overview"):
    """Answer questions about the AML system without running any ML."""
    kb = {
        "system_overview": {
            "name": "AI-Powered AML Agent",
            "architecture": "Planner - Router - Specialised Tools - Hybrid ML - LLM",
            "ml_pipeline": "XGBoost (85%) + Isolation Forest (15%)",
            "data": "IBM HI-Small AML dataset — 5,078,345 transactions",
            "llm": "Groq LLaMA 3.3 70B — summarisation only, never makes predictions",
        },
        "hybrid_ml": {
            "components": ["XGBoost classifier (supervised, 85% weight)",
                           "Isolation Forest anomaly detector (unsupervised, 15% weight)"],
            "formula": "Final Risk Score = 0.85 x XGBoost_probability + 0.15 x Isolation_Forest_flag",
        },
        "xgboost": {
            "type": "Gradient Boosting Classifier",
            "task": "Binary classification — P(transaction is money laundering)",
            "features": 35, "output": "Probability 0.0 to 1.0",
        },
        "isolation_forest": {
            "type": "Unsupervised Anomaly Detection",
            "principle": "Anomalous transactions are isolated in fewer random-tree splits",
            "output": "1 = anomaly, 0 = normal",
        },
        "risk_score": {
            "formula": "0.85 x XGBoost_score + 0.15 x Isolation_Forest_flag",
            "levels": {"CRITICAL": "0.90+ Freeze account", "HIGH": "0.75-0.89 Escalate",
                       "MEDIUM": "0.50-0.74 Manual review", "LOW": "below 0.50 Monitor"},
        },
        "features": {
            "categories": ["Temporal: Hour, Day, Month, Weekday",
                           "Amount: High_Value, Near_Threshold, Sender_Deviation",
                           "Behaviour: Rapid_5m, Unique_Receivers",
                           "Bank: Cross_Bank, Currency_Change"],
            "total_count": 35,
        },
        "aml_patterns": {
            "structuring": "Splitting transactions below $10,000 to avoid reporting thresholds",
            "layering": "Cross-bank and cross-currency transfers to obscure the money trail",
            "rapid_transactions": "Multiple transactions within 5 minutes from the same account",
            "fan_out_layering": "Single sender distributing funds rapidly to many unique receivers",
            "high_value": "Transactions in the top 1 percent by amount",
            "anomaly": "Statistically unusual transactions flagged by Isolation Forest",
        },
        "agent_architecture": {
            "planner": "Classifies intent, extracts entities, builds dynamic tool-chained plan",
            "router": "Executes the plan, resolves missing parameters from prior tool outputs",
            "tools": ["analytics_tool", "investigation_tool", "pattern_detection_tool",
                      "comparison_tool", "knowledge_tool"],
            "llm_role": "Summarises structured tool output — never predicts or invents",
        },
    }
    lowered = topic.lower()
    if any(w in lowered for w in ("xgboost", "gradient", "boost")):
        relevant = {"xgboost": kb["xgboost"], "hybrid_ml": kb["hybrid_ml"]}
    elif any(w in lowered for w in ("isolation", "anomaly", "forest")):
        relevant = {"isolation_forest": kb["isolation_forest"], "hybrid_ml": kb["hybrid_ml"]}
    elif any(w in lowered for w in ("score", "formula", "calculat", "level")):
        relevant = {"risk_score": kb["risk_score"], "hybrid_ml": kb["hybrid_ml"]}
    elif any(w in lowered for w in ("feature", "input", "variable")):
        relevant = {"features": kb["features"]}
    elif any(w in lowered for w in ("pattern", "structuring", "layering")):
        relevant = {"aml_patterns": kb["aml_patterns"]}
    elif any(w in lowered for w in ("architect", "system", "how", "agent", "work")):
        relevant = {"system_overview": kb["system_overview"], "agent_architecture": kb["agent_architecture"]}
    else:
        relevant = kb
    return safe_json({"topic": topic, "knowledge": relevant})


__all__ = [
    "run_eda", "predict_transaction", "top_suspicious_transactions",
    "customer_summary", "transaction_summary", "rule_engine",
    "generate_explanation", "generate_risk", "filter_data", "get_dashboard_stats",
    "analytics_tool", "investigation_tool", "pattern_detection_tool",
    "comparison_tool", "knowledge_tool",
]
'''

with open('backend/tools.py') as f:
    base = f.read()

# Remove old __all__ if present
import re
base_clean = re.sub(r'\n\n__all__ = \[.*?\]\n', '', base, flags=re.DOTALL)

with open('backend/tools.py', 'w', encoding='utf-8') as f:
    f.write(base_clean + NEW_CODE)

print('Done. New file lines:', (base_clean + NEW_CODE).count('\n'))
