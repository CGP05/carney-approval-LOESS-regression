import sqlite3
import pandas as pd

df = pd.read_csv("carney government approval polls.csv")

conn = sqlite3.connect("carney government approval polls.db")

df.to_sql("my_table", conn, if_exists="replace", index=False)

conn.close()
