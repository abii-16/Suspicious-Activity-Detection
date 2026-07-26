import pandas as pd
import joblib
import random

# ============================================================
# Load Models
# ============================================================

print("Loading models...")

xgb = joblib.load("models/xgb_model.pkl")
iso = joblib.load("models/isolation_forest.pkl")

# ============================================================
# Load Dataset
# ============================================================

print("Loading dataset...")

df = pd.read_csv("data/features.csv")

TARGET = "Is Laundering"

X = df.drop(columns=[TARGET])
y = df[TARGET]

print(f"Dataset Shape : {df.shape}")

# ============================================================
# Pick Positive & Negative Samples
# ============================================================

positive = df[df[TARGET] == 1].index.tolist()
negative = df[df[TARGET] == 0].index.tolist()

N = 10

positive_idx = random.sample(positive, N)
negative_idx = random.sample(negative, N)

indices = positive_idx + negative_idx

random.shuffle(indices)

# ============================================================
# Validation
# ============================================================

correct = 0
positive_correct = 0
negative_correct = 0

print("\n")
print("=" * 90)
print("VALIDATING MODEL")
print("=" * 90)

for count, idx in enumerate(indices, start=1):

    row = X.iloc[[idx]]

    actual = int(y.iloc[idx])

    # ------------------------------------------------

    xgb_prob = float(xgb.predict_proba(row)[0][1])

    pred = 1 if xgb_prob >= 0.5 else 0

    iso_pred = int(iso.predict(row)[0] == -1)

    risk = 0.85 * xgb_prob + 0.15 * iso_pred

    if risk >= 0.90:
        level = "CRITICAL"
    elif risk >= 0.75:
        level = "HIGH"
    elif risk >= 0.50:
        level = "MEDIUM"
    else:
        level = "LOW"

    if pred == actual:
        correct += 1

        if actual == 1:
            positive_correct += 1
        else:
            negative_correct += 1

    print("\n")
    print("=" * 90)
    print(f"Transaction #{count}")
    print("=" * 90)

    print(f"Dataset Index          : {idx}")
    print(f"Actual Label           : {actual}")
    print(f"Predicted Label        : {pred}")

    print(f"XGBoost Probability    : {xgb_prob:.6f}")
    print(f"Isolation Forest       : {'Anomaly' if iso_pred else 'Normal'}")
    print(f"Hybrid Risk Score      : {risk:.6f}")
    print(f"Risk Level             : {level}")

    print("\nImportant Features")

    print(f"Amount Paid            : {df.loc[idx,'Amount Paid']}")
    print(f"Amount Received        : {df.loc[idx,'Amount Received']}")
    print(f"Cross Bank             : {df.loc[idx,'Cross_Bank']}")
    print(f"Currency Change        : {df.loc[idx,'Currency_Change']}")
    print(f"Rapid <5 min           : {df.loc[idx,'Rapid_5m']}")
    print(f"Rapid <10 min          : {df.loc[idx,'Rapid_10m']}")
    print(f"High Value             : {df.loc[idx,'High_Value']}")
    print(f"Near Threshold         : {df.loc[idx,'Near_Threshold']}")
    print(f"Unique Receivers       : {df.loc[idx,'Unique_Receivers']}")
    print(f"Unique Senders         : {df.loc[idx,'Unique_Senders']}")
    print(f"Sender Avg             : {df.loc[idx,'Sender_Avg']:.2f}")
    print(f"Receiver Avg           : {df.loc[idx,'Receiver_Avg']:.2f}")
    print(f"Sender Deviation       : {df.loc[idx,'Sender_Deviation']:.2f}")
    print(f"Receiver Deviation     : {df.loc[idx,'Receiver_Deviation']:.2f}")
    print(f"Daily Tx Count         : {df.loc[idx,'Daily_Tx_Count']}")
    print(f"Daily Sent Amount      : {df.loc[idx,'Daily_Sent_Amount']:.2f}")

    if pred == actual:
        print("\nPrediction : ✅ Correct")
    else:
        print("\nPrediction : ❌ Incorrect")

# ============================================================
# Summary
# ============================================================

print("\n")
print("=" * 90)
print("SUMMARY")
print("=" * 90)

print(f"Overall Accuracy : {correct}/{len(indices)}")

print(f"\nPositive Correct : {positive_correct}/{N}")

print(f"Negative Correct : {negative_correct}/{N}")

print("=" * 90)