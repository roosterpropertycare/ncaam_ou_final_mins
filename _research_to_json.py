import pandas as pd
import pyarrow.parquet as pq
import json
import os

def get_info(filename):
    df = pq.read_table(f'data/{filename}').to_pandas()
    keywords = ['spread', 'favorite', 'rank', 'strength', 'seed', 'odds', 'line', 'score']
    features = [c for c in df.columns if any(k in c.lower() for k in keywords)]
    return {
        "all_columns": df.columns.tolist(),
        "potential_features": features,
        "sample": df[features].head(10).to_dict(orient='records')
    }

if __name__ == "__main__":
    results = {
        "schedule": get_info("schedule_2024.parquet"),
        "team_box": get_info("team_box_2024.parquet")
    }
    with open("research_results.json", "w") as f:
        json.dump(results, f, indent=2)
