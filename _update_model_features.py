import json
from pathlib import Path

NB_PATH = Path("05_model_training.ipynb")

def main():
    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    # 1. Update Cell 1 (c1) - Load multiple seasons
    for cell in nb["cells"]:
        if cell["id"] == "c1":
            source = cell["source"]
            new_source = []
            for line in source:
                if line.strip() == "SEASON = 2024":
                    new_source.append("SEASONS = [2021, 2022, 2023, 2024]\n")
                elif line.strip() == "pbp      = pq.read_table(os.path.join(DATA_DIR, f'pbp_{SEASON}.parquet')).to_pandas()":
                    new_source.append("pbp = pd.concat([pq.read_table(os.path.join(DATA_DIR, f'pbp_{s}.parquet')).to_pandas() for s in SEASONS])\n")
                elif line.strip() == "team_box = pq.read_table(os.path.join(DATA_DIR, f'team_box_{SEASON}.parquet')).to_pandas()":
                    new_source.append("team_box = pd.concat([pq.read_table(os.path.join(DATA_DIR, f'team_box_{s}.parquet')).to_pandas() for s in SEASONS])\n")
                elif line.strip() == "schedule = pq.read_table(os.path.join(DATA_DIR, f'schedule_{SEASON}.parquet')).to_pandas()":
                    new_source.append("schedule = pd.concat([pq.read_table(os.path.join(DATA_DIR, f'schedule_{s}.parquet')).to_pandas() for s in SEASONS])\n")
                else:
                    new_source.append(line)
            cell["source"] = new_source
            print("Updated Cell c1 (Multi-season loading)")
            break

    # 2. Update Cell 5 (c4_snapshot) - Build features with ranking
    for cell in nb["cells"]:
        if cell["id"] == "c4_snapshot":
            source = "".join(cell["source"])
            # Update return statement of get_entry_info to include ranks
            source = source.replace(
                "return entry[['margin', 'home_team_id', 'away_team_id', 'home_score', 'away_score', 'home_team_spread']]",
                "return entry[['margin', 'home_team_id', 'away_team_id', 'home_score', 'away_score', 'home_team_spread', 'home_current_rank', 'away_current_rank']]"
            )
            # Update build_features to map leading/trailing ranks
            find_str = "    # ── Leading / Trailing team IDs ──"
            insert_str = """
    # ── Leading / Trailing Ranks ──
    # Unranked team rank (99.0) is kept as is
    entry['lead_rank'] = np.where(entry['margin'] > 0, entry['home_current_rank'], entry['away_current_rank'])
    entry['trail_rank'] = np.where(entry['margin'] > 0, entry['away_current_rank'], entry['home_current_rank'])
    
"""
            source = source.replace(find_str, insert_str + find_str)
            
            # Add trail_rank to feature_cols list (it will be added to the matrix)
            source = source.replace(
                "feature_cols += ['abs_margin', 'lead_is_home', 'snapshot_total', 'lead_spread']",
                "feature_cols += ['abs_margin', 'lead_is_home', 'snapshot_total', 'lead_spread', 'lead_rank', 'trail_rank']"
            )
            
            # Split back into lines
            lines = source.split("\n")
            cell["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
            print("Updated Cell c4_snapshot (Ranking feature integration)")
            break

    # 3. Update Cell 6 (c4_features) - Add new continuous features
    for cell in nb["cells"]:
        if cell["id"] == "c4_features":
            source = "".join(cell["source"])
            source = source.replace(
                "    'trail_avg_ft_pct',          # FT% (trailing) [NEW]\n",
                "    'trail_avg_ft_pct',          # FT% (trailing) [NEW]\n    'lead_rank',                 # Team rank (leading) [NEW]\n    'trail_rank',                # Team rank (trailing) [NEW]\n"
            )
            lines = source.split("\n")
            cell["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
            print("Updated Cell c4_features (Ranking feature inclusion)")
            break

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Updated {NB_PATH}")

if __name__ == "__main__":
    main()
