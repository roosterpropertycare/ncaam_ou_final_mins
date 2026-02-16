"""
Update 04_driver_analysis.ipynb to use fine-grained margin bucketing
(FINE_LABELS / fine_bucket) instead of directional bucketing (BUCKET_ORDER / margin_bucket)
throughout all analysis cells.

This script modifies the notebook JSON in-place and backs up the original.
"""
import json
import shutil
from pathlib import Path

NB_PATH = Path("04_driver_analysis.ipynb")
BACKUP_PATH = NB_PATH.with_suffix(".ipynb.bak")

def load_notebook(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_notebook(nb, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")

def set_cell_source(cell, source_str):
    """Set cell source from a multi-line string, converting to list-of-lines format."""
    lines = source_str.split("\n")
    # Convert to notebook format: each line ends with \n except the last
    result = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            result.append(line + "\n")
        else:
            result.append(line)
    cell["source"] = result
    # Clear old outputs
    cell["outputs"] = []
    cell["execution_count"] = None

FINE_BUCKET_DEF = """
# ── Fine-grained margin buckets ──
FINE_LABELS = ['0 (Tied)', '1-3', '4-6', '7-9', '10-12', '13-15', '16-18', '19+']

def fine_bucket(m):
    m = int(abs(m))
    if   m == 0:        return '0 (Tied)'
    elif m <= 3:        return '1-3'
    elif m <= 6:        return '4-6'
    elif m <= 9:        return '7-9'
    elif m <= 12:       return '10-12'
    elif m <= 15:       return '13-15'
    elif m <= 18:       return '16-18'
    else:               return '19+'
""".strip()

def main():
    # Backup
    shutil.copy2(NB_PATH, BACKUP_PATH)
    print(f"Backed up to {BACKUP_PATH}")

    nb = load_notebook(NB_PATH)
    cells = nb["cells"]

    # ═══════════════════════════════════════════════════════════
    # Cell 2 (id=c1): Add FINE_LABELS and fine_bucket definitions
    # ═══════════════════════════════════════════════════════════
    cell2 = cells[2]
    src2 = "".join(cell2["source"])
    if "FINE_LABELS" not in src2:
        src2 = src2.rstrip() + "\n\n" + FINE_BUCKET_DEF + "\n"
        set_cell_source(cell2, src2)
        print("Cell  2: Added FINE_LABELS and fine_bucket definitions")

    # ═══════════════════════════════════════════════════════════
    # Cell 10 (id=c4): Add fine_bucket to entry_3 and entry_3_lt,
    # update distribution printout
    # ═══════════════════════════════════════════════════════════
    cell10 = cells[10]
    src10 = "".join(cell10["source"])
    # Add fine_bucket to entry_3 after margin_bucket assignment
    if "entry_3['fine_bucket']" not in src10:
        src10 = src10.replace(
            "entry_3['margin_bucket'] = entry_3['margin'].apply(margin_bucket)",
            "entry_3['margin_bucket'] = entry_3['margin'].apply(margin_bucket)\n"
            "entry_3['fine_bucket'] = entry_3['margin'].apply(fine_bucket)"
        )
    # Add fine_bucket to entry_3_lt after abs_margin
    if "entry_3_lt['fine_bucket']" not in src10:
        src10 = src10.replace(
            "entry_3_lt['abs_margin'] = entry_3_lt['margin'].abs()",
            "entry_3_lt['abs_margin'] = entry_3_lt['margin'].abs()\n"
            "entry_3_lt['fine_bucket'] = entry_3_lt['margin'].apply(fine_bucket)"
        )
    set_cell_source(cell10, src10)
    print("Cell 10: Added fine_bucket columns to entry_3 and entry_3_lt")

    # ═══════════════════════════════════════════════════════════
    # Cell 14 (id=c6): Change entry_bucket mapping
    # ═══════════════════════════════════════════════════════════
    cell14 = cells[14]
    src14 = "".join(cell14["source"])
    src14 = src14.replace(
        "scoring_3['entry_bucket'] = scoring_3['game_id'].map(entry_3['margin_bucket'])",
        "scoring_3['entry_bucket'] = scoring_3['game_id'].map(entry_3['fine_bucket'])"
    )
    set_cell_source(cell14, src14)
    print("Cell 14: Changed entry_bucket mapping to fine_bucket")

    # ═══════════════════════════════════════════════════════════
    # Cell 19 (id=c8): Interaction computation
    # ═══════════════════════════════════════════════════════════
    cell19 = cells[19]
    src19 = "".join(cell19["source"])
    src19 = src19.replace("for b in BUCKET_ORDER:", "for b in FINE_LABELS:")
    src19 = src19.replace(
        "g_bucket = games_valid[games_valid['margin_bucket'] == b]",
        "g_bucket = games_valid[games_valid['fine_bucket'] == b]"
    )
    src19 = src19.replace("len(BUCKET_ORDER)", "len(FINE_LABELS)")
    set_cell_source(cell19, src19)
    print("Cell 19: Updated interaction computation to use FINE_LABELS/fine_bucket")

    # ═══════════════════════════════════════════════════════════
    # Cells 20-24: Driver pivot tables
    # ═══════════════════════════════════════════════════════════
    for idx in range(20, 25):
        cell = cells[idx]
        src = "".join(cell["source"])
        src = src.replace(".reindex(BUCKET_ORDER)", ".reindex(FINE_LABELS)")
        set_cell_source(cell, src)
        print(f"Cell {idx}: Updated .reindex(BUCKET_ORDER) -> .reindex(FINE_LABELS)")

    # ═══════════════════════════════════════════════════════════
    # Cell 26 (id=c8a_valid): Update — fine_bucket/FINE_LABELS 
    # are now in Cell 2, so remove their definitions from here.
    # Keep only the operational parts.
    # ═══════════════════════════════════════════════════════════
    cell26 = cells[26]
    src26 = "".join(cell26["source"])
    # Remove the FINE_LABELS and fine_bucket definitions since they're now in Cell 2
    # But keep the rest (5-min snapshot, fine_bucket column assignments, chart)
    src26 = src26.replace(
        "# ── Fine-grained margin buckets ──\n"
        "FINE_LABELS = ['0 (Tied)', '1-3', '4-6', '7-9', '10-12', '13-15', '16-18', '19+']\n"
        "\n"
        "def fine_bucket(m):\n"
        "    m = int(abs(m))\n"
        "    if   m == 0:        return '0 (Tied)'\n"
        "    elif m <= 3:        return '1-3'\n"
        "    elif m <= 6:        return '4-6'\n"
        "    elif m <= 9:        return '7-9'\n"
        "    elif m <= 12:       return '10-12'\n"
        "    elif m <= 15:       return '13-15'\n"
        "    elif m <= 18:       return '16-18'\n"
        "    else:               return '19+'\n"
        "\n",
        "# fine_bucket() and FINE_LABELS are defined in the setup cell above\n\n"
    )
    set_cell_source(cell26, src26)
    print("Cell 26: Removed redundant fine_bucket/FINE_LABELS definitions")

    # ═══════════════════════════════════════════════════════════
    # Cell 28 (id=c8g): Heatmap visualizations
    # ═══════════════════════════════════════════════════════════
    cell28 = cells[28]
    src28 = "".join(cell28["source"])
    src28 = src28.replace("BUCKET_ORDER", "FINE_LABELS")
    set_cell_source(cell28, src28)
    print("Cell 28: Updated heatmap to use FINE_LABELS")

    # ═══════════════════════════════════════════════════════════
    # Cell 32 (id=c8b, second): 5-min snapshot + profile PPM
    # ═══════════════════════════════════════════════════════════
    cell32 = cells[32]
    src32 = "".join(cell32["source"])
    
    # Add fine_bucket to entry_5 after margin_bucket
    if "entry_5['fine_bucket']" not in src32:
        src32 = src32.replace(
            "entry_5['margin_bucket'] = entry_5['margin'].apply(margin_bucket)",
            "entry_5['margin_bucket'] = entry_5['margin'].apply(margin_bucket)\n"
            "entry_5['fine_bucket'] = entry_5['margin'].apply(fine_bucket)"
        )
    
    # Add fine_bucket to entry_5_lt after abs_margin
    if "entry_5_lt['fine_bucket']" not in src32:
        src32 = src32.replace(
            "entry_5_lt['abs_margin'] = entry_5_lt['margin'].abs()",
            "entry_5_lt['abs_margin'] = entry_5_lt['margin'].abs()\n"
            "entry_5_lt['fine_bucket'] = entry_5_lt['margin'].apply(fine_bucket)"
        )
    
    # Change scoring_5 entry_bucket mapping
    src32 = src32.replace(
        "scoring_5['entry_bucket'] = scoring_5['game_id'].map(entry_5['margin_bucket'])",
        "scoring_5['entry_bucket'] = scoring_5['game_id'].map(entry_5['fine_bucket'])"
    )
    
    # Update compute_profile_ppm function: BUCKET_ORDER -> FINE_LABELS
    src32 = src32.replace(
        "for bucket in BUCKET_ORDER:",
        "for bucket in FINE_LABELS:"
    )
    src32 = src32.replace(
        "snapshot_entry.loc[g, 'margin_bucket'] == bucket",
        "snapshot_entry.loc[g, 'fine_bucket'] == bucket"
    )
    
    set_cell_source(cell32, src32)
    print("Cell 32: Updated 5-min snapshot to use fine_bucket + FINE_LABELS")

    # ═══════════════════════════════════════════════════════════
    # Cell 35 (id=c8c_tables): Role PPM tables
    # ═══════════════════════════════════════════════════════════
    cell35 = cells[35]
    src35 = "".join(cell35["source"])
    src35 = src35.replace(
        "for bucket in BUCKET_ORDER:",
        "for bucket in FINE_LABELS:"
    )
    src35 = src35.replace(
        "entry_df[entry_df['margin_bucket'] == bucket]",
        "entry_df[entry_df['fine_bucket'] == bucket]"
    )
    src35 = src35.replace(
        ".reindex(BUCKET_ORDER)",
        ".reindex(FINE_LABELS)"
    )
    set_cell_source(cell35, src35)
    print("Cell 35: Updated role PPM computation to use FINE_LABELS/fine_bucket")

    # ═══════════════════════════════════════════════════════════
    # Cell 36 (id=c8c_viz): Role PPM visualization
    # ═══════════════════════════════════════════════════════════
    cell36 = cells[36]
    src36 = "".join(cell36["source"])
    src36 = src36.replace("BUCKET_ORDER", "FINE_LABELS")
    set_cell_source(cell36, src36)
    print("Cell 36: Updated role PPM visualization to use FINE_LABELS")

    # ═══════════════════════════════════════════════════════════
    # Cell 37 (id=c8b_viz): Profile PPM grouped bar chart
    # ═══════════════════════════════════════════════════════════
    cell37 = cells[37]
    src37 = "".join(cell37["source"])
    src37 = src37.replace("BUCKET_ORDER", "FINE_LABELS")
    set_cell_source(cell37, src37)
    print("Cell 37: Updated profile PPM bar chart to use FINE_LABELS")

    # Save modified notebook
    save_notebook(nb, NB_PATH)
    print(f"\nNotebook saved to {NB_PATH}")
    print("Done! Please run all cells to verify.")

if __name__ == "__main__":
    main()
