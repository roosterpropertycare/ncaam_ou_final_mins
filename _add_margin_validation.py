"""
Insert 2 new cells into 04_driver_analysis.ipynb:
  - Markdown header for margin distribution validation
  - Code cell that builds 5-min snapshot margin distribution & plots grouped bar chart
Inserts right before the team profile section (id=m8b).
"""
import json, pathlib

NB = pathlib.Path(r"c:\Users\patgd\Downloads\Github\ncaam_ou_final_mins\04_driver_analysis.ipynb")

cell_md = {
    "cell_type": "markdown",
    "id": "m8a_valid",
    "metadata": {},
    "source": [
        "---\n",
        "## 8a — Validate Point-Differential Bucketing\n",
        "\n",
        "Before assessing drivers, confirm the distribution of absolute margins at\n",
        "the **3-minute** and **5-minute** snapshots looks reasonable.\n",
        "\n",
        "Buckets: `0 (Tied)`, `1-3`, `4-6`, `7-9`, `10-12`, `13-15`, `16-18`, `19+`"
    ]
}

cell_code = {
    "cell_type": "code",
    "execution_count": None,
    "id": "c8a_valid",
    "metadata": {},
    "outputs": [],
    "source": [
        "# ── 5-Minute Snapshot (if not already built) ──\n",
        "entry_5 = get_entry_info(reg, 300)\n",
        "entry_5['margin_bucket'] = entry_5['margin'].apply(margin_bucket)\n",
        "entry_5['abs_margin'] = entry_5['margin'].abs()\n",
        "\n",
        "entry_3['abs_margin'] = entry_3['margin'].abs()  # add to 3-min too\n",
        "\n",
        "# ── Fine-grained margin buckets ──\n",
        "FINE_LABELS = ['0 (Tied)', '1-3', '4-6', '7-9', '10-12', '13-15', '16-18', '19+']\n",
        "\n",
        "def fine_bucket(m):\n",
        "    m = int(abs(m))\n",
        "    if   m == 0:        return '0 (Tied)'\n",
        "    elif m <= 3:        return '1-3'\n",
        "    elif m <= 6:        return '4-6'\n",
        "    elif m <= 9:        return '7-9'\n",
        "    elif m <= 12:       return '10-12'\n",
        "    elif m <= 15:       return '13-15'\n",
        "    elif m <= 18:       return '16-18'\n",
        "    else:               return '19+'\n",
        "\n",
        "entry_3['fine_bucket'] = entry_3['margin'].apply(fine_bucket)\n",
        "entry_5['fine_bucket'] = entry_5['margin'].apply(fine_bucket)\n",
        "\n",
        "counts_3 = entry_3['fine_bucket'].value_counts().reindex(FINE_LABELS, fill_value=0)\n",
        "counts_5 = entry_5['fine_bucket'].value_counts().reindex(FINE_LABELS, fill_value=0)\n",
        "\n",
        "print('=== Margin Distribution at 3-Minute Snapshot ===')\n",
        "for b, c in counts_3.items():\n",
        "    print(f'  {b:10s}  {c:>5}')\n",
        "print(f'  {\"TOTAL\":10s}  {counts_3.sum():>5}')\n",
        "\n",
        "print('\\n=== Margin Distribution at 5-Minute Snapshot ===')\n",
        "for b, c in counts_5.items():\n",
        "    print(f'  {b:10s}  {c:>5}')\n",
        "print(f'  {\"TOTAL\":10s}  {counts_5.sum():>5}')\n",
        "\n",
        "# ── Grouped Bar Chart ──\n",
        "fig, ax = plt.subplots(figsize=(12, 6))\n",
        "\n",
        "x = np.arange(len(FINE_LABELS))\n",
        "width = 0.35\n",
        "\n",
        "bars_3 = ax.bar(x - width/2, counts_3.values, width,\n",
        "                label='3-min Snapshot', color='#4C72B0', alpha=0.85)\n",
        "bars_5 = ax.bar(x + width/2, counts_5.values, width,\n",
        "                label='5-min Snapshot', color='#DD8452', alpha=0.85)\n",
        "\n",
        "ax.set_xlabel('Absolute Point Differential', fontsize=12)\n",
        "ax.set_ylabel('Number of Games', fontsize=12)\n",
        "ax.set_title('Point-Differential Distribution at Snapshot\\n'\n",
        "             '(P6 vs P6 Games, 2024 Season)', fontsize=14, fontweight='bold')\n",
        "ax.set_xticks(x)\n",
        "ax.set_xticklabels(FINE_LABELS, rotation=45, ha='right')\n",
        "ax.legend()\n",
        "ax.grid(axis='y', alpha=0.3)\n",
        "\n",
        "# Annotate counts above bars\n",
        "for bar in bars_3:\n",
        "    h = bar.get_height()\n",
        "    if h > 0:\n",
        "        ax.text(bar.get_x() + bar.get_width()/2, h + 2,\n",
        "                str(int(h)), ha='center', va='bottom', fontsize=9)\n",
        "for bar in bars_5:\n",
        "    h = bar.get_height()\n",
        "    if h > 0:\n",
        "        ax.text(bar.get_x() + bar.get_width()/2, h + 2,\n",
        "                str(int(h)), ha='center', va='bottom', fontsize=9)\n",
        "\n",
        "plt.tight_layout()\n",
        "plt.savefig('data/viz_margin_distribution.png', dpi=150, bbox_inches='tight')\n",
        "plt.show()\n",
        "print('Saved: data/viz_margin_distribution.png')"
    ]
}

# ── Read notebook and insert before the team profile section (m8b) ──
nb = json.loads(NB.read_text(encoding="utf-8"))

insert_idx = None
for i, cell in enumerate(nb["cells"]):
    if cell.get("id") == "m8b":
        insert_idx = i
        break

if insert_idx is None:
    # Fallback: insert before Summary (m10)
    for i, cell in enumerate(nb["cells"]):
        if cell.get("id") == "m10":
            insert_idx = i
            break

if insert_idx is None:
    raise RuntimeError("Could not find insertion point")

nb["cells"].insert(insert_idx, cell_md)
nb["cells"].insert(insert_idx + 1, cell_code)

NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"✓ Inserted 2 cells at index {insert_idx}")
print(f"  Total cells now: {len(nb['cells'])}")
