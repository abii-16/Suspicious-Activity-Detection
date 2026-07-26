
"""
08_fastapi_backend.py

Run:
    pip install fastapi uvicorn joblib pandas xgboost scikit-learn

Start:
    uvicorn 08_fastapi_backend:app --reload
"""

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --------------------------------------------------
# Load Models
# --------------------------------------------------

print("Loading models...")

xgb = joblib.load("models/xgb_model.pkl")
iso = joblib.load("models/isolation_forest.pkl")

df = pd.read_csv("data/features.csv")

TARGET = "Is Laundering"

FEATURE_COLUMNS = [c for c in df.columns if c != TARGET]

app = FastAPI(
    title="AI AML Detection API",
    version="1.0"
)

# --------------------------------------------------
# Utilities
# --------------------------------------------------

def risk_level(score):
    if score >= 0.90:
        return "CRITICAL"
    elif score >= 0.75:
        return "HIGH"
    elif score >= 0.50:
        return "MEDIUM"
    return "LOW"

def recommendation(level):
    return {
        "CRITICAL":"Freeze account immediately and escalate.",
        "HIGH":"Escalate to AML analyst.",
        "MEDIUM":"Manual review required.",
        "LOW":"Continue monitoring."
    }[level]

def explain(row, iso_flag):
    reasons=[]

    if row["Cross_Bank"]==1:
        reasons.append("Cross-bank transfer")

    if row["Currency_Change"]==1:
        reasons.append("Currency conversion")

    if row["Rapid_5m"]==1:
        reasons.append("Rapid transactions")

    if row["High_Value"]==1:
        reasons.append("High-value transaction")

    if row["Near_Threshold"]==1:
        reasons.append("Near AML reporting threshold")

    if row["Unique_Receivers"]>10:
        reasons.append(f"{int(row['Unique_Receivers'])} unique receivers")

    if row["Sender_Deviation"]>3:
        reasons.append("Amount exceeds sender's normal behaviour")

    if iso_flag:
        reasons.append("Isolation Forest detected anomaly")

    if not reasons:
        reasons.append("No major suspicious indicators")

    return reasons

# --------------------------------------------------
# Request Model
# --------------------------------------------------

class PredictionRequest(BaseModel):
    features: dict

# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message":"AI AML Detection API Running",
        "endpoints":[
            "/health",
            "/sample/{index}",
            "/predict"
        ]
    }

@app.get("/health")
def health():
    return {"status":"healthy"}

@app.get("/sample/{index}")
def sample(index:int):

    if index<0 or index>=len(df):
        raise HTTPException(status_code=404,detail="Index out of range")

    row=df.iloc[index]

    x=row[FEATURE_COLUMNS].to_frame().T

    prob=float(xgb.predict_proba(x)[0][1])

    iso_flag=int(iso.predict(x)[0]==-1)

    score=0.85*prob+0.15*iso_flag

    level=risk_level(score)

    return {
        "transaction_index":index,
        "actual_label":int(row[TARGET]),
        "xgb_score":round(prob,4),
        "isolation_anomaly":bool(iso_flag),
        "risk_score":round(score,4),
        "risk_level":level,
        "reasons":explain(row,iso_flag),
        "recommendation":recommendation(level)
    }

@app.post("/predict")
def predict(req:PredictionRequest):

    data=req.features

    missing=[c for c in FEATURE_COLUMNS if c not in data]

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing features: {missing}"
        )

    x=pd.DataFrame([data])[FEATURE_COLUMNS]

    prob=float(xgb.predict_proba(x)[0][1])
    iso_flag=int(iso.predict(x)[0]==-1)

    score=0.85*prob+0.15*iso_flag
    level=risk_level(score)

    return {
        "xgb_score":round(prob,4),
        "isolation_anomaly":bool(iso_flag),
        "risk_score":round(score,4),
        "risk_level":level,
        "reasons":explain(x.iloc[0],iso_flag),
        "recommendation":recommendation(level)
    }
