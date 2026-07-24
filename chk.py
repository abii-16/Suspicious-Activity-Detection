import pandas as pd

df = pd.read_csv("data/HI-Small_Trans.csv")

print(df["Timestamp"].head(20).tolist())