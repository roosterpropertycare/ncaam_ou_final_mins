import pandas as pd
import pyarrow.parquet as pq

def inspect_pbp_file():
    try:
        pbp = pd.read_parquet('data/pbp_2024.parquet')
        
        with open('pbp_columns.txt', 'w', encoding='utf-8') as f:
            f.write("=== PBP Columns ===\n")
            cols = pbp.columns.tolist()
            f.write(str(cols) + "\n\n")
            
            f.write("=== Sample Row (Dict) ===\n")
            if not pbp.empty:
                row = pbp.iloc[0].to_dict()
                for k, v in row.items():
                    f.write(f"{k}: {v}\n")
            
            text_col = 'text' if 'text' in cols else ('description' if 'description' in cols else None)
            
            if text_col:
                f.write(f"\n=== Searching '{text_col}' for 'foul' ===\n")
                fouls = pbp[pbp[text_col].str.contains('foul', case=False, na=False)]
                if not fouls.empty:
                    f.write(fouls[[text_col]].head(10).to_string() + "\n")
                
                f.write(f"\n=== Searching '{text_col}' for 'timeout' ===\n")
                timeouts = pbp[pbp[text_col].str.contains('timeout', case=False, na=False)]
                if not timeouts.empty:
                    f.write(timeouts[[text_col]].head(10).to_string() + "\n")
            else:
                f.write("\nCould not find a text/description column.\n")

    except Exception as e:
        with open('pbp_columns.txt', 'w', encoding='utf-8') as f:
            f.write(f"Error: {e}")

if __name__ == '__main__':
    inspect_pbp_file()
