"""Build 04_driver_analysis.ipynb programmatically."""
import json

cells = []

def md(id_, lines):
    cells.append({"cell_type":"markdown","id":id_,"metadata":{},"source":lines})

def code(id_, lines):
    cells.append({"cell_type":"code","execution_count":None,"id":id_,"metadata":{},"outputs":[],"source":lines})

# ── Title ──
md("m0", [
    "# Phase 4 — Driver Analysis: What Affects Final 3-Minute Scoring?\n",
    "\n",
    "Building on P6 snapshot PPM from notebook 03, this notebook analyzes how\n",
    "specific team characteristics of the **leading** and **trailing** teams\n",
    "affect endgame scoring rates.\n",
    "\n",
    "### Drivers\n",
    "1. **Leading team OREB** — more offensive rebounds = more second-chance possessions\n",
    "2. **Trailing team 3PT volume** — trailing teams may increase 3PA to close the gap\n",
    "3. **Trailing team 3PT efficiency** — better shooters make up ground faster\n",
    "4. **Leading team pace** (sec/poss) — slower teams burn more clock\n",
    "5. **Trailing team pace** — faster trailing teams create more scoring opportunities\n",
    "\n",
    "---"
])

# ── Setup ──
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
    "print(f'PBP: {pbp.shape[0]:,} rows ({pbp[\"game_id\"].nunique():,} games)')\n",
    "print(f'Team Box: {team_box.shape[0]:,} rows')\n",
    "print(f'Schedule: {schedule.shape[0]:,} rows')"
])

# ── P6 Filter ──
md("m2", ["---\n", "## 1 — Power 6 Filter"])
code("c2", [
    "# ── Conference mapping (reuse from NB03) ──\n",
    "gmap = schedule[['groups_id', 'groups_short_name']].drop_duplicates().dropna()\n",
    "gmap['groups_id'] = gmap['groups_id'].astype(int)\n",
    "conf_id_to_name = gmap.set_index('groups_id')['groups_short_name'].to_dict()\n",
    "\n",
    "home = schedule[['home_id','home_conference_id']].rename(columns={'home_id':'team_id','home_conference_id':'conf_id'})\n",
    "away = schedule[['away_id','away_conference_id']].rename(columns={'away_id':'team_id','away_conference_id':'conf_id'})\n",
    "all_teams = pd.concat([home, away]).dropna(subset=['conf_id'])\n",
    "all_teams['conf_id'] = all_teams['conf_id'].astype(int)\n",
    "team_conf = all_teams.groupby('team_id')['conf_id'].agg(lambda x: x.mode().iloc[0]).reset_index()\n",
    "team_conf['conf'] = team_conf['conf_id'].map(conf_id_to_name)\n",
    "\n",
    "POWER_6 = ['ACC', 'Big 12', 'Big East', 'Big Ten', 'Pac-12', 'SEC']\n",
    "p6_ids = set(team_conf[team_conf['conf'].isin(POWER_6)]['team_id'])\n",
    "\n",
    "p6_games = schedule[\n",
    "    schedule['home_id'].isin(p6_ids) & schedule['away_id'].isin(p6_ids)\n",
    "]['game_id'].unique()\n",
    "\n",
    "pbp_p6 = pbp[pbp['game_id'].isin(p6_games)].copy()\n",
    "print(f'P6 teams: {len(p6_ids)} | P6-vs-P6 games: {len(p6_games):,}')"
])

# ── Regulation prep ──
code("c2b", [
    "# ── Regulation data ──\n",
    "reg = pbp_p6[pbp_p6['period_number'].isin([1, 2])].copy()\n",
    "reg['home_score'] = pd.to_numeric(reg['home_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg['away_score'] = pd.to_numeric(reg['away_score'], errors='coerce').fillna(0).astype(int)\n",
    "reg['score_value'] = pd.to_numeric(reg['score_value'], errors='coerce').fillna(0).astype(int)\n",
    "reg['secs_remaining'] = pd.to_numeric(reg['end_game_seconds_remaining'], errors='coerce')\n",
    "reg['margin'] = reg['home_score'] - reg['away_score']\n",
    "reg = reg.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)\n",
    "\n",
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
    "\n",
    "n_games = reg['game_id'].nunique()\n",
    "print(f'Regulation: {len(reg):,} events, {n_games:,} games')"
])

