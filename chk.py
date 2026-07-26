import pandas as pd

df = pd.read_csv("data/features.csv")

print(df.shape)
print(df.select_dtypes(include="object").columns)