import json
import csv
import hashlib
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
SNAPSHOT = BASE / "live_snapshot.json"

PERIOD = 160
MAX_LAG = 300

raw = SNAPSHOT.read_bytes()
snapshot_hash = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

if int(data["rule"]) != 110:
    raise ValueError("El snapshot no corresponde a Rule 110.")

active = np.asarray(data["active"], dtype=np.int64)
active.sort()

if len(active) == 0:
    raise ValueError("Snapshot sin células activas.")

if len(np.unique(active)) != len(active):
    raise ValueError("Se encontraron coordenadas duplicadas.")

minimum = int(active[0])
maximum = int(active[-1])
span = maximum - minimum + 1

state = np.zeros(span, dtype=np.uint8)
state[active - minimum] = 1

def matching_runs(mask):
    indexes = np.flatnonzero(mask)

    if len(indexes) == 0:
        return []

    cuts = np.where(np.diff(indexes) > 1)[0] + 1
    groups = np.split(indexes, cuts)

    return [
        (
            int(group[0]),
            int(group[-1]),
            len(group)
        )
        for group in groups
    ]

# Análisis principal: lag 160.
left = state[:-PERIOD]
right = state[PERIOD:]

match_mask = left == right
mismatch_mask = ~match_mask

match_count = int(np.count_nonzero(match_mask))
mismatch_count = int(np.count_nonzero(mismatch_mask))
comparisons = len(match_mask)

exact_runs = matching_runs(match_mask)
mismatch_runs = matching_runs(mismatch_mask)

longest_exact = max(
    exact_runs,
    key=lambda r: r[2],
    default=None
)

longest_mismatch = max(
    mismatch_runs,
    key=lambda r: r[2],
    default=None
)

# Búsqueda de períodos espaciales entre 1 y 300.
lag_results = []

for lag in range(1, MAX_LAG + 1):
    mask = state[:-lag] == state[lag:]

    lag_results.append({
        "lag": lag,
        "comparisons": len(mask),
        "matches": int(np.count_nonzero(mask)),
        "mismatches": int(np.count_nonzero(~mask)),
        "match_rate": float(np.mean(mask))
    })

lag_results.sort(
    key=lambda row: row["match_rate"],
    reverse=True
)

with (BASE / "period_search_001_300.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(lag_results[0])
    )
    writer.writeheader()
    writer.writerows(lag_results)

# Guardar segmentos exactos de lag 160.
with (BASE / "exact_segments_lag160.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = [
        "start_coordinate",
        "end_coordinate",
        "length"
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for start, end, length in exact_runs:
        writer.writerow({
            "start_coordinate": minimum + start,
            "end_coordinate": minimum + end,
            "length": length
        })

report = {
    "experiment": "025_LIVE_PERIODICITY_REVALIDATION",
    "rule": data["rule"],
    "generation": data["generation"],
    "active_cells": len(active),
    "minimum_coordinate": minimum,
    "maximum_coordinate": maximum,
    "spatial_span": span,
    "density": float(len(active) / span),
    "tested_period": PERIOD,
    "comparisons": comparisons,
    "matches": match_count,
    "mismatches": mismatch_count,
    "match_rate": float(match_count / comparisons),
    "exact_segment_count": len(exact_runs),
    "mismatch_segment_count": len(mismatch_runs),
    "longest_exact_segment": (
        {
            "start": minimum + longest_exact[0],
            "end": minimum + longest_exact[1],
            "length": longest_exact[2]
        } if longest_exact else None
    ),
    "longest_mismatch_segment": (
        {
            "start": minimum + longest_mismatch[0],
            "end": minimum + longest_mismatch[1],
            "length": longest_mismatch[2]
        } if longest_mismatch else None
    ),
    "top_10_lags": lag_results[:10],
    "snapshot_sha256": snapshot_hash
}

with (BASE / "experiment_025_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

# Verificación de integridad de la copia analizada.
hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if snapshot_hash != hash_after:
    raise RuntimeError("La copia del snapshot cambió durante el análisis.")

print("\n=== DSHADOW | EXPERIMENTO 025 ===")
print("Rule:", data["rule"])
print("Generation:", data["generation"])
print("Active cells:", len(active))
print("Spatial span:", span)

print("\nLAG 160")
print("Comparisons:", comparisons)
print("Matches:", match_count)
print("Mismatches:", mismatch_count)
print("Match rate:", report["match_rate"])
print("Exact segments:", len(exact_runs))
print("Mismatch segments:", len(mismatch_runs))
print("Longest exact segment:", longest_exact)

print("\nTOP 10 SPATIAL LAGS")

for row in lag_results[:10]:
    print(row)

print("\nINTEGRITY")
print("SHA256:", snapshot_hash)
print("Integrity:", snapshot_hash == hash_after)

print("\nExperiment 025 completed.")
