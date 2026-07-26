"""
tools.py

All AML business logic for the agent backend.

ML models and datasets are accessed exclusively through loader.py.
Utility helpers come from utils.py.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.loader import (
    TARGET_COLUMN,
    get_feature_columns,
    get_features_df,
    get_isolation_forest,
    get_risk_predictions_df,
    get_xgb_model,
)
from backend.utils import (
    format_currency,
    recommendation,
    records_from_df,
    risk_level,
    safe_json,
)

logger = logging.getLogger(__name__)

HYBRID_XGB_WEIGHT = 0.85
HYBRID_ISO_WEIGHT = 0.15


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_filters(
    df: pd.DataFrame,
    filters: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Apply planner-extracted filters to a dataframe."""
    if not filters:
        return df

    filtered = df.copy()
    pattern = filters.get("aml_pattern")

    if pattern == "STRUCTURING / SMURFING":
        if "Near_Threshold" in filtered.columns:
            filtered = filtered[filtered["Near_Threshold"] == 1]
    elif pattern == "RAPID TRANSACTIONS":
        if "Rapid_5m" in filtered.columns:
            filtered = filtered[filtered["Rapid_5m"] == 1]
    elif pattern == "LAYERING":
        if {"Cross_Bank", "Currency_Change"}.issubset(filtered.columns):
            filtered = filtered[
                (filtered["Cross_Bank"] == 1) | (filtered["Currency_Change"] == 1)
            ]

    if "customer_id" in filters and "Account" in filtered.columns:
        filtered = filtered[filtered["Account"] == int(filters["customer_id"])]

    if "transaction_id" in filters and filtered.index.name != "transaction_id":
        tx_id = int(filters["transaction_id"])
        if tx_id in filtered.index:
            filtered = filtered.loc[[tx_id]]
        elif tx_id < len(filtered):
            filtered = filtered.iloc[[tx_id]]

    if "min_amount" in filters and "Amount Paid" in filtered.columns:
        filtered = filtered[filtered["Amount Paid"] >= float(filters["min_amount"])]

    if "max_amount" in filters and "Amount Paid" in filtered.columns:
        filtered = filtered[filtered["Amount Paid"] <= float(filters["max_amount"])]

    if "days" in filters and "Month" in filtered.columns:
        # Timestamp was dropped during feature engineering; use Month as a proxy.
        latest_month = int(filtered["Month"].max())
        window = int(filters["days"])
        month_window = max(1, min(12, math.ceil(window / 30))) if window else 1
        start_month = max(1, latest_month - month_window + 1)
        filtered = filtered[filtered["Month"] >= start_month]

    return filtered


def _detect_aml_pattern(row: pd.Series) -> str:
    """Classify the dominant AML typology for a single transaction."""
    if row.get("Rapid_5m") == 1 and row.get("Unique_Receivers", 0) > 10:
        return "Fan-Out Layering"
    if row.get("Near_Threshold") == 1:
        return "Structuring / Smurfing"
    if row.get("Cross_Bank") == 1 and row.get("Currency_Change") == 1:
        return "Cross-Border Layering"
    if row.get("High_Value") == 1:
        return "Large Value Transfer"
    if row.get("Rapid_5m") == 1:
        return "Rapid Transaction Pattern"
    return "No dominant AML pattern"


