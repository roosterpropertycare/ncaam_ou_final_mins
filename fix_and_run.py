import json
import re

def fix_and_run():
    nb_path = '05_model_training.ipynb'
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # 1. Fix c4_features
    # The cell likely contains:
    # CONTINUOUS_FEATURES = [ ... ] <old_garbage> ... ]
    
    for c in nb['cells']:
        if c.get('id') == 'c4_features':
            src = "".join(c['source'])
            
            # The pattern I inserted ends with `]`. 
            # The garbage following it likely starts with `'trail_avg_3pt_pct'` or similar.
            # I want to keep everything from start up to the first `]` (which closes my new list), 
            # and then remove everything until the *next* `]` (which closed the old list).
            # But safer is to just find `CONTINUOUS_FEATURES = [...]` and replace the whole thing with the clean version.
            
            # Let's just find the start of CONTINUOUS_FEATURES and the start of prepare_features (which is `def prepare_features`).
            # Everything in between is the list.
            
            start_marker = "CONTINUOUS_FEATURES = ["
            end_marker = "def prepare_features(df):"
            
            start_idx = src.find(start_marker)
            end_idx = src.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                # Re-insert the correct list
                new_list = """CONTINUOUS_FEATURES = [
    # 'abs_margin',             # REMOVED: Redundant with fine_bucket
    'lead_avg_def_eff',         # Adj defensive efficiency (leading team)
    'lead_avg_off_eff',         # Adj offensive efficiency (leading team)
    'trail_avg_off_eff',        # Adj offensive efficiency (trailing team)
    'lead_avg_pace',            # Pace (leading team)
    'trail_avg_pace',           # Pace (trailing team) [NEW]
    'trail_avg_3pt_pct',        # 3P% (trailing team)
    'trail_avg_3pa',            # 3PA Volume (trailing team) [NEW]
    'lead_avg_3pt_pct',         # 3P% (leading team) [NEW]
    'lead_oreb_pctile',         # ORB ranking (leading team)
    'lead_is_home',             # Home/away status
    'snapshot_total',           # Total score at snapshot [NEW]
    'lead_spread',              # Game spread relative to leader [NEW]
    'lead_is_fav',              # Is leading team the favorite? [NEW]
    'spread_mag',               # Magnitude of spread [NEW]
    'lead_avg_to_rate',         # Turnover rate (leading) [NEW]
    'trail_avg_to_rate',        # Turnover rate (trailing) [NEW]
    'lead_avg_ft_pct',          # FT% (leading) [NEW]
    'trail_avg_ft_pct',         # FT% (trailing) [NEW]
    'lead_rank',                # Team rank (leading) [NEW]
    'trail_rank',               # Team rank (trailing) [NEW]
]

# One-hot encode the margin bucket (most important feature)
"""
                pre = src[:start_idx]
                post = src[end_idx:]
                new_src = pre + new_list + post
                c['source'] = new_src.splitlines(keepends=True)
                print("Fixed c4_features.")
            else:
                 print("Could not find markers in c4_features to fix.")

    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

    # 2. Execute the notebook logic
    print("Executing notebook logic...")
    code = ""
    for c in nb['cells']:
        if c['cell_type'] == 'code':
            cell_code = "".join(c['source'])
            # Skip magic commands
            cell_code = "\n".join([line for line in cell_code.splitlines() if not line.strip().startswith('%')])
            code += cell_code + "\n"
    
    # Execute in a discrete environment
    exec_globals = {}
    try:
        exec(code, exec_globals)
        print("Execution complete.")
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_and_run()
