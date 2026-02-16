import pandas as pd
import pyarrow.parquet as pq
import urllib.request
import os

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
BASE_URL = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
SEASONS = [2021, 2022, 2023]

def download_parquet(url, filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Downloading from {url} ...")
        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"  -> saved to {filepath}")
        except Exception as e:
            print(f"  FAILED to download {filename}: {e}")
    else:
        print(f"Using cached {filename}")

if __name__ == "__main__":
    for season in SEASONS:
        print(f"--- Processing Season {season} ---")
        # PBP
        url = f"{BASE_URL}/espn_mens_college_basketball_pbp/play_by_play_{season}.parquet"
        download_parquet(url, f"pbp_{season}.parquet")
        # Team Box
        url = f"{BASE_URL}/espn_mens_college_basketball_team_boxscores/team_box_{season}.parquet"
        download_parquet(url, f"team_box_{season}.parquet")
        # Schedule
        url = f"{BASE_URL}/espn_mens_college_basketball_schedules/mbb_schedule_{season}.parquet"
        download_parquet(url, f"schedule_{season}.parquet")
