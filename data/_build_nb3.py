"""Build 03_major_conf_analysis.ipynb programmatically."""
import json

cells = []

def md(id_, lines):
    cells.append({"cell_type":"markdown","id":id_,"metadata":{},"source":lines})

def code(id_, lines):
    cells.append({"cell_type":"code","execution_count":None,"id":id_,"metadata":{},"outputs":[],"source":lines})

# ── 0: Title ──
md("m0", [
    "# Phase 3 — Major-Conference Endgame Scoring Analysis\n",
    "\n",
    "Same snapshot-based PPM methodology as `02_analysis.ipynb`, but:\n",
    "1. **Filtered to Power 6** conference games (ACC, Big 12, Big East, Big Ten, Pac-12, SEC)\n",
    "2. **SOS-adjusted** defensive efficiency via iterative KenPom-style ratings\n",
    "\n",
    "---"
])

# ── 1: Setup ──
md("m1", ["## 0 — Setup & Load Data"])
code("c1", [
    "import pandas as pd\n",
    "import pyarrow.parquet as pq\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import os, warnings\n",
    "\n",
    "warnings.filterwarnings('ignore')\n",
    "pd.set_option('display.max_columns', 60)\n",
    "pd.set_option('display.width', 200)\n",
    "\n",
    "SEASON = 2024\n",
    "DATA_DIR = os.path.join(os.getcwd(), 'data')\n",
    "\n",
    "pbp      = pq.read_table(os.path.join(DATA_DIR, f'pbp_{SEASON}.parquet')).to_pandas()\n",
    "team_box = pq.read_table(os.path.join(DATA_DIR, f'team_box_{SEASON}.parquet')).to_pandas()\n",
    "schedule = pq.read_table(os.path.join(DATA_DIR, f'schedule_{SEASON}.parquet')).to_pandas()\n",
    "\n",
    "print(f'PBP:      {pbp.shape[0]:>10,} rows  ({pbp[\"game_id\"].nunique():,} games)')\n",
    "print(f'Team Box: {team_box.shape[0]:>10,} rows  ({team_box[\"game_id\"].nunique():,} games)')\n",
    "print(f'Schedule: {schedule.shape[0]:>10,} rows')"
])

# ── 2: Conference mapping ──
md("m2", ["---\n", "## 1 — Conference Mapping & Power 6 Filter"])
code("c2", [
    "# ── Build team -> conference mapping from schedule ──\n",
    "gmap = schedule[['groups_id', 'groups_short_name', 'groups_name']].drop_duplicates().dropna()\n",
    "gmap['groups_id'] = gmap['groups_id'].astype(int)\n",
    "conf_id_to_name = gmap.set_index('groups_id')['groups_short_name'].to_dict()\n",
    "\n",
    "home = schedule[['home_id', 'home_conference_id']].rename(\n",
    "    columns={'home_id': 'team_id', 'home_conference_id': 'conf_id'})\n",
    "away = schedule[['away_id', 'away_conference_id']].rename(\n",
    "    columns={'away_id': 'team_id', 'away_conference_id': 'conf_id'})\n",
    "all_teams = pd.concat([home, away]).dropna(subset=['conf_id'])\n",
    "all_teams['conf_id'] = all_teams['conf_id'].astype(int)\n",
    "\n",
    "team_conf = all_teams.groupby('team_id')['conf_id'].agg(\n",
    "    lambda x: x.mode().iloc[0]).reset_index()\n",
    "team_conf['conf'] = team_conf['conf_id'].map(conf_id_to_name)\n",
    "\n",
    "POWER_6 = ['ACC', 'Big 12', 'Big East', 'Big Ten', 'Pac-12', 'SEC']\n",
    "p6_teams = team_conf[team_conf['conf'].isin(POWER_6)]\n",
    "p6_ids = set(p6_teams['team_id'])\n",
    "\n",
    "print(f'Total teams mapped: {len(team_conf):,}')\n",
    "print(f'Power 6 teams: {len(p6_teams)}')\n",
    "for c in POWER_6:\n",
    "    print(f'  {c:<10} {(p6_teams[\"conf\"]==c).sum():>3} teams')"
])

code("c2b", [
    "# ── Filter PBP to P6-vs-P6 games ──\n",
    "# Identify games where both home & away are P6\n",
    "p6_games = schedule[\n",
    "    schedule['home_id'].isin(p6_ids) & schedule['away_id'].isin(p6_ids)\n",
    "]['game_id'].unique()\n",
    "\n",
    "pbp_p6 = pbp[pbp['game_id'].isin(p6_games)].copy()\n",
    "n_p6_games = pbp_p6['game_id'].nunique()\n",
    "\n",
    "print(f'P6-vs-P6 games: {n_p6_games:,} / {pbp[\"game_id\"].nunique():,} total')\n",
    "print(f'P6 PBP events:  {len(pbp_p6):,} / {len(pbp):,} total')"
])

# ── 3: Regulation prep ──
md("m3", ["---\n", "## 2 — Prepare Regulation Data"])
code("c3", [
    "# ── Filter to regulation, convert types, compute margin ──\n",
    "reg = pbp_p6[pbp_p6['period_number'].isin([1, 2])].copy()\n",
    "reg['home_score'] = pd.to_numeric(reg['home_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg['away_score'] = pd.to_numeric(reg['away_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg['score_value'] = pd.to_numeric(reg['score_value'], errors='coerce').fillna(0).astype(int)\n",
    "reg['secs_remaining'] = pd.to_numeric(reg['end_game_seconds_remaining'], errors='coerce')\n",
    "reg['margin'] = reg['home_score'] - reg['away_score']\n",
    "reg = reg.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)\n",
    "reg['scorer_is_home'] = reg['team_id'] == reg['home_team_id']\n",
    "reg['scorer_venue'] = np.where(reg['scorer_is_home'], 'Home', 'Away')\n",
    "\n",
    "n_games = reg['game_id'].nunique()\n",
    "print(f'P6 regulation events: {len(reg):,}  ({n_games:,} games)')"
])

