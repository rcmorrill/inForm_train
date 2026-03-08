"""
viz_10 — INTERACTIVE COLUMN BAR CHART WITH PACKED CIRCLES
Three columns (Education | Other | Police+Fire) acting like bar chart bars.
Greedy drop-packing: each circle drops to the lowest available position
within column walls, like sand settling in a jar.
Toggle between base salary and total income — columns grow on toggle.
Variable circle size (same encoding as V7): r ∝ sqrt(income / π).
Generates visualization_10.html.
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
df['TOTAL_K']   = df['TOTAL'].apply(parse_dollars)

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

# ── Sampling ──────────────────────────────────────────────────────────────────
SAMPLE_N = {'education': 500, 'other': 200, 'police_fire': 300}
PIXEL_SCALE = 1.32

rng = np.random.default_rng(42)
records = []

for cat in ['education', 'other', 'police_fire']:
    sub_all = df[df['category'] == cat].sort_values('REGULAR_K').reset_index(drop=True)
    n_all = len(sub_all)
    n_samp = min(SAMPLE_N[cat], n_all)
    step = n_all / n_samp
    idx = np.round(np.arange(n_samp) * step).astype(int).clip(0, n_all - 1)
    sub = sub_all.iloc[idx].reset_index(drop=True)

    print(f"  {cat}: {n_all} → {len(sub)} sampled")

    for _, row in sub.iterrows():
        reg_k = max(row['REGULAR_K'], 0.01)
        supp_k = max(row['SUPP_K'], 0.0)
        total_k = reg_k + supp_k
        r_base = np.sqrt(reg_k / np.pi) * PIXEL_SCALE
        r_total = np.sqrt(total_k / np.pi) * PIXEL_SCALE
        r_pink = np.sqrt(max(supp_k, 0.001) / np.pi) * PIXEL_SCALE if supp_k > 0 else 0
        records.append({
            'cat': cat,
            'rb': round(float(r_base), 2),
            'rt': round(float(r_total), 2),
            'rp': round(float(r_pink), 2),
        })

print(f"Total records: {len(records)}")

# ── Greedy drop-pack algorithm ───────────────────────────────────────────────
def drop_pack(radii, col_left, col_right, floor_y, order=None, gap=0.4, n_x=50):
    """Drop each circle to the lowest available position within column walls.
    If order is provided, place circles in that order (for consistent stacking).
    Returns (xs, ys) arrays of circle centers in SVG coordinates."""
    n = len(radii)
    if order is None:
        order = np.argsort(-radii)  # largest first

    placed_x = []
    placed_y = []
    placed_r = []
    positions = np.zeros((n, 2))

    for idx in order:
        r = radii[idx]
        x_min = col_left + r
        x_max = col_right - r

        if x_min >= x_max:
            x_candidates = np.array([(col_left + col_right) / 2])
        else:
            x_candidates = np.linspace(x_min, x_max, n_x)

        best_x = x_candidates[0]
        best_y = -1e9

        px_arr = np.array(placed_x) if placed_x else np.array([])
        py_arr = np.array(placed_y) if placed_y else np.array([])
        pr_arr = np.array(placed_r) if placed_r else np.array([])

        for x in x_candidates:
            y = floor_y - r
            if len(px_arr) > 0:
                dx = np.abs(x - px_arr)
                min_dist = r + pr_arr + gap
                mask = dx < min_dist
                if mask.any():
                    dx_close = dx[mask]
                    py_close = py_arr[mask]
                    min_dist_close = min_dist[mask]
                    dy_needed = np.sqrt(min_dist_close**2 - dx_close**2)
                    y_limits = py_close - dy_needed
                    y = min(y, y_limits.min())
            if y > best_y:
                best_y = y
                best_x = x

        placed_x.append(best_x)
        placed_y.append(best_y)
        placed_r.append(r)
        positions[idx] = [best_x, best_y]

    return positions[:, 0], positions[:, 1]

# ── Column layout constants ──────────────────────────────────────────────────
COL_W = 180
COL_GAP = 60
MARGIN_LEFT = 80
SVG_W = MARGIN_LEFT + 3 * COL_W + 2 * COL_GAP + 40
FLOOR_Y = 650

col_specs = {}
for i, cat in enumerate(['education', 'other', 'police_fire']):
    left = MARGIN_LEFT + i * (COL_W + COL_GAP)
    col_specs[cat] = {
        'left': left,
        'right': left + COL_W,
        'cx': left + COL_W / 2,
    }

# ── Precompute both states with same ordering ────────────────────────────────
print("Packing circles (both states, same order)...")
max_total_height = 0
for cat in ['education', 'other', 'police_fire']:
    cat_indices = [i for i, r in enumerate(records) if r['cat'] == cat]
    radii_base = np.array([records[i]['rb'] for i in cat_indices])
    radii_total = np.array([records[i]['rt'] for i in cat_indices])
    col = col_specs[cat]

    # Use same placement order for both: sort by base radius (largest first)
    pack_order = np.argsort(-radii_base)

    bx, by = drop_pack(radii_base, col['left'], col['right'], FLOOR_Y, order=pack_order)
    tx, ty = drop_pack(radii_total, col['left'], col['right'], FLOOR_Y, order=pack_order)

    total_height = FLOOR_Y - (ty.min() - radii_total[np.argmin(ty)])
    max_total_height = max(max_total_height, total_height)

    for j, gi in enumerate(cat_indices):
        records[gi]['bx'] = round(float(bx[j]), 1)
        records[gi]['by'] = round(float(by[j]), 1)
        records[gi]['tx'] = round(float(tx[j]), 1)
        records[gi]['ty'] = round(float(ty[j]), 1)

    print(f"  {cat}: base top={by.min():.0f}, total top={ty.min():.0f}")

SVG_H = int(FLOOR_Y + 50)
print(f"SVG: {SVG_W} x {SVG_H}, max total column height: {max_total_height:.0f}px")

# Compute totals for y-axis
sampled_totals = {}
for cat in ['education', 'other', 'police_fire']:
    cat_records = [r for r in records if r['cat'] == cat]
    base_total = sum(np.pi * (r['rb'] / PIXEL_SCALE) ** 2 for r in cat_records)
    income_total = sum(np.pi * (r['rt'] / PIXEL_SCALE) ** 2 for r in cat_records)
    sampled_totals[cat] = {
        'base_k': round(float(base_total), 0),
        'total_k': round(float(income_total), 0),
    }
    print(f"  {cat}: base=${base_total:.0f}K, total=${income_total:.0f}K")

# Compute fixed y-axis scale: use max total dollars / max total height
max_total_dollars = max(t['total_k'] for t in sampled_totals.values())
dollars_per_px = max_total_dollars / max_total_height
print(f"Fixed y-axis: {dollars_per_px:.1f} $K/px, max ${max_total_dollars:.0f}K")

data_json = json.dumps(records)
totals_json = json.dumps(sampled_totals)
columns_json = json.dumps(col_specs)

# ── Generate HTML ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Boston Payroll — Column Bar Toggle</title>
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
const GOLD = "rgba(246,174,45,0.65)";
const PINK = "rgba(249,0,147,0.55)";
const BG = "rgb(229,236,233)";
const LC = "rgb(90,95,80)";
const FLOOR_Y = {FLOOR_Y};

const columns = {columns_json};
const data = {data_json};
const totals = {totals_json};
const DPP = {dollars_per_px};  // fixed dollars-per-pixel scale

let showSupp = false;

const svg = d3.select("#viz").style("background", BG);

// Fixed Y-axis — computed once, never changes
const yAxisX = columns.education.left - 5;
const maxDollars = Math.max(totals.education.total_k, totals.other.total_k, totals.police_fire.total_k);
const rawStep = maxDollars / 5;
const niceSteps = [1000, 2000, 5000, 10000, 20000, 50000];
let tickStep = niceSteps[0];
for (const s of niceSteps) {{
  if (s >= rawStep * 0.7) {{ tickStep = s; break; }}
}}
for (let dollarK = tickStep; dollarK <= maxDollars + tickStep; dollarK += tickStep) {{
  const y = FLOOR_Y - dollarK / DPP;
  if (y < 20) break;
  svg.append("line")
    .attr("x1", yAxisX)
    .attr("x2", columns.police_fire.right + 5)
    .attr("y1", y).attr("y2", y)
    .attr("stroke", "rgba(90,95,80,0.08)")
    .attr("stroke-width", 0.5);
  const label = dollarK >= 1000 ? "$" + (dollarK / 1000).toFixed(0) + "M" : "$" + dollarK + "K";
  svg.append("text")
    .attr("x", yAxisX - 5)
    .attr("y", y + 3)
    .attr("text-anchor", "end")
    .attr("font-family", "'Courier New', monospace")
    .attr("font-size", 9)
    .attr("fill", "rgba(90,95,80,0.45)")
    .text(label);
}}

// Column outlines and labels
Object.entries(columns).forEach(([cat, col]) => {{
  const labels = {{
    education: "Education",
    other: "Other City",
    police_fire: "Police + Fire"
  }};
  const wallTop = 30;
  const wallColor = "rgba(90,95,80,0.15)";

  svg.append("line")
    .attr("x1", col.left).attr("x2", col.right)
    .attr("y1", FLOOR_Y).attr("y2", FLOOR_Y)
    .attr("stroke", wallColor).attr("stroke-width", 1);
  svg.append("line")
    .attr("x1", col.left).attr("x2", col.left)
    .attr("y1", FLOOR_Y).attr("y2", wallTop)
    .attr("stroke", wallColor).attr("stroke-width", 1);
  svg.append("line")
    .attr("x1", col.right).attr("x2", col.right)
    .attr("y1", FLOOR_Y).attr("y2", wallTop)
    .attr("stroke", wallColor).attr("stroke-width", 1);

  svg.append("text")
    .attr("x", col.cx)
    .attr("y", FLOOR_Y + 25)
    .attr("text-anchor", "middle")
    .attr("font-family", "'Courier New', monospace")
    .attr("font-size", 13)
    .attr("fill", LC)
    .text(labels[cat]);
}});

// Initialize positions from precomputed base layout
data.forEach(d => {{ d.x = d.bx; d.y = d.by; }});

// Create circle groups
const nodes = svg.selectAll("g.node")
  .data(data)
  .join("g")
  .attr("class", "node")
  .attr("transform", d => `translate(${{d.x}},${{d.y}})`);

nodes.append("circle")
  .attr("class", "gold")
  .attr("r", d => d.rb)
  .attr("fill", "none")
  .attr("stroke", GOLD)
  .attr("stroke-width", 0.9);

nodes.append("circle")
  .attr("class", "pink")
  .attr("r", 0)
  .attr("fill", "none")
  .attr("stroke", PINK)
  .attr("stroke-width", 0.9);

// Force sim — springs toward target positions + collision
const sim = d3.forceSimulation(data)
  .force("targetX", d3.forceX(d => d.bx).strength(0.5))
  .force("targetY", d3.forceY(d => d.by).strength(0.5))
  .force("collide", d3.forceCollide(d => d.rb + 0.4).iterations(20).strength(1))
  .alphaDecay(0.02)
  .alphaMin(0.001)
  .velocityDecay(0.78)
  .on("tick", () => {{
    data.forEach(d => {{
      const col = columns[d.cat];
      const r = showSupp ? d.rt : d.rb;
      if (d.x - r < col.left)  {{ d.x = col.left + r;  d.vx = 0; }}
      if (d.x + r > col.right) {{ d.x = col.right - r; d.vx = 0; }}
      if (d.y + r > FLOOR_Y)   {{ d.y = FLOOR_Y - r;   d.vy = 0; }}
      if (d.y - r < 10)        {{ d.y = 10 + r;        d.vy = 0; }}
      d.vx = Math.max(-3, Math.min(3, d.vx));
      d.vy = Math.max(-3, Math.min(3, d.vy));
    }});
    nodes.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
  }})
  .on("end", () => {{
    data.forEach(d => {{ d.vx = 0; d.vy = 0; }});
  }})
  .stop();

// Toggle
d3.select("#toggle").on("click", function() {{
  showSupp = !showSupp;

  d3.select(this).text(
    showSupp
      ? "Show base salary only"
      : "Show total income (with supplemental)"
  );
  d3.select("#state-label").text(
    showSupp
      ? "Showing: total income (base + supplemental)"
      : "Showing: base salary only"
  );

  const dur = 1200;

  // Pink starts slightly before gold so magenta is visible as growth begins
  if (showSupp) {{
    nodes.selectAll(".pink")
      .transition()
      .duration(dur)
      .ease(d3.easeCubicOut)
      .attr("r", d => d.rp);

    nodes.selectAll(".gold")
      .transition()
      .delay(80)
      .duration(dur)
      .ease(d3.easeCubicInOut)
      .attr("r", d => d.rt);
  }} else {{
    nodes.selectAll(".gold")
      .transition()
      .duration(dur)
      .ease(d3.easeCubicInOut)
      .attr("r", d => d.rb);

    nodes.selectAll(".pink")
      .transition()
      .duration(dur * 0.6)
      .ease(d3.easeCubicIn)
      .attr("r", 0);
  }}

  // Update spring targets
  const xKey = showSupp ? "tx" : "bx";
  const yKey = showSupp ? "ty" : "by";
  const rKey = showSupp ? "rt" : "rb";

  sim.force("targetX", d3.forceX(d => d[xKey]).strength(0.5));
  sim.force("targetY", d3.forceY(d => d[yKey]).strength(0.5));
  sim.force("collide", d3.forceCollide(d => d[rKey] + 0.4).iterations(20).strength(1));

  data.forEach(d => {{ d.vx = 0; d.vy = 0; }});
  sim.alphaDecay(0.02).alpha(1).restart();
}});
</script>
</body>
</html>
"""

with open('visualization_10.html', 'w') as f:
    f.write(html)

print("Saved → visualization_10.html")
