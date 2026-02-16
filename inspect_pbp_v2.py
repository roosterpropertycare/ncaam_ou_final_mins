import pandas as pd
import pyarrow.parquet as pq

def inspect_pbp():
    # Load just one season of PBP to check columns and content
    # Use try/except block for robustness
    try:
        pbp = pd.read_parquet('data/pbp_2024.parquet')
        
        print("=== PBP Columns ===")
        cols = pbp.columns.tolist()
        print(cols)
        
        print("\n=== Sample Row (Dict) ===")
        # Print first row as dictionary to see values
        if not pbp.empty:
            row = pbp.iloc[0].to_dict()
            for k, v in row.items():
                print(f"{k}: {v}")
        
        # Check for specific keywords in text column if it exists
        text_col = 'text' if 'text' in cols else ('description' if 'description' in cols else None)
        
        if text_col:
            print(f"\n=== Searching '{text_col}' for 'foul' ===")
            fouls = pbp[pbp[text_col].str.contains('foul', case=False, na=False)]
            if not fouls.empty:
                print(fouls[[text_col]].head(5).to_string())
            
            print(f"\n=== Searching '{text_col}' for 'timeout' ===")
            timeouts = pbp[pbp[text_col].str.contains('timeout', case=False, na=False)]
            if not timeouts.empty:
                print(timeouts[[text_col]].head(5).to_string())
        else:
            print("\nCould not find a text/description column.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    inspect_pbp()
