"""
viz_9 — INTERACTIVE STACKED DOT HISTOGRAM WITH TOGGLE
Three swim lanes (Education | Other | Police+Fire).
Uniform circles. Toggle between base salary and total income distributions.
Circles animate from base-salary positions to total-income positions.
Magenta inner circle appears on toggle showing supplemental fraction.
Generates visualization_9.html.
"""
import pandas as pd
import numpy as np
import json

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
    d = str(row['DEPARTMENT_NAME'])
    if d in ['Boston Police Department', 'Boston Fire Department']:
        return 'police_fire'
    return 'education' if row['Education'] == 1.0 else 'other'

df['category'] = df.apply(categorize, axis=1)

# ── Sampling ──────────────────────────────────────────────────────────────────
SAMPLE_N = {'education': 1200, 'other': 400, 'police_fire': 700}

# ── Layout constants (in SVG pixels) ─────────────────────────────────────────
SVG_W = 1400
R = 2.5        # circle radius in px
PAD = 0.5      # gap between circles
D = 2 * R + PAD  # center-to-center

# Income range — start at $10K to avoid left cutoff, cap at $300K (covers 95%+)
INC_MIN, INC_MAX = 10, 300  # $K
X_LEFT, X_RIGHT = 200, 1360  # px — wide left margin for labels
X_SPAN = X_RIGHT - X_LEFT

BIN_W_PX = D  # one circle width
BIN_W_INC = (INC_MAX - INC_MIN) * BIN_W_PX / X_SPAN  # $K per bin

# Band baselines computed dynamically after placing each band
# Process top-to-bottom: police_fire, other, education
BAND_PROCESS_ORDER = ['police_fire', 'other', 'education']
BAND_LABELS = {
    'education': 'Education',
    'other': 'Other City',
    'police_fire': 'Police + Fire',
}
BAND_GAP = 25  # px between bands

def income_to_bin(inc_k):
    """Map income ($K) to bin index."""
    return int(np.clip((inc_k - INC_MIN) / BIN_W_INC, 0, (INC_MAX - INC_MIN) / BIN_W_INC))

def compute_positions(incomes, baseline):
    """Compute stacked dot-histogram positions for a set of incomes.
    Returns (xs, ys) in SVG coordinates (y=0 at top)."""
    n = len(incomes)
    bin_indices = np.array([income_to_bin(v) for v in incomes])

    # Sort by income within each bin for stable stacking
    order = np.argsort(incomes)
    bin_counts = {}
    xs = np.empty(n)
    ys = np.empty(n)

    for idx in order:
        b = bin_indices[idx]
        count = bin_counts.get(b, 0)
        cx = X_LEFT + (b + 0.5) * BIN_W_PX
        row = count
        # Hex offset: odd rows shift right
        if row % 2 == 1:
            cx += BIN_W_PX * 0.5
        # Stack upward (decreasing y in SVG)
        cy = baseline - R - row * D * np.sqrt(3) / 2
        xs[idx] = cx
        ys[idx] = cy
        bin_counts[b] = count + 1

    return xs, ys

# ── First pass: compute max stack heights to determine band sizes ─────────────
def max_stack_height(incomes):
    """Return max number of circles in any single bin."""
    bin_indices = np.array([income_to_bin(v) for v in incomes])
    counts = {}
    for b in bin_indices:
        counts[b] = counts.get(b, 0) + 1
    return max(counts.values()) if counts else 0

band_heights = {}  # px height needed for each band (max of base and total views)
sampled_data = {}

rng = np.random.default_rng(42)

