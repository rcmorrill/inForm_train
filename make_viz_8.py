"""
viz_8 — STACKED UNIT CHART, THREE SWIM LANES
Every circle is the same size. Gold = total income (base + supplemental).
Magenta inner circle proportional to supplemental fraction of total.
X = actual total income (not rank). Circles stacked vertically at each
income bin, forming a dot histogram — height shows density at each income level.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
import numpy as np

# ── Load & parse ─────────────────────────────────────────────────────────────
df = pd.read_csv('cityComp.csv')

def parse_dollars(val):
    if pd.isna(val) or str(val).strip() == '':
        return 0.0
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0

for col in ['REGULAR', 'OVERTIME', 'DETAIL', 'OTHER', 'INJURED']:
    df[col + '_N'] = df[col].apply(parse_dollars)

df['REGULAR_K'] = df['REGULAR_N'] / 1000
df['SUPP_K']    = (df['OVERTIME_N'] + df['DETAIL_N']
                   + df['OTHER_N']  + df['INJURED_N']) / 1000
df['TOTAL_K']   = df['TOTAL'].apply(parse_dollars)  # already in $K

df = df[(df['TOTAL_K'] > 0) & (df['REGULAR_K'] > 15)].copy()

def categorize(row):
    dept = str(row['DEPARTMENT_NAME'])
    if dept in ['Boston Police Department', 'Boston Fire Department']:
        return 'police_fire'
    elif row['Education'] == 1.0:
        return 'education'
    else:
        return 'other'

df['category'] = df.apply(categorize, axis=1)

# ── Palette ───────────────────────────────────────────────────────────────────
GOLD = (246/255, 174/255,  45/255)
PINK = (249/255,   0/255, 147/255)
BG   = np.array([229, 236, 233]) / 255
LC   = np.array([90, 95, 80]) / 255

# ── Uniform circle radius ────────────────────────────────────────────────────
R = 0.55
PAD = 0.05
D = 2 * R + PAD  # center-to-center distance in stack

# ── Sampling ──────────────────────────────────────────────────────────────────
SAMPLE_N = {'education': 2000, 'other': 600, 'police_fire': 1000}

# ── Income range mapping ─────────────────────────────────────────────────────
# X axis = actual total income in $K, mapped to canvas coordinates
# Income range: ~$20K to ~$400K (with outliers)
INC_MIN, INC_MAX = 20, 350   # $K — clips outliers
X_MIN, X_MAX = 10, 210       # canvas x

def income_to_x(inc_k):
    """Map income ($K) to canvas x coordinate."""
    return X_MIN + (np.clip(inc_k, INC_MIN, INC_MAX) - INC_MIN) / (INC_MAX - INC_MIN) * (X_MAX - X_MIN)

# Bin width in income space — each bin holds one column of circles
BIN_W_CANVAS = D  # one circle width on canvas
BIN_W_INCOME = (INC_MAX - INC_MIN) * BIN_W_CANVAS / (X_MAX - X_MIN)  # in $K

print(f"Bin width: {BIN_W_INCOME:.1f}K (canvas: {BIN_W_CANVAS:.2f})")

# ── Band layout ───────────────────────────────────────────────────────────────
# Band y0 values computed dynamically after each band is placed
BAND_ORDER = ['education', 'other', 'police_fire']
BAND_LABELS = {
    'education': 'Education',
    'other': 'Other City',
    'police_fire': 'Police + Fire',
}
BAND_GAP = 8  # vertical gap between bands

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(28, 22))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

rng = np.random.default_rng(42)

all_gold_patches = []
all_pink_patches = []
band_tops = {}
band_floors = {}

y_cursor = 2  # start near bottom

for cat in BAND_ORDER:
    sub_all = df[df['category'] == cat].sort_values('TOTAL_K').reset_index(drop=True)
    n_all   = len(sub_all)
    n_samp  = min(SAMPLE_N[cat], n_all)
    step    = n_all / n_samp
    idx     = np.round(np.arange(n_samp) * step).astype(int).clip(0, n_all - 1)
    sub     = sub_all.iloc[idx].reset_index(drop=True)
    n       = len(sub)

    print(f"  {cat}: {n_all} employees → {n} sampled")

    y_floor = y_cursor
    band_floors[cat] = y_floor

    # Bin each employee by income
    incomes = sub['TOTAL_K'].values
    bin_indices = np.floor((np.clip(incomes, INC_MIN, INC_MAX) - INC_MIN) / BIN_W_INCOME).astype(int)
    max_bin = int((INC_MAX - INC_MIN) / BIN_W_INCOME)
    bin_indices = np.clip(bin_indices, 0, max_bin)

    # Count per bin to track stack position
    bin_counts = {}

    supp_frac = np.where(incomes > 0, sub['SUPP_K'].values / incomes, 0.0)
    r_pink_arr = R * np.sqrt(np.clip(supp_frac, 0, 1))

    xs = np.empty(n)
    ys = np.empty(n)

    for i in range(n):
        b = bin_indices[i]
        count_in_bin = bin_counts.get(b, 0)

        cx = X_MIN + (b + 0.5) * BIN_W_CANVAS
        row = count_in_bin
        cy = y_floor + R + row * D * np.sqrt(3) / 2
        if row % 2 == 1:
            cx += BIN_W_CANVAS * 0.5

        xs[i] = cx
        ys[i] = cy
        bin_counts[b] = count_in_bin + 1

    band_top = ys.max() + R + 2 if n > 0 else y_floor + 5
    band_tops[cat] = band_top
    y_cursor = band_top + BAND_GAP

    for i in range(n):
        all_gold_patches.append(mpatches.Circle((xs[i], ys[i]), R))
        if r_pink_arr[i] > 0.08:
            all_pink_patches.append(mpatches.Circle((xs[i], ys[i]), r_pink_arr[i]))

    max_stack = max(bin_counts.values()) if bin_counts else 0
    n_bins_used = len(bin_counts)
    print(f"    {n_bins_used} income bins used, max stack height: {max_stack}, band height: {band_top - y_floor:.0f}")

print("Rendering…")

gold_col = PatchCollection(all_gold_patches,
                           facecolors='none',
                           edgecolors=[(*GOLD, 0.65)],
                           linewidths=0.7, zorder=2)
pink_col = PatchCollection(all_pink_patches,
                           facecolors='none',
                           edgecolors=[(*PINK, 0.55)],
                           linewidths=0.7, zorder=3)
ax.add_collection(gold_col)
ax.add_collection(pink_col)

# ── Band separators ──────────────────────────────────────────────────────────
for i in range(len(BAND_ORDER) - 1):
    cat_a = BAND_ORDER[i]
    cat_b = BAND_ORDER[i + 1]
    y_sep = (band_tops[cat_a] + band_floors[cat_b]) / 2
    ax.axhline(y_sep, color=(*tuple(BG * 0.78), 1.0), linewidth=1.2, zorder=1)

# ── Band labels ──────────────────────────────────────────────────────────────
for cat in BAND_ORDER:
    yc = (band_floors[cat] + band_tops[cat]) / 2
    ax.text(5, yc, BAND_LABELS[cat],
            fontsize=10, color=LC, fontfamily='monospace',
            ha='right', va='center')

# ── Income axis labels ───────────────────────────────────────────────────────
for inc_k in [50, 100, 150, 200, 250, 300]:
    xv = income_to_x(inc_k)
    ax.axvline(xv, color=(*tuple(LC), 0.07), linewidth=0.6, zorder=1)
    ax.text(xv, -1, f'${inc_k}K',
            fontsize=6.5, color=(*tuple(LC), 0.5), fontfamily='monospace',
            ha='center', va='top')

ax.text((X_MIN + X_MAX) / 2, -4,
        '← lower total income  |  higher total income →',
        fontsize=9, color=LC, fontfamily='monospace',
        ha='center', va='top')

# ── Legend ────────────────────────────────────────────────────────────────────
leg_x, leg_y = X_MAX - 8, -6
ax.add_patch(mpatches.Circle((leg_x, leg_y), R,
             facecolor='none', edgecolor=(*GOLD, 0.65), linewidth=0.7, zorder=5))
ax.add_patch(mpatches.Circle((leg_x + 3.5, leg_y), R,
             facecolor='none', edgecolor=(*GOLD, 0.65), linewidth=0.7, zorder=5))
ax.add_patch(mpatches.Circle((leg_x + 3.5, leg_y), R * np.sqrt(0.5),
             facecolor='none', edgecolor=(*PINK, 0.55), linewidth=0.7, zorder=6))

ax.text(leg_x, leg_y - R - 0.8, 'no supp.',
        fontsize=5.5, color=LC, fontfamily='monospace', ha='center', va='top')
ax.text(leg_x + 3.5, leg_y - R - 0.8, '50% supp.',
        fontsize=5.5, color=LC, fontfamily='monospace', ha='center', va='top')

y_max = max(band_tops.values()) + 3

ax.set_xlim(-5, 220)
ax.set_ylim(-8, y_max)
ax.set_aspect('equal')
ax.axis('off')

plt.tight_layout(pad=0.4)
plt.savefig('visualization_8.png', dpi=180, bbox_inches='tight', facecolor=BG)
plt.close()
print("Saved → visualization_8.png")
