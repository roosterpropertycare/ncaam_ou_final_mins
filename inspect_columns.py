import pandas as pd
import glob

files = glob.glob('data/*.parquet')
for f in files:
    try:
        df = pd.read_parquet(f)
        print(f"=== {f} columns ===")
        print(df.columns.tolist())
        print("\n")
    except Exception as e:
        print(f"Error reading {f}: {e}")
