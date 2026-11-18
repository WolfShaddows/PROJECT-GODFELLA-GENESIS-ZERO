import csv
import json
import hashlib
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
RAW = RESULTS / "raw"
OUT = BASE / "analysis" / "run_001"
if OUT.exists() and any(OUT.iterdir()):
    raise SystemExit("ABORT: run_001 contiene archivos. No se sobrescribirá evidencia.")

RULES = 256
CYCLES = 10000
WINDOW = 1000

OUT.mkdir(parents=True, exist_ok=True)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def binary_entropy(p):
    p = np.asarray(p, dtype=float)
    result = np.zeros_like(p)
    mask = (p > 0) & (p < 1)
    result[mask] = -(
        p[mask] * np.log2(p[mask]) +
        (1-p[mask]) * np.log2(1-p[mask])
    )
    return result

def exact_period(trajectory):
    seen = {}
    for cycle, state in enumerate(trajectory):
        key = np.packbits(state).tobytes()
        if key in seen:
            first = seen[key]
            return {
                "detected": True,
                "first_cycle": first,
                "repeat_cycle": cycle,
                "period": cycle - first
            }
        seen[key] = cycle

    return {
        "detected": False,
        "first_cycle": None,
        "repeat_cycle": None,
        "period": None
    }

def mutual_information_binary(x, y):
    joint = np.zeros((2, 2), dtype=float)
    for a in (0, 1):
        for b in (0, 1):
            joint[a, b] = np.mean((x == a) & (y == b))

    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    mi = 0.0

    for a in (0, 1):
        for b in (0, 1):
            if joint[a, b] > 0:
                mi += joint[a, b] * np.log2(
                    joint[a, b] / (px[a] * py[b])
                )

    return float(mi)

def analyze_rule(rule):
    path = RAW / f"rule_{rule:03d}.npz"

    if not path.exists():
        raise FileNotFoundError(path)

    with np.load(path) as data:
        packed = data["trajectory"]
        trajectory = np.unpackbits(
            packed,
            axis=1,
            count=256,
            bitorder="big"
        ).astype(np.uint8)

        stored_rule = int(data["rule"])
        stored_cycles = int(data["cycles"])
        stored_cells = int(data["cells"])

    if stored_rule != rule:
        raise ValueError(f"Rule identity mismatch: {rule}")

    if stored_cycles != CYCLES or stored_cells != 256:
        raise ValueError(f"Unexpected dimensions for rule {rule}")

    if trajectory.shape != (CYCLES + 1, 256):
        raise ValueError(f"Incomplete trajectory for rule {rule}")

    # --------------------------------------------------------
    # 1. PERSISTENCE
    # --------------------------------------------------------

    changes = np.count_nonzero(
        trajectory[1:] != trajectory[:-1],
        axis=1
    )

    flips_per_cell = np.count_nonzero(
        trajectory[-WINDOW:] != trajectory[-WINDOW-1:-1],
        axis=0
    )

    persistent_cells = float(
        np.mean(flips_per_cell == 0)
    )

    mean_cell_flips = float(np.mean(flips_per_cell))

    # --------------------------------------------------------
    # 2. STABILITY
    # --------------------------------------------------------

    terminal_change_count = int(changes[-1])
    terminal_fixed = bool(terminal_change_count == 0)

    suffix_all_zero = np.logical_and.accumulate((changes == 0)[::-1])[::-1]
    permanent_indices = np.flatnonzero(suffix_all_zero)
    first_permanent_fixed_cycle = (
        int(permanent_indices[0] + 1)
        if len(permanent_indices) else None
    )

    # --------------------------------------------------------
    # 3. PERIODICITY
    # --------------------------------------------------------

    period = exact_period(trajectory)

    # --------------------------------------------------------
    # 4. DYNAMICS
    # --------------------------------------------------------

    density = trajectory.mean(axis=1)
    recent_changes = changes[-WINDOW:]

    dynamics = {
        "mean_changes_last_1000": float(np.mean(recent_changes)),
        "max_changes_last_1000": int(np.max(recent_changes)),
        "min_changes_last_1000": int(np.min(recent_changes)),
        "changes_at_cycle_10000": terminal_change_count,
        "density_initial": float(density[0]),
        "density_final": float(density[-1]),
        "density_min": float(np.min(density)),
        "density_max": float(np.max(density)),
        "density_range": float(np.ptp(density))
    }

    # --------------------------------------------------------
    # 5. INFORMATION PROXIES
    # --------------------------------------------------------

    spatial_entropy = binary_entropy(density)

    # Distribution of all 8 possible local 3-cell patterns.
    local_pattern_entropy = []

    for state in trajectory:
        left = np.roll(state, 1)
        right = np.roll(state, -1)
        pattern = left * 4 + state * 2 + right

        counts = np.bincount(pattern, minlength=8) / len(state)
        positive = counts[counts > 0]

        local_pattern_entropy.append(
            float(-np.sum(positive * np.log2(positive)))
        )

    # Same-cell temporal mutual information.
    # This is correlation/predictability, not proof of memory.
    x = trajectory[:-1].ravel()
    y = trajectory[1:].ravel()
    temporal_mi = mutual_information_binary(x, y)

    return {
        "rule": rule,
        "trajectory_sha256": sha256(path),

        "persistence": {
            "fraction_cells_unchanged_last_1000": persistent_cells,
            "mean_flips_per_cell_last_1000": mean_cell_flips
        },

        "stability": {
            "first_permanent_fixed_cycle": first_permanent_fixed_cycle,
            "terminal_fixed": bool(terminal_fixed),
            "terminal_change_count": terminal_change_count
        },

        "periodicity": period,

        "dynamics": dynamics,

        "information_proxies": {
            "spatial_entropy_final_bits": float(spatial_entropy[-1]),
            "spatial_entropy_mean_bits": float(np.mean(spatial_entropy)),
            "local_pattern_entropy_final_bits": local_pattern_entropy[-1],
            "local_pattern_entropy_mean_bits": float(
                np.mean(local_pattern_entropy)
            ),
            "same_cell_temporal_mutual_information_bits": temporal_mi
        }
    }

