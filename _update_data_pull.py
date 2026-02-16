import json
from pathlib import Path

NB_PATH = Path("01_data_pull.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    modified = False
    
    # Update Cell 2 (a0003) - Change SEASON to SEASONS list
    for cell in nb["cells"]:
        if cell["id"] == "a0003":
            source = cell["source"]
            new_source = []
            for line in source:
                if line.strip() == "SEASON = 2024":
                    new_source.append("SEASONS = [2021, 2022, 2023, 2024]\n")
                elif "PBP_URL" in line or "TEAM_BOX_URL" in line or "SCHEDULE_URL" in line:
                    continue # We will handle these in a loop
                elif "print(f\"Season: {SEASON}\")" in line:
                    new_source.append("print(f\"Seasons: {SEASONS}\")\n")
                else:
                    new_source.append(line)
            cell["source"] = new_source
            modified = True
            print("Modified Cell a0003 (Seasons config)")

    # Replace download cells with a loop-based approach or add new cells
    # Instead of surgical edits to a0011, a0021, etc., let's construct a new execution cell
    
    # Find execution cells and update them to loop through seasons
    for cell in nb["cells"]:
        if cell["id"] == "a0011": # PBP Download
            cell["source"] = [
                "for season in SEASONS:\n",
                "    url = f\"{BASE_URL}/espn_mens_college_basketball_pbp/play_by_play_{season}.parquet\"\n",
                "    download_parquet(url, f\"pbp_{season}.parquet\")\n"
            ]
        elif cell["id"] == "a0021": # Team Box Download
            cell["source"] = [
                "for season in SEASONS:\n",
                "    url = f\"{BASE_URL}/espn_mens_college_basketball_team_boxscores/team_box_{season}.parquet\"\n",
                "    download_parquet(url, f\"team_box_{season}.parquet\")\n"
            ]
        elif cell["id"] == "a0031": # Schedule Download
            cell["source"] = [
                "for season in SEASONS:\n",
                "    url = f\"{BASE_URL}/espn_mens_college_basketball_schedules/mbb_schedule_{season}.parquet\"\n",
                "    download_parquet(url, f\"schedule_{season}.parquet\")\n"
            ]

    if modified:
        with open(NB_PATH, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"Updated {NB_PATH}")
    else:
        print("Could not find relevant cells in notebook.")

if __name__ == "__main__":
    main()
