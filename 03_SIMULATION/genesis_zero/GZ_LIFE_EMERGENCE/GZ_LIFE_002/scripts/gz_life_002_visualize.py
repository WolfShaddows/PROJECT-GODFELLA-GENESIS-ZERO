import csv
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "derived"
OUT = ROOT / "visualizations"

OUT.mkdir(parents=True, exist_ok=True)

def read_csv(name):
    with (DATA / name).open(
        encoding="utf-8-sig", newline=""
    ) as f:
        return list(csv.DictReader(f))

summary = read_csv("GZ_LIFE_002_RULE_SUMMARY.csv")
transitions = read_csv("GZ_LIFE_002_TRANSITION_SUMMARY.csv")

rules = [67, 109, 137]

colors = {
    67: "#40C4FF",
    109: "#FFD166",
    137: "#FF5C8A"
}

# 1. Asociaciones candidatas por transición
fig, ax = plt.subplots(figsize=(10, 6))

values = [
    int(next(r for r in summary if int(r["rule"]) == rule)
        ["candidate_edges"]) /
    int(next(r for r in summary if int(r["rule"]) == rule)
        ["transitions_analyzed"])
    for rule in rules
]

ax.bar(
    [str(r) for r in rules],
    values,
    color=[colors[r] for r in rules]
)

ax.set_title("GZ-LIFE-002 | Asociaciones candidatas por transición")
ax.set_xlabel("Regla celular")
ax.set_ylabel("Promedio de asociaciones candidatas")
ax.grid(axis="y", alpha=0.25)

fig.tight_layout()
fig.savefig(OUT / "GZ_LIFE_002_01_ASSOCIATIONS.png", dpi=180)
plt.close(fig)

# 2. Divisiones y fusiones candidatas
fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(len(rules))
width = 0.35

splits = [
    int(next(r for r in summary if int(r["rule"]) == rule)
        ["split_parent_events"]) /
    int(next(r for r in summary if int(r["rule"]) == rule)
        ["transitions_analyzed"])
    for rule in rules
]

merges = [
    int(next(r for r in summary if int(r["rule"]) == rule)
        ["merge_child_events"]) /
    int(next(r for r in summary if int(r["rule"]) == rule)
        ["transitions_analyzed"])
    for rule in rules
]

ax.bar(x - width/2, splits, width, label="Divisiones candidatas")
ax.bar(x + width/2, merges, width, label="Fusiones candidatas")

ax.set_xticks(x)
ax.set_xticklabels([str(r) for r in rules])
ax.set_ylabel("Eventos candidatos por transición")
ax.set_title("GZ-LIFE-002 | Actividad estructural")
ax.legend()
ax.grid(axis="y", alpha=0.25)

fig.tight_layout()
fig.savefig(OUT / "GZ_LIFE_002_02_SPLITS_MERGES.png", dpi=180)
plt.close(fig)

# 3. Evolución temporal de asociaciones
fig, axes = plt.subplots(3, 1, figsize=(14, 11))

for ax, rule in zip(axes, rules):
    rows = [
        r for r in transitions
        if int(r["rule"]) == rule
    ]

    frames = [int(r["transition"]) for r in rows]
    edges = [int(r["candidate_edges"]) for r in rows]

    ax.plot(frames, edges, linewidth=0.8, color=colors[rule])
    ax.set_title(f"Regla {rule}")
    ax.set_ylabel("Asociaciones")
    ax.grid(alpha=0.2)

axes[-1].set_xlabel("Transición temporal")

fig.suptitle(
    "GZ-LIFE-002 | Evolución de asociaciones candidatas",
    fontsize=15
)

fig.tight_layout()
fig.savefig(OUT / "GZ_LIFE_002_03_TEMPORAL_EVOLUTION.png", dpi=180)
plt.close(fig)

# 4. Dashboard comparativo
fig, axes = plt.subplots(1, 3, figsize=(16, 6))

for ax, rule in zip(axes, rules):
    rows = [
        r for r in transitions
        if int(r["rule"]) == rule
    ]

    edges = [int(r["candidate_edges"]) for r in rows]
    splits_t = [int(r["split_parents"]) for r in rows]
    merges_t = [int(r["merge_children"]) for r in rows]

    ax.plot(edges, label="Asociaciones", linewidth=0.8)
    ax.plot(splits_t, label="Divisiones", alpha=0.8)
    ax.plot(merges_t, label="Fusiones", alpha=0.8)

    ax.set_title(f"Regla {rule}")
    ax.set_xlabel("Transición")
    ax.grid(alpha=0.2)

axes[0].set_ylabel("Eventos por transición")
axes[-1].legend(fontsize=8)

fig.suptitle("GENESIS ZERO | GZ-LIFE-002")
fig.tight_layout()
fig.savefig(OUT / "GZ_LIFE_002_04_ATLAS_DASHBOARD.png", dpi=180)
plt.close(fig)

print("\nGRAFICOS GENERADOS CORRECTAMENTE")
for path in sorted(OUT.glob("GZ_LIFE_002_*.png")):
    print(f"{path.name} | {path.stat().st_size:,} bytes")
