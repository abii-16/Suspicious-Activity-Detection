import pandas as pd
import joblib
import random

# ============================================
# Load trained models
# ============================================

print("Loading models...")

xgb = joblib.load("models/xgb_model.pkl")
iso = joblib.load("models/isolation_forest.pkl")

# ============================================
# Load engineered features
# ============================================

print("Loading features...")

df = pd.read_csv("data/features.csv")

TARGET = "Is Laundering"

X = df.drop(columns=[TARGET])
y = df[TARGET]

print(f"Dataset Shape : {df.shape}")

# ============================================
# Select random transactions
# ============================================

NUM_SAMPLES = 20

indices = random.sample(range(len(df)), NUM_SAMPLES)

print("\n==============================================")
print(f"Testing {NUM_SAMPLES} Random Transactions")
print("==============================================\n")

correct = 0

for i, idx in enumerate(indices, start=1):

    row = X.iloc[[idx]]

    actual = int(y.iloc[idx])

    # ----------------------------
    # XGBoost prediction
    # ----------------------------

    probability = float(xgb.predict_proba(row)[0][1])

    prediction = int(probability >= 0.5)

    # ----------------------------
    # Isolation Forest
    # ----------------------------

    iso_prediction = int(iso.predict(row)[0] == -1)

    # ----------------------------
    # Hybrid Risk
    # ----------------------------

    final_score = 0.85 * probability + 0.15 * iso_prediction

    # ----------------------------
    # Risk Level
    # ----------------------------

    if final_score >= 0.90:
        risk = "CRITICAL"
    elif final_score >= 0.75:
        risk = "HIGH"
    elif final_score >= 0.50:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    if prediction == actual:
        correct += 1

    print("=" * 60)
    print(f"Transaction #{i}")
    print(f"Dataset Index     : {idx}")
    print(f"Actual Label      : {actual}")
    print(f"Predicted Label   : {prediction}")
    print(f"XGBoost Score     : {probability:.4f}")
    print(f"Isolation Forest  : {'Anomaly' if iso_prediction else 'Normal'}")
    print(f"Final Risk Score  : {final_score:.4f}")
    print(f"Risk Level        : {risk}")

    if prediction == actual:
        print("Result            : ✅ Correct")
    else:
        print("Result            : ❌ Incorrect")

print("\n==============================================")
print(f"Accuracy on {NUM_SAMPLES} random samples : {correct}/{NUM_SAMPLES}")
print("==============================================")