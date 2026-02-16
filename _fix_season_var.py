import json
from pathlib import Path

NB_PATH = Path("01_data_pull.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    modified = False
    
    # 1. Update Cell 2 (a0003) - Restore SEASON alongside SEASONS
    for cell in nb["cells"]:
        if cell["id"] == "a0003":
            source = cell["source"]
            new_source = []
            has_season = any("SEASON =" in line for line in source)
            if not has_season:
                for line in source:
                    if "SEASONS =" in line:
                        new_source.append(line)
                        new_source.append("SEASON = SEASONS[-1]  # Legacy for check cells\n")
                    else:
                        new_source.append(line)
                cell["source"] = new_source
                modified = True
                print("Restored SEASON in a0003")

    # 2. Update Cell IDs a0011, a0021, a0031 to assign pbp, team_box, schedule the LAST season in the loop
    # (Checking if they already do this from previous fix)
    # The previous fix assigned them INSIDE the loop: pbp = download_parquet(...)
    # This is correct as it leaves the last season's DF in the variable.

    if modified:
        with open(NB_PATH, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"Updated {NB_PATH} to include SEASON.")
    else:
        print("SEASON already exists or cell not found.")

if __name__ == "__main__":
    main()
