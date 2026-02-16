import json

def fix_pbp_impl():
    path = '05_model_training.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Helper to find cell index
    def find_cell_index(fragment):
        for i, c in enumerate(nb['cells']):
            if c['cell_type'] == 'code' and fragment in "".join(c['source']):
                return i
        return -1

    # 1. Remove the incorrectly placed 'extract_derived_pbp_stats' cell (if exists)
    # It was inserted before 'def build_features'
    idx_old_def = find_cell_index("def extract_derived_pbp_stats")
    if idx_old_def != -1:
        # Check if it's the one we added
        print(f"Removing old definition at index {idx_old_def}")
        nb['cells'].pop(idx_old_def)
    
    # 2. Insert 'extract_derived_pbp_stats' BEFORE 'reg = pbp_p6...' (Cell 35ish)
    # Anchor: "reg = pbp_p6[pbp_p6['period_number'].isin([1, 2])]"
    idx_reg = find_cell_index("reg = pbp_p6[pbp_p6['period_number'].isin([1, 2])]")
    if idx_reg == -1:
        print("Could not find 'reg' creation cell.")
        return

    new_source = [
        "# ── Helper: Extract Cumulative PBP Stats ──\n",
        "def extract_derived_pbp_stats(pbp_df):\n",
        "    \"\"\"Calculate cumulative fouls and timeouts per game/half.\"\"\"\n",
        "    df = pbp_df.copy()\n",
        "    \n",
        "    # 1. Fouls (Text contains 'Foul on')\n",
        "    # We assume 'team_id' is the committing team for these rows.\n",
        "    text_col = 'text' if 'text' in df.columns else 'description'\n",
        "    df['is_foul'] = df[text_col].str.contains('Foul on', case=False, na=False).astype(int)\n",
        "    \n",
        "    # 2. Timeouts\n",
        "    if 'home_timeout_called' in df.columns:\n",
        "        df['home_to_taken'] = df['home_timeout_called'].fillna(False).astype(int)\n",
        "        df['away_to_taken'] = df['away_timeout_called'].fillna(False).astype(int)\n",
        "    else:\n",
        "        # Validation fallback\n",
        "        df['home_to_taken'] = 0\n",
        "        df['away_to_taken'] = 0\n",
        "    \n",
        "    # 3. Cumulative Counts (Team-specific)\n",
        "    # Filter to foul rows to assign to correct team column\n",
        "    df['home_foul_commit'] = ((df['is_foul'] == 1) & (df['team_id'] == df['home_team_id'])).astype(int)\n",
        "    df['away_foul_commit'] = ((df['is_foul'] == 1) & (df['team_id'] == df['away_team_id'])).astype(int)\n",
        "    \n",
        "    # Group by Game, Half\n",
        "    df['home_fouls_half'] = df.groupby(['game_id', 'half'])['home_foul_commit'].cumsum()\n",
        "    df['away_fouls_half'] = df.groupby(['game_id', 'half'])['away_foul_commit'].cumsum()\n",
        "    \n",
        "    # Timeouts (Game total)\n",
        "    df['home_tos_total'] = df.groupby('game_id')['home_to_taken'].cumsum()\n",
        "    df['away_tos_total'] = df.groupby('game_id')['away_to_taken'].cumsum()\n",
        "    \n",
        "    return df[['id', 'home_fouls_half', 'away_fouls_half', 'home_tos_total', 'away_tos_total']]\n"
    ]
    
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "id": "c_feature_pbp_fixed",
        "metadata": {},
        "outputs": [],
        "source": new_source
    }
    
    # Insert BEFORE reg creation so it's defined when we call it
    nb['cells'].insert(idx_reg, new_cell)
    print(f"Inserted extract_derived_pbp_stats at index {idx_reg}")
    
    # Re-find idx_reg because we inserted a cell before it
    idx_reg += 1
    cell_reg = nb['cells'][idx_reg]
    src_reg = "".join(cell_reg['source'])
    
    # 3. Apply the MERGE logic in the 'reg' cell
    # Anchor: "reg = reg.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)"
    anchor = "reg = reg.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)"
    
    if anchor in src_reg:
        # Check if we already added it (to avoid double add if ran multiple times)
        if "extract_derived_pbp_stats(reg)" not in src_reg:
            print("Injecting PBP stats merge logic...")
            replacement = anchor + "\n    \n    # ── Advanced PBP Features ──\n" + \
                          "    pbp_stats = extract_derived_pbp_stats(reg)\n" + \
                          "    reg = reg.merge(pbp_stats, on='id', how='left').fillna(0)\n"
            
            cell_reg['source'] = src_reg.replace(anchor, replacement).splitlines(keepends=True)
        else:
            print("PBP stats merge logic already present.")
    else:
        print(f"Could not find anchor in reg cell: {anchor}")

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    fix_pbp_impl()
