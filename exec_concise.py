import json
import sys
import pandas as pd

# Shim for display()
def display(*args):
    pass # Do nothing to avoid spam

def exec_concise():
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
    
    exec_globals = {'display': display, 'pd': pd}
    print("Executing notebook...")
    try:
        exec(code, exec_globals)
        print("Execution complete.")
        
        # Helper to print summary
        def print_summary(name, results_df):
            print(f"\n=== {name} Model Results ===")
            if isinstance(results_df, pd.DataFrame):
                # Sort by R2 descending if available, else just print
                if 'CV R²' in results_df.columns:
                     # Extract mean R2 for sorting if it's a string "mean ± std"
                     # Actually the notebook implies 'R2_mean' col exists in results_df creation
                     if 'R2_mean' in results_df.columns:
                         results_df = results_df.sort_values('R2_mean', ascending=False)
                
                print(results_df[['Model', 'CV RMSE', 'CV R²']].to_string(index=False))
            else:
                print("Results not found or not a DataFrame")

        if 'results_3' in exec_globals:
             print_summary("3-Minute", exec_globals['results_3'])
        else:
            print("results_3 not found in globals")

        if 'results_5' in exec_globals:
             print_summary("5-Minute", exec_globals['results_5'])
        else:
            print("results_5 not found in globals")

    except Exception as e:
        print(f"Execution failed: {e}")
        # print first few lines of error to avoid massive output
        import traceback
        exc_lines = traceback.format_exc().splitlines()
        print("\n".join(exc_lines[-10:]))

if __name__ == '__main__':
    exec_concise()
