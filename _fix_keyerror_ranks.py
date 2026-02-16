import json
from pathlib import Path

NB_PATH = Path("05_model_training.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    modified = False
    
    # Update Cell c2b (ID: c2b) - Merge rankings into reg
    for cell in nb["cells"]:
        if cell["id"] == "c2b":
            source = "".join(cell["source"])
            if "reg.merge(schedule[['game_id', 'home_current_rank', 'away_current_rank']]" not in source:
                # Insert merge logic after reg is created
                find_str = "reg = pbp_p6[pbp_p6['period_number'].isin([1, 2])].copy()"
                replace_str = find_str + "\n\n# Merge rankings from schedule\nreg = reg.merge(\n    schedule[['game_id', 'home_current_rank', 'away_current_rank']], \n    on='game_id', how='left'\n)"
                source = source.replace(find_str, replace_str)
                
                # Split back into lines
                lines = source.split("\n")
                cell["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
                modified = True
                print("Merged ranking columns into reg in Cell c2b.")
            break

    if modified:
        with open(NB_PATH, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"Updated {NB_PATH} to fix KeyError.")
    else:
        print("Rankings already merged or cell not found.")

if __name__ == "__main__":
    main()
