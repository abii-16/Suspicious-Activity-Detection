import os
import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix

# -----------------------------
# Load Features
# -----------------------------

DATA_PATH = "data/features.csv"

print("Loading features...")

df = pd.read_csv(DATA_PATH)

TARGET = "Is Laundering"

X = df.drop(columns=[TARGET])
y = df[TARGET]

print("Dataset Shape:", X.shape)

# -----------------------------
# Train Isolation Forest
# -----------------------------

print("\nTraining Isolation Forest...")

iso = IsolationForest(
    n_estimators=300,
    contamination=0.001,     # ≈ 0.1% anomalies
    max_samples="auto",
    random_state=42,
    n_jobs=-1
)

iso.fit(X)

# -----------------------------
# Predict
# -----------------------------

print("\nPredicting...")

pred = iso.predict(X)

# Isolation Forest returns:
# -1 = anomaly
#  1 = normal

pred = (pred == -1).astype(int)

# -----------------------------
# Evaluation
# -----------------------------

print("\nConfusion Matrix")

print(confusion_matrix(y, pred))

print("\nClassification Report")

print(classification_report(
    y,
    pred,
    digits=4,
    zero_division=0
))

# -----------------------------
# Save Model
# -----------------------------

os.makedirs("models", exist_ok=True)

joblib.dump(
    iso,
    "models/isolation_forest.pkl"
)

print("\nSaved:")
print("models/isolation_forest.pkl")