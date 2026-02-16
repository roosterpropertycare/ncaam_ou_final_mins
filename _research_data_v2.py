import pandas as pd
import pyarrow.parquet as pq
import os

DATA_DIR = 'data'

def dump_columns(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File {filename} not found.")
        return
    
    table = pq.read_table(filepath)
    df = table.to_pandas()
    print(f"\n--- {filename} Columns ---")
    print(", ".join(df.columns.tolist()))
    print("\n--- Example Data (Potential Features) ---")
    keywords = ['spread', 'favorite', 'rank', 'strength', 'seed', 'odds', 'line']
    found = [c for c in df.columns if any(k in c.lower() for k in keywords)]
    if found:
        print(df[found].head(10).to_string())

if __name__ == "__main__":
    dump_columns("schedule_2024.parquet")
    dump_columns("team_box_2024.parquet")