code("c3b", [
    "# ── Margin buckets ──\n",
    "def margin_bucket(m):\n",
    "    if pd.isna(m): return None\n",
    "    m = int(m)\n",
    "    if   m > 15:          return 'Leading >15'\n",
    "    elif 10 <= m <= 15:   return 'Leading 10-15'\n",
    "    elif 5  <= m <= 9:    return 'Leading 5-9'\n",
    "    elif 1  <= m <= 4:    return 'Leading 1-4'\n",
    "    elif m == 0:          return 'Tied'\n",
    "    elif -4 <= m <= -1:   return 'Trailing 1-4'\n",
    "    elif -9 <= m <= -5:   return 'Trailing 5-9'\n",
    "    elif -15 <= m <= -10: return 'Trailing 10-15'\n",
    "    else:                 return 'Trailing >15'\n",
    "\n",
    "BUCKET_ORDER = [\n",
    "    'Leading >15', 'Leading 10-15', 'Leading 5-9', 'Leading 1-4',\n",
    "    'Tied',\n",
    "    'Trailing 1-4', 'Trailing 5-9', 'Trailing 10-15', 'Trailing >15'\n",
    "]\n",
    "print('Margin buckets ready.')"
])

# ── 4: SOS-adjusted defense ──
md("m4", [
    "---\n",
    "## 3 — SOS-Adjusted Defensive Efficiency\n",
    "\n",
    "Iterative KenPom-style adjustment using **all games** (full schedule),\n",
    "then quartile assignment on the **P6 subset** only.\n",
    "\n",
    "$$\\text{adj\\_def}_{t}^{(k+1)} = \\text{raw\\_def}_{t} \\times \\frac{\\text{league avg off}}{\\text{mean}(\\text{adj\\_off}_{\\text{opponents}}^{(k)})}$$"
])

code("c4", [
    "# ── Raw efficiency from ALL games (full schedule) ──\n",
    "tb = team_box.copy()\n",
    "for col in ['field_goals_attempted', 'offensive_rebounds', 'turnovers',\n",
    "            'free_throws_attempted', 'team_score', 'opponent_team_score']:\n",
    "    tb[col] = pd.to_numeric(tb[col], errors='coerce')\n",
    "\n",
    "tb['possessions'] = (\n",
    "    tb['field_goals_attempted'] - tb['offensive_rebounds']\n",
    "    + tb['turnovers'] + 0.475 * tb['free_throws_attempted']\n",
    ")\n",
    "tb['off_eff'] = np.where(tb['possessions'] > 0,\n",
    "                          tb['team_score'] / tb['possessions'] * 100, np.nan)\n",
    "tb['def_eff'] = np.where(tb['possessions'] > 0,\n",
    "                          tb['opponent_team_score'] / tb['possessions'] * 100, np.nan)\n",
    "\n",
    "# Season-level raw efficiency\n",
    "team_stats = tb.groupby('team_id').agg(\n",
    "    total_pts=('team_score', 'sum'),\n",
    "    total_opp_pts=('opponent_team_score', 'sum'),\n",
    "    total_poss=('possessions', 'sum'),\n",
    "    games=('game_id', 'nunique'),\n",
    "    team_name=('team_display_name', 'first'),\n",
    ").reset_index()\n",
    "\n",
    "team_stats['raw_off'] = team_stats['total_pts'] / team_stats['total_poss'] * 100\n",
    "team_stats['raw_def'] = team_stats['total_opp_pts'] / team_stats['total_poss'] * 100\n",
    "\n",
    "# Filter to teams with >= 10 games for stability\n",
    "team_stats = team_stats[team_stats['games'] >= 10].copy()\n",
    "print(f'Teams with >= 10 games: {len(team_stats)}')\n",
    "print(f'League avg off eff: {team_stats[\"raw_off\"].mean():.1f}')\n",
    "print(f'League avg def eff: {team_stats[\"raw_def\"].mean():.1f}')"
])

code("c4b", [
    "# ── Build opponent schedule for SOS adjustment ──\n",
    "# For each team-game, identify the opponent\n",
    "tb_slim = tb[['game_id', 'team_id']].copy()\n",
    "# Each game has 2 rows in team_box; merge to find opponent\n",
    "opp_map = tb_slim.merge(tb_slim, on='game_id', suffixes=('', '_opp'))\n",
    "opp_map = opp_map[opp_map['team_id'] != opp_map['team_id_opp']]\n",
    "\n",
    "# Build dict: team_id -> list of opponent team_ids\n",
    "opp_lists = opp_map.groupby('team_id')['team_id_opp'].apply(list).to_dict()\n",
    "\n",
    "print(f'Opponent schedules built for {len(opp_lists)} teams')"
])

