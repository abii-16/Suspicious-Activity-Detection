
"""
03_train_xgboost.py
Train an XGBoost AML classifier on features.csv
"""

import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_fscore_support
)
from xgboost import XGBClassifier

DATA = "data/features.csv"

os.makedirs("models", exist_ok=True)

print("Loading features...")
df = pd.read_csv(DATA)

TARGET = "Is Laundering"

if TARGET not in df.columns:
    raise ValueError(f"{TARGET} column not found")

X = df.drop(columns=[TARGET])
y = df[TARGET]

print("Dataset:", X.shape)
print("Positive class:", y.sum())
print("Negative class:", len(y)-y.sum())

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale = neg / max(pos, 1)

print("scale_pos_weight =", scale)

model = XGBClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="logloss",
    tree_method="hist",
    device="cuda",     # change to "cpu" if GPU unavailable
    scale_pos_weight=scale,
    random_state=42
)

print("\nTraining...")
model.fit(X_train, y_train)

print("\nPredicting...")
pred = model.predict(X_test)
prob = model.predict_proba(X_test)[:, 1]

print("\nROC-AUC :", roc_auc_score(y_test, prob))

p, r, f1, _ = precision_recall_fscore_support(
    y_test,
    pred,
    average="binary",
    zero_division=0
)

print("Precision :", round(p, 4))
print("Recall    :", round(r, 4))
print("F1 Score  :", round(f1, 4))

print("\nConfusion Matrix")
print(confusion_matrix(y_test, pred))

print("\nClassification Report")
print(classification_report(y_test, pred, digits=4))

importance = (
    pd.DataFrame({
        "Feature": X.columns,
        "Importance": model.feature_importances_
    })
    .sort_values("Importance", ascending=False)
)

print("\nTop 20 Features")
print(importance.head(20))

importance.to_csv(
    "models/feature_importance.csv",
    index=False
)

joblib.dump(model, "models/xgb_model.pkl")

print("\nSaved:")
print("models/xgb_model.pkl")
print("models/feature_importance.csv")
