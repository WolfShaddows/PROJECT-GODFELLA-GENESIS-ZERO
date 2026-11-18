import numpy as np
import json
import csv
import hashlib
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPACETIME_038_20261106_102543\038_spacetime_matrix.npz")
SNAPSHOT = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\DEEP_UNIVERSE_035_20261106_084957\frozen_universe.json")

SHIFTS = [-4, -1, 0, 1]
TILE_SIZE = 256
LUT = np.array([0, 1, 1, 1, 0, 1, 1, 0], dtype=np.uint8)

start = time.time()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def compare(a, b, shift):
    if shift > 0:
        x, y = a[:-shift], b[shift:]
    elif shift < 0:
        x, y = a[-shift:], b[:shift]
    else:
        x, y = a, b

    equal = (x == y)
    equality = float(np.mean(equal))

    xf = x.astype(np.float64)
    yf = y.astype(np.float64)

    sx = xf.std()
    sy = yf.std()

    if sx == 0 or sy == 0:
        phi = None
    else:
        phi = float(np.mean((xf - xf.mean()) * (yf - yf.mean())) / (sx * sy))

    return equality, phi, x, y

def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

print("=" * 72)
print("EXPERIMENT 040 - ANOMALY FORENSICS")
print("=" * 72)

print("\n[1] Loading original spacetime matrix...")

data = np.load(SOURCE, allow_pickle=False)

candidates = []

for key in data.files:
    arr = data[key]
    print(f"  NPZ key={key}, shape={arr.shape}, dtype={arr.dtype}")

    if arr.ndim == 2 and arr.shape == (501, 8192):
        candidates.append((key, arr))

if len(candidates) != 1:
    raise RuntimeError(
        f"Expected exactly one matrix with shape (501,8192); found {len(candidates)}"
    )

matrix_key, matrix = candidates[0]
matrix = np.asarray(matrix, dtype=np.uint8)

if not np.isin(matrix, [0, 1]).all():
    raise RuntimeError("Matrix contains values other than 0 and 1.")

T, W = matrix.shape

print(f"\nMatrix: {T} generations x {W} positions")
print(f"Source SHA256: {sha256(SOURCE)}")

print("\n[2] Checking Rule 110 evolution...")

rule_errors = 0
rule_checked = 0

for t in range(T - 1):
    a = matrix[t]
    expected = (
        (a[:-2] << 2) |
        (a[1:-1] << 1) |
        a[2:]
    )

    expected = LUT[expected]

    actual = matrix[t + 1, 1:-1]

    errors = int(np.count_nonzero(expected != actual))

    rule_errors += errors
    rule_checked += len(actual)

print(f"Rule110 checked cells: {rule_checked:,}")
print(f"Rule110 errors: {rule_errors:,}")
print(f"Rule110 error rate: {rule_errors / rule_checked:.12f}")

print("\n[3] Transition-by-transition correlations...")

transition_rows = []
mismatch_rows = []
local_rows = []

for t in range(T - 1):
    a = matrix[t]
    b = matrix[t + 1]

    for shift in SHIFTS:
        equality, phi, x, y = compare(a, b, shift)

        transition_rows.append({
            "transition": t,
            "shift": shift,
            "equality": equality,
            "phi": phi,
            "compared_cells": len(x),
            "mismatches": int(np.count_nonzero(x != y))
        })

        if shift == -4:
            mismatch = np.flatnonzero(x != y)

            for idx in mismatch:
                position = int(idx + 4)

                mismatch_rows.append({
                    "transition": t,
                    "matrix_index": position,
                    "source_value": int(a[position]),
                    "next_value_at_shift": int(b[position - 4])
                })

    # Local analysis: tiles of 256 positions.
    for tile_start in range(0, W, TILE_SIZE):
        tile_end = min(tile_start + TILE_SIZE, W)

        for shift in SHIFTS:
            equality, phi, x, y = compare(
                a[tile_start:tile_end],
                b[tile_start:tile_end],
                shift
            )

            local_rows.append({
                "transition": t,
                "tile": tile_start // TILE_SIZE,
                "start": tile_start,
                "end": tile_end,
                "shift": shift,
                "equality": equality,
                "phi": phi,
                "mismatches": int(np.count_nonzero(x != y))
            })

    if (t + 1) % 100 == 0:
        print(f"  Processed {t + 1}/{T - 1} transitions")

