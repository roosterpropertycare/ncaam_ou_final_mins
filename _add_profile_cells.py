"""
Insert 3 new cells (team profile analysis) into 04_driver_analysis.ipynb
right before the Section 9 Summary.
"""
import json, pathlib

NB = pathlib.Path(r"c:\Users\patgd\Downloads\Github\ncaam_ou_final_mins\04_driver_analysis.ipynb")

# ── Define the 3 new cells ──────────────────────────────────────

cell_markdown = {
    "cell_type": "markdown",
    "id": "m8b",
    "metadata": {},
    "source": [
        "---\n",
        "## 8b — Team Profile: Slow Pace + Low 3P% + Low OREB\n",
        "\n",
        "Filter to games matching **all four** conditions:\n",
        "\n",
        "| Driver | Allowed Quartiles |\n",
        "|---|---|\n",
        "| Trailing team pace | Q2, Q3, or Q4 (not Q1 Fast) |\n",
        "| Leading team pace | Q2, Q3, or Q4 (not Q1 Fast) |\n",
        "| Trailing team 3P% | Q3 or Q4 (Low) |\n",
        "| Leading team OREB | Q3 or Q4 (Low) |\n",
        "\n",
        "Then compute PPM by margin bucket at both the **3-minute** and **5-minute** snapshots."
    ]
}

cell_compute = {
    "cell_type": "code",
    "execution_count": None,
    "id": "c8b",
    "metadata": {},
    "outputs": [],
    "source": [
        "# ── 5-Minute Snapshot (same pattern as the 3-min snapshot) ──\n",
        "entry_5 = get_entry_info(reg, 300)\n",
        "entry_5['margin_bucket'] = entry_5['margin'].apply(margin_bucket)\n",
        "\n",
        "entry_5['leading_team_id'] = np.where(\n",
        "    entry_5['margin'] > 0, entry_5['home_team_id'],\n",
        "    np.where(entry_5['margin'] < 0, entry_5['away_team_id'], np.nan)\n",
        ")\n",
        "entry_5['trailing_team_id'] = np.where(\n",
        "    entry_5['margin'] > 0, entry_5['away_team_id'],\n",
        "    np.where(entry_5['margin'] < 0, entry_5['home_team_id'], np.nan)\n",
        ")\n",
        "\n",
        "entry_5_lt = entry_5[entry_5['margin'] != 0].copy()\n",
        "entry_5_lt['abs_margin'] = entry_5_lt['margin'].abs()\n",
        "\n",
        "# Map driver quartiles onto the 5-min snapshot\n",
        "for q_name, lookup in driver_lookups.items():\n",
        "    entry_5_lt[f'lead_{q_name}'] = entry_5_lt['leading_team_id'].map(lookup)\n",
        "    entry_5_lt[f'trail_{q_name}'] = entry_5_lt['trailing_team_id'].map(lookup)\n",
        "\n",
        "# 5-min scoring events\n",
        "scoring_5 = reg[(reg['scoring_play'] == True) & (reg['secs_remaining'] <= 300)].copy()\n",
        "scoring_5['entry_bucket'] = scoring_5['game_id'].map(entry_5['margin_bucket'])\n",
        "scoring_5 = scoring_5.dropna(subset=['entry_bucket'])\n",
        "scoring_5_lt = scoring_5[scoring_5['game_id'].isin(entry_5_lt.index)].copy()\n",
        "\n",
        "print(f'5-min snapshot: {len(entry_5_lt):,} non-tied games, '\n",
        "      f'{len(scoring_5_lt):,} scoring events')\n",
        "\n",
        "# ── Team Profile Filter ──\n",
        "def apply_profile_mask(df):\n",
        "    return (\n",
        "        (df['trail_Pace Q'].isin(['Q2', 'Q3', 'Q4 (Slow)'])) &\n",
        "        (df['lead_Pace Q'].isin(['Q2', 'Q3', 'Q4 (Slow)'])) &\n",
        "        (df['trail_3P% Q'].isin(['Q3', 'Q4 (Low)'])) &\n",
        "        (df['lead_OREB Q'].isin(['Q3', 'Q4 (Low)']))\n",
        "    )\n",
        "\n",
        "profile_3_games = set(entry_3_lt[apply_profile_mask(entry_3_lt)].index)\n",
        "profile_5_games = set(entry_5_lt[apply_profile_mask(entry_5_lt)].index)\n",
        "\n",
        "print(f'Profile matches — 3-min: {len(profile_3_games)} games, '\n",
        "      f'5-min: {len(profile_5_games)} games')\n",
        "\n",
        "# ── PPM by Margin Bucket ──\n",
        "def compute_profile_ppm(profile_ids, scoring_df, window_mins, snapshot_entry):\n",
        "    rows = []\n",
        "    for bucket in BUCKET_ORDER:\n",
        "        bucket_ids = [g for g in profile_ids\n",
        "                      if snapshot_entry.loc[g, 'margin_bucket'] == bucket]\n",
        "        n_g = len(bucket_ids)\n",
        "        if n_g == 0:\n",
        "            rows.append({'Margin Bucket': bucket, 'Games': 0,\n",
        "                         'Total Pts': 0, 'PPM': np.nan})\n",
        "            continue\n",
        "        pts = scoring_df[scoring_df['game_id'].isin(bucket_ids)]['score_value'].sum()\n",
        "        ppm = pts / (n_g * window_mins)\n",
        "        rows.append({'Margin Bucket': bucket, 'Games': n_g,\n",
        "                     'Total Pts': int(pts), 'PPM': round(ppm, 3)})\n",
        "    return pd.DataFrame(rows)\n",
        "\n",
        "ppm_3 = compute_profile_ppm(profile_3_games, scoring_3_lt, 3, entry_3_lt)\n",
        "ppm_5 = compute_profile_ppm(profile_5_games, scoring_5_lt, 5, entry_5_lt)\n",
        "\n",
        "# Baselines\n",
        "baseline_3_ppm = scoring_3_lt['score_value'].sum() / (len(entry_3_lt) * 3)\n",
        "baseline_5_ppm = scoring_5_lt['score_value'].sum() / (len(entry_5_lt) * 5)\n",
        "print(f'\\nBaseline PPM — 3-min: {baseline_3_ppm:.3f},  5-min: {baseline_5_ppm:.3f}')\n",
        "\n",
        "print('\\n=== Profile PPM by Margin Bucket — 3-Minute Snapshot ===')\n",
        "display(ppm_3)\n",
        "print('\\n=== Profile PPM by Margin Bucket — 5-Minute Snapshot ===')\n",
        "display(ppm_5)"
    ]
}

