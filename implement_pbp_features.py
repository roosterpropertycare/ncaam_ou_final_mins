import json
import re

def add_pbp_features():
    path = '05_model_training.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    def get_cell_by_source_fragment(fragment):
        for i, c in enumerate(nb['cells']):
            if c['cell_type'] == 'code' and fragment in "".join(c['source']):
                return i, c
        return -1, None

    # 1. Insert new function definition cell BEFORE 'build_features'
    # Find 'def build_features'
    idx, cell = get_cell_by_source_fragment("def build_features")
    if idx != -1:
        new_source = [
            "# ── New Helper: Extract Cumulative PBP Stats ──\n",
            "def extract_derived_pbp_stats(pbp_df):\n",
            "    \"\"\"Calculate cumulative fouls and timeouts per game/half.\"\"\"\n",
            "    # Create copies to avoid SettingWithCopy warnings\n",
            "    df = pbp_df.copy()\n",
            "    \n",
            "    # ── Foul Parsing ──\n",
            "    # Identify fouls committed by a team (using 'text' or 'description')\n",
            "    # Note: 'team_id' on a 'Foul on' row is ideally the team committing the foul.\n",
            "    # We filter for only rows with 'Foul on' in text.\n",
            "    \n",
            "    text_col = 'text' if 'text' in df.columns else 'description'\n",
            "    \n",
            "    # Flag rows\n",
            "    # We want cumulative count per (game_id, half, team_id)\n",
            "    df['is_foul'] = df[text_col].str.contains('Foul on', case=False, na=False).astype(int)\n",
            "    \n",
            "    # Timeouts\n",
            "    # 'home_timeout_called' / 'away_timeout_called' are booleans in dataset\n",
            "    # Note: These columns might be per-play indicators. Let's assume they are True if timeout called.\n",
            "    # If they don't exist, check text.\n",
            "    if 'home_timeout_called' in df.columns:\n",
            "        df['home_to_taken'] = df['home_timeout_called'].fillna(False).astype(int)\n",
            "        df['away_to_taken'] = df['away_timeout_called'].fillna(False).astype(int)\n",
            "    else:\n",
            "        # Fallback to text parsing (less reliable if not explicit)\n",
            "        # 'Timeout' in text\n",
            "        df['is_timeout'] = df[text_col].str.contains('timeout', case=False, na=False).astype(int)\n",
            "        # Assign to team_id\n",
            "        df['home_to_taken'] = ((df['is_timeout'] == 1) & (df['team_id'] == df['home_team_id'])).astype(int)\n",
            "        df['away_to_taken'] = ((df['is_timeout'] == 1) & (df['team_id'] == df['away_team_id'])).astype(int)\n",
            "    \n",
            "    # ── Cumulative Counts ──\n",
            "    # We need to CumSum these logic flags grouped by Game/Half/Team\n",
            "    # For fouls, simply grouping by (game, half, team) and cumsum is tricky because \n",
            "    # we need the state at every row of the game, including non-foul rows.\n",
            "    \n",
            "    # Better approach: Calculate cumsum per game/half for the *committing* team.\n",
            "    # But 'team_id' varies. We need 'home_fouls' and 'away_fouls' columns.\n",
            "    \n",
            "    df['home_foul_commit'] = ((df['is_foul'] == 1) & (df['team_id'] == df['home_team_id'])).astype(int)\n",
            "    df['away_foul_commit'] = ((df['is_foul'] == 1) & (df['team_id'] == df['away_team_id'])).astype(int)\n",
            "    \n",
            "    # Group by Game + Half to reset foul counts at halftime\n",
            "    # We use transform(cumsum) to broadcast back to original shape\n",
            "    df['home_fouls_half'] = df.groupby(['game_id', 'half'])['home_foul_commit'].cumsum()\n",
            "    df['away_fouls_half'] = df.groupby(['game_id', 'half'])['away_foul_commit'].cumsum()\n",
            "    \n",
            "    # Timeouts (Cumulative for whole game usually, or per half? Rules vary, but let's track Total Taken)\n",
            "    # NCAA: Timeouts are game-long resources mostly.\n",
            "    df['home_tos_total'] = df.groupby('game_id')['home_to_taken'].cumsum()\n",
            "    df['away_tos_total'] = df.groupby('game_id')['away_to_taken'].cumsum()\n",
            "    \n",
            "    return df[['game_id', 'id', 'home_fouls_half', 'away_fouls_half', 'home_tos_total', 'away_tos_total']]\n"
        ]
        
        new_cell = {
            "cell_type": "code",
            "execution_count": None,
            "id": "c_feature_pbp",
            "metadata": {},
            "outputs": [],
            "source": new_source
        }
        
        nb['cells'].insert(idx, new_cell)
        print("Inserted extract_derived_pbp_stats function.")

    # 2. Update build_features to use it
    # We need to merge this info. The `get_entry_info` gets the last row.
    # We should merge the processed PBP stats to `reg_df` *before* getting the entry, OR\n",
    # just map the stats to the `entry` dataframe using the last play ID or similar.
    # Actually, `get_entry_info` groups by game_id and takes .last().
    # If we add these columns to `reg_df` (which is passed to build_features as `reg_df`), they will be picked up!
    
    # Wait, `get_entry_info` manually selects columns: 
    # return entry[['margin', 'home_team_id', ...]]
    # So we need to update `get_entry_info` AND `build_features`.
    
    # Let's update `get_entry_info` first.
    idx_ge, cell_ge = get_cell_by_source_fragment("def get_entry_info")
    if cell_ge:
        src = "".join(cell_ge['source'])
        # Add new columns to the list
        repl = "    return entry[['margin', 'home_team_id', 'away_team_id', 'home_score', 'away_score', 'home_team_spread', 'home_current_rank', 'away_current_rank', 'home_fouls_half', 'away_fouls_half', 'home_tos_total', 'away_tos_total']]"
        pattern = "    return entry[['margin', 'home_team_id', 'away_team_id', 'home_score', 'away_score', 'home_team_spread', 'home_current_rank', 'away_current_rank']]"
        if pattern in src:
            cell_ge['source'] = src.replace(pattern, repl).splitlines(keepends=True)
            print("Updated get_entry_info columns.")

    # 3. Update build_features to compute Lead/Trail stats
    idx_bf, cell_bf = get_cell_by_source_fragment("def build_features")
    if cell_bf:
        src = "".join(cell_bf['source'])
        
        # We need to map home/away fouls to lead/trail fouls
        # Insert logic after `entry['lead_is_home'] = ...`
        
        target = "entry['lead_is_home'] = (entry['leading_team_id'] == entry['home_team_id']).astype(int)"
        replacement = target + "\n    \n    # ── Foul & Timeout Mapping ──\n" + \
        "    entry['lead_fouls_half'] = np.where(entry['lead_is_home'] == 1, entry['home_fouls_half'], entry['away_fouls_half'])\n" + \
        "    entry['trail_fouls_half'] = np.where(entry['lead_is_home'] == 1, entry['away_fouls_half'], entry['home_fouls_half'])\n" + \
        "    \n" + \
        "    entry['lead_tos_taken'] = np.where(entry['lead_is_home'] == 1, entry['home_tos_total'], entry['away_tos_total'])\n" + \
        "    entry['trail_tos_taken'] = np.where(entry['lead_is_home'] == 1, entry['away_tos_total'], entry['home_tos_total'])\n" + \
        "    \n" + \
        "    # Bonus Flags (7+ = Bonus, 10+ = Double Bonus)\n" + \
        "    entry['lead_in_bonus'] = (entry['lead_fouls_half'] >= 7).astype(int)\n" + \
        "    entry['lead_in_db'] = (entry['lead_fouls_half'] >= 10).astype(int)\n" + \
        "    entry['trail_in_bonus'] = (entry['trail_fouls_half'] >= 7).astype(int)\n" + \
        "    entry['trail_in_db'] = (entry['trail_fouls_half'] >= 10).astype(int)"
        
        cell_bf['source'] = src.replace(target, replacement).splitlines(keepends=True)
        print("Updated build_features logic.")

    # 4. Integrate `extract_derived_pbp_stats` call in the main workflow
    # Look for where `filter_p6` is called or where `reg` is created.
    # "reg = pbp[(pbp['game_id'].isin(p6_game_ids)) & ..."
    
    idx_main, cell_main = get_cell_by_source_fragment("reg = pbp[(pbp['game_id'].isin")
    if cell_main:
        src = "".join(cell_main['source'])
        # We need to run extraction BEFORE filtering for regulation/snapshots? 
        # Actually, running it on the full P6 subset is fine.
        # But `reg` is filtered for regulation only. Fouls happen in OT too but we only care about pre-OT.
        # So applying to `reg` is safe IF we do it *before* filtering for `secs_remaining`.
        
        # Better place:
        # "p6_games = schedule[...]"
        # "pbp_p6 = pbp[pbp['game_id'].isin(p6_game_ids)].copy()"
        # "pbp_p6 = extract_derived_pbp_stats(pbp_p6).merge(pbp_p6, ...)" ?? No, merge is messy.
        
        # Let's just modify `reg` creation block.
        # We need to calculate stats on the *sorted* PBP.
        
        pre_code = "reg = pbp[...]" # This cell does filtering.
        
        if "reg = reg.sort_values(['game_id', 'period_number', 'clock_minutes', 'clock_seconds'], ascending=[True, True, False, False])" in src:
            # Insert calculation after sorting
            target_sort = "ascending=[True, True, False, False])"
            repl_sort = target_sort + "\n    \n    # Calculate advanced PBP stats\n    pbp_stats = extract_derived_pbp_stats(reg)\n    # Merge back (left join on id)\n    reg = reg.merge(pbp_stats[['id', 'home_fouls_half', 'away_fouls_half', 'home_tos_total', 'away_tos_total']], on='id', how='left')"
            
            cell_main['source'] = src.replace(target_sort, repl_sort).splitlines(keepends=True)
            print("Integrated PBP stats calculation into main workflow.")
        else:
             print("Could not find sort line in main block.")

    # 5. Update CONTINUOUS_FEATURES
    idx_feat, cell_feat = get_cell_by_source_fragment("CONTINUOUS_FEATURES = [")
    if cell_feat:
        src = "".join(cell_feat['source'])
        new_feats = "    'trail_rank',               # Team rank (trailing) [NEW]\n    'lead_in_bonus',\n    'lead_in_db',\n    'trail_in_bonus',\n    'trail_in_db',\n    'lead_tos_taken',\n    'trail_tos_taken',"
        src = src.replace("'trail_rank',               # Team rank (trailing) [NEW]", new_feats)
        cell_feat['source'] = src.splitlines(keepends=True)
        print("Updated CONTINUOUS_FEATURES.")

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    add_pbp_features()