code("c4c", [
    "# ── Iterative SOS adjustment ──\n",
    "league_avg = team_stats['raw_off'].mean()  # ~100\n",
    "\n",
    "# Initialize adjusted = raw\n",
    "team_stats['adj_off'] = team_stats['raw_off'].copy()\n",
    "team_stats['adj_def'] = team_stats['raw_def'].copy()\n",
    "\n",
    "ts = team_stats.set_index('team_id')\n",
    "\n",
    "N_ITER = 15\n",
    "for iteration in range(N_ITER):\n",
    "    new_adj_off = ts['raw_off'].copy()\n",
    "    new_adj_def = ts['raw_def'].copy()\n",
    "    \n",
    "    for tid in ts.index:\n",
    "        opps = opp_lists.get(tid, [])\n",
    "        # Filter to opponents that are in our stable set\n",
    "        valid_opps = [o for o in opps if o in ts.index]\n",
    "        if len(valid_opps) == 0:\n",
    "            continue\n",
    "        \n",
    "        # Adjust offense: scale by opponent defense strength\n",
    "        mean_opp_def = ts.loc[valid_opps, 'adj_def'].mean()\n",
    "        new_adj_off[tid] = ts.loc[tid, 'raw_off'] * (league_avg / mean_opp_def)\n",
    "        \n",
    "        # Adjust defense: scale by opponent offense strength\n",
    "        mean_opp_off = ts.loc[valid_opps, 'adj_off'].mean()\n",
    "        new_adj_def[tid] = ts.loc[tid, 'raw_def'] * (league_avg / mean_opp_off)\n",
    "    \n",
    "    delta_off = (new_adj_off - ts['adj_off']).abs().max()\n",
    "    delta_def = (new_adj_def - ts['adj_def']).abs().max()\n",
    "    \n",
    "    ts['adj_off'] = new_adj_off\n",
    "    ts['adj_def'] = new_adj_def\n",
    "    \n",
    "    if iteration < 3 or iteration == N_ITER - 1:\n",
    "        print(f'Iter {iteration+1:>2}: max delta off={delta_off:.4f}  def={delta_def:.4f}')\n",
    "\n",
    "team_stats = ts.reset_index()\n",
    "print(f'\\nConverged. Adj off range: {team_stats[\"adj_off\"].min():.1f} - {team_stats[\"adj_off\"].max():.1f}')\n",
    "print(f'Adj def range: {team_stats[\"adj_def\"].min():.1f} - {team_stats[\"adj_def\"].max():.1f}')"
])

code("c4d", [
    "# ── Assign defense quartiles from P6 subset only ──\n",
    "p6_stats = team_stats[team_stats['team_id'].isin(p6_ids)].copy()\n",
    "print(f'P6 teams with adjusted ratings: {len(p6_stats)}')\n",
    "\n",
    "p6_stats['def_quartile'] = pd.qcut(\n",
    "    p6_stats['adj_def'], q=4,\n",
    "    labels=['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']\n",
    ")\n",
    "\n",
    "print(f'\\n=== P6 Defense Quartiles (SOS-Adjusted) ===')\n",
    "print(p6_stats['def_quartile'].value_counts().sort_index().to_string())\n",
    "print(f'\\n=== Adj Def Eff by Quartile ===')\n",
    "print(p6_stats.groupby('def_quartile')['adj_def'].describe()[['mean','min','max']].round(1).to_string())\n",
    "\n",
    "print(f'\\n=== Top 10 P6 Defenses (SOS-Adjusted) ===')\n",
    "display(p6_stats.nsmallest(10, 'adj_def')[['team_name','adj_def','raw_def','games','def_quartile']])\n",
    "\n",
    "print(f'\\n=== Bottom 10 P6 Defenses ===')\n",
    "display(p6_stats.nlargest(10, 'adj_def')[['team_name','adj_def','raw_def','games','def_quartile']])"
])

# ── 5: Snapshot PPM ──
md("m5", ["---\n", "## 4 — Snapshot-Based PPM (P6 Games Only)"])
code("c5", [
    "# ── Entry margins at each window ──\n",
    "def get_entry_margins(reg_df, window_secs):\n",
    "    pre = reg_df[reg_df['secs_remaining'] >= window_secs]\n",
    "    return pre.groupby('game_id').last()['margin']\n",
    "\n",
    "entry_10 = get_entry_margins(reg, 600).apply(margin_bucket)\n",
    "entry_5  = get_entry_margins(reg, 300).apply(margin_bucket)\n",
    "entry_3  = get_entry_margins(reg, 180).apply(margin_bucket)\n",
    "\n",
    "print(f'P6 games with entry data: F10={len(entry_10)}, F5={len(entry_5)}, F3={len(entry_3)}')\n",
    "print(f'\\n=== Entry Margin Distribution at 3:00 (P6 Only) ===')\n",
    "for b in BUCKET_ORDER:\n",
    "    cnt = (entry_3 == b).sum()\n",
    "    print(f'  {b:<20} {cnt:>5} games ({100*cnt/len(entry_3):5.1f}%)')"
])

code("c5b", [
    "# ── Snapshot PPM function ──\n",
    "def compute_snapshot_ppm(reg_df, entry_buckets, window_secs, label):\n",
    "    window_mins = window_secs / 60\n",
    "    scoring = reg_df[(reg_df['scoring_play']==True) & (reg_df['secs_remaining']<=window_secs)].copy()\n",
    "    scoring['entry_bucket'] = scoring['game_id'].map(entry_buckets)\n",
    "    scoring = scoring.dropna(subset=['entry_bucket'])\n",
    "    pts_by = scoring.groupby('entry_bucket')['score_value'].sum()\n",
    "    games_by = entry_buckets.value_counts()\n",
    "    rows = []\n",
    "    for b in BUCKET_ORDER:\n",
    "        pts = pts_by.get(b, 0)\n",
    "        n_g = games_by.get(b, 0)\n",
    "        ppm = pts / (n_g * window_mins) if n_g > 0 else 0\n",
    "        rows.append({'Window': label, 'Margin Bucket': b, 'Games': n_g,\n",
    "                     'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
    "    return rows, scoring\n",
    "\n",
    "r10, s10 = compute_snapshot_ppm(reg, entry_10, 600, 'Final 10 min')\n",
    "r5,  s5  = compute_snapshot_ppm(reg, entry_5,  300, 'Final 5 min')\n",
    "r3,  s3  = compute_snapshot_ppm(reg, entry_3,  180, 'Final 3 min')\n",
    "\n",
    "scoring_all = {'Final 10 min': s10, 'Final 5 min': s5, 'Final 3 min': s3}\n",
    "entry_all = {'Final 10 min': entry_10, 'Final 5 min': entry_5, 'Final 3 min': entry_3}\n",
    "\n",
    "# Add opponent defense quartile\n",
    "def_lookup = p6_stats.set_index('team_id')['def_quartile'].to_dict()\n",
    "for key, sdf in scoring_all.items():\n",
    "    sdf['opp_team_id'] = np.where(sdf['scorer_is_home'], sdf['away_team_id'], sdf['home_team_id'])\n",
    "    sdf['opp_def_quartile'] = sdf['opp_team_id'].map(def_lookup)\n",
    "\n",
    "print('PPM computed for all windows.')"
])

