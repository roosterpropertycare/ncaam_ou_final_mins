import json
import sys
import pandas as pd

def check_importance():
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
            cell_code = "\n".join([line for line in cell_code.splitlines() if not line.strip().startswith('%')])
            code += cell_code + "\n"
    
    # Shim
    def display(*args): pass
    exec_globals = {'display': display, 'pd': pd}
    
    print("Executing notebook to get models...")
    try:
        exec(code, exec_globals)
        print("Execution complete.")
        
        # Access 'fitted_3' or similar?
        # In evaluate_models, it returns `fitted, results_df`.
        # The notebook calls: `fitted_3, results_3 = evaluate_models(...)`
        
        if 'fitted_3' in exec_globals:
            fitted = exec_globals['fitted_3']
            if 'Random Forest' in fitted:
                rf = fitted['Random Forest']
                # Feature names?
                # The notebook doesn't save feature names in the model object by default unless we wrap it.
                # But X_3 columns are available.
                if 'X_3' in exec_globals:
                    feature_names = exec_globals['X_3'].columns.tolist()
                    importances = rf.feature_importances_
                    
                    df_imp = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
                    df_imp = df_imp.sort_values('Importance', ascending=False)
                    
                    output = "\n=== 3-Minute Random Forest Feature Importance ===\n"
                    output += df_imp.head(15).to_string(index=False)
                    print(output)
                    
                    with open('importance.txt', 'w', encoding='utf-8') as f:
                        f.write(output)
                else:
                    print("X_3 not found.")
            else:
                print("Random Forest not in fitted_3")
        else:
            print("fitted_3 not found.")

    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_importance()