def _build_reasons(row: pd.Series, iso_flag: bool = False) -> List[str]:
    """Generate concise human-readable risk reasons for a transaction."""
    reasons: List[str] = []

    if row.get("Cross_Bank") == 1:
        reasons.append("Cross-bank transfer")
    if row.get("Currency_Change") == 1:
        reasons.append("Currency conversion")
    if row.get("Rapid_5m") == 1:
        reasons.append("Rapid transactions")
    if row.get("High_Value") == 1:
        reasons.append("High transaction amount")
    if row.get("Near_Threshold") == 1:
        reasons.append("Near reporting threshold")
    if row.get("Unique_Receivers", 0) > 10:
        reasons.append(f"{int(row['Unique_Receivers'])} unique receivers")
    if row.get("Sender_Deviation", 0) > 3:
        reasons.append("Amount exceeds sender's normal behaviour")
    if iso_flag or row.get("Isolation Score") == 1:
        reasons.append("Isolation Forest anomaly")

    return reasons or ["No major suspicious indicators"]


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def run_eda(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Exploratory data analysis over the risk-scored transaction dataset.

    Returns rows, columns, fraud rate, amount stats, and categorical breakdowns.
    """
    df = get_risk_predictions_df()
    df = _apply_filters(df, filters)

    fraud_pct = round(float(df[TARGET_COLUMN].mean() * 100), 4) if len(df) else 0.0
    avg_amount = round(float(df["Amount Paid"].mean()), 2) if len(df) else 0.0

    top_banks = (
        df["From Bank"].value_counts().head(5).to_dict()
        if "From Bank" in df.columns and len(df)
        else {}
    )
    top_formats = (
        df["Payment Format"].value_counts().head(5).to_dict()
        if "Payment Format" in df.columns and len(df)
        else {}
    )
    currency_dist = (
        df["Payment Currency"].value_counts().head(5).to_dict()
        if "Payment Currency" in df.columns and len(df)
        else {}
    )

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    stats = (
        safe_json(df[numeric_cols].describe().to_dict())
        if numeric_cols and len(df)
        else {}
    )

    return safe_json(
        {
            "rows": len(df),
            "columns": list(df.columns),
            "fraud_pct": fraud_pct,
            "average_amount": avg_amount,
            "average_amount_formatted": format_currency(avg_amount),
            "top_banks": top_banks,
            "top_payment_formats": top_formats,
            "currency_distribution": currency_dist,
            "statistics": stats,
        }
    )


def predict_transaction(features: Dict[str, Any]) -> Dict[str, Any]:
    """Score a single transaction using the hybrid XGBoost + Isolation Forest model."""
    feature_columns = get_feature_columns()
    missing = [col for col in feature_columns if col not in features]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    xgb = get_xgb_model()
    iso = get_isolation_forest()

    row = pd.DataFrame([features])[feature_columns]
    prob = float(xgb.predict_proba(row)[0][1])
    iso_flag = int(iso.predict(row)[0] == -1)
    score = HYBRID_XGB_WEIGHT * prob + HYBRID_ISO_WEIGHT * iso_flag
    level = risk_level(score)

    enriched = pd.Series({**features, "Isolation Score": iso_flag})
    reasons = _build_reasons(enriched, iso_flag=bool(iso_flag))

    return safe_json(
        {
            "xgb_score": round(prob, 4),
            "isolation_anomaly": bool(iso_flag),
            "risk_score": round(score, 4),
            "risk_level": level,
            "aml_pattern": _detect_aml_pattern(enriched),
            "reasons": reasons,
            "recommendation": recommendation(level),
        }
    )


def top_suspicious_transactions(
    n: int = 20,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the top-N highest-risk transactions from pre-computed scores."""
    df = get_risk_predictions_df()
    df = _apply_filters(df, filters)

    sort_col = "Final Risk Score" if "Final Risk Score" in df.columns else "Risk Score"
    top = df.sort_values(sort_col, ascending=False).head(n)

    records = []
    for idx, row in top.iterrows():
        records.append(
            safe_json(
                {
                    "transaction_id": int(idx),
                    "account": int(row["Account"]),
                    "amount_paid": round(float(row["Amount Paid"]), 2),
                    "risk_score": round(float(row[sort_col]), 4),
                    "risk_level": row.get("Risk Level", risk_level(float(row[sort_col]))),
                    "aml_pattern": _detect_aml_pattern(row),
                    "actual_label": int(row[TARGET_COLUMN]),
                    "recommended_action": row.get("Recommended Action"),
                }
            )
        )

    return {"count": len(records), "transactions": records}


def customer_summary(
    customer_id: int,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Summarise all transactions and risk profile for a customer account."""
    df = get_risk_predictions_df()
    merged_filters = {**(filters or {}), "customer_id": customer_id}
    customer_df = _apply_filters(df, merged_filters)

    if customer_df.empty:
        return {
            "customer_id": customer_id,
            "found": False,
            "message": f"No transactions found for customer {customer_id}.",
        }

    sort_col = "Final Risk Score" if "Final Risk Score" in customer_df.columns else None
    max_risk = float(customer_df[sort_col].max()) if sort_col else 0.0
    level = (
        customer_df.loc[customer_df[sort_col].idxmax(), "Risk Level"]
        if sort_col and "Risk Level" in customer_df.columns
        else risk_level(max_risk)
    )

    suspicious = int((customer_df[TARGET_COLUMN] == 1).sum()) if TARGET_COLUMN in customer_df.columns else 0

    return safe_json(
        {
            "customer_id": customer_id,
            "found": True,
            "transaction_count": len(customer_df),
            "total_amount_sent": round(float(customer_df["Amount Paid"].sum()), 2),
            "max_risk_score": round(max_risk, 4),
            "risk_level": level,
            "suspicious_transactions": suspicious,
            "recommendation": recommendation(level),
            "recent_transactions": records_from_df(
                customer_df.sort_values(sort_col, ascending=False) if sort_col else customer_df,
                limit=10,
            ),
        }
    )


def transaction_summary(
    transaction_id: int,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return full details and risk assessment for a single transaction."""
    features_df = get_features_df()
    risk_df = get_risk_predictions_df()

    if transaction_id < 0 or transaction_id >= len(features_df):
        return {
            "transaction_id": transaction_id,
            "found": False,
            "message": f"Transaction {transaction_id} is out of range.",
        }

    feature_row = features_df.iloc[transaction_id]
    risk_row = risk_df.iloc[transaction_id]

    sort_col = "Final Risk Score" if "Final Risk Score" in risk_row.index else None
    score = float(risk_row[sort_col]) if sort_col else 0.0
    level = risk_row.get("Risk Level", risk_level(score))
    iso_flag = bool(risk_row.get("Isolation Score", 0))
    reasons = _build_reasons(risk_row, iso_flag=iso_flag)

    return safe_json(
        {
            "transaction_id": transaction_id,
            "found": True,
            "account": int(risk_row["Account"]),
            "counterparty": int(risk_row["Account.1"]),
            "amount_paid": round(float(risk_row["Amount Paid"]), 2),
            "risk_score": round(score, 4),
            "risk_level": level,
            "aml_pattern": _detect_aml_pattern(risk_row),
            "actual_label": int(risk_row[TARGET_COLUMN]),
            "reasons": reasons,
            "recommendation": risk_row.get("Recommended Action", recommendation(level)),
            "features": safe_json(feature_row.to_dict()),
        }
    )


def rule_engine(rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Apply deterministic AML rules without ML.

    Supported rule keys:
        - min_transactions_under_amount (e.g. 10 tx under $10 000)
        - amount_threshold (default 10 000)
        - min_daily_volume
        - rapid_transactions (bool)
        - near_threshold (bool)
    """
    rules = rules or {}
    df = get_risk_predictions_df()
    matches: List[Dict[str, Any]] = []
    rule_type = "custom"

    if rules.get("rapid_transactions"):
        rule_type = "rapid_transactions"
        flagged = df[df["Rapid_5m"] == 1].groupby("Account").size().reset_index(name="rapid_count")
        flagged = flagged[flagged["rapid_count"] >= rules.get("min_count", 3)]
        for _, row in flagged.head(50).iterrows():
            matches.append(
                {
                    "account": int(row["Account"]),
                    "rapid_count": int(row["rapid_count"]),
                    "rule": "rapid_transactions",
                }
            )

    elif rules.get("near_threshold"):
        rule_type = "near_reporting_threshold"
        flagged = df[df["Near_Threshold"] == 1].groupby("Account").size().reset_index(name="near_threshold_count")
        flagged = flagged[flagged["near_threshold_count"] >= rules.get("min_count", 2)]
        for _, row in flagged.head(50).iterrows():
            matches.append(
                {
                    "account": int(row["Account"]),
                    "near_threshold_count": int(row["near_threshold_count"]),
                    "rule": "near_reporting_threshold",
                }
            )

    elif rules.get("min_daily_volume"):
        rule_type = "high_daily_volume"
        if "Daily_Sent_Amount" in get_features_df().columns:
            features = get_features_df()
            daily = features.groupby("Account")["Daily_Sent_Amount"].max().reset_index()
            threshold = float(rules["min_daily_volume"])
            flagged = daily[daily["Daily_Sent_Amount"] >= threshold]
            for _, row in flagged.head(50).iterrows():
                matches.append(
                    {
                        "account": int(row["Account"]),
                        "max_daily_volume": round(float(row["Daily_Sent_Amount"]), 2),
                        "rule": "high_daily_volume",
                    }
                )

    else:
        min_tx = int(rules.get("min_transactions_under_amount", rules.get("min_transactions", 10)))
        amount_cap = float(rules.get("amount_threshold", 10_000))
        rule_type = f"transactions_under_{int(amount_cap)}"

        under = df[df["Amount Paid"] < amount_cap]
        grouped = under.groupby("Account").size().reset_index(name="tx_count")
        flagged = grouped[grouped["tx_count"] >= min_tx].sort_values("tx_count", ascending=False)

        for _, row in flagged.head(50).iterrows():
            matches.append(
                {
                    "account": int(row["Account"]),
                    "transaction_count": int(row["tx_count"]),
                    "amount_threshold": amount_cap,
                    "rule": rule_type,
                }
            )

    return safe_json(
        {
            "rule_type": rule_type,
            "rules_applied": rules,
            "match_count": len(matches),
            "matches": matches,
        }
    )


def generate_explanation(
    transaction_id: Optional[int] = None,
    row: Optional[pd.Series] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate human-readable explanations for one or many transactions."""
    if row is not None:
        iso_flag = bool(row.get("Isolation Score", 0))
        reasons = _build_reasons(row, iso_flag=iso_flag)
        pattern = _detect_aml_pattern(row)
        return safe_json(
            {
                "aml_pattern": pattern,
                "reasons": reasons,
                "explanation": " | ".join(reasons),
            }
        )

    df = get_risk_predictions_df()
    df = _apply_filters(df, filters)

    if transaction_id is not None:
        if transaction_id < 0 or transaction_id >= len(df):
            return {"found": False, "message": f"Transaction {transaction_id} not found."}
        target_row = df.iloc[transaction_id]
        result = generate_explanation(row=target_row)
        result["transaction_id"] = transaction_id
        return result

    sort_col = "Final Risk Score" if "Final Risk Score" in df.columns else None
    sample = df.sort_values(sort_col, ascending=False).head(5) if sort_col else df.head(5)

    explanations = []
    for idx, tx_row in sample.iterrows():
        detail = generate_explanation(row=tx_row)
        detail["transaction_id"] = int(idx)
        explanations.append(detail)

    return {"count": len(explanations), "explanations": explanations}


def generate_risk(
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Run hybrid risk scoring on filtered transactions.

    Uses pre-computed scores when available; falls back to live inference
    for small subsets.
    """
    risk_df = get_risk_predictions_df()
    filtered = _apply_filters(risk_df, filters)

    if "Final Risk Score" in filtered.columns:
        sort_col = "Final Risk Score"
        top = filtered.sort_values(sort_col, ascending=False).head(limit)
        records = []
        for idx, row in top.iterrows():
            score = float(row[sort_col])
            level = row.get("Risk Level", risk_level(score))
            records.append(
                {
                    "transaction_id": int(idx),
                    "risk_score": round(score, 4),
                    "risk_level": level,
                    "xgb_score": round(float(row.get("XGB Score", 0)), 4),
                    "isolation_anomaly": bool(row.get("Isolation Score", 0)),
                    "recommendation": row.get("Recommended Action", recommendation(level)),
                }
            )

        overall_level = records[0]["risk_level"] if records else "LOW"
        return safe_json(
            {
                "scored_count": len(filtered),
                "returned_count": len(records),
                "top_risk_level": overall_level,
                "transactions": records,
            }
        )

    # Live inference fallback for unexpected schema
    features_df = get_features_df()
    feature_columns = get_feature_columns()
    xgb = get_xgb_model()
    iso = get_isolation_forest()

    subset = _apply_filters(features_df, filters).head(limit)
    records = []
    for idx, row in subset.iterrows():
        x = row[feature_columns].to_frame().T
        prob = float(xgb.predict_proba(x)[0][1])
        iso_flag = int(iso.predict(x)[0] == -1)
        score = HYBRID_XGB_WEIGHT * prob + HYBRID_ISO_WEIGHT * iso_flag
        level = risk_level(score)
        records.append(
            {
                "transaction_id": int(idx),
                "risk_score": round(score, 4),
                "risk_level": level,
                "xgb_score": round(prob, 4),
                "isolation_anomaly": bool(iso_flag),
                "recommendation": recommendation(level),
            }
        )

    records.sort(key=lambda item: item["risk_score"], reverse=True)
    overall_level = records[0]["risk_level"] if records else "LOW"

    return safe_json(
        {
            "scored_count": len(subset),
            "returned_count": len(records),
            "top_risk_level": overall_level,
            "transactions": records,
        }
    )


def filter_data(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Apply query filters and return dataset scope metadata."""
    df = get_risk_predictions_df()
    filtered = _apply_filters(df, filters)
    return safe_json(
        {
            "total_rows": len(df),
            "filtered_rows": len(filtered),
            "filters_applied": filters or {},
            "columns": list(filtered.columns),
        }
    )


__all__ = [
    "run_eda",
    "predict_transaction",
    "top_suspicious_transactions",
    "customer_summary",
    "transaction_summary",
    "rule_engine",
    "generate_explanation",
    "generate_risk",
    "filter_data",
]