# ── 6: Tables A/B/C ──
md("m6", ["---\n", "## 5 — PPM Tables (P6 Only)"])
code("c6a", [
    "# ── TABLE A: PPM by Entry Margin x Window ──\n",
    "table_a = pd.DataFrame(r10 + r5 + r3)\n",
    "print(f'=== TABLE A: PPM by Entry Margin x Window (P6 Only, {n_games} games) ===\\n')\n",
    "pivot_a = table_a.pivot_table(index='Margin Bucket', columns='Window', values='PPM', sort=False\n",
    "    ).reindex(BUCKET_ORDER)[['Final 10 min','Final 5 min','Final 3 min']]\n",
    "display(pivot_a)"
])

code("c6b", [
    "# ── TABLE A Detail ──\n",
    "display(table_a)"
])

code("c6c", [
    "# ── TABLE B: PPM by Entry Margin x Home/Away ──\n",
    "def table_b_rows(sdf, eb, ws, wl):\n",
    "    wm = ws / 60\n",
    "    gb = eb.value_counts()\n",
    "    rows = []\n",
    "    for b in BUCKET_ORDER:\n",
    "        n_g = gb.get(b, 0)\n",
    "        be = sdf[sdf['entry_bucket'] == b]\n",
    "        for v in ['Home', 'Away']:\n",
    "            pts = be[be['scorer_venue'] == v]['score_value'].sum()\n",
    "            ppm = pts / (n_g * wm) if n_g > 0 else 0\n",
    "            rows.append({'Window': wl, 'Margin Bucket': b, 'Venue': v,\n",
    "                         'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
    "    return rows\n",
    "\n",
    "tb_data = []\n",
    "for wl, ws, eb, sd in [('Final 10 min',600,entry_10,s10),\n",
    "                        ('Final 5 min',300,entry_5,s5),\n",
    "                        ('Final 3 min',180,entry_3,s3)]:\n",
    "    tb_data += table_b_rows(sd, eb, ws, wl)\n",
    "table_b = pd.DataFrame(tb_data)\n",
    "\n",
    "for wl in ['Final 10 min', 'Final 5 min', 'Final 3 min']:\n",
    "    print(f'\\n=== TABLE B: PPM by Entry Margin x Home/Away ({wl}) ===')\n",
    "    p = table_b[table_b['Window']==wl].pivot_table(index='Margin Bucket',\n",
    "        columns='Venue', values='PPM', sort=False).reindex(BUCKET_ORDER)[['Home','Away']]\n",
    "    p['Delta'] = p['Home'] - p['Away']\n",
    "    display(p)"
])

code("c6d", [
    "# ── TABLE C: PPM by Entry Margin x Opp Defense Quartile (SOS-Adjusted) ──\n",
    "def table_c_rows(sdf, eb, ws, wl):\n",
    "    wm = ws / 60\n",
    "    gb = eb.value_counts()\n",
    "    swd = sdf.dropna(subset=['opp_def_quartile'])\n",
    "    rows = []\n",
    "    for b in BUCKET_ORDER:\n",
    "        n_g = gb.get(b, 0)\n",
    "        be = swd[swd['entry_bucket'] == b]\n",
    "        for q in ['Q1 (Elite)','Q2','Q3','Q4 (Weak)']:\n",
    "            pts = be[be['opp_def_quartile']==q]['score_value'].sum()\n",
    "            ppm = pts / (n_g * wm) if n_g > 0 else 0\n",
    "            rows.append({'Window': wl, 'Margin Bucket': b, 'Opp Defense': q,\n",
    "                         'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
    "    return rows\n",
    "\n",
    "tc_data = []\n",
    "for wl, ws, eb, sd in [('Final 10 min',600,entry_10,s10),\n",
    "                        ('Final 5 min',300,entry_5,s5),\n",
    "                        ('Final 3 min',180,entry_3,s3)]:\n",
    "    tc_data += table_c_rows(sd, eb, ws, wl)\n",
    "table_c = pd.DataFrame(tc_data)\n",
    "\n",
    "for wl in ['Final 3 min', 'Final 5 min']:\n",
    "    print(f'\\n=== TABLE C: PPM x Opp SOS-Adj Defense ({wl}) ===')\n",
    "    p = table_c[table_c['Window']==wl].pivot_table(index='Margin Bucket',\n",
    "        columns='Opp Defense', values='PPM', sort=False\n",
    "    ).reindex(BUCKET_ORDER)[['Q1 (Elite)','Q2','Q3','Q4 (Weak)']]\n",
    "    display(p)"
])

