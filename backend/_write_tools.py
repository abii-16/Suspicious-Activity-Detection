"""Run this once to rebuild tools.py with all functions."""
import pathlib, sys

src = pathlib.Path(__file__).parent / "tools.py"

code = """\
from __future__ import annotations
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
            filtered = filtered.loc[[tid]] if tid in filtered.index else (
                filtered.iloc[[tid]] if tid < len(filtered) else filtered)
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
        mw = max(1, min(12, math.ceil(int(filters["days"]) / 30)))
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


# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------

def run_eda(filters=None):
    from backend.loader import get_eda_cache
    if not filters:
        return get_eda_cache()
    df = _apply_filters(get_risk_predictions_df(), filters)
    n = len(df)
    fp = round(float(df[TARGET_COLUMN].mean() * 100), 4) if n else 0.0
    aa = round(float(df["Amount Paid"].mean()), 2) if n else 0.0
    tl = int(df[TARGET_COLUMN].sum()) if TARGET_COLUMN in df.columns else 0
    return safe_json({
        "total_rows": n, "total_columns": len(df.columns),
        "fraud_percentage": fp, "total_laundering_transactions": tl,
        "average_amount": aa, "average_amount_formatted": format_currency(aa),
        "amount_min": round(float(df["Amount Paid"].min()), 2) if n else 0.0,
        "amount_max": round(float(df["Amount Paid"].max()), 2) if n else 0.0,
        "amount_max_formatted": format_currency(round(float(df["Amount Paid"].max()), 2)) if n else "",
        "amount_median": round(float(df["Amount Paid"].median()), 2) if n else 0.0,
        "top_banks": {str(k): int(v) for k, v in df["From Bank"].value_counts().head(8).items()} if "From Bank" in df.columns else {},
        "top_currencies": {str(k): int(v) for k, v in df["Payment Currency"].value_counts().head(8).items()} if "Payment Currency" in df.columns else {},
        "payment_formats": {str(k): int(v) for k, v in df["Payment Format"].value_counts().head(8).items()} if "Payment Format" in df.columns else {},
        "risk_distribution": {str(k): int(v) for k, v in df["Risk Level"].value_counts().items()} if "Risk Level" in df.columns else {},
        "dataset_summary": f"{n:,} transactions. {tl:,} flagged ({fp}%). Avg: {format_currency(aa)}.",
        "rows": n, "fraud_pct": fp,
        "currency_distribution": {str(k): int(v) for k, v in df["Payment Currency"].value_counts().head(8).items()} if "Payment Currency" in df.columns else {},
        "top_payment_formats": {str(k): int(v) for k, v in df["Payment Format"].value_counts().head(8).items()} if "Payment Format" in df.columns else {},
    })


def predict_transaction(features):
    fc = get_feature_columns()
    missing = [c for c in fc if c not in features]
    if missing:
        raise ValueError(f"Missing features: {missing}")
    xgb = get_xgb_model(); iso = get_isolation_forest()
    row = pd.DataFrame([features])[fc]
    prob = float(xgb.predict_proba(row)[0][1])
    iso_flag = int(iso.predict(row)[0] == -1)
    score = HYBRID_XGB_WEIGHT * prob + HYBRID_ISO_WEIGHT * iso_flag
    level = risk_level(score)
    enriched = pd.Series({**features, "Isolation Score": iso_flag})
    return safe_json({"xgb_score": round(prob, 4), "isolation_anomaly": bool(iso_flag),
                      "risk_score": round(score, 4), "risk_level": level,
                      "aml_pattern": _detect_aml_pattern(enriched),
                      "reasons": _build_reasons(enriched, iso_flag=bool(iso_flag)),
                      "recommendation": recommendation(level)})


def top_suspicious_transactions(n=20, filters=None):
    df = _apply_filters(get_risk_predictions_df(), filters)
    sc = "Final Risk Score" if "Final Risk Score" in df.columns else "Risk Score"
    top = df.sort_values(sc, ascending=False).head(n)
    records = []
    for idx, row in top.iterrows():
        records.append(safe_json({
            "transaction_id": int(idx), "account": int(row["Account"]),
            "amount_paid": round(float(row["Amount Paid"]), 2),
            "risk_score": round(float(row[sc]), 4),
            "risk_level": row.get("Risk Level", risk_level(float(row[sc]))),
            "aml_pattern": _detect_aml_pattern(row), "actual_label": int(row[TARGET_COLUMN]),
            "recommended_action": row.get("Recommended Action"),
        }))
    return {"count": len(records), "transactions": records}


def customer_summary(customer_id, filters=None):
    cdf = get_customer_df(customer_id)
    if cdf is None:
        cdf = _apply_filters(get_risk_predictions_df(), {**(filters or {}), "customer_id": customer_id})
    if cdf is None or len(cdf) == 0:
        return {"customer_id": customer_id, "found": False, "message": f"No transactions for customer {customer_id}."}
    sc = "Final Risk Score" if "Final Risk Score" in cdf.columns else None
    max_risk = float(cdf[sc].max()) if sc else 0.0
    level = (cdf.loc[cdf[sc].idxmax(), "Risk Level"] if sc and "Risk Level" in cdf.columns else risk_level(max_risk))
    suspicious = int((cdf[TARGET_COLUMN] == 1).sum()) if TARGET_COLUMN in cdf.columns else 0
    hrc = int(cdf["Risk Level"].isin(["HIGH", "CRITICAL"]).sum()) if "Risk Level" in cdf.columns else 0
    hrp = round((hrc / len(cdf)) * 100, 2) if len(cdf) else 0.0
    is_susp = suspicious > 0 or hrp > 0 or str(level).upper() in ("HIGH", "CRITICAL")
    top_reasons = []
    if sc and len(cdf) > 0:
        tr = cdf.loc[cdf[sc].idxmax()]
        top_reasons = [x for x in _build_reasons(tr, iso_flag=bool(tr.get("Isolation Score", 0))) if "no major" not in x.lower()]
    sdf = cdf.sort_values(sc, ascending=False) if sc else cdf
    return safe_json({
        "customer_id": customer_id, "found": True, "is_suspicious": is_susp,
        "transaction_count": len(cdf),
        "total_amount_sent": round(float(cdf["Amount Paid"].sum()), 2),
        "total_amount_received": round(float(cdf["Amount Received"].sum()), 2) if "Amount Received" in cdf.columns else 0.0,
        "max_risk_score": round(max_risk, 4), "risk_level": level,
        "high_risk_pct": hrp, "high_risk_count": hrc,
        "suspicious_transactions": suspicious, "top_risk_reasons": top_reasons,
        "recommendation": recommendation(level),
        "recent_transactions": records_from_df(sdf, limit=10),
    })


def transaction_summary(transaction_id, filters=None):
    fdf = get_features_df(); rdf = get_risk_predictions_df()
    if transaction_id < 0 or transaction_id >= len(fdf):
        return {"transaction_id": transaction_id, "found": False, "message": f"Transaction {transaction_id} out of range."}
    fr = fdf.iloc[transaction_id]; rr = rdf.iloc[transaction_id]
    sc = "Final Risk Score" if "Final Risk Score" in rr.index else None
    score = float(rr[sc]) if sc else 0.0
    level = rr.get("Risk Level", risk_level(score))
    iso_flag = bool(rr.get("Isolation Score", 0))
    return safe_json({
        "transaction_id": transaction_id, "found": True,
        "account": int(rr["Account"]), "counterparty": int(rr["Account.1"]),
        "amount_paid": round(float(rr["Amount Paid"]), 2),
        "from_bank": int(rr["From Bank"]) if "From Bank" in rr.index else None,
        "to_bank": int(rr["To Bank"]) if "To Bank" in rr.index else None,
        "payment_currency": int(rr["Payment Currency"]) if "Payment Currency" in rr.index else None,
        "payment_format": int(rr["Payment Format"]) if "Payment Format" in rr.index else None,
        "xgb_score": round(float(rr.get("XGB Score", 0)), 4),
        "isolation_anomaly": iso_flag, "isolation_score": int(rr.get("Isolation Score", 0)),
        "risk_score": round(score, 4), "risk_level": level,
        "aml_pattern": _detect_aml_pattern(rr), "actual_label": int(rr[TARGET_COLUMN]),
        "reasons": _build_reasons(rr, iso_flag=iso_flag),
        "recommendation": rr.get("Recommended Action", recommendation(level)),
        "features": safe_json(fr.to_dict()),
    })


def rule_engine(rules=None):
    rules = rules or {}; df = get_risk_predictions_df(); matches = []; rule_type = "custom"
    if rules.get("rapid_transactions"):
        rule_type = "rapid_transactions"
        flagged = df[df["Rapid_5m"] == 1].groupby("Account").size().reset_index(name="cnt")
        flagged = flagged[flagged["cnt"] >= rules.get("min_count", 3)]
        for _, row in flagged.head(50).iterrows():
            matches.append({"account": int(row["Account"]), "rapid_count": int(row["cnt"]), "rule": rule_type})
    elif rules.get("near_threshold"):
        rule_type = "near_reporting_threshold"
        flagged = df[df["Near_Threshold"] == 1].groupby("Account").size().reset_index(name="cnt")
        flagged = flagged[flagged["cnt"] >= rules.get("min_count", 2)]
        for _, row in flagged.head(50).iterrows():
            matches.append({"account": int(row["Account"]), "near_threshold_count": int(row["cnt"]), "rule": rule_type})
    else:
        min_tx = int(rules.get("min_transactions_under_amount", 10))
        cap = float(rules.get("amount_threshold", 10000))
        rule_type = f"transactions_under_{int(cap)}"
        grouped = df[df["Amount Paid"] < cap].groupby("Account").size().reset_index(name="tx_count")
        flagged = grouped[grouped["tx_count"] >= min_tx].sort_values("tx_count", ascending=False)
        for _, row in flagged.head(50).iterrows():
            matches.append({"account": int(row["Account"]), "transaction_count": int(row["tx_count"]), "amount_threshold": cap, "rule": rule_type})
    return safe_json({"rule_type": rule_type, "rules_applied": rules, "match_count": len(matches), "matches": matches})


def generate_explanation(transaction_id=None, row=None, filters=None):
    if row is not None:
        iso = bool(row.get("Isolation Score", 0))
        reasons = _build_reasons(row, iso_flag=iso)
        return safe_json({"aml_pattern": _detect_aml_pattern(row), "reasons": reasons, "explanation": " | ".join(reasons)})
    df = _apply_filters(get_risk_predictions_df(), filters)
    if transaction_id is not None:
        if transaction_id < 0 or transaction_id >= len(df):
            return {"found": False, "message": f"Transaction {transaction_id} not found."}
        res = generate_explanation(row=df.iloc[transaction_id])
        res["transaction_id"] = transaction_id
        return res
    sc = "Final Risk Score" if "Final Risk Score" in df.columns else None
    sample = df.sort_values(sc, ascending=False).head(5) if sc else df.head(5)
    explanations = []
    for idx, r in sample.iterrows():
        d = generate_explanation(row=r); d["transaction_id"] = int(idx); explanations.append(d)
    return {"count": len(explanations), "explanations": explanations}


def generate_risk(filters=None, limit=20):
    cid = None
    if filters:
        try: cid = int(filters["customer_id"])
        except (KeyError, TypeError, ValueError): pass
    filtered = get_customer_df(cid) if cid is not None else _apply_filters(get_risk_predictions_df(), filters)
    if filtered is None or len(filtered) == 0:
        return {"scored_count": 0, "returned_count": 0, "top_risk_level": "LOW", "transactions": []}
    if "Final Risk Score" in filtered.columns:
        sc = "Final Risk Score"; top = filtered.nlargest(limit, sc); records = []
        for idx, row in top.iterrows():
            s = float(row[sc]); lv = row.get("Risk Level", risk_level(s))
            records.append({"transaction_id": int(idx), "risk_score": round(s, 4), "risk_level": lv,
                            "xgb_score": round(float(row.get("XGB Score", 0)), 4),
                            "isolation_anomaly": bool(row.get("Isolation Score", 0)),
                            "recommendation": row.get("Recommended Action", recommendation(lv))})
        return safe_json({"scored_count": len(filtered), "returned_count": len(records),
                          "top_risk_level": records[0]["risk_level"] if records else "LOW", "transactions": records})
    # live inference fallback
    fc = get_feature_columns(); xgb = get_xgb_model(); iso = get_isolation_forest()
    subset = _apply_filters(get_features_df(), filters).head(limit); records = []
    for idx, row in subset.iterrows():
        x = row[fc].to_frame().T
        prob = float(xgb.predict_proba(x)[0][1]); iso_flag = int(iso.predict(x)[0] == -1)
        s = HYBRID_XGB_WEIGHT * prob + HYBRID_ISO_WEIGHT * iso_flag; lv = risk_level(s)
        records.append({"transaction_id": int(idx), "risk_score": round(s, 4), "risk_level": lv,
                        "xgb_score": round(prob, 4), "isolation_anomaly": bool(iso_flag), "recommendation": recommendation(lv)})
    records.sort(key=lambda x: x["risk_score"], reverse=True)
    return safe_json({"scored_count": len(subset), "returned_count": len(records),
                      "top_risk_level": records[0]["risk_level"] if records else "LOW", "transactions": records})


def filter_data(filters=None):
    df = get_risk_predictions_df(); filtered = _apply_filters(df, filters)
    return safe_json({"total_rows": len(df), "filtered_rows": len(filtered),
                      "filters_applied": filters or {}, "columns": list(filtered.columns)})


def get_dashboard_stats(filters=None):
    df = _apply_filters(get_risk_predictions_df(), filters)
    total = len(df); sc = "Final Risk Score" if "Final Risk Score" in df.columns else None
    avg_score = round(float(df[sc].mean()), 4) if sc and total else 0.0
    rd = df["Risk Level"].value_counts().to_dict() if "Risk Level" in df.columns and total else {}
    fp = round(float(df[TARGET_COLUMN].mean() * 100), 4) if TARGET_COLUMN in df.columns and total else 0.0
    fdf = get_features_df(); risk_trend = []
    if total and sc and "Month" in fdf.columns and len(fdf) == len(get_risk_predictions_df()):
        tdf = df[[sc]].copy(); tdf["Month"] = fdf["Month"].values
        if "Risk Level" in df.columns: tdf["Risk Level"] = df["Risk Level"].values
        grp = tdf.groupby("Month").agg(avg_risk_score=(sc, "mean"), transaction_count=(sc, "count")).reset_index().sort_values("Month")
        for _, row in grp.iterrows():
            risk_trend.append(safe_json({"month": int(row["Month"]), "avg_risk_score": round(float(row["avg_risk_score"]), 4), "transaction_count": int(row["transaction_count"]), "high_risk_count": 0}))
    return safe_json({
        "total_transactions": total,
        "high_risk_count": int(rd.get("HIGH", 0)),
        "critical_risk_count": int(rd.get("CRITICAL", 0)),
        "average_risk_score": avg_score, "flagged_pct": fp,
        "risk_distribution": rd, "risk_trend": risk_trend,
        "top_banks": df["From Bank"].value_counts().head(8).to_dict() if "From Bank" in df.columns and total else {},
        "currency_distribution": df["Payment Currency"].value_counts().head(8).to_dict() if "Payment Currency" in df.columns and total else {},
        "payment_format_distribution": df["Payment Format"].value_counts().head(8).to_dict() if "Payment Format" in df.columns and total else {},
        "top_suspicious_transactions": top_suspicious_transactions(n=10, filters=filters).get("transactions", []),
    })
"""