for cat in BAND_PROCESS_ORDER:
    sub_all = df[df['category'] == cat].sort_values('REGULAR_K').reset_index(drop=True)
    n_all = len(sub_all)
    n_samp = min(SAMPLE_N[cat], n_all)
    step = n_all / n_samp
    idx = np.round(np.arange(n_samp) * step).astype(int).clip(0, n_all - 1)
    sub = sub_all.iloc[idx].reset_index(drop=True)

    base_incomes = sub['REGULAR_K'].values
    total_incomes = sub['TOTAL_K'].values

    max_base = max_stack_height(base_incomes)
    max_total = max_stack_height(total_incomes)
    max_rows = max(max_base, max_total)
    height_px = max_rows * D * np.sqrt(3) / 2 + R * 2 + 15  # +padding for label

    band_heights[cat] = height_px
    sampled_data[cat] = sub
    print(f"  {cat}: {n_all} → {len(sub)} sampled, max_stack={max_rows}, band_height={height_px:.0f}px")

# Compute baselines: stack bands from bottom up
total_height = sum(band_heights.values()) + BAND_GAP * 2 + 50  # +margins
SVG_H = int(total_height)

baselines = {}
# Bottom-to-top: education (bottom), other (middle), police_fire (top)
y_cursor = SVG_H - 25  # bottom margin
for cat in ['education', 'other', 'police_fire']:
    baselines[cat] = y_cursor
    y_cursor -= band_heights[cat] + BAND_GAP

print(f"SVG_H = {SVG_H}")
for cat in ['education', 'other', 'police_fire']:
    print(f"  {cat}: baseline={baselines[cat]:.0f}, height={band_heights[cat]:.0f}")

# ── Build data with dynamic baselines ─────────────────────────────────────────
records = []

for cat in BAND_PROCESS_ORDER:
    sub = sampled_data[cat]
    n = len(sub)

    base_incomes = sub['REGULAR_K'].values
    total_incomes = sub['TOTAL_K'].values
    supp_k = sub['SUPP_K'].values
    supp_frac = np.where(total_incomes > 0, supp_k / total_incomes, 0.0)

    baseline = baselines[cat]

    bx, by = compute_positions(base_incomes, baseline)
    tx, ty = compute_positions(total_incomes, baseline)

    r_pink = R * np.sqrt(np.clip(supp_frac, 0, 1))

    for i in range(n):
        records.append({
            'cat': cat,
            'bx': round(float(bx[i]), 1),
            'by': round(float(by[i]), 1),
            'tx': round(float(tx[i]), 1),
            'ty': round(float(ty[i]), 1),
            'rp': round(float(r_pink[i]), 2),
        })

data_json = json.dumps(records)
print(f"Total: {len(records)} circles")

# ── Income axis tick positions ────────────────────────────────────────────────
ticks = []
for inc in [50, 100, 150, 200, 250, 300]:
    px = X_LEFT + (inc - INC_MIN) / (INC_MAX - INC_MIN) * X_SPAN
    ticks.append({'x': round(px, 1), 'label': f'${inc}K'})
ticks_json = json.dumps(ticks)

# ── Band info ─────────────────────────────────────────────────────────────────
bands_json = json.dumps([
    {'baseline': baselines[cat], 'label': BAND_LABELS[cat]}
    for cat in ['education', 'other', 'police_fire']
])

# ── Generate HTML ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Boston Payroll — Income Distribution Toggle</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: rgb(229,236,233);
    font-family: 'Courier New', monospace;
    color: rgb(90,95,80);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px;
  }}
  #controls {{
    margin: 12px 0;
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  #toggle {{
    padding: 10px 28px;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    color: rgb(90,95,80);
    background: rgba(90,95,80,0.08);
    border: 1px solid rgba(90,95,80,0.25);
    cursor: pointer;
    transition: background 0.2s;
  }}
  #toggle:hover {{ background: rgba(90,95,80,0.15); }}
  #state-label {{
    font-size: 13px;
    color: rgba(90,95,80,0.7);
  }}
  svg {{ display: block; width: 100%; max-width: {SVG_W}px; height: auto; }}
</style>
</head>
<body>
<div id="controls">
  <button id="toggle">Show total income (with supplemental)</button>
  <span id="state-label">Showing: base salary only</span>