# ------------------------------------------------------------
# VALIDATE INPUTS
# ------------------------------------------------------------

missing = [
    rule for rule in range(RULES)
    if not (RAW / f"rule_{rule:03d}.npz").exists()
]

if missing:
    raise SystemExit(f"Missing trajectories: {missing}")

print("INPUT VALIDATION: 256/256 trajectories found", flush=True)

# ------------------------------------------------------------
# ANALYZE ALL RULES
# ------------------------------------------------------------

started = time.time()
results = []
failures = []

for rule in range(RULES):
    try:
        result = analyze_rule(rule)
        results.append(result)
        print(f"ANALYZED RULE {rule:03d}/255", flush=True)

    except Exception as exc:
        failures.append({
            "rule": rule,
            "error": repr(exc)
        })
        print(f"FAILED RULE {rule:03d}: {exc}", flush=True)

if failures:
    raise SystemExit(
        f"Analysis incomplete: {len(failures)} failures. "
        "Inspect output before interpretation."
    )

# ------------------------------------------------------------
# SAVE COMPLETE JSON
# ------------------------------------------------------------

with open(OUT / "all_rules_analysis.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

# ------------------------------------------------------------
# SAVE COMPARATIVE CSV
# ------------------------------------------------------------

csv_path = OUT / "all_rules_comparison.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
        "rule",
        "persistent_cell_fraction_last_1000",
        "mean_cell_flips_last_1000",
        "first_permanent_fixed_cycle",
        "terminal_fixed",
        "terminal_changes",
        "period_detected",
        "period",
        "period_first_cycle",
        "mean_changes_last_1000",
        "density_final",
        "density_range",
        "spatial_entropy_final",
        "local_pattern_entropy_final",
        "same_cell_temporal_MI",
        "trajectory_sha256"
    ])

    for r in results:
        p = r["persistence"]
        s = r["stability"]
        q = r["periodicity"]
        d = r["dynamics"]
        i = r["information_proxies"]

        writer.writerow([
            r["rule"],
            p["fraction_cells_unchanged_last_1000"],
            p["mean_flips_per_cell_last_1000"],
            s["first_permanent_fixed_cycle"],
            s["terminal_fixed"],
            s["terminal_change_count"],
            q["detected"],
            q["period"],
            q["first_cycle"],
            d["mean_changes_last_1000"],
            d["density_final"],
            d["density_range"],
            i["spatial_entropy_final_bits"],
            i["local_pattern_entropy_final_bits"],
            i["same_cell_temporal_mutual_information_bits"],
            r["trajectory_sha256"]
        ])

