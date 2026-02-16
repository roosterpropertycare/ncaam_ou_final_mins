import json

def remove_leakage():
    path = '05_model_training.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            modified = False
            for line in source:
                if "'lead_rank'," in line and "REMOVED" not in line:
                    new_source.append("    # 'lead_rank',                # REMOVED: Likely leakage\n")
                    modified = True
                elif "'trail_rank'," in line and "REMOVED" not in line:
                    new_source.append("    # 'trail_rank',               # REMOVED: Likely leakage\n")
                    modified = True
                elif "    entry['lead_rank'] = " in line:
                    # Comment out the calculation too
                    new_source.append("# " + line)
                    modified = True
                elif "    entry['trail_rank'] = " in line:
                    new_source.append("# " + line)
                    modified = True
                elif "'lead_rank'" in line and "entry.dropna" in line:
                     # e.g. feature_cols += [..., 'lead_rank', ...]
                     # This line is harder to patch with simple string replace if it's dynamic
                     # Let's hope dropna relies on CONTINUOUS_FEATURES or explicit list
                     # In build_features, I saw:
                     # feature_cols += ['abs_margin', ..., 'lead_rank', 'trail_rank']
                     new_line = line.replace("'lead_rank', ", "").replace("'trail_rank'", "")
                     # If it leaves a trailing comma or empty logic, verify
                     # It was: ... 'lead_rank', 'trail_rank']
                     # Becomes: ... ]
                     new_source.append(new_line)
                     modified = True
                else:
                    new_source.append(line)
            
            if modified:
                cell['source'] = new_source
                print("Removed rank features in cell.")

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    remove_leakage()