# ── Team Season Stats ──
md("m3", [
    "---\n",
    "## 2 — Team Season Stats & Driver Quartiles\n",
    "\n",
    "Compute season-level averages from **all games** (full schedule),\n",
    "then bucket into quartiles."
])

code("c3", [
    "# ── Compute per-game stats from team_box ──\n",
    "tb = team_box.copy()\n",
    "for col in ['offensive_rebounds', 'defensive_rebounds',\n",
    "            'three_point_field_goals_made', 'three_point_field_goals_attempted',\n",
    "            'field_goals_attempted', 'turnovers', 'free_throws_attempted',\n",
    "            'team_score', 'opponent_team_score']:\n",
    "    tb[col] = pd.to_numeric(tb[col], errors='coerce')\n",
    "\n",
    "tb['three_pt_pct'] = pd.to_numeric(tb['three_point_field_goal_pct'], errors='coerce')\n",
    "tb['possessions'] = (tb['field_goals_attempted'] - tb['offensive_rebounds']\n",
    "                     + tb['turnovers'] + 0.475 * tb['free_throws_attempted'])\n",
    "tb['sec_per_poss'] = 40 * 60 / tb['possessions']\n",
    "\n",
    "# Season-level averages per team\n",
    "team_stats = tb.groupby('team_id').agg(\n",
    "    avg_oreb=('offensive_rebounds', 'mean'),\n",
    "    avg_3pa=('three_point_field_goals_attempted', 'mean'),\n",
    "    avg_3pt_pct=('three_pt_pct', 'mean'),\n",
    "    avg_sec_per_poss=('sec_per_poss', 'mean'),\n",
    "    avg_poss=('possessions', 'mean'),\n",
    "    games=('game_id', 'nunique'),\n",
    "    team_name=('team_display_name', 'first'),\n",
    ").reset_index()\n",
    "\n",
    "# Filter to stable teams\n",
    "team_stats = team_stats[team_stats['games'] >= 10].copy()\n",
    "\n",
    "# Assign quartiles for each driver\n",
    "DRIVERS = {\n",
    "    'avg_oreb':         ('OREB Q', True),    # higher = more boards = Q1\n",
    "    'avg_3pa':          ('3PA Q',  True),     # higher volume = Q1\n",
    "    'avg_3pt_pct':      ('3P% Q',  True),     # higher pct = Q1\n",
    "    'avg_sec_per_poss': ('Pace Q', False),    # LOWER sec/poss = faster = Q1\n",
    "}\n",
    "\n",
    "for col, (q_name, ascending_is_q1) in DRIVERS.items():\n",
    "    if ascending_is_q1:\n",
    "        # Higher value = Q1 (best), so we reverse the labels\n",
    "        team_stats[q_name] = pd.qcut(\n",
    "            team_stats[col], q=4,\n",
    "            labels=['Q4 (Low)', 'Q3', 'Q2', 'Q1 (High)']\n",
    "        )\n",
    "    else:\n",
    "        # Lower value = Q1 (fastest)\n",
    "        team_stats[q_name] = pd.qcut(\n",
    "            team_stats[col], q=4,\n",
    "            labels=['Q1 (Fast)', 'Q2', 'Q3', 'Q4 (Slow)']\n",
    "        )\n",
    "\n",
    "print(f'Teams with season stats: {len(team_stats)}')\n",
    "print(f'\\n=== Driver Distributions ===')\n",
    "for col, (q_name, _) in DRIVERS.items():\n",
    "    print(f'\\n{q_name} ({col}):')\n",
    "    desc = team_stats.groupby(q_name)[col].agg(['count', 'mean', 'min', 'max']).round(2)\n",
    "    print(desc.to_string())"
])

code("c3b", [
    "# ── Show P6 teams' driver stats ──\n",
    "p6_stats = team_stats[team_stats['team_id'].isin(p6_ids)].copy()\n",
    "print(f'P6 teams with stats: {len(p6_stats)}')\n",
    "\n",
    "print(f'\\n=== P6 Team Driver Averages ===')\n",
    "for col in ['avg_oreb', 'avg_3pa', 'avg_3pt_pct', 'avg_sec_per_poss']:\n",
    "    print(f'  {col:<20} mean={p6_stats[col].mean():.2f}  min={p6_stats[col].min():.2f}  max={p6_stats[col].max():.2f}')"
])

# ── Identify leading/trailing at 3:00 ──
md("m4", [
    "---\n",
    "## 3 — Identify Leading & Trailing Teams at 3:00 Mark"
])

