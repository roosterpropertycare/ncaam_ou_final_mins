import pyarrow.parquet as pq
import pandas as pd
import numpy as np

tb = pq.read_table('data/team_box_2024.parquet').to_pandas()

# Check key columns for driver analysis
cols = ['game_id', 'team_id', 'team_display_name', 'team_home_away',
        'offensive_rebounds', 'defensive_rebounds', 'total_rebounds',
        'three_point_field_goals_made', 'three_point_field_goals_attempted',
        'three_point_field_goal_pct',
        'field_goals_attempted', 'turnovers', 'free_throws_attempted',
        'team_score', 'opponent_team_score']

sample = tb[cols].head(6)
print("=== Sample Team Box Data ===")
print(sample.to_string())

# Compute season averages for a few teams
for col in ['offensive_rebounds', 'three_point_field_goals_attempted',
            'three_point_field_goals_made', 'field_goals_attempted',
            'turnovers', 'free_throws_attempted']:
    tb[col] = pd.to_numeric(tb[col], errors='coerce')

tb['possessions'] = (tb['field_goals_attempted'] - pd.to_numeric(tb['offensive_rebounds'], errors='coerce')
                     + tb['turnovers'] + 0.475 * tb['free_throws_attempted'])
tb['sec_per_poss'] = 40 * 60 / tb['possessions']  # 40 min game / possessions
tb['three_pt_rate'] = tb['three_point_field_goals_attempted'] / tb['field_goals_attempted']
tb['three_pt_pct'] = pd.to_numeric(tb['three_point_field_goal_pct'], errors='coerce')

print("\n=== Season Averages (Per Game) ===")
print(f"OREB:          {tb['offensive_rebounds'].mean():.1f} (range {tb['offensive_rebounds'].min():.0f}-{tb['offensive_rebounds'].max():.0f})")
print(f"3PA:           {tb['three_point_field_goals_attempted'].mean():.1f}")
print(f"3P%:           {tb['three_pt_pct'].mean():.1f}%")
print(f"3PT Rate:      {tb['three_pt_rate'].mean():.1%}")
print(f"Possessions:   {tb['possessions'].mean():.1f}")
print(f"Sec/Poss:      {tb['sec_per_poss'].mean():.1f}")
