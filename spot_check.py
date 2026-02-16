import json
import pandas as pd
import numpy as np

def spot_check():
    nb_path = '05_model_training.ipynb'
    try:
        with open(nb_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)
    except Exception as e:
        print(f"Error reading notebook: {e}")
        return

    code = ""
    for c in nb['cells']:
        if c['cell_type'] == 'code':
            cell_code = "".join(c['source'])
            # Skip magic commands
            cell_code = "\n".join([line for line in cell_code.splitlines() if not line.strip().startswith('%')])
            code += cell_code + "\n"
    
    # Shim
    def display(*args): pass
    exec_globals = {'display': display, 'pd': pd, 'np': np}
    
    print("Executing notebook to generate dataframes...")
    output_log = []
    def log(msg):
        print(msg)
        output_log.append(str(msg))

    try:
        exec(code, exec_globals)
        log("Execution complete.\n")
        
        if 'df_3' in exec_globals:
            df = exec_globals['df_3']
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            
            log(f"=== Shape: {df.shape} ===")
            
            log("\n=== Sample Rows (Key Features) ===")
            cols = ['game_id', 'margin', 'lead_is_home', 
                    'lead_spread', 'lead_is_fav', 'spread_mag', 
                    'lead_avg_pace', 'trail_avg_pace', 
                    'snapshot_total', 'total_pts']
            
            # Check availability of columns
            present_cols = [c for c in cols if c in df.columns]
            log(df[present_cols].head(10).to_string())
            
            log("\n=== Descriptive Stats (New Features) ===")
            new_feats = ['lead_spread', 'spread_mag', 'snapshot_total', 
                         'lead_avg_pace', 'trail_avg_pace', 
                         'margin_x_trail_3p', 'total_pts']
            
            log(df[[c for c in new_feats if c in df.columns]].describe().round(2).to_string())
            
            log("\n=== Logic Checks ===")
            # 1. Lead is Fav consistency
            if 'lead_is_fav' in df.columns and 'lead_spread' in df.columns:
                inconsistent = df[((df['lead_spread'] < 0) & (df['lead_is_fav'] == 0)) | 
                                  ((df['lead_spread'] >= 0) & (df['lead_is_fav'] == 1))]
                log(f"Inconsistent Favorite Status Rows: {len(inconsistent)}")
                if len(inconsistent) > 0:
                    log(inconsistent[['lead_spread', 'lead_is_fav']].head().to_string())
            
            # 2. Score sanity
            if 'total_pts' in df.columns:
                log(f"Zero Points Games: {len(df[df['total_pts'] == 0])}")
                
            # 3. Missing Values
            log("\n=== Missing Values ===")
            log(df[present_cols].isnull().sum().to_string())
            
            # 4. Check Interaction (X_3)
            if 'X_3' in exec_globals:
                X = exec_globals['X_3']
                log("\n=== X_3 Interaction Stats ===")
                if 'margin_x_trail_3p' in X.columns:
                    log(X['margin_x_trail_3p'].describe().round(4).to_string())
                else:
                    log("margin_x_trail_3p not in X_3")

        else:
            log("df_3 not found in globals.")

    except Exception as e:
        log(f"Execution failed: {e}")
    
    with open('spot_check_results.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(output_log))

if __name__ == '__main__':
    spot_check()
