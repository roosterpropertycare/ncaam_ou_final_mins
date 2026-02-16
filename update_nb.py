import json
import re

def update_notebook():
    path = '05_model_training.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    def get_cell(cell_id):
        for c in nb['cells']:
            if c.get('id') == cell_id:
                return c
        return None

    # 1. Update c4_snapshot (build_features)
    cell = get_cell('c4_snapshot')
    if cell:
        src = "".join(cell['source'])
        # Precise string match for the block we want to append to
        target = "    entry['lead_spread'] = np.where(\n        entry['margin'] > 0, entry['home_team_spread'], -entry['home_team_spread']\n    )"
        replacement = target + "\n    \n    # ── Leading Team Favorite Status ──\n    entry['lead_is_fav'] = (entry['lead_spread'] < 0).astype(int)\n    entry['spread_mag'] = entry['lead_spread'].abs()"
        
        if target in src:
            src = src.replace(target, replacement)
        else:
            print("Warning: Could not match target in c4_snapshot")
            # Fallback: try to match without indentation if possible or print src to debug
            # print(src) 
        
        cell['source'] = src.splitlines(keepends=True)

    # 2. Update c4_features (CONTINUOUS_FEATURES and prepare_features)
    cell = get_cell('c4_features')
    if cell:
        src = "".join(cell['source'])
        
        # New list
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
]"""
        # Regex to replace the old list
        pattern = r"CONTINUOUS_FEATURES = \[\n.*?\]"
        src = re.sub(pattern, new_list, src, flags=re.DOTALL)
        
        # Interactions
        # Replace usage of X['abs_margin'] with df['abs_margin']
        src = src.replace("X['margin_x_pace'] = X['abs_margin'] * X['lead_avg_pace']", 
                          "X['margin_x_pace'] = df['abs_margin'] * X['lead_avg_pace']")
        
        # Add new interaction
        old_interaction = "X['margin_x_trail_3p'] = X['abs_margin'] * X['trail_avg_3pt_pct']"
        new_interaction = "X['margin_x_trail_3p'] = df['abs_margin'] * X['trail_avg_3pt_pct']\n    X['fav_x_margin'] = X['lead_is_fav'] * df['abs_margin']"
        src = src.replace(old_interaction, new_interaction)
        
        cell['source'] = src.splitlines(keepends=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print("Notebook updated successfully.")

if __name__ == '__main__':
    update_notebook()
