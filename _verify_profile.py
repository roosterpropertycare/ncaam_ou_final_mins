"""
Standalone verification: run the full notebook logic through the new team profile cells.
"""
import pandas as pd
import pyarrow.parquet as pq
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import os, warnings
warnings.filterwarnings('ignore')

SEASON = 2024
DATA_DIR = os.path.join(os.getcwd(), 'data')

# ── Load data (same as cell c1) ──
pbp      = pq.read_table(os.path.join(DATA_DIR, f'pbp_{SEASON}.parquet')).to_pandas()
team_box = pq.read_table(os.path.join(DATA_DIR, f'team_box_{SEASON}.parquet')).to_pandas()
schedule = pq.read_table(os.path.join(DATA_DIR, f'schedule_{SEASON}.parquet')).to_pandas()
print(f'Loaded: PBP={pbp.shape[0]:,}, TeamBox={team_box.shape[0]:,}, Sched={schedule.shape[0]:,}')

# ── P6 filter (cell c2) ──
gmap = schedule[['groups_id', 'groups_short_name']].drop_duplicates().dropna()
gmap['groups_id'] = gmap['groups_id'].astype(int)
conf_id_to_name = gmap.set_index('groups_id')['groups_short_name'].to_dict()
home = schedule[['home_id','home_conference_id']].rename(columns={'home_id':'team_id','home_conference_id':'conf_id'})
away = schedule[['away_id','away_conference_id']].rename(columns={'away_id':'team_id','away_conference_id':'conf_id'})
all_teams = pd.concat([home, away]).dropna(subset=['conf_id'])
all_teams['conf_id'] = all_teams['conf_id'].astype(int)
team_conf = all_teams.groupby('team_id')['conf_id'].agg(lambda x: x.mode().iloc[0]).reset_index()
team_conf['conf'] = team_conf['conf_id'].map(conf_id_to_name)
POWER_6 = ['ACC', 'Big 12', 'Big East', 'Big Ten', 'Pac-12', 'SEC']
p6_ids = set(team_conf[team_conf['conf'].isin(POWER_6)]['team_id'])
p6_games = schedule[schedule['home_id'].isin(p6_ids) & schedule['away_id'].isin(p6_ids)]['game_id'].unique()
pbp_p6 = pbp[pbp['game_id'].isin(p6_games)].copy()

# ── Regulation + buckets (cell c2b) ──
reg = pbp_p6[pbp_p6['period_number'].isin([1, 2])].copy()
reg['home_score'] = pd.to_numeric(reg['home_score'], errors='coerce').fillna(0).astype(int)
reg['away_score'] = pd.to_numeric(reg['away_score'], errors='coerce').fillna(0).astype(int)
reg['score_value'] = pd.to_numeric(reg['score_value'], errors='coerce').fillna(0).astype(int)
reg['secs_remaining'] = pd.to_numeric(reg['end_game_seconds_remaining'], errors='coerce')
reg['margin'] = reg['home_score'] - reg['away_score']
reg = reg.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)

def margin_bucket(m):
    if pd.isna(m): return None
    m = int(m)
    if   m > 15:          return 'Leading >15'
    elif 10 <= m <= 15:   return 'Leading 10-15'
    elif 5  <= m <= 9:    return 'Leading 5-9'
    elif 1  <= m <= 4:    return 'Leading 1-4'
    elif m == 0:          return 'Tied'
    elif -4 <= m <= -1:   return 'Trailing 1-4'
    elif -9 <= m <= -5:   return 'Trailing 5-9'
    elif -15 <= m <= -10: return 'Trailing 10-15'
    else:                 return 'Trailing >15'

BUCKET_ORDER = [
    'Leading >15', 'Leading 10-15', 'Leading 5-9', 'Leading 1-4',
    'Tied',
    'Trailing 1-4', 'Trailing 5-9', 'Trailing 10-15', 'Trailing >15'
]

# ── Team stats + quartiles (cell c3) ──
tb = team_box.copy()
for col in ['offensive_rebounds', 'defensive_rebounds',
            'three_point_field_goals_made', 'three_point_field_goals_attempted',
            'field_goals_attempted', 'turnovers', 'free_throws_attempted',
            'team_score', 'opponent_team_score']:
    tb[col] = pd.to_numeric(tb[col], errors='coerce')
