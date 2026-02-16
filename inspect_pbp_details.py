import pandas as pd
import pyarrow.parquet as pq
import os

def inspect_pbp():
    # Load just one season of PBP to check columns and content
    pbp = pd.read_parquet('data/pbp_2024.parquet')
    
    print("=== PBP Columns ===")
    print(pbp.columns.tolist())
    
    # Check for foul/timeout text in 'text' or 'type' columns if they exist
    # Inspect a sample of rows where 'foul' or 'timeout' appears
    if 'text' in pbp.columns:
        print("\n=== Sample Foul Plays ===")
        fouls = pbp[pbp['text'].str.contains('foul', case=False, na=False)]
        print(fouls[['text', 'clock', 'home_score', 'away_score']].head().to_string())
        
        print("\n=== Sample Timeout Plays ===")
        timeouts = pbp[pbp['text'].str.contains('timeout', case=False, na=False)]
        print(timeouts[['text', 'clock']].head().to_string())

if __name__ == '__main__':
    inspect_pbp()
