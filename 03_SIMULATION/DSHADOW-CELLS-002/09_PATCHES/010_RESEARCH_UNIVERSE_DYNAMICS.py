import json
import math
import csv
import statistics
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "evidence" / "UNIVERSE_EXPORT_20261105_112658"

SNAPSHOT = EXPORT / "universe_snapshot.json"
HISTORY = ROOT / "logs" / "observations.jsonl"
OUT = EXPORT / "RESEARCH_4_LINES"

OUT.mkdir(parents=True, exist_ok=True)

def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def read_history():
    records = []
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8") as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records

def get_number(record, *keys):
    for key in keys:
        value = record.get(key)
        if isinstance(value, (int, float)):
            return value
    return None

data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
cells = sorted(set(map(int, data["active"])))
generation = data.get("generation")
history = read_history()

if not cells:
    raise SystemExit("El snapshot no contiene células activas.")

minimum, maximum = cells[0], cells[-1]
span = maximum - minimum + 1
gaps = [b - a - 1 for a, b in zip(cells, cells[1:])]
components = 1 + sum(g > 0 for g in gaps)

# ---------------------------------------------------------
# 1. PERSISTENCIA ESTRUCTURAL
# No equivale a persistencia temporal de células individuales.
# ---------------------------------------------------------

runs = []
run_start = cells[0]
previous = cells[0]

for x in cells[1:]:
    if x != previous + 1:
        runs.append((run_start, previous, previous - run_start + 1))
        run_start = x
    previous = x

runs.append((run_start, previous, previous - run_start + 1))

run_lengths = [r[2] for r in runs]
run_frequency = Counter(run_lengths)

write_csv(
    OUT / "persistence_structure_runs.csv",
    ["start_x", "end_x", "run_length"],
    runs
)

write_csv(
    OUT / "persistence_run_length_frequency.csv",
    ["run_length", "frequency"],
    sorted(run_frequency.items())
)

# ---------------------------------------------------------
# 2. CORRELACIÓN ESPACIAL
# Autocorrelación binaria para diferentes distancias.
# Se calcula sobre el intervalo completo del snapshot.
# ---------------------------------------------------------

occupied = set(cells)
lags = [1, 2, 3, 4, 5, 8, 10, 16, 20, 32, 50, 64, 100, 128]

density = len(cells) / span
correlations = []

for lag in lags:
    if lag >= span:
        continue

    pairs = span - lag
    joint = sum(
        1 for x in cells
        if x + lag <= maximum and x + lag in occupied
    )

    joint_probability = joint / pairs
    denominator = density * (1 - density)

    if denominator:
        correlation = (
            joint_probability - density * density
        ) / denominator
    else:
        correlation = None

    correlations.append((
        lag,
        joint,
        pairs,
        joint_probability,
        correlation
    ))

write_csv(
    OUT / "spatial_autocorrelation.csv",
    ["lag", "joint_occupied_pairs", "total_pairs",
     "joint_probability", "binary_correlation"],
    correlations
)

# ---------------------------------------------------------
# 3. FRAGMENTACIÓN
# Distribución actual de componentes y métricas históricas.
# ---------------------------------------------------------

gap_frequency = Counter(gaps)

write_csv(
    OUT / "fragmentation_gap_frequency.csv",
    ["empty_gap_length", "frequency"],
    sorted(gap_frequency.items())
)

write_csv(
    OUT / "fragmentation_components.csv",
    ["component_start", "component_end", "component_size"],
    runs
)

# ---------------------------------------------------------
# 4. DINÁMICA TEMPORAL
# Tendencias de observaciones agregadas.
# ---------------------------------------------------------

temporal = []

for record in history:
    gen = get_number(record, "generation")
    active = get_number(record, "active", "active_cells")
    comp = get_number(record, "components")
    spatial_span = get_number(record, "span")

    if gen is None:
        continue

    temporal.append((
        gen,
        active,
        comp,
        spatial_span
    ))

