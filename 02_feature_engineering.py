
"""
02_feature_engineering.py
IBM AML (HI-Small) Feature Engineering
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

INPUT = "data/HI-Small_Trans.csv"
OUTPUT = "data/features.csv"

os.makedirs("models", exist_ok=True)

print("Loading dataset...")
df = pd.read_csv(INPUT)

print("Rows:", len(df))

# ---------------- Timestamp ----------------
df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%Y/%m/%d %H:%M")

df = df.sort_values("Timestamp").reset_index(drop=True)

# ---------------- Time Features ----------------
df["Hour"] = df["Timestamp"].dt.hour
df["Day"] = df["Timestamp"].dt.day
df["Month"] = df["Timestamp"].dt.month
df["Weekday"] = df["Timestamp"].dt.weekday
df["Weekend"] = (df["Weekday"] >= 5).astype(int)

# ---------------- Amount ----------------
df["Log_Amount"] = np.log1p(df["Amount Paid"])
df["Amount_Diff"] = df["Amount Paid"] - df["Amount Received"]
df["Amount_Ratio"] = df["Amount Paid"] / (df["Amount Received"] + 1e-6)

sender_avg = df.groupby("Account")["Amount Paid"].transform("mean")
receiver_avg = df.groupby("Account.1")["Amount Received"].transform("mean")

df["Sender_Avg"] = sender_avg
df["Receiver_Avg"] = receiver_avg

df["Sender_Deviation"] = df["Amount Paid"] / (sender_avg + 1)
df["Receiver_Deviation"] = df["Amount Received"] / (receiver_avg + 1)

high = df["Amount Paid"].quantile(.99)
df["High_Value"] = (df["Amount Paid"] >= high).astype(int)
df["Near_Threshold"] = df["Amount Paid"].between(9000, 10000).astype(int)

# ---------------- Bank / Currency ----------------
df["Cross_Bank"] = (df["From Bank"] != df["To Bank"]).astype(int)
df["Currency_Change"] = (
    df["Receiving Currency"] != df["Payment Currency"]
).astype(int)

# ---------------- Behaviour ----------------
df["Sender_Tx_Count"] = df.groupby("Account").cumcount() + 1
df["Receiver_Tx_Count"] = df.groupby("Account.1").cumcount() + 1

df["Unique_Receivers"] = (
    df.groupby("Account")["Account.1"].transform("nunique")
)

df["Unique_Senders"] = (
    df.groupby("Account.1")["Account"].transform("nunique")
)

prev = df.groupby("Account")["Timestamp"].shift()

df["Minutes_Since_Last"] = (
    (df["Timestamp"] - prev).dt.total_seconds() / 60
).fillna(999999)

df["Rapid_5m"] = (df["Minutes_Since_Last"] < 5).astype(int)
df["Rapid_10m"] = (df["Minutes_Since_Last"] < 10).astype(int)
df["Rapid_30m"] = (df["Minutes_Since_Last"] < 30).astype(int)

# ---------------- Daily aggregates (fast) ----------------
daily_sender = (
    df.groupby(["Account", df["Timestamp"].dt.date])["Amount Paid"]
      .transform("sum")
)

daily_count = (
    df.groupby(["Account", df["Timestamp"].dt.date])["Amount Paid"]
      .transform("count")
)

df["Daily_Sent_Amount"] = daily_sender
df["Daily_Tx_Count"] = daily_count

# ---------------- Encoding ----------------
encoders = {}
cat_cols = [
    "Account",
    "Account.1",
    "Receiving Currency",
    "Payment Currency",
    "Payment Format",
]

for c in cat_cols:
    le = LabelEncoder()
    df[c] = le.fit_transform(df[c].astype(str))
    encoders[c] = le

joblib.dump(encoders, "models/label_encoders.pkl")

# Drop timestamp for ML
df.drop(columns=["Timestamp"], inplace=True)

df.to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)
print("Shape:", df.shape)
print(df.head())
