import pandas as pd
import pyarrow.parquet as pq
import os

DATA_DIR = 'data'

def check_file(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File {filename} not found.")
        return
    
    try:
        table = pq.read_table(filepath)
        df = table.to_pandas()
        print(f"\n=== {filename} ===")
        print(f"Columns ({len(df.columns)}):")
        # Print columns in groups of 5 for readability
        cols = df.columns.tolist()
        for i in range(0, len(cols), 5):
            print(", ".join(cols[i:i+5]))
        
        print("\nFirst row sample:")
        print(df.head(1).T)
        
        # Look for spread/ranking keywords
        keywords = ['spread', 'favorite', 'rank', 'strength', 'seed', 'odds', 'line']
        found = [c for c in df.columns if any(k in c.lower() for k in keywords)]
        if found:
            print(f"\nPotential feature columns: {found}")
            print(df[found].head(5))
            
    except Exception as e:
        print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    check_file("schedule_2024.parquet")
    check_file("team_box_2024.parquet")
    check_file("pbp_2024.parquet")