</div>
<svg id="viz" viewBox="0 0 {SVG_W} {SVG_H}"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const W = {SVG_W}, H = {SVG_H};
const R = {R};
const GOLD = "rgba(246,174,45,0.65)";
const PINK = "rgba(249,0,147,0.55)";
const BG = "rgb(229,236,233)";
const LC = "rgb(90,95,80)";

const data = {data_json};
const ticks = {ticks_json};
const bands = {bands_json};

let showTotal = false;

const svg = d3.select("#viz").style("background", BG);

// Band labels
bands.forEach(b => {{
  svg.append("text")
    .attr("x", 15)
    .attr("y", b.baseline - 5)
    .attr("font-family", "'Courier New', monospace")
    .attr("font-size", 12)
    .attr("fill", LC)
    .text(b.label);

  // Baseline
  svg.append("line")
    .attr("x1", {X_LEFT}).attr("x2", {X_RIGHT})
    .attr("y1", b.baseline).attr("y2", b.baseline)
    .attr("stroke", "rgba(90,95,80,0.12)")
    .attr("stroke-width", 0.5);
}});

// Income axis ticks
ticks.forEach(t => {{
  svg.append("line")
    .attr("x1", t.x).attr("x2", t.x)
    .attr("y1", 0).attr("y2", H)
    .attr("stroke", "rgba(90,95,80,0.06)")
    .attr("stroke-width", 0.5);
  svg.append("text")
    .attr("x", t.x)
    .attr("y", H - 5)
    .attr("text-anchor", "middle")
    .attr("font-family", "'Courier New', monospace")
    .attr("font-size", 10)
    .attr("fill", "rgba(90,95,80,0.5)")
    .text(t.label);
}});

// Axis label
svg.append("text")
  .attr("x", ({X_LEFT} + {X_RIGHT}) / 2)
  .attr("y", H - 18)
  .attr("text-anchor", "middle")
  .attr("font-family", "'Courier New', monospace")
  .attr("font-size", 11)
  .attr("fill", LC)
  .attr("id", "axis-label")
  .text("\\u2190 lower base salary  |  higher base salary \\u2192");

// Create circle groups — start at base positions
const nodes = svg.selectAll("g.node")
  .data(data)
  .join("g")
  .attr("class", "node")
  .attr("transform", d => `translate(${{d.bx}},${{d.by}})`);

// Gold circles (uniform size)
nodes.append("circle")
  .attr("class", "gold")
  .attr("r", R)
  .attr("fill", "none")
  .attr("stroke", GOLD)
  .attr("stroke-width", 0.7);

// Magenta circles (hidden initially)
nodes.append("circle")
  .attr("class", "pink")
  .attr("r", d => d.rp)
  .attr("fill", "none")
  .attr("stroke", PINK)
  .attr("stroke-width", 0.7)
  .attr("opacity", 0);

// Toggle
d3.select("#toggle").on("click", function() {{
  showTotal = !showTotal;

  d3.select(this).text(
    showTotal
      ? "Show base salary only"
      : "Show total income (with supplemental)"
  );
  d3.select("#state-label").text(
    showTotal
      ? "Showing: total income (base + supplemental)"
      : "Showing: base salary only"
  );
  d3.select("#axis-label").text(
    showTotal
      ? "\\u2190 lower total income  |  higher total income \\u2192"
      : "\\u2190 lower base salary  |  higher base salary \\u2192"
  );

  // Animate circles to new positions
  nodes.transition()
    .duration(1200)
    .ease(d3.easeCubicInOut)
    .attr("transform", d => {{
      const x = showTotal ? d.tx : d.bx;
      const y = showTotal ? d.ty : d.by;
      return `translate(${{x}},${{y}})`;
    }});

  // Fade magenta in/out
  nodes.selectAll(".pink")
    .transition()
    .duration(1200)
    .ease(d3.easeCubicInOut)
    .attr("opacity", showTotal ? 1 : 0);
}});
</script>
</body>
</html>
"""

with open('visualization_9.html', 'w') as f:
    f.write(html)

print("Saved → visualization_9.html")
