import json
from pathlib import Path

NB_PATH = Path("01_data_pull.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    # Update download cells to assign the last season's data to the expected variable for inspection
    for cell in nb["cells"]:
        if cell["id"] == "a0011": # PBP Download
            cell["source"] = [
                "for season in SEASONS:\n",
                "    url = f\"{BASE_URL}/espn_mens_college_basketball_pbp/play_by_play_{season}.parquet\"\n",
                "    pbp = download_parquet(url, f\"pbp_{season}.parquet\")  # Keeps last season for inspection\n"
            ]
        elif cell["id"] == "a0021": # Team Box Download
            cell["source"] = [
                "for season in SEASONS:\n",
                "    url = f\"{BASE_URL}/espn_mens_college_basketball_team_boxscores/team_box_{season}.parquet\"\n",
                "    team_box = download_parquet(url, f\"team_box_{season}.parquet\")\n"
            ]
        elif cell["id"] == "a0031": # Schedule Download
            cell["source"] = [
                "for season in SEASONS:\n",
                "    url = f\"{BASE_URL}/espn_mens_college_basketball_schedules/mbb_schedule_{season}.parquet\"\n",
                "    schedule = download_parquet(url, f\"schedule_{season}.parquet\")\n"
            ]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Updated {NB_PATH} variables.")

if __name__ == "__main__":
    main()