temporal.sort(key=lambda x: x[0])

write_csv(
    OUT / "temporal_dynamics.csv",
    ["generation", "active_cells", "components", "span"],
    temporal
)

def trend(values):
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return None

    return {
        "first": values[0],
        "last": values[-1],
        "absolute_change": values[-1] - values[0],
        "relative_change_percent": (
            (values[-1] - values[0]) / values[0] * 100
            if values[0] != 0 else None
        ),
        "minimum": min(values),
        "maximum": max(values),
        "mean": statistics.fmean(values)
    }

active_values = [r[1] for r in temporal if r[1] is not None]
component_values = [r[2] for r in temporal if r[2] is not None]
span_values = [r[3] for r in temporal if r[3] is not None]

report = {
    "experiment": "DSHADOW-CELLS-002",
    "snapshot_generation": generation,
    "snapshot_active_cells": len(cells),
    "snapshot_unique_cells": len(cells) == len(data["active"]),
    "snapshot_min_x": minimum,
    "snapshot_max_x": maximum,
    "snapshot_span": span,
    "snapshot_components": components,
    "snapshot_occupancy_percent": density * 100,

    "persistence_structural": {
        "component_count": len(runs),
        "mean_component_length": statistics.fmean(run_lengths),
        "median_component_length": statistics.median(run_lengths),
        "maximum_component_length": max(run_lengths),
        "maximum_component_length_frequency": run_frequency[
            max(run_lengths)
        ],
        "temporal_cell_identity_tracking_available": False
    },

    "spatial_correlation": {
        "method": "binary occupancy autocorrelation",
        "density": density,
        "lags": [
            {
                "lag": r[0],
                "joint_probability": r[3],
                "correlation": r[4]
            }
            for r in correlations
        ]
    },

    "fragmentation": {
        "component_count": components,
        "nonzero_gaps": sum(g > 0 for g in gaps),
        "mean_gap": statistics.fmean(gaps) if gaps else 0,
        "maximum_gap": max(gaps) if gaps else 0,
        "gap_frequency": dict(sorted(gap_frequency.items())),
        "historical_component_lineage_available": False
    },

    "temporal_dynamics": {
        "historical_records": len(temporal),
        "generation": trend([r[0] for r in temporal]),
        "active_cells": trend(active_values),
        "components": trend(component_values),
        "span": trend(span_values)
    },

    "limitations": [
        "Historical observations are aggregate metrics, not complete cell configurations.",
        "Cell-by-cell survival cannot be reconstructed from aggregate history.",
        "Component births, deaths, mergers and splits cannot be assigned individual lineages.",
        "Spatial autocorrelation describes this snapshot, not the complete temporal process.",
        "This analysis does not establish biological life, sentience or agency."
    ]
}

(OUT / "four_line_research_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n=== DSHADOW: FOUR-LINE RESEARCH ===")
print(f"Snapshot generation:       {generation}")
print(f"Active cells:               {len(cells):,}")
print(f"Components:                 {components:,}")
print(f"Mean component length:      {statistics.fmean(run_lengths):.4f}")
print(f"Maximum component length:   {max(run_lengths)}")
print(f"Mean empty gap:             {statistics.fmean(gaps):.4f}")
print(f"Maximum empty gap:          {max(gaps)}")
print(f"Spatial density:            {density * 100:.6f}%")
print(f"Autocorrelation lags:       {len(correlations)}")
print(f"Historical observations:    {len(temporal):,}")

print("\n=== TEMPORAL TRENDS ===")
for name, values in [
    ("Active cells", active_values),
    ("Components", component_values),
    ("Spatial span", span_values)
]:
    result = trend(values)
    print(f"\n{name}:")
    print(json.dumps(result, indent=2))

print(f"\nResearch output: {OUT}")
print("Original snapshot and engine files were not modified.")