code("c4", [
    "# ── Snapshot margin at 180s and assign leading/trailing team IDs ──\n",
    "def get_entry_info(reg_df, window_secs):\n",
    "    pre = reg_df[reg_df['secs_remaining'] >= window_secs]\n",
    "    entry = pre.groupby('game_id').last()\n",
    "    return entry[['margin', 'home_team_id', 'away_team_id', 'home_score', 'away_score']]\n",
    "\n",
    "entry_3 = get_entry_info(reg, 180)\n",
    "entry_3['margin_bucket'] = entry_3['margin'].apply(margin_bucket)\n",
    "\n",
    "# Leading = home if margin > 0, away if margin < 0\n",
    "entry_3['leading_team_id'] = np.where(\n",
    "    entry_3['margin'] > 0, entry_3['home_team_id'],\n",
    "    np.where(entry_3['margin'] < 0, entry_3['away_team_id'], np.nan)\n",
    ")\n",
    "entry_3['trailing_team_id'] = np.where(\n",
    "    entry_3['margin'] > 0, entry_3['away_team_id'],\n",
    "    np.where(entry_3['margin'] < 0, entry_3['home_team_id'], np.nan)\n",
    ")\n",
    "\n",
    "# Drop ties (no leading/trailing in ties)\n",
    "entry_3_lt = entry_3[entry_3['margin'] != 0].copy()\n",
    "entry_3_lt['abs_margin'] = entry_3_lt['margin'].abs()\n",
    "\n",
    "print(f'Total games at 3:00 mark: {len(entry_3):,}')\n",
    "print(f'  With leader/trailer:    {len(entry_3_lt):,}')\n",
    "print(f'  Tied (excluded):        {(entry_3[\"margin\"]==0).sum():,}')\n",
    "print(f'\\n=== Margin Bucket Distribution ===')\n",
    "for b in BUCKET_ORDER:\n",
    "    cnt = (entry_3['margin_bucket'] == b).sum()\n",
    "    print(f'  {b:<20} {cnt:>5}')"
])

# ── Merge driver quartiles into game-level data ──
md("m5", [
    "---\n",
    "## 4 — Merge Driver Quartiles into Game Data"
])

code("c5", [
    "# ── Build lookup dicts for each driver quartile ──\n",
    "driver_lookups = {}\n",
    "for col, (q_name, _) in DRIVERS.items():\n",
    "    driver_lookups[q_name] = team_stats.set_index('team_id')[q_name].to_dict()\n",
    "\n",
    "# ── Map driver quartiles for leading and trailing teams ──\n",
    "for q_name, lookup in driver_lookups.items():\n",
    "    entry_3_lt[f'lead_{q_name}'] = entry_3_lt['leading_team_id'].map(lookup)\n",
    "    entry_3_lt[f'trail_{q_name}'] = entry_3_lt['trailing_team_id'].map(lookup)\n",
    "\n",
    "# Show coverage\n",
    "for q_name in driver_lookups:\n",
    "    lead_cov = entry_3_lt[f'lead_{q_name}'].notna().mean()\n",
    "    trail_cov = entry_3_lt[f'trail_{q_name}'].notna().mean()\n",
    "    print(f'{q_name}: lead coverage={lead_cov:.1%}, trail coverage={trail_cov:.1%}')"
])

# ── PPM by driver quartile ──
md("m6", [
    "---\n",
    "## 5 — PPM by Driver Quartile (Final 3 Minutes)\n",
    "\n",
    "For each driver, compute total PPM in the final 3 minutes,\n",
    "bucketed by the leading or trailing team's quartile for that stat."
])

code("c6", [
    "# ── Get all F3 scoring events ──\n",
    "scoring_3 = reg[(reg['scoring_play'] == True) & (reg['secs_remaining'] <= 180)].copy()\n",
    "scoring_3['entry_bucket'] = scoring_3['game_id'].map(entry_3['margin_bucket'])\n",
    "scoring_3 = scoring_3.dropna(subset=['entry_bucket'])\n",
    "\n",
    "# Only non-tied games\n",
    "scoring_3_lt = scoring_3[scoring_3['game_id'].isin(entry_3_lt.index)].copy()\n",
    "\n",
    "# Merge driver quartiles into scoring events\n",
    "for q_name in driver_lookups:\n",
    "    scoring_3_lt[f'lead_{q_name}'] = scoring_3_lt['game_id'].map(\n",
    "        entry_3_lt[f'lead_{q_name}'])\n",
    "    scoring_3_lt[f'trail_{q_name}'] = scoring_3_lt['game_id'].map(\n",
    "        entry_3_lt[f'trail_{q_name}'])\n",
    "\n",
    "print(f'F3 scoring events (non-tied): {len(scoring_3_lt):,}')\n",
    "print(f'Games: {scoring_3_lt[\"game_id\"].nunique():,}')"
])

