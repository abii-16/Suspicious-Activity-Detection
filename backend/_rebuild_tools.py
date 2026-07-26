"""Rebuilds backend/tools.py with all required functions."""
import pathlib

HEADER = '''from __future__ import annotations
import logging, math
from typing import Any, Dict, List, Optional
import pandas as pd
from backend.loader import (
    TARGET_COLUMN, get_customer_df, get_feature_columns,
    get_features_df, get_isolation_forest, get_risk_predictions_df, get_xgb_model,
)
from backend.utils import format_currency, recommendation, records_from_df, risk_level, safe_json

logger = logging.getLogger(__name__)
HYBRID_XGB_WEIGHT = 0.85
HYBRID_ISO_WEIGHT = 0.15
_GROUP_BY_COL = {
    "bank": "From Bank", "from_bank": "From Bank", "to_bank": "To Bank",
    "currency": "Payment Currency", "payment_format": "Payment Format",
    "payment_method": "Payment Format", "risk_level": "Risk Level", "month": "Month",
}
'''

HELPERS = '''
def _apply_filters(df, filters=None):
    if not filters:
        return df
    filtered = df.copy()
    pat = filters.get("aml_pattern")
    if pat == "STRUCTURING / SMURFING" and "Near_Threshold" in filtered.columns:
        filtered = filtered[filtered["Near_Threshold"] == 1]
    elif pat == "RAPID TRANSACTIONS" and "Rapid_5m" in filtered.columns:
        filtered = filtered[filtered["Rapid_5m"] == 1]
    elif pat == "LAYERING" and {"Cross_Bank", "Currency_Change"}.issubset(filtered.columns):
        filtered = filtered[(filtered["Cross_Bank"] == 1) | (filtered["Currency_Change"] == 1)]
    if "customer_id" in filters and "Account" in filtered.columns:
        try:
            filtered = filtered[filtered["Account"] == int(filters["customer_id"])]
        except (TypeError, ValueError):
            pass
    if "transaction_id" in filters:
        try:
            tid = int(filters["transaction_id"])
            if tid in filtered.index:
                filtered = filtered.loc[[tid]]
            elif tid < len(filtered):
                filtered = filtered.iloc[[tid]]
        except (TypeError, ValueError):
            pass
    if "min_amount" in filters and "Amount Paid" in filtered.columns:
        try:
            filtered = filtered[filtered["Amount Paid"] >= float(filters["min_amount"])]
        except (TypeError, ValueError):
            pass
    if "max_amount" in filters and "Amount Paid" in filtered.columns:
        try:
            filtered = filtered[filtered["Amount Paid"] <= float(filters["max_amount"])]
        except (TypeError, ValueError):
            pass
    if "days" in filters and "Month" in filtered.columns:
        lm = int(filtered["Month"].max())
        w = int(filters["days"])
        mw = max(1, min(12, math.ceil(w / 30)))
        filtered = filtered[filtered["Month"] >= max(1, lm - mw + 1)]
    return filtered


def _detect_aml_pattern(row):
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


def _build_reasons(row, iso_flag=False):
    r = []
    if row.get("Cross_Bank") == 1: r.append("Cross-bank transfer")
    if row.get("Currency_Change") == 1: r.append("Currency conversion")
    if row.get("Rapid_5m") == 1: r.append("Rapid transactions")
    if row.get("High_Value") == 1: r.append("High transaction amount")
    if row.get("Near_Threshold") == 1: r.append("Near reporting threshold")
    if row.get("Unique_Receivers", 0) > 10:
        r.append(f"{int(row['Unique_Receivers'])} unique receivers")
    if row.get("Sender_Deviation", 0) > 3:
        r.append("Amount exceeds sender normal behaviour")
    if iso_flag or row.get("Isolation Score") == 1:
        r.append("Isolation Forest anomaly")
    return r or ["No major suspicious indicators"]
'''
