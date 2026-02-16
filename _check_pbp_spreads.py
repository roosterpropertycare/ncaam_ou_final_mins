import pandas as pd
import pyarrow.parquet as pq
import os

def check_pbp():
    df = pq.read_table('data/pbp_2024.parquet').to_pandas()
    spread_cols = [c for c in df.columns if 'spread' in c.lower() or 'line' in c.lower() or 'odds' in c.lower()]
    print("Spread-related columns in PBP:")
    print(spread_cols)
    print("\nSample values:")
    print(df[spread_cols].head(10))
    
    # Check if they change within a game
    for col in spread_cols:
        if df[col].nunique() > 1:
            game_id = df['game_id'].iloc[0]
            game_data = df[df['game_id'] == game_id][col]
            if game_data.nunique() > 1:
                print(f"Column {col} changes within a single game!")
            else:
                print(f"Column {col} is constant within game {game_id}")

if __name__ == "__main__":
    check_pbp()