code("c6b", [
    "# ── PPM computation by driver quartile ──\n",
    "plt.rcParams.update({\n",
    "    'figure.facecolor': '#1a1a2e', 'axes.facecolor': '#16213e',\n",
    "    'axes.edgecolor': '#e0e0e0', 'axes.labelcolor': '#e0e0e0',\n",
    "    'text.color': '#e0e0e0', 'xtick.color': '#e0e0e0', 'ytick.color': '#e0e0e0',\n",
    "    'font.size': 11, 'axes.titlesize': 14, 'figure.titlesize': 16,\n",
    "})\n",
    "\n",
    "DRIVER_CONFIGS = [\n",
    "    ('lead_OREB Q',  'Leading Team OREB',  ['Q1 (High)','Q2','Q3','Q4 (Low)']),\n",
    "    ('trail_3PA Q',  'Trailing Team 3PA Volume', ['Q1 (High)','Q2','Q3','Q4 (Low)']),\n",
    "    ('trail_3P% Q',  'Trailing Team 3P%',  ['Q1 (High)','Q2','Q3','Q4 (Low)']),\n",
    "    ('lead_Pace Q',  'Leading Team Pace',  ['Q1 (Fast)','Q2','Q3','Q4 (Slow)']),\n",
    "    ('trail_Pace Q', 'Trailing Team Pace', ['Q1 (Fast)','Q2','Q3','Q4 (Slow)']),\n",
    "]\n",
    "\n",
    "all_driver_results = []\n",
    "\n",
    "for driver_col, driver_label, q_labels in DRIVER_CONFIGS:\n",
    "    s_valid = scoring_3_lt.dropna(subset=[driver_col])\n",
    "    games_valid = entry_3_lt.dropna(subset=[driver_col])\n",
    "    \n",
    "    pts_by_q = s_valid.groupby(driver_col)['score_value'].sum()\n",
    "    games_by_q = games_valid[driver_col].value_counts()\n",
    "    \n",
    "    rows = []\n",
    "    for q in q_labels:\n",
    "        pts = pts_by_q.get(q, 0)\n",
    "        n_g = games_by_q.get(q, 0)\n",
    "        ppm = pts / (n_g * 3) if n_g > 0 else 0\n",
    "        rows.append({'Driver': driver_label, 'Quartile': q, 'Games': n_g,\n",
    "                     'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
    "    all_driver_results.extend(rows)\n",
    "\n",
    "driver_df = pd.DataFrame(all_driver_results)\n",
    "\n",
    "print('=== PPM by Driver Quartile — Final 3 Minutes (P6, non-tied) ===')\n",
    "for driver_label in driver_df['Driver'].unique():\n",
    "    print(f'\\n--- {driver_label} ---')\n",
    "    sub = driver_df[driver_df['Driver'] == driver_label][['Quartile','Games','Total Pts','PPM']]\n",
    "    display(sub.reset_index(drop=True))"
])

# ── Visualization: Driver PPM bars ──
md("m7", [
    "---\n",
    "## 6 — Visualizations"
])