print("\n[4] Aggregating local behavior...")

aggregate_rows = []

for tile in sorted(set(r["tile"] for r in local_rows)):
    for shift in SHIFTS:
        subset = [
            r for r in local_rows
            if r["tile"] == tile and r["shift"] == shift
        ]

        values = np.array([r["equality"] for r in subset])

        aggregate_rows.append({
            "tile": tile,
            "start": subset[0]["start"],
            "end": subset[0]["end"],
            "shift": shift,
            "mean_equality": float(values.mean()),
            "min_equality": float(values.min()),
            "max_equality": float(values.max()),
            "std_equality": float(values.std()),
            "total_mismatches": int(sum(r["mismatches"] for r in subset))
        })

print("\n[5] Saving evidence...")

write_csv(
    ROOT / "040_transition_correlations.csv",
    transition_rows,
    ["transition", "shift", "equality", "phi", "compared_cells", "mismatches"]
)

write_csv(
    ROOT / "040_local_transition_analysis.csv",
    local_rows,
    ["transition", "tile", "start", "end", "shift", "equality", "phi", "mismatches"]
)

write_csv(
    ROOT / "040_local_aggregate.csv",
    aggregate_rows,
    ["tile", "start", "end", "shift", "mean_equality",
     "min_equality", "max_equality", "std_equality", "total_mismatches"]
)

write_csv(
    ROOT / "040_shift_minus4_mismatches.csv",
    mismatch_rows,
    ["transition", "matrix_index", "source_value", "next_value_at_shift"]
)

summary = {}

for shift in SHIFTS:
    subset = [r for r in transition_rows if r["shift"] == shift]

    eq = np.array([r["equality"] for r in subset])
    phis = [r["phi"] for r in subset if r["phi"] is not None]

    summary[str(shift)] = {
        "mean_equality": float(eq.mean()),
        "min_equality": float(eq.min()),
        "max_equality": float(eq.max()),
        "std_equality": float(eq.std()),
        "mean_phi": float(np.mean(phis)) if phis else None,
        "total_mismatches": int(sum(r["mismatches"] for r in subset))
    }

minus4 = [r for r in transition_rows if r["shift"] == -4]

best = sorted(
    minus4,
    key=lambda r: r["equality"],
    reverse=True
)

report = {
    "experiment": "040_ANOMALY_FORENSICS",
    "source_matrix": str(SOURCE),
    "matrix_key": matrix_key,
    "matrix_shape": [int(T), int(W)],
    "rule110": {
        "checked_cells": rule_checked,
        "errors": rule_errors,
        "error_rate": rule_errors / rule_checked
    },
    "shift_summary": summary,
    "minus4": {
        "transitions": len(minus4),
        "mismatch_records": len(mismatch_rows),
        "best_10_transitions": best[:10],
        "worst_10_transitions": sorted(
            minus4, key=lambda r: r["equality"]
        )[:10]
    },
    "tile_size": TILE_SIZE,
    "snapshot_sha256": sha256(SNAPSHOT),
    "matrix_sha256": sha256(SOURCE),
    "runtime_seconds": round(time.time() - start, 3)
}

with open(ROOT / "040_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\n" + "=" * 72)
print("EXPERIMENT 040 SUMMARY")
print("=" * 72)

for shift in SHIFTS:
    s = summary[str(shift)]
    print(
        f"Shift {shift:+}: "
        f"mean equality={s['mean_equality']:.6f} | "
        f"mean phi={s['mean_phi']} | "
        f"mismatches={s['total_mismatches']:,}"
    )

print(f"\nRule110 errors: {rule_errors:,}")
print(f"Shift -4 mismatch records: {len(mismatch_rows):,}")
print(f"Runtime: {report['runtime_seconds']} seconds")
print("\nEvidence saved in:", ROOT)
print("Snapshot SHA256:", report["snapshot_sha256"])
print("Matrix SHA256:", report["matrix_sha256"])
print("\nEXPERIMENT 040 COMPLETED")
