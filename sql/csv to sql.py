import sqlite3
import pandas as pd

df = pd.read_csv("carney government approval polls.csv")

with sqlite3.connect("carney government approval polls.db") as conn:
  df.to_sql("my_table", conn, if_exists="replace", index=False)
