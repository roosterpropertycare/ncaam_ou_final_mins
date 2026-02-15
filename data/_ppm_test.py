import pyarrow.parquet as pq
import pandas as pd
import numpy as np

pbp = pq.read_table('data/pbp_2024.parquet').to_pandas()
reg = pbp[pbp['period_number'].isin([1, 2])].copy()
reg['home_score'] = pd.to_numeric(reg['home_score'], errors='coerce').fillna(0).astype(int)
reg['away_score'] = pd.to_numeric(reg['away_score'], errors='coerce').fillna(0).astype(int)
reg['margin'] = reg['home_score'] - reg['away_score']
reg['secs_remaining'] = pd.to_numeric(reg['end_game_seconds_remaining'], errors='coerce')
reg['score_value'] = pd.to_numeric(reg['score_value'], errors='coerce').fillna(0).astype(int)
reg = reg.sort_values(['game_id', 'sequence_number']).reset_index(drop=True)

def get_entry_margin(game_df, window_secs):
    at_or_above = game_df[game_df['secs_remaining'] >= window_secs]
    if len(at_or_above) == 0:
        return None
    entry_event = at_or_above.iloc[-1]
    return entry_event['margin']

def margin_bucket(m):
    m = int(m)
    if   m > 15:            return 'Leading >15'
    elif 10 <= m <= 15:     return 'Leading 10-15'
    elif 5  <= m <= 9:      return 'Leading 5-9'
    elif 1  <= m <= 4:      return 'Leading 1-4'
    elif m == 0:            return 'Tied'
    elif -4 <= m <= -1:     return 'Trailing 1-4'
    elif -9 <= m <= -5:     return 'Trailing 5-9'
    elif -15 <= m <= -10:   return 'Trailing 10-15'
    else:                   return 'Trailing >15'

BUCKET_ORDER = [
    'Leading >15', 'Leading 10-15', 'Leading 5-9', 'Leading 1-4',
    'Tied', 'Trailing 1-4', 'Trailing 5-9', 'Trailing 10-15', 'Trailing >15'
]

games = reg.groupby('game_id')

with open('data/_ppm_check.txt', 'w') as f:
    for window_secs, window_label in [(600, 'Final 10 min'), (300, 'Final 5 min'), (180, 'Final 3 min')]:
        entry_margins = games.apply(lambda g: get_entry_margin(g, window_secs)).dropna()
        entry_buckets = entry_margins.apply(margin_bucket)
        
        scoring = reg[(reg['scoring_play'] == True) & (reg['secs_remaining'] <= window_secs)]
        scoring_wb = scoring.copy()
        scoring_wb['entry_bucket'] = scoring_wb['game_id'].map(entry_buckets)
        scoring_wb = scoring_wb.dropna(subset=['entry_bucket'])
        
        pts_by_bucket = scoring_wb.groupby('entry_bucket')['score_value'].sum()
        games_by_bucket = entry_buckets.value_counts()
        window_mins = window_secs / 60
        
        f.write(f'\n=== {window_label} (snapshot at {window_secs}s) ===\n')
        f.write(f'Games with entry data: {len(entry_margins)}\n')
        hdr = f'{"Bucket":<20} {"Games":>6} {"Pts":>8} {"PPM":>8}\n'
        f.write(hdr)
        f.write('-' * len(hdr) + '\n')
        for b in BUCKET_ORDER:
            pts = pts_by_bucket.get(b, 0)
            n_g = games_by_bucket.get(b, 0)
            ppm = pts / (n_g * window_mins) if n_g > 0 else 0
            f.write(f'{b:<20} {n_g:>6} {pts:>8,} {ppm:>8.3f}\n')
        
        total_pts = pts_by_bucket.sum()
        total_games = len(entry_margins)
        overall_ppm = total_pts / (total_games * window_mins) if total_games > 0 else 0
        f.write(f'{"TOTAL":<20} {total_games:>6} {total_pts:>8,} {overall_ppm:>8.3f}\n')

print('Done - results in data/_ppm_check.txt')
