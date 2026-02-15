"""
Quick standalone verification of the margin distribution logic.
Reuses core notebook setup, then runs the new validation cell logic.
"""
import pandas as pd, pyarrow.parquet as pq, numpy as np, os, warnings
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.getcwd(), 'data')
pbp      = pq.read_table(os.path.join(DATA_DIR, 'pbp_2024.parquet')).to_pandas()
schedule = pq.read_table(os.path.join(DATA_DIR, 'schedule_2024.parquet')).to_pandas()

# P6 filter
gmap = schedule[['groups_id','groups_short_name']].drop_duplicates().dropna()
gmap['groups_id'] = gmap['groups_id'].astype(int)
cmap = gmap.set_index('groups_id')['groups_short_name'].to_dict()
h = schedule[['home_id','home_conference_id']].rename(columns={'home_id':'team_id','home_conference_id':'conf_id'})
a = schedule[['away_id','away_conference_id']].rename(columns={'away_id':'team_id','away_conference_id':'conf_id'})
tc = pd.concat([h,a]).dropna(subset=['conf_id']); tc['conf_id']=tc['conf_id'].astype(int)
tc = tc.groupby('team_id')['conf_id'].agg(lambda x: x.mode().iloc[0]).reset_index()
tc['conf'] = tc['conf_id'].map(cmap)
p6_ids = set(tc[tc['conf'].isin(['ACC','Big 12','Big East','Big Ten','Pac-12','SEC'])]['team_id'])
p6_games = schedule[schedule['home_id'].isin(p6_ids) & schedule['away_id'].isin(p6_ids)]['game_id'].unique()

reg = pbp[pbp['game_id'].isin(p6_games) & pbp['period_number'].isin([1,2])].copy()
reg['home_score'] = pd.to_numeric(reg['home_score'], errors='coerce').fillna(0).astype(int)
reg['away_score'] = pd.to_numeric(reg['away_score'], errors='coerce').fillna(0).astype(int)
reg['secs_remaining'] = pd.to_numeric(reg['end_game_seconds_remaining'], errors='coerce')
reg['margin'] = reg['home_score'] - reg['away_score']
reg = reg.sort_values(['game_id','sequence_number']).reset_index(drop=True)

def get_entry_info(reg_df, window_secs):
    pre = reg_df[reg_df['secs_remaining'] >= window_secs]
    return pre.groupby('game_id').last()[['margin','home_team_id','away_team_id','home_score','away_score']]

entry_3 = get_entry_info(reg, 180); entry_3['abs_margin'] = entry_3['margin'].abs()
entry_5 = get_entry_info(reg, 300); entry_5['abs_margin'] = entry_5['margin'].abs()

FINE_LABELS = ['0 (Tied)', '1-3', '4-6', '7-9', '10-12', '13-15', '16-18', '19+']
def fine_bucket(m):
    m = int(abs(m))
    if   m == 0:  return '0 (Tied)'
    elif m <= 3:  return '1-3'
    elif m <= 6:  return '4-6'
    elif m <= 9:  return '7-9'
    elif m <= 12: return '10-12'
    elif m <= 15: return '13-15'
    elif m <= 18: return '16-18'
    else:         return '19+'

entry_3['fine_bucket'] = entry_3['margin'].apply(fine_bucket)
entry_5['fine_bucket'] = entry_5['margin'].apply(fine_bucket)

counts_3 = entry_3['fine_bucket'].value_counts().reindex(FINE_LABELS, fill_value=0)
counts_5 = entry_5['fine_bucket'].value_counts().reindex(FINE_LABELS, fill_value=0)

print('=== Margin Distribution at 3-Minute Snapshot ===')
for b, c in counts_3.items():
    print(f'  {b:10s}  {c:>5}')
print(f'  {"TOTAL":10s}  {counts_3.sum():>5}')

print('\n=== Margin Distribution at 5-Minute Snapshot ===')
for b, c in counts_5.items():
    print(f'  {b:10s}  {c:>5}')
print(f'  {"TOTAL":10s}  {counts_5.sum():>5}')

# ── Plot ──
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(FINE_LABELS)); width = 0.35
bars_3 = ax.bar(x - width/2, counts_3.values, width, label='3-min Snapshot', color='#4C72B0', alpha=0.85)
bars_5 = ax.bar(x + width/2, counts_5.values, width, label='5-min Snapshot', color='#DD8452', alpha=0.85)
ax.set_xlabel('Absolute Point Differential', fontsize=12)
ax.set_ylabel('Number of Games', fontsize=12)
ax.set_title('Point-Differential Distribution at Snapshot\n(P6 vs P6 Games, 2024 Season)', fontsize=14, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(FINE_LABELS, rotation=45, ha='right')
ax.legend(); ax.grid(axis='y', alpha=0.3)
for bar in bars_3:
    h = bar.get_height()
    if h > 0: ax.text(bar.get_x()+bar.get_width()/2, h+2, str(int(h)), ha='center', va='bottom', fontsize=9)
for bar in bars_5:
    h = bar.get_height()
    if h > 0: ax.text(bar.get_x()+bar.get_width()/2, h+2, str(int(h)), ha='center', va='bottom', fontsize=9)
plt.tight_layout()
plt.savefig('data/viz_margin_distribution.png', dpi=150, bbox_inches='tight')
print('\n✓ Saved: data/viz_margin_distribution.png')
