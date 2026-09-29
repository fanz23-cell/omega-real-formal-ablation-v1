"""Generates the two most decision-relevant figures. Real data only, from
154_statistical_analysis.json (itself reproducible from raw rows via analyze.py).
Run from the harness/ directory (relative paths only, no machine-specific paths)."""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_JSON = os.path.join(HERE, "154_statistical_analysis.json")
if not os.path.exists(RESULTS_JSON):
    RESULTS_JSON = os.path.join(HERE, "..", "results", "154_statistical_analysis.json")
FIGURES_DIR = os.path.join(HERE, "..", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

d = json.load(open(RESULTS_JSON))

# Figure: primary + secondary contrasts, forest-plot style
fig, ax = plt.subplots(figsize=(7, 3.2))
contrasts = [("B1 - B0", d["b1_minus_b0"]["ci"]), ("C - B1 (PRIMARY)", d["c_minus_b1"]["ci"]),
             ("C - B0", d["c_minus_b0"]["ci"])]
y = list(range(len(contrasts)))[::-1]
for yi, (name, ci) in zip(y, contrasts):
    color = "#2a9d8f" if abs(ci["point_estimate_pp"]) < 10 and ci["ci95_lo_pp"] < 0 < ci["ci95_hi_pp"] else "#e76f51"
    ax.plot([ci["ci95_lo_pp"], ci["ci95_hi_pp"]], [yi, yi], color=color, lw=2, solid_capstyle="round")
    ax.plot(ci["point_estimate_pp"], yi, "o", color=color, ms=8)
ax.axvline(0, color="#888", lw=1, ls="--")
ax.axvspan(-10, 10, color="#ddd", alpha=0.3, zorder=0)
ax.set_yticks(y)
ax.set_yticklabels([c[0] for c in contrasts])
ax.set_xlabel("Paired decision_correct delta (percentage points)")
ax.set_title("Primary result: C adds no measurable value over B1\n(paired bootstrap 95% CI, n=189)")
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "02_primary_effect.svg"))
plt.savefig(os.path.join(FIGURES_DIR, "02_primary_effect.png"), dpi=150)
plt.close()

# Figure: per-geometry breakdown
fig, ax = plt.subplots(figsize=(9, 4))
geoms = sorted(d["by_geometry"].keys())
b0 = [d["by_geometry"][g]["b0_rate"] * 100 for g in geoms]
b1 = [d["by_geometry"][g]["b1_rate"] * 100 for g in geoms]
c = [d["by_geometry"][g]["c_rate"] * 100 for g in geoms]
x = range(len(geoms))
w = 0.27
ax.bar([xi - w for xi in x], b0, width=w, label="B0", color="#8d99ae")
ax.bar([xi for xi in x], b1, width=w, label="B1", color="#3b82f6")
ax.bar([xi + w for xi in x], c, width=w, label="C", color="#8b5cf6")
ax.set_xticks(list(x))
ax.set_xticklabels([g.replace("_", "\n") for g in geoms], fontsize=7)
ax.set_ylabel("decision_correct (%)")
ax.set_title("Per-geometry breakdown (n=21 each — individually underpowered, shown for pattern only)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "04_by_geometry.svg"))
plt.savefig(os.path.join(FIGURES_DIR, "04_by_geometry.png"), dpi=150)
plt.close()

print("wrote 2 figures (SVG+PNG)")
