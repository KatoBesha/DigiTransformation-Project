import os 
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

conn = sqlite3.connect("widetable.db")

query = """
SELECT *
FROM pollutant_wide
"""

df = pd.read_sql(query, conn)





missing = df.isnull().sum()

plt.figure(figsize=(10,5))
missing.sort_values(ascending=False).plot(kind="bar")

plt.title("Missing Values by Pollutant")
plt.ylabel("Number of Missing Values")
plt.tight_layout()

plt.show()
print(df.head())
print(df.shape)

print(df.info())
print(df.isnull().sum())
print(df.duplicated().sum())


before = len(df)

missing_pct = df.isnull().mean() * 100

print(missing_pct.sort_values(ascending=False))


cols_to_drop = missing_pct[missing_pct > 70].index

df = df.drop(columns=cols_to_drop)

df = df.drop_duplicates()

after = len(df)

print("Duplicates removed:", before - after)


metadata_cols = [
    "station_id",
    "state",
    "city",
    "station_name",
    "timestamp",
    "datetime"
]


pollutant_cols = [
    col for col in df.columns
    if col not in metadata_cols
]


print(df[pollutant_cols].isnull().sum())

for col in pollutant_cols:
    df[col] = df[col].fillna(df[col].median())


for col in pollutant_cols:

    negative_count = (df[col] < 0).sum()

    print(col, "negative values:", negative_count)

    df.loc[df[col] < 0, col] = None


for col in pollutant_cols:
    df[col] = df[col].fillna(df[col].median())


print(df.isnull().sum())

print(df.describe())


df.to_sql(
    "pollutant_wide_cleaned",
    conn,
    if_exists="replace",
    index=False
)

query = """
SELECT *
FROM pollutant_wide_cleaned
LIMIT 10
"""

cleaned = pd.read_sql(query, conn)

print(cleaned)
