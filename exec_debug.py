import json
import sys

# Shim for display()
def display(*args):
    for arg in args:
        print(arg)

def exec_only():
    print(f"Python executable: {sys.executable}")
    try:
        import sklearn
        print(f"sklearn version: {sklearn.__version__}")
    except ImportError as e:
        print(f"ImportError for sklearn: {e}")
        print(f"sys.path: {sys.path}")
        return

    nb_path = '05_model_training.ipynb'
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    code = ""
    for c in nb['cells']:
        if c['cell_type'] == 'code':
            cell_code = "".join(c['source'])
            # Skip magic commands
            cell_code = "\n".join([line for line in cell_code.splitlines() if not line.strip().startswith('%')])
            code += cell_code + "\n"
    
    exec_globals = {'display': display}
    try:
        exec(code, exec_globals)
        print("Execution complete.")
        # Retrieve results directly
        if 'results_3' in exec_globals:
             print("\n=== 3-Minute Model Results (DataFrame) ===")
             print(exec_globals['results_3'])
        if 'results_5' in exec_globals:
             print("\n=== 5-Minute Model Results (DataFrame) ===")
             print(exec_globals['results_5'])
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    exec_only()