# ── 7: Visualizations ──
md("m7", ["---\n", "## 6 — Visualizations"])
code("c7a", [
    "plt.rcParams.update({\n",
    "    'figure.facecolor': '#1a1a2e', 'axes.facecolor': '#16213e',\n",
    "    'axes.edgecolor': '#e0e0e0', 'axes.labelcolor': '#e0e0e0',\n",
    "    'text.color': '#e0e0e0', 'xtick.color': '#e0e0e0', 'ytick.color': '#e0e0e0',\n",
    "    'font.size': 11, 'axes.titlesize': 14, 'figure.titlesize': 16,\n",
    "})\n",
    "COLORS = {'Final 10 min':'#4cc9f0','Final 5 min':'#f72585','Final 3 min':'#7209b7'}\n",
    "print('Plot style set.')"
])

code("c7b", [
    "# ── VIZ 1: PPM by Entry Margin per Window ──\n",
    "fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharey=True)\n",
    "fig.suptitle(f'PPM by Entry Margin — Power 6 Games Only ({SEASON})',\n",
    "             fontsize=16, fontweight='bold')\n",
    "for ax, wl in zip(axes, ['Final 10 min','Final 5 min','Final 3 min']):\n",
    "    data = table_a[table_a['Window']==wl].set_index('Margin Bucket').reindex(BUCKET_ORDER)\n",
    "    ax.barh(range(len(BUCKET_ORDER)), data['PPM'].values, color=COLORS[wl],\n",
    "            alpha=0.85, edgecolor='white', linewidth=0.5)\n",
    "    ax.set_yticks(range(len(BUCKET_ORDER)))\n",
    "    ax.set_yticklabels(BUCKET_ORDER, fontsize=9)\n",
    "    ax.set_xlabel('PPM'); ax.set_title(wl, fontweight='bold'); ax.invert_yaxis()\n",
    "    for i, v in enumerate(data['PPM'].values):\n",
    "        if not np.isnan(v): ax.text(v+0.02, i, f'{v:.2f}', va='center', fontsize=8, color='white')\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_p6_table_a.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_p6_table_a.png')"
])

code("c7c", [
    "# ── VIZ 2: Home vs Away (Final 3 min) ──\n",
    "fig, ax = plt.subplots(figsize=(12, 7))\n",
    "tb_f3 = table_b[table_b['Window']=='Final 3 min']\n",
    "x = np.arange(len(BUCKET_ORDER)); w = 0.35\n",
    "hp = [tb_f3[(tb_f3['Margin Bucket']==b)&(tb_f3['Venue']=='Home')]['PPM'].values[0] for b in BUCKET_ORDER]\n",
    "ap = [tb_f3[(tb_f3['Margin Bucket']==b)&(tb_f3['Venue']=='Away')]['PPM'].values[0] for b in BUCKET_ORDER]\n",
    "ax.bar(x-w/2, hp, w, label='Home', color='#4cc9f0', alpha=0.85, edgecolor='white', linewidth=0.5)\n",
    "ax.bar(x+w/2, ap, w, label='Away', color='#f72585', alpha=0.85, edgecolor='white', linewidth=0.5)\n",
    "ax.set_xlabel('Entry Margin (Home perspective)'); ax.set_ylabel('PPM')\n",
    "ax.set_title(f'Home vs Away PPM — P6 Final 3 Min ({SEASON})', fontweight='bold')\n",
    "ax.set_xticks(x); ax.set_xticklabels(BUCKET_ORDER, rotation=45, ha='right', fontsize=9)\n",
    "ax.legend(loc='upper right'); ax.grid(axis='y', alpha=0.2)\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_p6_table_b.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_p6_table_b.png')"
])

code("c7d", [
    "# ── VIZ 3: Defense Quartile Faceted (Final 3 min) ──\n",
    "fig, axes = plt.subplots(2, 2, figsize=(16, 12), sharey=True)\n",
    "fig.suptitle(f'PPM x SOS-Adj Opp Defense — P6 Final 3 Min ({SEASON})',\n",
    "             fontsize=16, fontweight='bold')\n",
    "qc = {'Q1 (Elite)':'#06d6a0','Q2':'#4cc9f0','Q3':'#f4a261','Q4 (Weak)':'#ef476f'}\n",
    "tc_f3 = table_c[table_c['Window']=='Final 3 min']\n",
    "for ax, q in zip(axes.flat, ['Q1 (Elite)','Q2','Q3','Q4 (Weak)']):\n",
    "    qd = tc_f3[tc_f3['Opp Defense']==q].set_index('Margin Bucket').reindex(BUCKET_ORDER)\n",
    "    ax.barh(range(len(BUCKET_ORDER)), qd['PPM'].values, color=qc[q],\n",
    "            alpha=0.85, edgecolor='white', linewidth=0.5)\n",
    "    ax.set_yticks(range(len(BUCKET_ORDER))); ax.set_yticklabels(BUCKET_ORDER, fontsize=9)\n",
    "    ax.set_xlabel('PPM'); ax.set_title(f'Opp: {q}', fontweight='bold'); ax.invert_yaxis()\n",
    "    for i, v in enumerate(qd['PPM'].values):\n",
    "        if not np.isnan(v): ax.text(v+0.02, i, f'{v:.2f}', va='center', fontsize=8, color='white')\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_p6_table_c.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_p6_table_c.png')"
])

