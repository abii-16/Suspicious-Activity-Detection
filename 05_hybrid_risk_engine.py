import joblib
import pandas as pd
import numpy as np

# ============================================
# Load Models
# ============================================

print("Loading Models...")

xgb = joblib.load("models/xgb_model.pkl")
iso = joblib.load("models/isolation_forest.pkl")

# ============================================
# Load Features
# ============================================

df = pd.read_csv("data/features.csv")

TARGET = "Is Laundering"

X = df.drop(columns=[TARGET])

# ============================================
# XGBoost Probability
# ============================================

print("Running XGBoost...")

xgb_prob = xgb.predict_proba(X)[:,1]

# ============================================
# Isolation Forest
# ============================================

print("Running Isolation Forest...")

iso_pred = iso.predict(X)

# Convert

# Normal -> 0

# Anomaly -> 1

iso_score = (iso_pred==-1).astype(int)

# ============================================
# Hybrid Score
# ============================================

df["XGB Score"] = xgb_prob

df["Isolation Score"] = iso_score

df["Final Risk Score"] = (

    0.85*xgb_prob +

    0.15*iso_score

)

# ============================================
# Risk Levels
# ============================================

def risk(score):

    if score>=0.90:
        return "CRITICAL"

    elif score>=0.75:
        return "HIGH"

    elif score>=0.50:
        return "MEDIUM"

    return "LOW"

df["Risk Level"] = df["Final Risk Score"].apply(risk)

# ============================================
# Recommended Action
# ============================================

def action(level):

    if level=="CRITICAL":
        return "Freeze account and escalate immediately"

    elif level=="HIGH":
        return "Escalate to AML analyst"

    elif level=="MEDIUM":
        return "Manual Review"

    return "No Action"

df["Recommended Action"] = (

    df["Risk Level"]

    .apply(action)

)

# ============================================
# Top Suspicious Transactions
# ============================================

top = (

    df

    .sort_values(

        "Final Risk Score",

        ascending=False

    )

)

print()

print(top[[

    "Final Risk Score",

    "Risk Level",

    "Recommended Action"

]].head(20))

# ============================================
# Save
# ============================================

top.to_csv(

    "data/risk_predictions.csv",

    index=False

)

print()

print("Saved")

print("data/risk_predictions.csv")