code("c7", [
    "# ── VIZ 1: PPM by each driver (grouped bar) ──\n",
    "fig, axes = plt.subplots(2, 3, figsize=(20, 12))\n",
    "fig.suptitle(f'Impact of Team Drivers on Final 3-Min PPM — P6 {SEASON}',\n",
    "             fontsize=16, fontweight='bold')\n",
    "\n",
    "driver_colors = ['#06d6a0', '#4cc9f0', '#f4a261', '#ef476f']\n",
    "\n",
    "for idx, (driver_col, driver_label, q_labels) in enumerate(DRIVER_CONFIGS):\n",
    "    ax = axes.flat[idx]\n",
    "    sub = driver_df[driver_df['Driver'] == driver_label]\n",
    "    ppms = [sub[sub['Quartile'] == q]['PPM'].values[0] for q in q_labels]\n",
    "    \n",
    "    bars = ax.bar(range(len(q_labels)), ppms, color=driver_colors, alpha=0.85,\n",
    "                  edgecolor='white', linewidth=0.5)\n",
    "    ax.set_xticks(range(len(q_labels)))\n",
    "    ax.set_xticklabels(q_labels, fontsize=9, rotation=15)\n",
    "    ax.set_ylabel('PPM')\n",
    "    ax.set_title(driver_label, fontweight='bold')\n",
    "    ax.grid(axis='y', alpha=0.2)\n",
    "    \n",
    "    for i, v in enumerate(ppms):\n",
    "        ax.text(i, v + 0.03, f'{v:.2f}', ha='center', fontsize=9, color='white')\n",
    "\n",
    "# Hide unused subplot\n",
    "axes.flat[-1].set_visible(False)\n",
    "\n",
    "plt.tight_layout()\n",
    "plt.savefig(os.path.join(DATA_DIR, 'viz_driver_ppm.png'), dpi=150, bbox_inches='tight')\n",
    "plt.show()\n",
    "print('Saved: viz_driver_ppm.png')"
])

# ── Driver x Margin Bucket interaction (ALL drivers, ALL buckets) ──
md("m8", [
    "---\n",
    "## 7 — Driver × Margin Bucket Profiles\n",
    "\n",
    "Each of the 5 drivers **individually paired** with **all** point differential buckets.\n",
    "PPM = total_pts / (games_in_cell × 3 minutes)."
])

code("c8", [
    "# ── PPM by driver quartile x ALL margin buckets for ALL 5 drivers ──\n",
    "interaction_results = []\n",
    "\n",
    "for driver_col, driver_label, q_labels in DRIVER_CONFIGS:\n",
    "    s_valid = scoring_3_lt.dropna(subset=[driver_col])\n",
    "    games_valid = entry_3_lt.dropna(subset=[driver_col])\n",
    "    \n",
    "    for b in BUCKET_ORDER:\n",
    "        s_bucket = s_valid[s_valid['entry_bucket'] == b]\n",
    "        g_bucket = games_valid[games_valid['margin_bucket'] == b]\n",
    "        \n",
    "        for q in q_labels:\n",
    "            pts = s_bucket[s_bucket[driver_col] == q]['score_value'].sum()\n",
    "            n_g = (g_bucket[driver_col] == q).sum()\n",
    "            ppm = pts / (n_g * 3) if n_g > 0 else np.nan\n",
    "            interaction_results.append({\n",
    "                'Driver': driver_label, 'Quartile': q,\n",
    "                'Margin Bucket': b, 'Games': n_g,\n",
    "                'Total Pts': int(pts),\n",
    "                'PPM': round(ppm, 3) if not np.isnan(ppm) else np.nan\n",
    "            })\n",
    "\n",
    "inter_df = pd.DataFrame(interaction_results)\n",
    "print(f'Total profiles computed: {len(inter_df)} (5 drivers × {len(BUCKET_ORDER)} buckets × 4 quartiles)')"
])

code("c8b", [
    "# ── TABLE: Driver 1 — Leading Team OREB × Margin Bucket ──\n",
    "d = inter_df[inter_df['Driver'] == 'Leading Team OREB']\n",
    "pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='PPM',\n",
    "                      sort=False).reindex(BUCKET_ORDER)\n",
    "games_pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='Games',\n",
    "                            aggfunc='sum', sort=False).reindex(BUCKET_ORDER)\n",
    "\n",
    "print('=== 1. Leading Team OREB × Margin Bucket PPM ===')\n",
    "print('PPM:')\n",
    "display(pivot)\n",
    "print('\\nGames per cell:')\n",
    "display(games_pivot)"
])

code("c8c", [
    "# ── TABLE: Driver 2 — Trailing Team 3PA Volume × Margin Bucket ──\n",
    "d = inter_df[inter_df['Driver'] == 'Trailing Team 3PA Volume']\n",
    "pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='PPM',\n",
    "                      sort=False).reindex(BUCKET_ORDER)\n",
    "games_pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='Games',\n",
    "                            aggfunc='sum', sort=False).reindex(BUCKET_ORDER)\n",
    "\n",
    "print('=== 2. Trailing Team 3PA Volume × Margin Bucket PPM ===')\n",
    "print('PPM:')\n",
    "display(pivot)\n",
    "print('\\nGames per cell:')\n",
    "display(games_pivot)"
])