cell_chart = {
    "cell_type": "code",
    "execution_count": None,
    "id": "c8b_viz",
    "metadata": {},
    "outputs": [],
    "source": [
        "# ── Grouped Bar Chart: Profile PPM at 3-min vs 5-min ──\n",
        "import seaborn as sns\n",
        "\n",
        "fig, ax = plt.subplots(figsize=(14, 6))\n",
        "\n",
        "x = np.arange(len(BUCKET_ORDER))\n",
        "width = 0.35\n",
        "\n",
        "bars_3 = ax.bar(x - width/2, ppm_3['PPM'].values, width,\n",
        "                label='3-min Snapshot', color='#4C72B0', alpha=0.85)\n",
        "bars_5 = ax.bar(x + width/2, ppm_5['PPM'].values, width,\n",
        "                label='5-min Snapshot', color='#DD8452', alpha=0.85)\n",
        "\n",
        "ax.axhline(baseline_3_ppm, color='#4C72B0', linestyle='--', alpha=0.6,\n",
        "           label=f'Baseline 3-min ({baseline_3_ppm:.2f})')\n",
        "ax.axhline(baseline_5_ppm, color='#DD8452', linestyle='--', alpha=0.6,\n",
        "           label=f'Baseline 5-min ({baseline_5_ppm:.2f})')\n",
        "\n",
        "ax.set_xlabel('Margin Bucket at Snapshot', fontsize=12)\n",
        "ax.set_ylabel('Points Per Minute (PPM)', fontsize=12)\n",
        "ax.set_title('Team Profile PPM by Margin Bucket\\n'\n",
        "             '(Slow Pace + Low 3P% Trail + Low OREB Lead)',\n",
        "             fontsize=14, fontweight='bold')\n",
        "ax.set_xticks(x)\n",
        "ax.set_xticklabels(BUCKET_ORDER, rotation=45, ha='right')\n",
        "ax.legend(loc='upper right')\n",
        "ax.grid(axis='y', alpha=0.3)\n",
        "\n",
        "# Annotate game counts above each bar\n",
        "for bar, games in zip(bars_3, ppm_3['Games'].values):\n",
        "    if games > 0 and not np.isnan(bar.get_height()):\n",
        "        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,\n",
        "                f'n={games}', ha='center', va='bottom', fontsize=8)\n",
        "for bar, games in zip(bars_5, ppm_5['Games'].values):\n",
        "    if games > 0 and not np.isnan(bar.get_height()):\n",
        "        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,\n",
        "                f'n={games}', ha='center', va='bottom', fontsize=8)\n",
        "\n",
        "plt.tight_layout()\n",
        "plt.savefig('data/viz_team_profile_ppm.png', dpi=150, bbox_inches='tight')\n",
        "plt.show()\n",
        "print('Saved: data/viz_team_profile_ppm.png')"
    ]
}

# ── Read notebook and insert ─────────────────────────────────
nb = json.loads(NB.read_text(encoding="utf-8"))

# Find the Summary section (cell with id "m10")
insert_idx = None
for i, cell in enumerate(nb["cells"]):
    if cell.get("id") == "m10":
        insert_idx = i
        break

if insert_idx is None:
    raise RuntimeError("Could not find Summary cell (id=m10)")

# Insert the 3 new cells right before the Summary
nb["cells"].insert(insert_idx, cell_markdown)
nb["cells"].insert(insert_idx + 1, cell_compute)
nb["cells"].insert(insert_idx + 2, cell_chart)

NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"✓ Inserted 3 cells before Summary (index {insert_idx})")
print(f"  Total cells now: {len(nb['cells'])}")
