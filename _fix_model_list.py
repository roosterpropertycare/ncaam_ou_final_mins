import json
from pathlib import Path

NB_PATH = Path("05_model_training.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    modified = False
    
    # Update Cell 6 (c4_features) - Actually add them to the list
    for cell in nb["cells"]:
        if cell["id"] == "c4_features":
            source = "".join(cell["source"])
            # Ensure lead_rank and trail_rank are in CONTINUOUS_FEATURES list
            if "'lead_rank'," not in source:
                source = source.replace(
                    "    'trail_avg_ft_pct',         # FT% (trailing) [NEW]\n",
                    "    'trail_avg_ft_pct',         # FT% (trailing) [NEW]\n    'lead_rank',                # Team rank (leading) [NEW]\n    'trail_rank',               # Team rank (trailing) [NEW]\n"
                )
                modified = True
            
            lines = source.split("\n")
            cell["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
            break

    if modified:
        with open(NB_PATH, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"Updated {NB_PATH}")
    else:
        print("Required features already present in list.")

if __name__ == "__main__":
    main()
