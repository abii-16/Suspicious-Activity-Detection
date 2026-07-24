import pandas as pd

df = pd.read_csv("data/HI-Small_Trans.csv")

print("Original Shape:", df.shape)

# -----------------------
# Remove duplicate rows
# -----------------------

df = df.drop_duplicates()

print("After removing duplicates:", df.shape)

# -----------------------
# Convert timestamp
# -----------------------

df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# -----------------------
# Sort chronologically
# -----------------------

df = df.sort_values("Timestamp")

# -----------------------
# Missing values
# -----------------------

print(df.isnull().sum())

# -----------------------
# Save cleaned file
# -----------------------

df.to_csv(
    "data/clean_transactions.csv",
    index=False
)

print("Saved clean_transactions.csv")