"""
app.py

FastAPI application for the AI-Powered AML Agent.

Contains ONLY route definitions — all logic is delegated to router.py.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend import loader
from backend.router import handle_query
from backend.tools import (
    customer_summary,
    generate_explanation,
    predict_transaction,
    rule_engine,
    run_eda,
    top_suspicious_transactions,
    transaction_summary,
)
from backend.utils import safe_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load ML artifacts once at startup."""
    logger.info("Starting AML Agent — loading resources …")
    loader.load_all()
    logger.info("AML Agent ready.")
    yield


app = FastAPI(
    title="AI-Powered AML Agent",
    description="Agentic anti-money laundering system with dynamic tool execution.",
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PredictionRequest(BaseModel):
    features: Dict[str, Any]


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language AML query")


class RuleEngineRequest(BaseModel):
    min_transactions_under_amount: Optional[int] = 10
    amount_threshold: Optional[float] = 10_000
    min_daily_volume: Optional[float] = None
    rapid_transactions: Optional[bool] = None
    near_threshold: Optional[bool] = None
    min_count: Optional[int] = 3


# ---------------------------------------------------------------------------
# Existing endpoints (preserved)
# ---------------------------------------------------------------------------


@app.get("/")
def home() -> Dict[str, Any]:
    return {
        "message": "AI-Powered AML Agent Running",
        "version": "2.0.0",
        "endpoints": [
            "/health",
            "/sample/{index}",
            "/predict",
            "/eda",
            "/top_suspicious",
            "/customer/{customer_id}",
            "/transaction/{transaction_id}",
            "/rule_engine",
            "/query",
        ],
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "models_loaded": loader.is_loaded(),
    }


@app.get("/sample/{index}")
def sample(index: int) -> Dict[str, Any]:
    result = transaction_summary(index)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))

    risk_df = loader.get_risk_predictions_df()
    risk_row = risk_df.iloc[index]

    return safe_json(
        {
            "transaction_index": index,
            "actual_label": result["actual_label"],
            "xgb_score": round(float(risk_row.get("XGB Score", 0)), 4),
            "isolation_anomaly": bool(risk_row.get("Isolation Score", 0)),
            "risk_score": result["risk_score"],
            "risk_level": result["risk_level"],
            "reasons": result["reasons"],
            "recommendation": result["recommendation"],
        }
    )


@app.post("/predict")
def predict(req: PredictionRequest) -> Dict[str, Any]:
    try:
        return predict_transaction(req.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# New agent endpoints
# ---------------------------------------------------------------------------


@app.get("/eda")
def eda() -> Dict[str, Any]:
    return run_eda()


@app.get("/top_suspicious")
def top_suspicious(n: int = 20) -> Dict[str, Any]:
    if n < 1 or n > 100:
        raise HTTPException(status_code=400, detail="n must be between 1 and 100")
    return top_suspicious_transactions(n=n)


@app.get("/customer/{customer_id}")
def customer(customer_id: int) -> Dict[str, Any]:
    result = customer_summary(customer_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "Customer not found"))
    return result


@app.get("/transaction/{transaction_id}")
def transaction(transaction_id: int) -> Dict[str, Any]:
    result = transaction_summary(transaction_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "Transaction not found"))
    return result


@app.post("/rule_engine")
def run_rule_engine(req: RuleEngineRequest) -> Dict[str, Any]:
    rules = req.model_dump(exclude_none=True)
    return rule_engine(rules)


@app.post("/query")
def query(req: QueryRequest) -> Dict[str, Any]:
    """
    Natural-language AML agent endpoint.

    The planner selects tools dynamically; the response includes an
    ``execution_summary`` block designed for hackathon judge inspection.
    """
    try:
        return handle_query(req.query)
    except Exception as exc:
        logger.exception("Query execution failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
