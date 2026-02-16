import json
import sys
import pandas as pd

# Shim for display()
def display(*args):
    pass 

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
    
    # We need to execute the code in one go to preserve state
    exec_globals = {'display': display, 'pd': pd}
    
    print("Executing notebook...")
    try:
        # Execute the entire accumulated code block
        exec(code, exec_globals)
        print("Execution complete.")
        
        # Helper to print summary
        def print_summary(name, results_df):
            output = f"\n=== {name} Model Results ===\n"
            if isinstance(results_df, pd.DataFrame):
                if 'R2_mean' in results_df.columns:
                     results_df = results_df.sort_values('R2_mean', ascending=False)
                
                output += results_df[['Model', 'CV RMSE', 'CV R²']].to_string(index=False) + "\n"
            else:
                output += "Results not found or not a DataFrame\n"
            
            print(output)
            with open('results_summary.txt', 'a', encoding='utf-8') as f:
                f.write(output)

        # Clear file first
        with open('results_summary.txt', 'w', encoding='utf-8') as f:
            f.write("Execution Started\n")

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
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    exec_concise()