# ── 8: Comparison vs full dataset ──
md("m8", ["---\n", "## 7 — P6 vs Full Dataset Comparison"])
code("c8", [
    "# ── Load the full-dataset Table A from 02_analysis for comparison ──\n",
    "# Re-compute full-dataset PPM using same methodology\n",
    "pbp_full = pbp.copy()\n",
    "reg_full = pbp_full[pbp_full['period_number'].isin([1,2])].copy()\n",
    "reg_full['home_score'] = pd.to_numeric(reg_full['home_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg_full['away_score'] = pd.to_numeric(reg_full['away_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg_full['score_value'] = pd.to_numeric(reg_full['score_value'], errors='coerce').fillna(0).astype(int)\n",
    "reg_full['secs_remaining'] = pd.to_numeric(reg_full['end_game_seconds_remaining'], errors='coerce')\n",
    "reg_full['margin'] = reg_full['home_score'] - reg_full['away_score']\n",
    "reg_full = reg_full.sort_values(['game_id','sequence_number']).reset_index(drop=True)\n",
    "\n",
    "entry_full_3 = get_entry_margins(reg_full, 180).apply(margin_bucket)\n",
    "\n",
    "full_scoring = reg_full[(reg_full['scoring_play']==True) & (reg_full['secs_remaining']<=180)].copy()\n",
    "full_scoring['entry_bucket'] = full_scoring['game_id'].map(entry_full_3)\n",
    "full_scoring = full_scoring.dropna(subset=['entry_bucket'])\n",
    "\n",
    "full_pts = full_scoring.groupby('entry_bucket')['score_value'].sum()\n",
    "full_games = entry_full_3.value_counts()\n",
    "\n",
    "rows = []\n",
    "for b in BUCKET_ORDER:\n",
    "    p6_row = table_a[(table_a['Window']=='Final 3 min')&(table_a['Margin Bucket']==b)]\n",
    "    p6_ppm = p6_row['PPM'].values[0] if len(p6_row) > 0 else 0\n",
    "    f_pts = full_pts.get(b, 0)\n",
    "    f_ng = full_games.get(b, 0)\n",
    "    f_ppm = f_pts / (f_ng * 3) if f_ng > 0 else 0\n",
    "    rows.append({'Margin Bucket': b, 'PPM (All Games)': round(f_ppm, 3),\n",
    "                 'PPM (P6 Only)': p6_ppm, 'Delta': round(p6_ppm - f_ppm, 3)})\n",
    "\n",
    "comp = pd.DataFrame(rows)\n",
    "n_full = reg_full['game_id'].nunique()\n",
    "print(f'=== PPM Comparison: Final 3 Min ===')\n",
    "print(f'    All games: {n_full:,} | P6 only: {n_games:,}\\n')\n",
    "display(comp)"
])

# ── 9: Robustness ──
md("m9", ["---\n", "## 8 — Robustness Checks"])
code("c9a", [
    "# ── 8a: Extended conference set (P6 + AAC/MWC/A10/WCC) ──\n",
    "EXT_CONFS = POWER_6 + ['American', 'Mountain West', 'A-10', 'WCC']\n",
    "ext_teams = team_conf[team_conf['conf'].isin(EXT_CONFS)]\n",
    "ext_ids = set(ext_teams['team_id'])\n",
    "ext_games = schedule[\n",
    "    schedule['home_id'].isin(ext_ids) & schedule['away_id'].isin(ext_ids)\n",
    "]['game_id'].unique()\n",
    "\n",
    "reg_ext = pbp[pbp['game_id'].isin(ext_games) & pbp['period_number'].isin([1,2])].copy()\n",
    "reg_ext['home_score'] = pd.to_numeric(reg_ext['home_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg_ext['away_score'] = pd.to_numeric(reg_ext['away_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg_ext['score_value'] = pd.to_numeric(reg_ext['score_value'], errors='coerce').fillna(0).astype(int)\n",
    "reg_ext['secs_remaining'] = pd.to_numeric(reg_ext['end_game_seconds_remaining'], errors='coerce')\n",
    "reg_ext['margin'] = reg_ext['home_score'] - reg_ext['away_score']\n",
    "reg_ext = reg_ext.sort_values(['game_id','sequence_number']).reset_index(drop=True)\n",
    "\n",
    "ext_entry_3 = get_entry_margins(reg_ext, 180).apply(margin_bucket)\n",
    "ext_scoring = reg_ext[(reg_ext['scoring_play']==True) & (reg_ext['secs_remaining']<=180)].copy()\n",
    "ext_scoring['entry_bucket'] = ext_scoring['game_id'].map(ext_entry_3)\n",
    "ext_scoring = ext_scoring.dropna(subset=['entry_bucket'])\n",
    "\n",
    "ext_pts = ext_scoring.groupby('entry_bucket')['score_value'].sum()\n",
    "ext_gb = ext_entry_3.value_counts()\n",
    "n_ext = reg_ext['game_id'].nunique()\n",
    "\n",
    "ext_rows = []\n",
    "for b in BUCKET_ORDER:\n",
    "    p6v = table_a[(table_a['Window']=='Final 3 min')&(table_a['Margin Bucket']==b)]['PPM'].values[0]\n",
    "    ep = ext_pts.get(b, 0)\n",
    "    eg = ext_gb.get(b, 0)\n",
    "    eppm = ep / (eg * 3) if eg > 0 else 0\n",
    "    ext_rows.append({'Margin Bucket': b, 'PPM (P6)': p6v, 'PPM (Extended)': round(eppm, 3)})\n",
    "\n",
    "print(f'=== Sensitivity: P6 ({n_games} games) vs Extended ({n_ext} games), Final 3 Min ===')\n",
    "display(pd.DataFrame(ext_rows))"
])

code("c9b", [
    "# ── 8b: OT verification ──\n",
    "ot = pbp_p6[pbp_p6['period_number'] > 2]\n",
    "print(f'P6 games with OT: {ot[\"game_id\"].nunique()} / {pbp_p6[\"game_id\"].nunique()}')\n",
    "print(f'OT events excluded: {len(ot):,}')"
])