code("c8d", [
    "# ── TABLE: Driver 3 — Trailing Team 3P% × Margin Bucket ──\n",
    "d = inter_df[inter_df['Driver'] == 'Trailing Team 3P%']\n",
    "pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='PPM',\n",
    "                      sort=False).reindex(BUCKET_ORDER)\n",
    "games_pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='Games',\n",
    "                            aggfunc='sum', sort=False).reindex(BUCKET_ORDER)\n",
    "\n",
    "print('=== 3. Trailing Team 3P% × Margin Bucket PPM ===')\n",
    "print('PPM:')\n",
    "display(pivot)\n",
    "print('\\nGames per cell:')\n",
    "display(games_pivot)"
])

code("c8e", [
    "# ── TABLE: Driver 4 — Leading Team Pace × Margin Bucket ──\n",
    "d = inter_df[inter_df['Driver'] == 'Leading Team Pace']\n",
    "pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='PPM',\n",
    "                      sort=False).reindex(BUCKET_ORDER)\n",
    "games_pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='Games',\n",
    "                            aggfunc='sum', sort=False).reindex(BUCKET_ORDER)\n",
    "\n",
    "print('=== 4. Leading Team Pace × Margin Bucket PPM ===')\n",
    "print('PPM:')\n",
    "display(pivot)\n",
    "print('\\nGames per cell:')\n",
    "display(games_pivot)"
])

code("c8f", [
    "# ── TABLE: Driver 5 — Trailing Team Pace × Margin Bucket ──\n",
    "d = inter_df[inter_df['Driver'] == 'Trailing Team Pace']\n",
    "pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='PPM',\n",
    "                      sort=False).reindex(BUCKET_ORDER)\n",
    "games_pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='Games',\n",
    "                            aggfunc='sum', sort=False).reindex(BUCKET_ORDER)\n",
    "\n",
    "print('=== 5. Trailing Team Pace × Margin Bucket PPM ===')\n",
    "print('PPM:')\n",
    "display(pivot)\n",
    "print('\\nGames per cell:')\n",
    "display(games_pivot)"
])

# ── Heatmaps for all 5 drivers ──
md("m8b", [
    "---\n",
    "## 7b — Heatmap Visualizations (All Drivers × All Buckets)"
])

code("c8g", [
    "# ── VIZ: Individual heatmap per driver (5 plots) ──\n",
    "for driver_col, driver_label, q_labels in DRIVER_CONFIGS:\n",
    "    fig, ax = plt.subplots(figsize=(10, 8))\n",
    "    d = inter_df[inter_df['Driver'] == driver_label]\n",
    "    pivot = d.pivot_table(index='Margin Bucket', columns='Quartile', values='PPM',\n",
    "                          sort=False).reindex(BUCKET_ORDER)[q_labels]\n",
    "    \n",
    "    valid_vals = pivot.values[~np.isnan(pivot.values)]\n",
    "    if len(valid_vals) == 0:\n",
    "        continue\n",
    "    \n",
    "    im = ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto',\n",
    "                   vmin=valid_vals.min() - 0.3,\n",
    "                   vmax=valid_vals.max() + 0.3)\n",
    "    ax.set_xticks(range(len(q_labels)))\n",
    "    ax.set_xticklabels(q_labels, fontsize=10)\n",
    "    ax.set_yticks(range(len(BUCKET_ORDER)))\n",
    "    ax.set_yticklabels(BUCKET_ORDER, fontsize=10)\n",
    "    ax.set_xlabel(driver_label + ' Quartile')\n",
    "    ax.set_ylabel('Entry Margin Bucket (Home Perspective)')\n",
    "    ax.set_title(f'{driver_label} × Margin Bucket — F3 PPM ({SEASON})',\n",
    "                 fontweight='bold', fontsize=13)\n",
    "    \n",
    "    for i in range(len(BUCKET_ORDER)):\n",
    "        for j in range(len(q_labels)):\n",
    "            val = pivot.values[i, j]\n",
    "            if not np.isnan(val):\n",
    "                ax.text(j, i, f'{val:.2f}', ha='center', va='center',\n",
    "                        fontsize=9, color='black', fontweight='bold')\n",
    "    \n",
    "    plt.colorbar(im, ax=ax, label='PPM', shrink=0.8)\n",
    "    plt.tight_layout()\n",
    "    fname = f'viz_driver_{driver_col.replace(\" \", \"_\").lower()}_heatmap.png'\n",
    "    plt.savefig(os.path.join(DATA_DIR, fname), dpi=150, bbox_inches='tight')\n",
    "    plt.show()\n",
    "    print(f'Saved: {fname}')"
])