tb['three_pt_pct'] = pd.to_numeric(tb['three_point_field_goal_pct'], errors='coerce')
tb['possessions'] = (tb['field_goals_attempted'] - tb['offensive_rebounds']
                     + tb['turnovers'] + 0.475 * tb['free_throws_attempted'])
tb['sec_per_poss'] = 40 * 60 / tb['possessions']
team_stats = tb.groupby('team_id').agg(
    avg_oreb=('offensive_rebounds', 'mean'),
    avg_3pa=('three_point_field_goals_attempted', 'mean'),
    avg_3pt_pct=('three_pt_pct', 'mean'),
    avg_sec_per_poss=('sec_per_poss', 'mean'),
    avg_poss=('possessions', 'mean'),
    games=('game_id', 'nunique'),
    team_name=('team_display_name', 'first'),
).reset_index()
team_stats = team_stats[team_stats['games'] >= 10].copy()

DRIVERS = {
    'avg_oreb':         ('OREB Q', True),
    'avg_3pa':          ('3PA Q',  True),
    'avg_3pt_pct':      ('3P% Q',  True),
    'avg_sec_per_poss': ('Pace Q', False),
}
for col, (q_name, ascending_is_q1) in DRIVERS.items():
    if ascending_is_q1:
        team_stats[q_name] = pd.qcut(team_stats[col], q=4, labels=['Q4 (Low)', 'Q3', 'Q2', 'Q1 (High)'])
    else:
        team_stats[q_name] = pd.qcut(team_stats[col], q=4, labels=['Q1 (Fast)', 'Q2', 'Q3', 'Q4 (Slow)'])

# ── Snapshots (cells c4, c5) ──
def get_entry_info(reg_df, window_secs):
    pre = reg_df[reg_df['secs_remaining'] >= window_secs]
    entry = pre.groupby('game_id').last()
    return entry[['margin', 'home_team_id', 'away_team_id', 'home_score', 'away_score']]

driver_lookups = {}
for col, (q_name, _) in DRIVERS.items():
    driver_lookups[q_name] = team_stats.set_index('team_id')[q_name].to_dict()

def build_snapshot(reg_df, window_secs, driver_lookups):
    entry = get_entry_info(reg_df, window_secs)
    entry['margin_bucket'] = entry['margin'].apply(margin_bucket)
    entry['leading_team_id'] = np.where(entry['margin']>0, entry['home_team_id'],
                                         np.where(entry['margin']<0, entry['away_team_id'], np.nan))
    entry['trailing_team_id'] = np.where(entry['margin']>0, entry['away_team_id'],
                                          np.where(entry['margin']<0, entry['home_team_id'], np.nan))
    lt = entry[entry['margin'] != 0].copy()
    lt['abs_margin'] = lt['margin'].abs()
    for q_name, lookup in driver_lookups.items():
        lt[f'lead_{q_name}'] = lt['leading_team_id'].map(lookup)
        lt[f'trail_{q_name}'] = lt['trailing_team_id'].map(lookup)
    return entry, lt

entry_3, entry_3_lt = build_snapshot(reg, 180, driver_lookups)
entry_5, entry_5_lt = build_snapshot(reg, 300, driver_lookups)

# ── Scoring events ──
scoring_3 = reg[(reg['scoring_play'] == True) & (reg['secs_remaining'] <= 180)].copy()
scoring_3['entry_bucket'] = scoring_3['game_id'].map(entry_3['margin_bucket'])
scoring_3 = scoring_3.dropna(subset=['entry_bucket'])
scoring_3_lt = scoring_3[scoring_3['game_id'].isin(entry_3_lt.index)].copy()

scoring_5 = reg[(reg['scoring_play'] == True) & (reg['secs_remaining'] <= 300)].copy()
scoring_5['entry_bucket'] = scoring_5['game_id'].map(entry_5['margin_bucket'])
scoring_5 = scoring_5.dropna(subset=['entry_bucket'])
scoring_5_lt = scoring_5[scoring_5['game_id'].isin(entry_5_lt.index)].copy()

print(f'3-min snapshot: {len(entry_3_lt):,} non-tied games, {len(scoring_3_lt):,} scoring events')
print(f'5-min snapshot: {len(entry_5_lt):,} non-tied games, {len(scoring_5_lt):,} scoring events')

