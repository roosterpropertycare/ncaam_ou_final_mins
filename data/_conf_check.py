import pyarrow.parquet as pq
import pandas as pd

sched = pq.read_table('data/schedule_2024.parquet').to_pandas()

# groups_id -> name mapping
gmap = sched[['groups_id', 'groups_name', 'groups_short_name']].drop_duplicates().dropna()
gmap['groups_id'] = gmap['groups_id'].astype(int)
print("=== Conference ID -> Name mapping ===")
for _, r in gmap.sort_values('groups_id').iterrows():
    print(f"  {r['groups_id']:>3} -> {r['groups_short_name']:<15} ({r['groups_name']})")

# Team -> conference mapping from schedule
home = sched[['home_id', 'home_conference_id', 'home_display_name']].rename(
    columns={'home_id': 'team_id', 'home_conference_id': 'conf_id', 'home_display_name': 'team_name'}
)
away = sched[['away_id', 'away_conference_id', 'away_display_name']].rename(
    columns={'away_id': 'team_id', 'away_conference_id': 'conf_id', 'away_display_name': 'team_name'}
)
all_teams = pd.concat([home, away], ignore_index=True).dropna(subset=['conf_id'])
all_teams['conf_id'] = all_teams['conf_id'].astype(int)

# Most frequent conference per team
team_conf = all_teams.groupby('team_id').agg(
    conf_id=('conf_id', lambda x: x.mode().iloc[0]),
    team_name=('team_name', 'first')
).reset_index()
team_conf = team_conf.merge(gmap[['groups_id', 'groups_short_name']].rename(
    columns={'groups_id': 'conf_id', 'groups_short_name': 'conf'}
), on='conf_id', how='left')

print(f"\nTotal teams with conference: {len(team_conf)}")

# Power conference teams
POWER_CONFS = ['ACC', 'Big 12', 'Big East', 'Big Ten', 'Pac-12', 'SEC']
power_teams = team_conf[team_conf['conf'].isin(POWER_CONFS)]
print(f"\nPower 6 conference teams: {len(power_teams)}")
for conf in POWER_CONFS:
    ct = team_conf[team_conf['conf'] == conf]
    print(f"  {conf:<10} {len(ct):>3} teams")

# How many games are between power teams?
power_ids = set(power_teams['team_id'])
power_games = sched[
    sched['home_id'].isin(power_ids) & sched['away_id'].isin(power_ids)
]
any_power = sched[
    sched['home_id'].isin(power_ids) | sched['away_id'].isin(power_ids)
]
print(f"\nGames: both power = {len(power_games):,}, at least one power = {len(any_power):,}, total = {len(sched):,}")

# Extended: include AAC, MWC, A-10, WCC
EXTENDED_CONFS = POWER_CONFS + ['American', 'Mountain West', 'A-10', 'WCC']
ext_teams = team_conf[team_conf['conf'].isin(EXTENDED_CONFS)]
ext_ids = set(ext_teams['team_id'])
print(f"\nExtended conf teams (Power 6 + AAC/MWC/A10/WCC): {len(ext_teams)}")
ext_games = sched[sched['home_id'].isin(ext_ids) & sched['away_id'].isin(ext_ids)]
print(f"Games between extended conf teams: {len(ext_games):,}")
