"""
utils.py

Pure helper functions for the AML Agent backend.

No ML logic — formatting, parsing, and lightweight transformations only.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Risk classification helpers
# ---------------------------------------------------------------------------


def risk_level(score: float) -> str:
    """Map a hybrid risk score (0–1) to a categorical level."""
    if score >= 0.90:
        return "CRITICAL"
    if score >= 0.75:
        return "HIGH"
    if score >= 0.50:
        return "MEDIUM"
    return "LOW"


def recommendation(level: str) -> str:
    """Return the recommended analyst action for a risk level."""
    actions = {
        "CRITICAL": "Freeze account immediately and escalate.",
        "HIGH": "Escalate to AML analyst.",
        "MEDIUM": "Manual review required.",
        "LOW": "Continue monitoring.",
    }
    return actions.get(level, "Continue monitoring.")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def safe_json(value: Any) -> Any:
    """
    Convert numpy/pandas scalars to native Python types for JSON output.

    Recursively handles dicts and lists.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        try:
            return safe_json(value.item())
        except (ValueError, AttributeError):
            pass
    return value


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_currency(amount: Union[int, float], currency: str = "USD") -> str:
    """Format a numeric amount as a human-readable currency string."""
    return f"{currency} {float(amount):,.2f}"


def format_timestamp(value: Union[str, datetime, pd.Timestamp]) -> str:
    """Normalize a timestamp value to an ISO-8601 string."""
    if isinstance(value, str):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def parse_date(value: str) -> Optional[datetime]:
    """Parse common date string formats; return None if parsing fails."""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(value).to_pydatetime()
    except (ValueError, TypeError):
        return None


def format_duration_ms(seconds: float) -> float:
    """Convert seconds to milliseconds rounded to two decimal places."""
    return round(seconds * 1000, 2)


def records_from_df(df: pd.DataFrame, limit: int = 50) -> List[Dict[str, Any]]:
    """Convert a DataFrame slice to JSON-safe record dicts."""
    subset = df.head(limit)
    return [safe_json(row) for row in subset.to_dict(orient="records")]


__all__ = [
    "risk_level",
    "recommendation",
    "safe_json",
    "format_currency",
    "format_timestamp",
    "parse_date",
    "format_duration_ms",
    "records_from_df",
]
