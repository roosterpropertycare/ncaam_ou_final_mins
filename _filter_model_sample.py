import json
from pathlib import Path

NB_PATH = Path("05_model_training.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    modified = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code" and "def build_features" in "".join(cell["source"]):
            source = cell["source"]
            new_source = []
            for line in source:
                new_source.append(line)
                if "entry = entry[entry['margin'] != 0].copy()" in line:
                    # Add filtering logic
                    indent = line[:line.find("entry")] # Keep indentation
                    new_source.append("\n")
                    new_source.append(f"{indent}# ── Filter to specific margin buckets (10-12, 13-15, 16-18, 19+) ──\n")
                    new_source.append(f"{indent}target_buckets = ['10-12', '13-15', '16-18', '19+']\n")
                    new_source.append(f"{indent}entry = entry[entry['fine_bucket'].isin(target_buckets)].copy()\n")
                    new_source.append("\n")
            
            cell["source"] = new_source
            modified = True
            print("Modified build_features cell.")
            break

    if modified:
        with open(NB_PATH, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"Updated {NB_PATH}")
    else:
        print("Could not find relevant cell in notebook.")

if __name__ == "__main__":
    main()