# ══════════════════════════════════════════════════════════════
# NEW CELL LOGIC — Team Profile Filter
# ══════════════════════════════════════════════════════════════
def apply_profile_mask(df):
    return (
        (df['trail_Pace Q'].isin(['Q2', 'Q3', 'Q4 (Slow)'])) &
        (df['lead_Pace Q'].isin(['Q2', 'Q3', 'Q4 (Slow)'])) &
        (df['trail_3P% Q'].isin(['Q3', 'Q4 (Low)'])) &
        (df['lead_OREB Q'].isin(['Q3', 'Q4 (Low)']))
    )

profile_3_games = set(entry_3_lt[apply_profile_mask(entry_3_lt)].index)
profile_5_games = set(entry_5_lt[apply_profile_mask(entry_5_lt)].index)

print(f'\nProfile matches — 3-min: {len(profile_3_games)} games, 5-min: {len(profile_5_games)} games')

# ── PPM by Margin Bucket ──
def compute_profile_ppm(profile_ids, scoring_df, window_mins, snapshot_entry):
    rows = []
    for bucket in BUCKET_ORDER:
        bucket_ids = [g for g in profile_ids
                      if snapshot_entry.loc[g, 'margin_bucket'] == bucket]
        n_g = len(bucket_ids)
        if n_g == 0:
            rows.append({'Margin Bucket': bucket, 'Games': 0, 'Total Pts': 0, 'PPM': np.nan})
            continue
        pts = scoring_df[scoring_df['game_id'].isin(bucket_ids)]['score_value'].sum()
        ppm = pts / (n_g * window_mins)
        rows.append({'Margin Bucket': bucket, 'Games': n_g,
                     'Total Pts': int(pts), 'PPM': round(ppm, 3)})
    return pd.DataFrame(rows)

ppm_3 = compute_profile_ppm(profile_3_games, scoring_3_lt, 3, entry_3_lt)
ppm_5 = compute_profile_ppm(profile_5_games, scoring_5_lt, 5, entry_5_lt)

baseline_3_ppm = scoring_3_lt['score_value'].sum() / (len(entry_3_lt) * 3)
baseline_5_ppm = scoring_5_lt['score_value'].sum() / (len(entry_5_lt) * 5)

print(f'\nBaseline PPM — 3-min: {baseline_3_ppm:.3f},  5-min: {baseline_5_ppm:.3f}')
print('\n=== Profile PPM by Margin Bucket — 3-Minute Snapshot ===')
print(ppm_3.to_string(index=False))
print('\n=== Profile PPM by Margin Bucket — 5-Minute Snapshot ===')
print(ppm_5.to_string(index=False))

# ══════════════════════════════════════════════════════════════
# NEW CELL LOGIC — Bar Chart
# ══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 6))
x = np.arange(len(BUCKET_ORDER))
width = 0.35

bars_3 = ax.bar(x - width/2, ppm_3['PPM'].values, width,
                label='3-min Snapshot', color='#4C72B0', alpha=0.85)
bars_5 = ax.bar(x + width/2, ppm_5['PPM'].values, width,
                label='5-min Snapshot', color='#DD8452', alpha=0.85)
ax.axhline(baseline_3_ppm, color='#4C72B0', linestyle='--', alpha=0.6,
           label=f'Baseline 3-min ({baseline_3_ppm:.2f})')
ax.axhline(baseline_5_ppm, color='#DD8452', linestyle='--', alpha=0.6,
           label=f'Baseline 5-min ({baseline_5_ppm:.2f})')
ax.set_xlabel('Margin Bucket at Snapshot', fontsize=12)
ax.set_ylabel('Points Per Minute (PPM)', fontsize=12)
ax.set_title('Team Profile PPM by Margin Bucket\n(Slow Pace + Low 3P% Trail + Low OREB Lead)',
             fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(BUCKET_ORDER, rotation=45, ha='right')
ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)

for bar, games in zip(bars_3, ppm_3['Games'].values):
    if games > 0 and not np.isnan(bar.get_height()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'n={games}', ha='center', va='bottom', fontsize=8)
for bar, games in zip(bars_5, ppm_5['Games'].values):
    if games > 0 and not np.isnan(bar.get_height()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'n={games}', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig('data/viz_team_profile_ppm.png', dpi=150, bbox_inches='tight')
print('\n✓ Chart saved: data/viz_team_profile_ppm.png')
print('✓ All cells verified successfully!')
