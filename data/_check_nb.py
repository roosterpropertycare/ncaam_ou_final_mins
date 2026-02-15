import json
with open('03_major_conf_analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)
print(f"Total cells: {len(nb['cells'])}")
for c in nb['cells']:
    first_line = c['source'][0].strip() if c['source'] else '(empty)'
    print(f"  {c['id']:<6} [{c['cell_type']:<8}] {first_line[:70]}")
