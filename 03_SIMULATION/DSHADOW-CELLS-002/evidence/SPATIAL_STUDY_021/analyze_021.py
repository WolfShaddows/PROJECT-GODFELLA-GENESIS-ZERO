import json
import csv
import hashlib
from pathlib import Path

import numpy as np

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json"
)

OUT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_021"
)

TARGET_LAG = 160
MAX_LAG = 300
MIN_RUN = 1000

raw = SNAPSHOT.read_bytes()
hash_before = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

active = np.asarray(data["active"], dtype=np.int64)
active.sort()

if len(np.unique(active)) != len(active):
    raise ValueError("Se encontraron coordenadas duplicadas.")

minimum = int(active[0])
maximum = int(active[-1])
span = maximum - minimum + 1

x = np.zeros(span, dtype=np.uint8)
x[active - minimum] = 1

def match_rate(values, lag):
    return float(np.mean(values[:-lag] == values[lag:]))

def pearson_lag(values, lag):
    a = values[:-lag].astype(np.float64)
    b = values[lag:].astype(np.float64)

    a -= a.mean()
    b -= b.mean()

    denominator = np.sqrt(np.dot(a, a) * np.dot(b, b))

    if denominator == 0:
        return None

    return float(np.dot(a, b) / denominator)

def true_runs(mask):
    padded = np.concatenate(([False], mask, [False]))
    changes = np.diff(padded.astype(np.int8))

    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]

    return [
        (int(start), int(end), int(end - start))
        for start, end in zip(starts, ends)
    ]

# -------------------------------------------------
# 1. Localizar todas las coincidencias a lag 160.
# -------------------------------------------------

equal160 = (x[:-TARGET_LAG] == x[TARGET_LAG:])
runs = true_runs(equal160)

run_records = []

for start, end, length in runs:
    if length >= MIN_RUN:
        run_records.append({
            "start_coordinate": minimum + start,
            "end_coordinate": minimum + end - 1,
            "paired_start_coordinate": minimum + start + TARGET_LAG,
            "paired_end_coordinate": minimum + end - 1 + TARGET_LAG,
            "length": length
        })

run_records.sort(key=lambda r: r["length"], reverse=True)

with (OUT / "period160_segments.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = [
        "start_coordinate",
        "end_coordinate",
        "paired_start_coordinate",
        "paired_end_coordinate",
        "length"
    ]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(run_records)

# -------------------------------------------------
# 2. Localizar las rupturas.
# -------------------------------------------------

mismatch = np.where(~equal160)[0]

ruptures = []

for index in mismatch:
    i = int(index)
    ruptures.append({
        "coordinate": minimum + i,
        "paired_coordinate": minimum + i + TARGET_LAG,
        "left_state": int(x[i]),
        "right_state": int(x[i + TARGET_LAG])
    })

with (OUT / "period160_ruptures.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = [
        "coordinate",
        "paired_coordinate",
        "left_state",
        "right_state"
    ]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(ruptures)

# -------------------------------------------------
# 3. Buscar períodos alternativos de 1 a 300.
# -------------------------------------------------

period_results = []

for lag in range(1, MAX_LAG + 1):
    period_results.append({
        "lag": lag,
        "match_rate": match_rate(x, lag),
        "pearson": pearson_lag(x, lag)
    })

period_results.sort(
    key=lambda r: r["match_rate"],
    reverse=True
)

with (OUT / "period_search_001_300.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = ["lag", "match_rate", "pearson"]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(period_results)

# -------------------------------------------------
# 4. Comprobar repetición literal de bloques.
# -------------------------------------------------

block_size = TARGET_LAG
complete_blocks = span // block_size

reference = x[:block_size]
block_comparisons = []

for block_index in range(1, complete_blocks):
    start = block_index * block_size
    candidate = x[start:start + block_size]

    matches = int(np.count_nonzero(reference == candidate))

    block_comparisons.append({
        "reference_block": 0,
        "compared_block": block_index,
        "start_coordinate": minimum + start,
        "end_coordinate": minimum + start + block_size - 1,
        "matching_bits": matches,
        "block_size": block_size,
        "match_rate": matches / block_size,
        "identical": bool(matches == block_size)
    })

with (OUT / "literal_160_block_comparison.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = list(block_comparisons[0])
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(block_comparisons)

# -------------------------------------------------
# 5. Resumen.
# -------------------------------------------------

best_periods = period_results[:20]

report = {
    "experiment": "021_PERIODICITY_BOUNDARY_MAPPING",
    "rule": data["rule"],
    "generation": data["generation"],
    "active_cells": len(active),
    "span": span,
    "density": float(x.mean()),
    "target_lag": TARGET_LAG,
    "compared_pairs": len(equal160),
    "matching_pairs": int(equal160.sum()),
    "mismatching_pairs": int((~equal160).sum()),
    "match_rate_160": float(equal160.mean()),
    "total_equal_segments": len(runs),
    "segments_at_least_1000": len(run_records),
    "longest_equal_segment": max(
        (r[2] for r in runs), default=0
    ),
    "total_ruptures": len(ruptures),
    "first_rupture": ruptures[0] if ruptures else None,
    "last_rupture": ruptures[-1] if ruptures else None,
    "longest_segments": run_records[:20],
    "best_periods_1_300": best_periods,
    "literal_block_comparisons": {
        "block_size": block_size,
        "complete_blocks": complete_blocks,
        "identical_blocks": sum(
            b["identical"] for b in block_comparisons
        ),
        "total_compared_blocks": len(block_comparisons)
    },
    "snapshot_sha256": hash_before
}

with (OUT / "experiment_021_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot original cambió.")

print("\n=== DSHADOW | EXPERIMENTO 021 ===")
print("Generation:", data["generation"])
print("Span:", span)
print("Density:", round(float(x.mean()), 9))

print("\nPERIOD 160")
print("Matching pairs:", int(equal160.sum()))
print("Mismatching pairs:", len(ruptures))
print("Match rate:", round(float(equal160.mean()), 9))
print("Total equal segments:", len(runs))
print("Segments >= 1000:", len(run_records))
print("Longest equal segment:", max((r[2] for r in runs), default=0))

print("\nLONGEST SEGMENTS")
for r in run_records[:20]:
    print(r)

print("\nFIRST 30 RUPTURES")
for r in ruptures[:30]:
    print(r)

print("\nBEST PERIODS 1-300")
for r in best_periods:
    print(r)

print("\nLITERAL 160-BLOCK COMPARISON")
print(report["literal_block_comparisons"])

print("\nSHA256 before:", hash_before)
print("SHA256 after:", hash_after)
print("Integrity:", hash_before == hash_after)

print("\nExperiment 021 completed.")