# ------------------------------------------------------------
# GLOBAL COUNTS
# ------------------------------------------------------------

fixed_count = sum(
    r["stability"]["terminal_fixed"] for r in results
)

periodic_count = sum(
    r["periodicity"]["detected"] for r in results
)

summary = {
    "experiment": "GZ-EMERGENCE-001",
    "rules_analyzed": len(results),
    "cycles_per_rule": CYCLES,
    "analysis_failures": len(failures),
    "terminal_fixed_rules": int(fixed_count),
    "exact_period_detected_rules": int(periodic_count),
    "non_fixed_terminal_rules": RULES - int(fixed_count),
    "interpretation": (
        "Descriptive analysis only. Information proxies do not "
        "establish functional memory, computation, intelligence, "
        "or consciousness."
    ),
    "elapsed_seconds": time.time() - started
}

with open(OUT / "global_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

# ------------------------------------------------------------
# FIGURES
# ------------------------------------------------------------

rule_ids = np.array([r["rule"] for r in results])

persistent = np.array([
    r["persistence"]["fraction_cells_unchanged_last_1000"]
    for r in results
])

mean_changes = np.array([
    r["dynamics"]["mean_changes_last_1000"]
    for r in results
])

entropy = np.array([
    r["information_proxies"]["spatial_entropy_final_bits"]
    for r in results
])

period_values = np.array([
    r["periodicity"]["period"]
    if r["periodicity"]["detected"] else np.nan
    for r in results
], dtype=float)

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

axes[0, 0].bar(rule_ids, persistent)
axes[0, 0].set_title("Persistence: unchanged cell fraction")
axes[0, 0].set_xlabel("Rule")
axes[0, 0].set_ylabel("Fraction")

axes[0, 1].bar(rule_ids, mean_changes)
axes[0, 1].set_title("Dynamics: mean changes in last 1000 cycles")
axes[0, 1].set_xlabel("Rule")
axes[0, 1].set_ylabel("Changed cells / cycle")

axes[1, 0].bar(rule_ids, entropy)
axes[1, 0].set_title("Final spatial binary entropy")
axes[1, 0].set_xlabel("Rule")
axes[1, 0].set_ylabel("Bits")

axes[1, 1].scatter(rule_ids, period_values, s=12)
axes[1, 1].set_title("Detected exact temporal periods")
axes[1, 1].set_xlabel("Rule")
axes[1, 1].set_ylabel("Period (cycles)")

fig.suptitle("GZ-EMERGENCE-001 — 256-rule comparative analysis")
fig.tight_layout()
fig.savefig(OUT / "five_dimensions_overview.png", dpi=180)
plt.close(fig)

# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

report = f"""# GZ-EMERGENCE-001 — Five-Dimension Analysis

## Execution coverage

- Rules analyzed: {len(results)}/256
- Cycles per rule: {CYCLES}
- Analysis failures: {len(failures)}
- Terminal fixed rules: {fixed_count}
- Rules with exact repeated global states: {periodic_count}

## Five dimensions

1. Persistence: fraction of cells with no state changes during
   the final 1,000 transitions.
2. Stability: first detected fixed state and terminal state.
3. Periodicity: exact recurrence of a complete lattice state.
4. Dynamics: changes and density variation over time.
5. Information proxies: spatial entropy, local pattern entropy,
   and same-cell temporal mutual information.

## Interpretation limits

These are descriptive measurements of deterministic cellular
automata. Spatial entropy is not algorithmic complexity.
Temporal mutual information is not proof of functional memory.
A repeated state is not evidence of intelligence.
No result establishes cognition or consciousness.

## Files

- all_rules_analysis.json
- all_rules_comparison.csv
- global_summary.json
- five_dimensions_overview.png

Analysis runtime: {summary["elapsed_seconds"]:.2f} seconds.
"""

(OUT / "GZ_EMERGENCE_001_ANALYSIS_REPORT.md").write_text(
    report, encoding="utf-8"
)

print("\n========================================")
print("GZ-EMERGENCE-001 ANALYSIS COMPLETE")
print("========================================")
print(json.dumps(summary, indent=2))
print(f"Output directory: {OUT}")