src.write_text(code, encoding="utf-8")
print("Written", len(code), "chars,", code.count("\\n"), "lines")
print("Functions:", [l.split("(")[0].replace("def ","") for l in code.split("\\n") if l.startswith("def ")])

# The script above writes everything except the 5 new tools.
# Append them now:

EXTRA = """

def analytics_tool(group_by="bank", metric="suspicious_transactions", top_n=10, filters=None):
    df = _apply_filters(get_risk_predictions_df(), filters) if filters else get_risk_predictions_df()
    col = _GROUP_BY_COL.get(group_by.lower(), group_by)
    if col not in df.columns:
        return safe_json({"error": f"Column not found: {col}"})
    sc = "Final Risk Score" if "Final Risk Score" in df.columns else None
    agg = {"transaction_count": (TARGET_COLUMN, "count")}
    if TARGET_COLUMN in df.columns: agg["suspicious_count"] = (TARGET_COLUMN, "sum")
    if sc: agg["avg_risk_score"] = (sc, "mean"); agg["max_risk_score"] = (sc, "max")
    if "Amount Paid" in df.columns: agg["total_amount"] = ("Amount Paid", "sum"); agg["avg_amount"] = ("Amount Paid", "mean")
    grouped = df.groupby(col).agg(**agg).reset_index()
    if "suspicious_count" in grouped.columns:
        grouped["fraud_rate_pct"] = (grouped["suspicious_count"] / grouped["transaction_count"].clip(lower=1) * 100).round(4)
    if "Risk Level" in df.columns:
        hc = df[df["Risk Level"].isin(["HIGH","CRITICAL"])].groupby(col).size().reset_index(name="high_risk_count")
        grouped = grouped.merge(hc, on=col, how="left")
        grouped["high_risk_count"] = grouped["high_risk_count"].fillna(0).astype(int)
    mm = {"suspicious_transactions":"suspicious_count","fraud_rate":"fraud_rate_pct","avg_risk_score":"avg_risk_score","transaction_count":"transaction_count","total_amount":"total_amount","high_risk_count":"high_risk_count"}
    sort_c = mm.get(metric, "suspicious_count")
    if sort_c not in grouped.columns: sort_c = "transaction_count"
    grouped = grouped.sort_values(sort_c, ascending=False).head(top_n)
    for c in grouped.select_dtypes(include="float").columns: grouped[c] = grouped[c].round(4)
    rows = []
    for _, row in grouped.iterrows():
        r = {group_by: str(row[col])}
        for k in ("transaction_count","suspicious_count","fraud_rate_pct","avg_risk_score","max_risk_score","total_amount","avg_amount","high_risk_count"):
            if k in row.index and pd.notna(row[k]): r[k] = row[k]
        rows.append(safe_json(r))
    top = rows[0] if rows else {}; tl = top.get(group_by, "N/A")
    if metric == "suspicious_transactions": headline = f"{group_by.title()} {tl} has highest suspicious transactions: {int(top.get('suspicious_count',0)):,}"
    elif metric == "fraud_rate": headline = f"{group_by.title()} {tl} has highest fraud rate: {top.get('fraud_rate_pct',0):.2f}%"
    elif metric == "avg_risk_score": headline = f"{group_by.title()} {tl} has highest avg risk score: {top.get('avg_risk_score',0):.4f}"
    elif metric == "transaction_count": headline = f"{group_by.title()} {tl} has most transactions: {int(top.get('transaction_count',0)):,}"
    else: headline = f"Top {group_by}: {tl}"
    return safe_json({"group_by": group_by, "metric": metric, "top_n": top_n, "headline": headline, "results": rows})


def investigation_tool(customer_id=None, transaction_id=None, bank_id=None):
    if customer_id is not None: return customer_summary(customer_id)
    if transaction_id is not None: return transaction_summary(transaction_id)
    if bank_id is not None:
        df = get_risk_predictions_df()
        bdf = df[df["From Bank"] == bank_id] if "From Bank" in df.columns else df.iloc[0:0]
        if len(bdf) == 0: return {"bank_id": bank_id, "found": False, "message": f"Bank {bank_id} not found."}
        sc = "Final Risk Score" if "Final Risk Score" in bdf.columns else None
        tot = len(bdf); susp = int((bdf[TARGET_COLUMN]==1).sum()) if TARGET_COLUMN in bdf.columns else 0
        fr = round(susp/tot*100,4) if tot else 0.0; avg = round(float(bdf[sc].mean()),4) if sc else 0.0
        mx = round(float(bdf[sc].max()),4) if sc else 0.0
        rd = {str(k):int(v) for k,v in bdf["Risk Level"].value_counts().items()} if "Risk Level" in bdf.columns else {}
        lv = "HIGH" if (fr>5 or avg>0.5) else ("MEDIUM" if (fr>1 or avg>0.2) else "LOW")
        return safe_json({"bank_id":bank_id,"found":True,"total_transactions":tot,"suspicious_transactions":susp,"fraud_rate_pct":fr,"avg_risk_score":avg,"max_risk_score":mx,"risk_level":lv,"risk_distribution":rd,"recommendation":recommendation(lv)})
    return {"error": "investigation_tool requires customer_id, transaction_id, or bank_id."}


def pattern_detection_tool(pattern_type="structuring", top_n=20, filters=None):
    df = _apply_filters(get_risk_predictions_df(), filters) if filters else get_risk_predictions_df()
    sc = "Final Risk Score" if "Final Risk Score" in df.columns else None
    pm = {"structuring":("Near_Threshold","Structuring / Smurfing"),"near_threshold":("Near_Threshold","Near Reporting Threshold"),"rapid_transactions":("Rapid_5m","Rapid Transaction Pattern"),"rapid":("Rapid_5m","Rapid Transaction Pattern"),"cross_bank":("Cross_Bank","Cross-Bank Transfer"),"currency_change":("Currency_Change","Currency Conversion"),"high_value":("High_Value","Large Value Transfer"),"anomaly":("Isolation Score","Isolation Forest Anomaly"),"fan_out":(None,"Fan-Out Layering")}
    entry = pm.get(pattern_type.lower())
    if not entry: return {"error": f"Unknown pattern_type '{pattern_type}'."}
    flag_col, label = entry
    if pattern_type.lower() == "fan_out":
        matched = df[(df["Rapid_5m"]==1)&(df["Unique_Receivers"]>10)] if "Rapid_5m" in df.columns else df.iloc[0:0]
    elif flag_col and flag_col in df.columns:
        matched = df[df[flag_col]==1]
    else:
        return {"error": f"Column '{flag_col}' not available."}
    tot = len(matched)
    if tot == 0: return safe_json({"pattern_type":pattern_type,"pattern_label":label,"matched_transactions":0,"matched_accounts":0,"headline":f"No {label} transactions found.","top_transactions":[]})
    accts = int(matched["Account"].nunique()) if "Account" in matched.columns else 0
    top = matched.nlargest(top_n, sc) if sc else matched.head(top_n)
    susp = int((matched[TARGET_COLUMN]==1).sum()) if TARGET_COLUMN in matched.columns else 0
    fr = round(susp/tot*100,4) if tot else 0.0; avg = round(float(matched[sc].mean()),4) if sc else None
    recs = []
    for idx, row in top.iterrows():
        rec = {"transaction_id":int(idx)}
        if "Account" in row.index: rec["account"]=int(row["Account"])
        if "Amount Paid" in row.index: rec["amount_paid"]=round(float(row["Amount Paid"]),2)
        if sc: rec["risk_score"]=round(float(row[sc]),4)
        if "Risk Level" in row.index: rec["risk_level"]=str(row["Risk Level"])
        recs.append(safe_json(rec))
    return safe_json({"pattern_type":pattern_type,"pattern_label":label,"matched_transactions":tot,"matched_accounts":accts,"suspicious_transactions":susp,"fraud_rate_pct":fr,"avg_risk_score":avg,"headline":f"Detected {tot:,} {label} transactions across {accts:,} accounts. Fraud rate: {fr}%.","top_transactions":recs})


def comparison_tool(entity_type="bank", entity_ids=None, top_n=5):
    df = get_risk_predictions_df()
    cm = {"bank":"From Bank","currency":"Payment Currency","payment_format":"Payment Format","customer":"Account"}
    col = cm.get(entity_type.lower())
    if not col or col not in df.columns: return {"error": f"Unknown entity_type '{entity_type}'."}
    if entity_ids:
        subset = df[df[col].isin([int(x) for x in entity_ids])]
    else:
        subset = df[df[col].isin(df[col].value_counts().head(top_n).index.tolist())]
    sc = "Final Risk Score" if "Final Risk Score" in df.columns else None
    agg = {"transaction_count":(TARGET_COLUMN,"count")}
    if TARGET_COLUMN in df.columns: agg["suspicious_count"]=(TARGET_COLUMN,"sum")
    if sc: agg["avg_risk_score"]=(sc,"mean"); agg["max_risk_score"]=(sc,"max")
    if "Amount Paid" in df.columns: agg["total_amount"]=("Amount Paid","sum")
    grouped = subset.groupby(col).agg(**agg).reset_index()
    if "suspicious_count" in grouped.columns:
        grouped["fraud_rate_pct"]=(grouped["suspicious_count"]/grouped["transaction_count"].clip(lower=1)*100).round(4)
    for c in grouped.select_dtypes(include="float").columns: grouped[c]=grouped[c].round(4)
    rows = []
    for _, row in grouped.iterrows():
        r = {entity_type: str(row[col])}
        for k in ("transaction_count","suspicious_count","fraud_rate_pct","avg_risk_score","max_risk_score","total_amount"):
            if k in row.index and pd.notna(row[k]): r[k]=row[k]
        rows.append(safe_json(r))
    rows.sort(key=lambda x: x.get("avg_risk_score") or x.get("fraud_rate_pct") or 0, reverse=True)
    return safe_json({"entity_type":entity_type,"compared_entities":len(rows),"comparison":rows,"highest_risk":rows[0] if rows else {},"lowest_risk":rows[-1] if rows else {}})


def knowledge_tool(topic="overview"):
    kb = {
        "system_overview": {"name":"AI-Powered AML Agent","architecture":"Planner - Router - Tools - Hybrid ML - LLM","ml_pipeline":"XGBoost (85%) + Isolation Forest (15%)","data":"IBM HI-Small AML dataset 5M+ transactions","llm":"Groq LLaMA 3.3 70B for summarisation only"},
        "hybrid_ml": {"components":["XGBoost classifier supervised 85% weight","Isolation Forest anomaly detector unsupervised 15% weight"],"formula":"Final Risk Score = 0.85 x XGBoost_probability + 0.15 x Isolation_Forest_flag"},
        "xgboost": {"type":"Gradient Boosting Classifier","task":"Binary classification P(transaction is money laundering)","features":35,"output":"Probability 0.0 to 1.0"},
        "isolation_forest": {"type":"Unsupervised Anomaly Detection","principle":"Anomalous transactions isolated in fewer random-tree splits","output":"1 anomaly 0 normal"},
        "risk_score": {"formula":"0.85 x XGBoost + 0.15 x IsolationForest","levels":{"CRITICAL":"0.90+ Freeze account","HIGH":"0.75-0.89 Escalate","MEDIUM":"0.50-0.74 Manual review","LOW":"below 0.50 Monitor"}},
        "features": {"categories":["Temporal Hour Day Month","Amount High_Value Near_Threshold","Behaviour Rapid_5m Unique_Receivers","Bank Cross_Bank Currency_Change"],"total_count":35},
        "aml_patterns": {"structuring":"Splitting transactions below $10000 to avoid reporting","layering":"Cross-bank cross-currency transfers to obscure trail","rapid_transactions":"Multiple transactions within 5 minutes","fan_out":"Single sender to many receivers rapidly","high_value":"Top 1 percent transactions by amount"},
        "agent_architecture": {"planner":"Classifies intent extracts entities builds dynamic plan","router":"Executes plan resolves missing parameters","tools":["analytics_tool","investigation_tool","pattern_detection_tool","comparison_tool","knowledge_tool"],"llm_role":"Summarises tool output never predicts"},
    }
    lowered = topic.lower()
    if any(w in lowered for w in ("xgboost","gradient","boost")): relevant = {"xgboost":kb["xgboost"],"hybrid_ml":kb["hybrid_ml"]}
    elif any(w in lowered for w in ("isolation","anomaly","forest")): relevant = {"isolation_forest":kb["isolation_forest"],"hybrid_ml":kb["hybrid_ml"]}
    elif any(w in lowered for w in ("score","formula","calculat","level")): relevant = {"risk_score":kb["risk_score"],"hybrid_ml":kb["hybrid_ml"]}
    elif any(w in lowered for w in ("feature","input")): relevant = {"features":kb["features"]}
    elif any(w in lowered for w in ("pattern","structuring","layering")): relevant = {"aml_patterns":kb["aml_patterns"]}
    elif any(w in lowered for w in ("architect","system","how","agent","work")): relevant = {"system_overview":kb["system_overview"],"agent_architecture":kb["agent_architecture"]}
    else: relevant = kb
    return safe_json({"topic": topic, "knowledge": relevant})


__all__ = [
    "run_eda", "predict_transaction", "top_suspicious_transactions",
    "customer_summary", "transaction_summary", "rule_engine",
    "generate_explanation", "generate_risk", "filter_data", "get_dashboard_stats",
    "analytics_tool", "investigation_tool", "pattern_detection_tool",
    "comparison_tool", "knowledge_tool",
]
"""

existing = src.read_text(encoding="utf-8")
src.write_text(existing + EXTRA, encoding="utf-8")
print("Final lines:", (existing + EXTRA).count("\\n"))
fns = [l.split("(")[0].replace("def ","") for l in (existing + EXTRA).split("\\n") if l.startswith("def ")]
print("Functions:", fns)