# ── Combined effect ──
md("m9", [
    "---\n",
    "## 8 — Combined Driver Effects\n",
    "\n",
    "Look at games where multiple drivers align (e.g., trailing team with\n",
    "high 3PA volume AND high 3P%, or leading team with high OREB AND slow pace)."
])

code("c9", [
    "# ── Combined: trailing team 3PA Q1 + 3P% Q1 vs Q4 + Q4 ──\n",
    "g = entry_3_lt.copy()\n",
    "\n",
    "# Good trailing shooters: high volume + high efficiency\n",
    "g['trail_good_shooter'] = (\n",
    "    (g['trail_3PA Q'] == 'Q1 (High)') & (g['trail_3P% Q'] == 'Q1 (High)')\n",
    ")\n",
    "g['trail_poor_shooter'] = (\n",
    "    (g['trail_3PA Q'] == 'Q4 (Low)') & (g['trail_3P% Q'] == 'Q4 (Low)')\n",
    ")\n",
    "\n",
    "# Stalling leaders: high OREB + slow pace\n",
    "g['lead_stall'] = (\n",
    "    (g['lead_OREB Q'] == 'Q1 (High)') & (g['lead_Pace Q'] == 'Q4 (Slow)')\n",
    ")\n",
    "g['lead_fast_no_boards'] = (\n",
    "    (g['lead_OREB Q'] == 'Q4 (Low)') & (g['lead_Pace Q'] == 'Q1 (Fast)')\n",
    ")\n",
    "\n",
    "combos = {\n",
    "    'Trail: High 3PA + High 3P%': 'trail_good_shooter',\n",
    "    'Trail: Low 3PA + Low 3P%':   'trail_poor_shooter',\n",
    "    'Lead: High OREB + Slow Pace': 'lead_stall',\n",
    "    'Lead: Low OREB + Fast Pace':  'lead_fast_no_boards',\n",
    "}\n",
    "\n",
    "combo_rows = []\n",
    "for label, col in combos.items():\n",
    "    game_ids = g[g[col]].index\n",
    "    n_g = len(game_ids)\n",
    "    pts = scoring_3_lt[scoring_3_lt['game_id'].isin(game_ids)]['score_value'].sum()\n",
    "    ppm = pts / (n_g * 3) if n_g > 0 else 0\n",
    "    combo_rows.append({'Profile': label, 'Games': n_g, 'Total Pts': int(pts),\n",
    "                       'PPM': round(ppm, 3)})\n",
    "\n",
    "combo_df = pd.DataFrame(combo_rows)\n",
    "\n",
    "# Baseline: all non-tied games\n",
    "baseline_pts = scoring_3_lt['score_value'].sum()\n",
    "baseline_games = len(entry_3_lt)\n",
    "baseline_ppm = baseline_pts / (baseline_games * 3)\n",
    "print(f'Baseline PPM (all non-tied F3): {baseline_ppm:.3f}')\n",
    "\n",
    "print(f'\\n=== Combined Driver Profiles — Final 3 Min PPM ===')\n",
    "display(combo_df)"
])

# ── Summary ──
md("m10", ["---\n", "## 9 — Summary"])
code("c10", [
    "print('='*60)\n",
    "print(f'  DRIVER ANALYSIS — {SEASON} Season')\n",
    "print('='*60)\n",
    "print(f'\\n  P6 games (non-tied at 3:00): {len(entry_3_lt):,}')\n",
    "print(f'  Drivers analyzed: 5')\n",
    "print(f'    1. Leading team OREB')\n",
    "print(f'    2. Trailing team 3PA volume')\n",
    "print(f'    3. Trailing team 3P% efficiency')\n",
    "print(f'    4. Leading team pace (sec/poss)')\n",
    "print(f'    5. Trailing team pace')\n",
    "print(f'\\n  Outputs:')\n",
    "print(f'    PPM by driver quartile tables')\n",
    "print(f'    Driver x margin bucket interactions')\n",
    "print(f'    Combined driver profiles')\n",
    "print(f'    3 visualizations saved to data/')"
])

# ── Assemble ──
nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "cfbtm_env", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.14"}
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open("04_driver_analysis.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Created 04_driver_analysis.ipynb successfully!")
print(f"Total cells: {len(cells)}")
