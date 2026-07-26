
# 07_explainability.py
import joblib
import pandas as pd

print("Loading models...")
xgb=joblib.load("models/xgb_model.pkl")
iso=joblib.load("models/isolation_forest.pkl")

print("Loading features...")
df=pd.read_csv("data/features.csv")
TARGET="Is Laundering"
X=df.drop(columns=[TARGET])

print("Running predictions...")
xgb_prob=xgb.predict_proba(X)[:,1]
iso_score=(iso.predict(X)==-1).astype(int)

df["XGB Score"]=xgb_prob
df["Isolation Score"]=iso_score
df["Risk Score"]=0.85*xgb_prob+0.15*iso_score

def risk_level(s):
    if s>=0.90:return "CRITICAL"
    if s>=0.75:return "HIGH"
    if s>=0.50:return "MEDIUM"
    return "LOW"
df["Risk Level"]=df["Risk Score"].apply(risk_level)

def explain(r):
    out=[]
    if r["Cross_Bank"]: out.append("Cross-bank transfer detected.")
    if r["Currency_Change"]: out.append("Currency conversion involved.")
    if r["Rapid_5m"]: out.append("Rapid transactions within 5 minutes.")
    if r["Rapid_10m"]: out.append("Multiple transactions within 10 minutes.")
    if r["High_Value"]: out.append("High-value transaction.")
    if r["Near_Threshold"]: out.append("Near AML reporting threshold.")
    if r["Unique_Receivers"]>10: out.append(f"{int(r['Unique_Receivers'])} unique receivers.")
    if r["Sender_Deviation"]>3: out.append(f"Sender deviation {r['Sender_Deviation']:.1f}x.")
    if r["Receiver_Deviation"]>3: out.append(f"Receiver deviation {r['Receiver_Deviation']:.1f}x.")
    if r["Daily_Tx_Count"]>20: out.append("High daily transaction count.")
    if r["Daily_Sent_Amount"]>50000: out.append("Large cumulative daily transfer amount.")
    if r["Isolation Score"]: out.append("Isolation Forest flagged anomaly.")
    return out or ["No major suspicious indicators detected."]

def pattern(r):
    if r["Rapid_5m"] and r["Unique_Receivers"]>10: return "Fan-Out Layering"
    if r["Near_Threshold"]: return "Structuring / Smurfing"
    if r["Cross_Bank"] and r["Currency_Change"]: return "Cross-Border Layering"
    if r["High_Value"]: return "Large Value Transfer"
    return "No dominant AML pattern"

def action(level):
    return {
        "CRITICAL":"Freeze account and escalate immediately.",
        "HIGH":"Escalate to AML analyst.",
        "MEDIUM":"Manual review required.",
        "LOW":"Continue monitoring."
    }[level]

reports=[]
top=df.sort_values("Risk Score",ascending=False).head(100)

for idx,row in top.iterrows():
    reasons=explain(row)
    reports.append({
        "Transaction Index":idx,
        "Actual Label":int(row[TARGET]),
        "Risk Score":round(float(row["Risk Score"]),4),
        "Risk Level":row["Risk Level"],
        "AML Pattern":pattern(row),
        "Recommendation":action(row["Risk Level"]),
        "Explanation":" | ".join(reasons)
    })

    print("="*70)
    print("AML INVESTIGATION REPORT")
    print(f"Transaction: {idx}")
    print(f"Actual Label: {int(row[TARGET])}")
    print(f"Risk Score: {row['Risk Score']:.4f}")
    print(f"Risk Level: {row['Risk Level']}")
    print("Evidence:")
    for e in reasons:
        print("✓",e)
    print("AML Pattern:",pattern(row))
    print("Recommendation:",action(row["Risk Level"]))

pd.DataFrame(reports).to_csv("data/investigation_reports.csv",index=False)
print("Saved: data/investigation_reports.csv")
