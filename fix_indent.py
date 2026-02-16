import json

def fix_indent():
    path = '05_model_training.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            source = cell['source']
            new_source = []
            modified = False
            for line in source:
                # Check for the lines we inserted with bad indentation
                if "    pbp_stats = extract_derived_pbp_stats(reg)" in line:
                    new_source.append("pbp_stats = extract_derived_pbp_stats(reg)\n")
                    modified = True
                elif "    reg = reg.merge(pbp_stats, on='id', how='left').fillna(0)" in line:
                    new_source.append("reg = reg.merge(pbp_stats, on='id', how='left').fillna(0)\n")
                    modified = True
                elif "    # ── Advanced PBP Features ──" in line:
                     new_source.append("# ── Advanced PBP Features ──\n")
                     modified = True
                else:
                    new_source.append(line)
            
            if modified:
                cell['source'] = new_source
                print("Fixed indentation in cell.")

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    fix_indent()