# ── 9c: Full-game PPM flow by opponent defense quartile ──
md("m9b", [
    "---\n",
    "## 8c — Full-Game PPM by Opponent Defense Quartile\n",
    "\n",
    "PPM across the full flow of the game, ignoring margin,\n",
    "sliced only by **opponent SOS-adjusted defense quartile**."
])

code("c9c", [
    "# ── Full-game PPM by time segment x opponent defense quartile ──\n",
    "# All scoring events in regulation (P6 games)\n",
    "all_scoring = reg[reg['scoring_play'] == True].copy()\n",
    "all_scoring['opp_team_id'] = np.where(\n",
    "    all_scoring['scorer_is_home'],\n",
    "    all_scoring['away_team_id'],\n",
    "    all_scoring['home_team_id']\n",
    ")\n",
    "all_scoring['opp_def_q'] = all_scoring['opp_team_id'].map(def_lookup)\n",
    "all_scoring = all_scoring.dropna(subset=['opp_def_q'])\n",
    "\n",
    "# Time segments\n",
    "TIME_SEGS = [\n",
    "    ('Full Game',  0, 2400),\n",
    "    ('1st Half', 1200, 2400),\n",
    "    ('2nd Half',   0, 1200),\n",
    "    ('Final 10',   0,  600),\n",
    "    ('Final 5',    0,  300),\n",
    "    ('Final 3',    0,  180),\n",
    "]\n",
    "\n",
    "# Count team-game observations per quartile (each game = 2 team-games)\n",
    "game_tm = reg.groupby('game_id').first()[['home_team_id', 'away_team_id']].copy()\n",
    "game_tm['home_opp_q'] = game_tm['away_team_id'].map(def_lookup)\n",
    "game_tm['away_opp_q'] = game_tm['home_team_id'].map(def_lookup)\n",
    "q_counts = pd.concat([game_tm['home_opp_q'].dropna(), game_tm['away_opp_q'].dropna()]).value_counts()\n",
    "\n",
    "rows = []\n",
    "for seg_name, lo, hi in TIME_SEGS:\n",
    "    seg_mins = (hi - lo) / 60\n",
    "    seg_events = all_scoring[\n",
    "        (all_scoring['secs_remaining'] >= lo) & (all_scoring['secs_remaining'] <= hi)\n",
    "    ]\n",
    "    pts_by_q = seg_events.groupby('opp_def_q')['score_value'].sum()\n",
    "    for q in ['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']:\n",
    "        pts = pts_by_q.get(q, 0)\n",
    "        n_tg = q_counts.get(q, 0)\n",
    "        ppm = pts / (n_tg * seg_mins) if n_tg > 0 and seg_mins > 0 else 0\n",
    "        rows.append({'Segment': seg_name, 'Opp Defense': q,\n",
    "                     'Team-Games': n_tg, 'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
    "\n",
    "full_flow = pd.DataFrame(rows)\n",
    "pivot_flow = full_flow.pivot_table(\n",
    "    index='Opp Defense', columns='Segment', values='PPM', sort=False\n",
    ")[['Full Game', '1st Half', '2nd Half', 'Final 10', 'Final 5', 'Final 3']]\n",
    "\n",
    "print(f'=== Full-Game PPM Flow by Opp Defense Quartile (P6 Only) ===')\n",
    "print(f'    No margin bucketing — pure scoring rate vs opponent strength\\n')\n",
    "display(pivot_flow)\n",
    "print(f'\\nTeam-games per quartile: {q_counts.sort_index().to_dict()}')"
])

code("c9d", [
    "# ── VIZ: Full-game flow line chart ──\n",
    "fig, ax = plt.subplots(figsize=(12, 6))\n",
    "qc = {'Q1 (Elite)': '#06d6a0', 'Q2': '#4cc9f0', 'Q3': '#f4a261', 'Q4 (Weak)': '#ef476f'}\n",
    "seg_labels = ['Full Game', '1st Half', '2nd Half', 'Final 10', 'Final 5', 'Final 3']\n",
    "\n",
    "for q in ['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']:\n",
    "    vals = [pivot_flow.loc[q, s] for s in seg_labels]\n",
    "    ax.plot(seg_labels, vals, 'o-', label=q, color=qc[q], linewidth=2.5, markersize=8)\n",
    "\n",
    "ax.set_ylabel('Points Per Minute')\n",
    "ax.set_title(f'PPM Across Game Flow by Opp Defense (SOS-Adj) — P6 {SEASON}', fontweight='bold')\n",
    "ax.legend(loc='upper left')\n",
    "ax.grid(axis='y', alpha=0.2)\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_p6_flow_by_def.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_p6_flow_by_def.png')"
])

# ── 9e: Minute-by-minute PPM for all 40 minutes ──
md("m9c", [
    "---\n",
    "## 8d — Minute-by-Minute PPM (All 40 Minutes)\n",
    "\n",
    "PPM for each individual game minute (1 through 40), by opponent defense quartile.\n",
    "Game minute 1 = start of game, minute 40 = final minute of regulation."
])

