"""
viz_7 — INTERACTIVE THREE-CLUSTER TOGGLE (HTML/D3)
Three packed clusters: Education | Other | Police+Fire.
Gold = total income. Toggle reveals magenta supplemental portion inside.
On toggle, gold circles grow from base-only to total; clusters expand.
Force simulation settles deliberately (no jitter).
Generates visualization_7.html.
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

data_json = json.dumps(records)
print(f"Total records: {len(records)}")

# Compute expected cluster growth for display
for cat in ['education', 'other', 'police_fire']:
    sub = df[df['category'] == cat]
    growth = (sub['REGULAR_K'] + sub['SUPP_K']).mean() / sub['REGULAR_K'].mean()
    print(f"  {cat}: total/base area growth = {growth:.2f}x")

# ── Generate HTML ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Boston Payroll — Base vs Supplemental</title>
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
  #toggle {{
    margin: 16px 0;
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
  svg {{ display: block; }}
  .label {{
    font-family: 'Courier New', monospace;
    fill: rgb(90,95,80);
    font-size: 13px;
    text-anchor: middle;
  }}
</style>
</head>
<body>
<button id="toggle">Show supplemental pay</button>
<svg id="viz"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const W = 1200, H = 750;
const GOLD = "rgba(246,174,45,0.65)";
const PINK = "rgba(249,0,147,0.55)";
const BG   = "rgb(229,236,233)";

const clusters = {{
  education:   {{ x: W * 0.22, y: H * 0.50, label: "Education" }},
  other:       {{ x: W * 0.55, y: H * 0.50, label: "Other City" }},
  police_fire: {{ x: W * 0.83, y: H * 0.50, label: "Police + Fire" }}
}};

const data = {data_json};

let showSupp = false;

// Assign initial positions near cluster centers
data.forEach(d => {{
  const c = clusters[d.cat];
  d.x = c.x + (Math.random() - 0.5) * 40;
  d.y = c.y + (Math.random() - 0.5) * 40;
}});

const svg = d3.select("#viz")
  .attr("width", W)
  .attr("height", H)
  .style("background", BG);

// Cluster labels
Object.values(clusters).forEach(c => {{
  svg.append("text")
    .attr("class", "label")
    .attr("x", c.x)
    .attr("y", 30)
    .text(c.label);
}});

// Placeholder reference circles — positioned after sim settles
const refCircles = {{}};
Object.entries(clusters).forEach(([cat, c]) => {{
  refCircles[cat] = svg.append("circle")
    .attr("cx", c.x)
    .attr("cy", c.y)
    .attr("r", 0)
    .attr("fill", "none")
    .attr("stroke", GOLD)
    .attr("stroke-width", 0.9)
    .attr("opacity", 0);
}});

// Create circle groups
const nodes = svg.selectAll("g.node")
  .data(data)
  .join("g")
  .attr("class", "node");

// Gold circles (starts at base-only size)
nodes.append("circle")
  .attr("class", "gold")
  .attr("r", d => d.rb)
  .attr("fill", "none")
  .attr("stroke", GOLD)
  .attr("stroke-width", 0.9);

// Magenta circles (hidden initially)
nodes.append("circle")
  .attr("class", "pink")
  .attr("r", d => d.rp)
  .attr("fill", "none")
  .attr("stroke", PINK)
  .attr("stroke-width", 0.9)
  .attr("opacity", 0);

// Force simulation — strong forces, high damping, stops when settled
const sim = d3.forceSimulation(data)
  .force("x", d3.forceX(d => clusters[d.cat].x).strength(0.2))
  .force("y", d3.forceY(d => clusters[d.cat].y).strength(0.2))
  .force("collide", d3.forceCollide(d => d.rb + 0.5).iterations(8).strength(1))
  .alphaDecay(0.05)
  .alphaMin(0.01)
  .velocityDecay(0.65)
  .on("tick", () => {{
    nodes.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
  }})
  .on("end", () => {{
    // Zero out all velocities when simulation ends — no residual drift
    data.forEach(d => {{ d.vx = 0; d.vy = 0; }});

    // Compute bounding circle for each cluster (only on first settle)
    if (!window._refDrawn) {{
      window._refDrawn = true;
      Object.entries(clusters).forEach(([cat, c]) => {{
        const pts = data.filter(d => d.cat === cat);
        // Start at centroid, then iteratively move toward the farthest disc
        let cx = pts.reduce((s, d) => s + d.x, 0) / pts.length;
        let cy = pts.reduce((s, d) => s + d.y, 0) / pts.length;
        for (let iter = 0; iter < 200; iter++) {{
          let maxD = 0, fi = 0;
          pts.forEach((d, i) => {{
            const dist = Math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2) + d.rb;
            if (dist > maxD) {{ maxD = dist; fi = i; }}
          }});
          // Move center toward farthest point
          const fd = pts[fi];
          const step = 0.5 / (1 + iter * 0.05);
          cx += (fd.x - cx) * step;
          cy += (fd.y - cy) * step;
        }}
        // Final radius = max distance from optimized center
        let maxR = 0;
        pts.forEach(d => {{
          const dist = Math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2) + d.rb;
          if (dist > maxR) maxR = dist;
        }});
        refCircles[cat]
          .attr("cx", cx)
          .attr("cy", cy)
          .attr("r", maxR)
          .transition().duration(400)
          .attr("opacity", 1);
      }});
    }}
  }});

// Let initial layout fully settle
sim.alpha(1).restart();

// Toggle button
d3.select("#toggle").on("click", function() {{
  showSupp = !showSupp;
  d3.select(this).text(showSupp ? "Hide supplemental pay" : "Show supplemental pay");

  // Zero velocities before restart so circles don't carry momentum
  data.forEach(d => {{ d.vx = 0; d.vy = 0; }});

  // Update collision radius
  sim.force("collide", d3.forceCollide(d => {{
    return (showSupp ? d.rt : d.rb) + 0.5;
  }}).iterations(8).strength(1));

  // Deliberate restart — moderate energy, high damping
  sim.alphaDecay(0.04).velocityDecay(0.65).alpha(0.5).restart();

  // Animate gold circles: grow to total or shrink to base
  nodes.selectAll(".gold")
    .transition()
    .duration(900)
    .ease(d3.easeCubicInOut)
    .attr("r", d => showSupp ? d.rt : d.rb);

  // Animate magenta circles: fade in/out
  nodes.selectAll(".pink")
    .transition()
    .duration(900)
    .ease(d3.easeCubicInOut)
    .attr("opacity", showSupp ? 1 : 0);
}});
</script>
</body>
</html>
"""

with open('visualization_7.html', 'w') as f:
    f.write(html)

print("Saved → visualization_7.html")