code("c9e", [
    "# ── Minute-by-minute PPM across all 40 regulation minutes ──\n",
    "# Game minute 1 = secs 2400-2340, minute 2 = 2340-2280, ... minute 40 = 60-0\n",
    "minute_rows = []\n",
    "for game_min in range(1, 41):\n",
    "    hi = 2400 - (game_min - 1) * 60  # top of this minute\n",
    "    lo = 2400 - game_min * 60         # bottom of this minute\n",
    "    seg_events = all_scoring[\n",
    "        (all_scoring['secs_remaining'] > lo) & (all_scoring['secs_remaining'] <= hi)\n",
    "    ]\n",
    "    pts_by_q = seg_events.groupby('opp_def_q')['score_value'].sum()\n",
    "    for q in ['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']:\n",
    "        pts = pts_by_q.get(q, 0)\n",
    "        n_tg = q_counts.get(q, 0)\n",
    "        ppm = pts / n_tg if n_tg > 0 else 0  # 1 minute window, so PPM = pts/games\n",
    "        minute_rows.append({'Game Minute': game_min, 'Opp Defense': q,\n",
    "                            'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
    "\n",
    "min_df = pd.DataFrame(minute_rows)\n",
    "\n",
    "# Display table for last 10 minutes\n",
    "print('=== PPM by Individual Game Minute x Opp Defense (Last 10 Minutes) ===')\n",
    "last10 = min_df[min_df['Game Minute'] >= 31].pivot_table(\n",
    "    index='Game Minute', columns='Opp Defense', values='PPM', sort=False\n",
    ")[['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']]\n",
    "display(last10)"
])

code("c9f", [
    "# ── VIZ: Minute-by-minute PPM line chart (all 40 minutes) ──\n",
    "fig, ax = plt.subplots(figsize=(16, 7))\n",
    "qc = {'Q1 (Elite)': '#06d6a0', 'Q2': '#4cc9f0', 'Q3': '#f4a261', 'Q4 (Weak)': '#ef476f'}\n",
    "\n",
    "for q in ['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']:\n",
    "    q_data = min_df[min_df['Opp Defense'] == q].sort_values('Game Minute')\n",
    "    ax.plot(q_data['Game Minute'], q_data['PPM'], '-', label=q, color=qc[q],\n",
    "            linewidth=2, alpha=0.85)\n",
    "\n",
    "# Add vertical lines for key moments\n",
    "ax.axvline(x=21, color='white', linestyle='--', alpha=0.3, label='2nd Half Start')\n",
    "ax.axvline(x=31, color='white', linestyle=':', alpha=0.3, label='Final 10 Min')\n",
    "ax.axvline(x=36, color='white', linestyle=':', alpha=0.2)\n",
    "ax.axvline(x=38, color='white', linestyle=':', alpha=0.2)\n",
    "\n",
    "ax.set_xlabel('Game Minute (1 = start, 40 = final minute)')\n",
    "ax.set_ylabel('Points Per Minute')\n",
    "ax.set_title(f'Minute-by-Minute PPM by Opp Defense (SOS-Adj) — P6 {SEASON}',\n",
    "             fontweight='bold', fontsize=14)\n",
    "ax.set_xticks(range(1, 41, 2))\n",
    "ax.legend(loc='upper left', fontsize=10)\n",
    "ax.grid(axis='both', alpha=0.15)\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_p6_minute_by_minute.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_p6_minute_by_minute.png')"
])

code("c9g", [
    "# ── VIZ: Smoothed version (3-minute rolling average) ──\n",
    "fig, ax = plt.subplots(figsize=(16, 7))\n",
    "\n",
    "for q in ['Q1 (Elite)', 'Q2', 'Q3', 'Q4 (Weak)']:\n",
    "    q_data = min_df[min_df['Opp Defense'] == q].sort_values('Game Minute').copy()\n",
    "    q_data['PPM_smooth'] = q_data['PPM'].rolling(3, center=True, min_periods=1).mean()\n",
    "    ax.plot(q_data['Game Minute'], q_data['PPM_smooth'], '-', label=q, color=qc[q],\n",
    "            linewidth=2.5, alpha=0.9)\n",
    "\n",
    "ax.axvline(x=21, color='white', linestyle='--', alpha=0.3, label='2nd Half')\n",
    "ax.axvline(x=31, color='white', linestyle=':', alpha=0.3, label='Final 10')\n",
    "ax.axvline(x=36, color='white', linestyle=':', alpha=0.2)\n",
    "ax.axvline(x=38, color='white', linestyle=':', alpha=0.2)\n",
    "\n",
    "ax.set_xlabel('Game Minute (1 = start, 40 = final minute)')\n",
    "ax.set_ylabel('PPM (3-min rolling avg)')\n",
    "ax.set_title(f'Smoothed Minute-by-Minute PPM by Opp Defense — P6 {SEASON}',\n",
    "             fontweight='bold', fontsize=14)\n",
    "ax.set_xticks(range(1, 41, 2))\n",
    "ax.legend(loc='upper left', fontsize=10)\n",
    "ax.grid(axis='both', alpha=0.15)\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_p6_minute_smoothed.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_p6_minute_smoothed.png')"
])

# ── 10: Summary ──
md("m10", ["---\n", "## 10 — Summary"])
code("c10", [
    "print('='*60)\n",
    "print(f'  P6 ENDGAME ANALYSIS — {SEASON} Season')\n",
    "print('='*60)\n",
    "print(f'\\n  P6 games analyzed:       {n_games:,}')\n",
    "print(f'  P6 teams:                {len(p6_stats)}')\n",
    "print(f'  SOS iterations:          {N_ITER}')\n",
    "print(f'  Def quartiles:           P6 subset of SOS-adjusted ratings')\n",
    "print(f'\\n  Methodology: snapshot entry margin, same as 02_analysis')\n",
    "print(f'  Outputs: Tables A/B/C, 3 visualizations, P6 vs Full comparison')"
])

# ── Assemble notebook ──
nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "cfbtm_env", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.14"}
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open("03_major_conf_analysis.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Created 03_major_conf_analysis.ipynb successfully!")
print(f"Total cells: {len(cells)}")
