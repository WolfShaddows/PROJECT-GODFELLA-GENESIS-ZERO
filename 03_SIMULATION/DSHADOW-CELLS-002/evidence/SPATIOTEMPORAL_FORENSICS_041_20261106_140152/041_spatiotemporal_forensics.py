import numpy as np
import json
import csv
import hashlib
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ============================================================
# PROJECT GODFELLA
# EXPERIMENT 041 - SPATIOTEMPORAL ANOMALY FORENSICS
# ============================================================

ROOT = Path(__file__).resolve().parent

SOURCE = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION"
    r"\DSHADOW-CELLS-002\evidence\SPACETIME_038_20261106_102543"
    r"\038_spacetime_matrix.npz"
)

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION"
    r"\DSHADOW-CELLS-002\evidence\DEEP_UNIVERSE_035_20261106_084957"
    r"\frozen_universe.json"
)

LUT = np.array(
    [0, 1, 1, 1, 0, 1, 1, 0],
    dtype=np.uint8
)

TILE_SIZE = 256
SHIFT = -4

start_time = time.time()

# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------

def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024), b""
        ):
            h.update(chunk)

    return h.hexdigest()


def save_csv(filename, rows, fields):

    with open(
        ROOT / filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


def safe_phi(a, b):

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    if a.size == 0:
        return None

    if a.std() == 0 or b.std() == 0:
        return None

    return float(
        np.mean(
            (a - a.mean()) *
            (b - b.mean())
        ) / (a.std() * b.std())
    )


def comparison(a, b, shift):

    if shift > 0:
        x = a[:-shift]
        y = b[shift:]

    elif shift < 0:
        x = a[-shift:]
        y = b[:shift]

    else:
        x = a
        y = b

    mismatch = x != y

    return {
        "equality": float(np.mean(~mismatch)),
        "phi": safe_phi(x, y),
        "mismatches": int(np.count_nonzero(mismatch)),
        "compared": int(x.size)
    }


# ------------------------------------------------------------
# LOAD ORIGINAL MATRIX
# ------------------------------------------------------------

print("=" * 72)
print("EXPERIMENT 041 - SPATIOTEMPORAL ANOMALY FORENSICS")
print("=" * 72)

print("\n[1] Loading original matrix...")

data = np.load(
    SOURCE,
    allow_pickle=False
)

matrix_candidates = []

for key in data.files:

    arr = data[key]

    print(
        f"NPZ: {key} | "
        f"shape={arr.shape} | "
        f"dtype={arr.dtype}"
    )

    if arr.ndim == 2 and arr.shape == (501, 8192):
        matrix_candidates.append((key, arr))

if len(matrix_candidates) != 1:

    raise RuntimeError(
        "Expected exactly one matrix with shape (501,8192)."
    )

matrix_key, matrix = matrix_candidates[0]

matrix = np.asarray(
    matrix,
    dtype=np.uint8
)

if not np.isin(matrix, [0, 1]).all():

    raise RuntimeError(
        "Invalid matrix: values other than 0 and 1."
    )

T, W = matrix.shape

print(f"\nMatrix dimensions: {T} x {W}")
print(f"Matrix SHA256: {sha256(SOURCE)}")

# ------------------------------------------------------------
# RULE 110 VALIDATION
# ------------------------------------------------------------

print("\n[2] Validating Rule 110...")

rule_errors = 0
rule_checked = 0

for t in range(T - 1):

    row = matrix[t]

    neighborhoods = (
        (row[:-2] << 2) |
        (row[1:-1] << 1) |
        row[2:]
    )

    expected = LUT[neighborhoods]

    actual = matrix[t + 1, 1:-1]

    rule_errors += int(
        np.count_nonzero(expected != actual)
    )

    rule_checked += actual.size

rule_error_rate = rule_errors / rule_checked

print(f"Checked cells: {rule_checked:,}")
print(f"Errors: {rule_errors:,}")
print(f"Error rate: {rule_error_rate:.12f}")

# ------------------------------------------------------------
# RECONSTRUCT SHIFT -4 ANOMALY MASK
#
# The original 040 convention compares:
#
# a[4:] against b[:-4]
#
# The resulting mask uses source coordinates x=4..W-1.
# ------------------------------------------------------------

print("\n[3] Reconstructing anomaly mask...")

M = np.zeros(
    (T - 1, W),
    dtype=np.uint8
)

for t in range(T - 1):

    a = matrix[t]
    b = matrix[t + 1]

    M[t, 4:] = (
        a[4:] != b[:-4]
    ).astype(np.uint8)

total_mismatches = int(M.sum())

print(
    f"Anomaly mask dimensions: {M.shape}"
)

print(
    f"Total mismatches: {total_mismatches:,}"
)

# ------------------------------------------------------------
# SHIFT COMPARISON
# ------------------------------------------------------------

print("\n[4] Comparing temporal shifts...")

shift_rows = []

for shift in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:

    values = []

    for t in range(T - 1):

        result = comparison(
            matrix[t],
            matrix[t + 1],
            shift
        )

        values.append(result)

    equality = np.array(
        [v["equality"] for v in values]
    )

    phis = [
        v["phi"]
        for v in values
        if v["phi"] is not None
    ]

    shift_rows.append({

        "shift": shift,

        "mean_equality": float(equality.mean()),

        "min_equality": float(equality.min()),

        "max_equality": float(equality.max()),

        "std_equality": float(equality.std()),

        "mean_phi": (
            float(np.mean(phis))
            if phis else None
        ),

        "total_mismatches": int(
            sum(v["mismatches"] for v in values)
        )
    })

save_csv(
    "041_shift_comparison.csv",
    shift_rows,
    list(shift_rows[0].keys())
)

# ------------------------------------------------------------
# SPATIAL SECTOR ANALYSIS
# ------------------------------------------------------------

print("\n[5] Analyzing spatial sectors...")

sector_count = (W + TILE_SIZE - 1) // TILE_SIZE

sector_rows = []

sector_masks = []

for sector in range(sector_count):

    left = sector * TILE_SIZE
    right = min(left + TILE_SIZE, W)

    local = M[:, left:right]

    count = int(local.sum())

    possible = local.size

    active_generations = int(
        np.count_nonzero(local.sum(axis=1))
    )

    active_positions = int(
        np.count_nonzero(local.sum(axis=0))
    )

    generation_counts = local.sum(axis=1)

    position_counts = local.sum(axis=0)

    first_generation = None
    last_generation = None

    active_times = np.flatnonzero(
        generation_counts
    )

    if active_times.size:

        first_generation = int(
            active_times[0]
        )

        last_generation = int(
            active_times[-1]
        )

    sector_masks.append(local.copy())

    sector_rows.append({

        "sector": sector,

        "start": left,

        "end": right,

        "mismatches": count,

        "equality": (
            1.0 - count / possible
        ),

        "active_generations": active_generations,

        "active_positions": active_positions,

        "first_generation": first_generation,

        "last_generation": last_generation,

        "mean_per_generation": float(
            generation_counts.mean()
        ),

        "max_per_generation": int(
            generation_counts.max()
        ),

        "max_per_position": int(
            position_counts.max()
        )
    })

save_csv(
    "041_sector_analysis.csv",
    sector_rows,
    list(sector_rows[0].keys())
)

# ------------------------------------------------------------
# EXACT TILE SIGNATURE COMPARISON
# ------------------------------------------------------------

print("\n[6] Comparing complete sector signatures...")

signature_rows = []

for i in range(sector_count):

    for j in range(i + 1, sector_count):

        a = sector_masks[i]
        b = sector_masks[j]

        if a.shape != b.shape:
            continue

        equal_cells = int(
            np.count_nonzero(a == b)
        )

        total = a.size

        equality = equal_cells / total

        if equality >= 0.90:

            signature_rows.append({

                "sector_a": i,

                "sector_b": j,

                "offset": (
                    j - i
                ) * TILE_SIZE,

                "exact_equality": equality,

                "mismatch_a": int(a.sum()),

                "mismatch_b": int(b.sum()),

                "exact_match": bool(
                    np.array_equal(a, b)
                )
            })

save_csv(
    "041_sector_signature_matches.csv",
    signature_rows,
    [
        "sector_a",
        "sector_b",
        "offset",
        "exact_equality",
        "mismatch_a",
        "mismatch_b",
        "exact_match"
    ]
)

# ------------------------------------------------------------
# SPATIAL PERIODICITY OF MISMATCH MASK
# ------------------------------------------------------------

print("\n[7] Searching spatial periodicity...")

spatial_profile = M.sum(axis=0).astype(
    np.float64
)

spatial_rows = []

for lag in range(1, W // 2):

    a = spatial_profile[:-lag]
    b = spatial_profile[lag:]

    if np.std(a) == 0 or np.std(b) == 0:
        phi = None
    else:
        phi = safe_phi(a, b)

    denominator = np.sum(
        np.maximum(a, b)
    )

    numerator = np.sum(
        np.minimum(a, b)
    )

    overlap = (
        float(numerator / denominator)
        if denominator > 0
        else None
    )

    if (
        phi is not None and
        (abs(phi) >= 0.50 or
         (overlap is not None and overlap >= 0.50))
    ):

        spatial_rows.append({

            "lag": lag,

            "phi": phi,

            "profile_overlap": overlap
        })

save_csv(
    "041_spatial_periodicity.csv",
    spatial_rows,
    [
        "lag",
        "phi",
        "profile_overlap"
    ]
)

# ------------------------------------------------------------
# EXPLICIT TEST OF 6400-POSITION OFFSET
# ------------------------------------------------------------

print("\n[8] Testing the 6400-position hypothesis...")

offset_tests = []

for offset in [
    256,
    512,
    1024,
    2048,
    4096,
    6144,
    6400,
    6656,
    7168
]:

    if offset >= W:
        continue

    a = M[:, :-offset]
    b = M[:, offset:]

    exact = int(
        np.count_nonzero(a == b)
    )

    total = a.size

    union = int(
        np.count_nonzero((a != 0) | (b != 0))
    )

    intersection = int(
        np.count_nonzero((a != 0) & (b != 0))
    )

    jaccard = (
        intersection / union
        if union else None
    )

    offset_tests.append({

        "offset": offset,

        "compared_cells": total,

        "exact_equality": exact / total,

        "mismatch_mask_jaccard": jaccard,

        "mismatches_a": int(a.sum()),

        "mismatches_b": int(b.sum())
    })

save_csv(
    "041_offset_hypothesis.csv",
    offset_tests,
    list(offset_tests[0].keys())
)

# ------------------------------------------------------------
# TEMPORAL ANALYSIS
# ------------------------------------------------------------

print("\n[9] Temporal anomaly analysis...")

temporal_rows = []

generation_counts = M.sum(axis=1)

for t in range(T - 1):

    positions = np.flatnonzero(M[t])

    temporal_rows.append({

        "generation": t,

        "mismatches": int(
            generation_counts[t]
        ),

        "first_position": (
            int(positions[0])
            if positions.size else None
        ),

        "last_position": (
            int(positions[-1])
            if positions.size else None
        ),

        "active_positions": int(
            positions.size
        )
    })

save_csv(
    "041_temporal_activity.csv",
    temporal_rows,
    list(temporal_rows[0].keys())
)

# Temporal recurrence of mismatch counts.

temporal_periods = []

for lag in range(1, (T - 1) // 2):

    a = generation_counts[:-lag].astype(
        np.float64
    )

    b = generation_counts[lag:].astype(
        np.float64
    )

    phi = safe_phi(a, b)

    temporal_periods.append({

        "lag": lag,

        "phi": phi
    })

save_csv(
    "041_temporal_recurrence.csv",
    temporal_periods,
    ["lag", "phi"]
)

# ------------------------------------------------------------
# CAUSAL CONTINUITY
#
# Compare anomaly masks between consecutive generations.
# This is NOT object tracking.
# It measures spatial overlap within the Rule110 radius.
# ------------------------------------------------------------

print("\n[10] Testing local causal continuity...")

causal_rows = []

for t in range(T - 2):

    previous = M[t]
    current = M[t + 1]

    for dx in [-1, 0, 1]:

        if dx > 0:

            a = previous[:-dx]
            b = current[dx:]

        elif dx < 0:

            a = previous[-dx:]
            b = current[:dx]

        else:

            a = previous
            b = current

        intersection = int(
            np.count_nonzero(
                (a != 0) & (b != 0)
            )
        )

        union = int(
            np.count_nonzero(
                (a != 0) | (b != 0)
            )
        )

        jaccard = (
            intersection / union
            if union else None
        )

        causal_rows.append({

            "transition": t,

            "dx": dx,

            "previous_anomalies": int(a.sum()),

            "current_anomalies": int(b.sum()),

            "intersection": intersection,

            "union": union,

            "jaccard": jaccard
        })

save_csv(
    "041_causal_overlap.csv",
    causal_rows,
    list(causal_rows[0].keys())
)

# ------------------------------------------------------------
# MISMATCH POSITION TRACKING
# ------------------------------------------------------------

print("\n[11] Exporting exact anomaly coordinates...")

coordinate_rows = []

for t in range(T - 1):

    positions = np.flatnonzero(M[t])

    for x in positions:

        coordinate_rows.append({

            "generation": t,

            "matrix_position": int(x),

            "source_value": int(matrix[t, x]),

            "next_value_at_x_minus_4": int(
                matrix[t + 1, x - 4]
            )
        })

save_csv(
    "041_anomaly_coordinates.csv",
    coordinate_rows,
    [
        "generation",
        "matrix_position",
        "source_value",
        "next_value_at_x_minus_4"
    ]
)

# ------------------------------------------------------------
# PLOTS
# ------------------------------------------------------------

print("\n[12] Generating visual evidence...")

plt.figure(figsize=(18, 8))

plt.imshow(
    M,
    aspect="auto",
    interpolation="nearest"
)

plt.title(
    "Experiment 041 - Spatiotemporal Anomaly Map"
)

plt.xlabel("Spatial position")
plt.ylabel("Generation")

plt.colorbar(
    label="Shift -4 mismatch"
)

plt.tight_layout()

plt.savefig(
    ROOT / "041_anomaly_heatmap.png",
    dpi=160
)

plt.close()

plt.figure(figsize=(16, 5))

plt.plot(
    spatial_profile
)

plt.title(
    "Spatial Distribution of Shift -4 Anomalies"
)

plt.xlabel("Spatial position")
plt.ylabel("Total mismatches")

plt.tight_layout()

plt.savefig(
    ROOT / "041_spatial_profile.png",
    dpi=160
)

plt.close()

plt.figure(figsize=(14, 5))

plt.plot(
    generation_counts
)

plt.title(
    "Temporal Anomaly Activity"
)

plt.xlabel("Generation")
plt.ylabel("Mismatch count")

plt.tight_layout()

plt.savefig(
    ROOT / "041_temporal_activity.png",
    dpi=160
)

plt.close()

plt.figure(figsize=(15, 6))

plt.imshow(
    matrix,
    aspect="auto",
    interpolation="nearest"
)

plt.title(
    "Original Rule110 Spacetime Matrix"
)

plt.xlabel("Spatial position")
plt.ylabel("Generation")

plt.tight_layout()

plt.savefig(
    ROOT / "041_original_spacetime.png",
    dpi=160
)

plt.close()

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n[13] Building final report...")

sector_sorted = sorted(
    sector_rows,
    key=lambda r: r["mismatches"],
    reverse=True
)

best_spatial = sorted(
    spatial_rows,
    key=lambda r: (
        abs(r["phi"])
        if r["phi"] is not None
        else 0
    ),
    reverse=True
)[:20]

best_temporal = sorted(
    temporal_periods,
    key=lambda r: (
        abs(r["phi"])
        if r["phi"] is not None
        else 0
    ),
    reverse=True
)[:20]

report = {

    "experiment": "041_SPATIOTEMPORAL_ANOMALY_FORENSICS",

    "matrix": {

        "key": matrix_key,

        "shape": [int(T), int(W)],

        "sha256": sha256(SOURCE)
    },

    "rule110_validation": {

        "checked_cells": int(rule_checked),

        "errors": int(rule_errors),

        "error_rate": float(rule_error_rate),

        "valid": bool(rule_errors == 0)
    },

    "anomaly": {

        "comparison": "row[t][x] != row[t+1][x-4]",

        "total_mismatches": total_mismatches,

        "generations": int(T - 1),

        "positions": int(W)
    },

    "sectors": {

        "tile_size": TILE_SIZE,

        "count": sector_count,

        "highest_mismatch_sectors": sector_sorted[:15]
    },

    "sector_signature_matches": signature_rows,

    "spatial_periodicity_candidates": best_spatial,

    "temporal_recurrence_candidates": best_temporal,

    "offset_hypothesis": offset_tests,

    "causal_overlap_summary": {

        str(dx): {

            "mean_jaccard": (

                float(np.mean([
                    r["jaccard"]
                    for r in causal_rows
                    if r["dx"] == dx
                    and r["jaccard"] is not None
                ]))

            )
        }

        for dx in [-1, 0, 1]
    },

    "snapshot_sha256": sha256(SNAPSHOT),

    "runtime_seconds": round(
        time.time() - start_time,
        3
    ),

    "interpretation_limits": [

        "A mismatch is not automatically a physical structure.",

        "Correlation does not establish object velocity.",

        "Causal overlap is not object identity.",

        "A repeated sector signature requires validation against raw configurations.",

        "The matrix is a finite observation window."
    ]
}

with open(
    ROOT / "041_final_report.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        report,
        f,
        indent=2
    )

# ------------------------------------------------------------
# FINAL OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 72)
print("EXPERIMENT 041 - FINAL RESULTS")
print("=" * 72)

print(f"Matrix: {T} x {W}")

print(
    f"Rule110 errors: {rule_errors:,}"
)

print(
    f"Anomaly mismatches: {total_mismatches:,}"
)

print("\nTop anomalous sectors:")

for item in sector_sorted[:10]:

    print(
        f"Sector {item['sector']:02d} | "
        f"positions {item['start']}-{item['end']} | "
        f"mismatches={item['mismatches']:,}"
    )

print("\nSector signature matches:")

for item in signature_rows[:20]:

    print(
        f"{item['sector_a']} -> {item['sector_b']} | "
        f"offset={item['offset']} | "
        f"equality={item['exact_equality']:.6f} | "
        f"exact={item['exact_match']}"
    )

print("\nSpatial periodicity candidates:")

for item in best_spatial[:10]:

    print(
        f"Lag {item['lag']} | "
        f"phi={item['phi']} | "
        f"overlap={item['profile_overlap']}"
    )

print("\nOffset hypothesis:")

for item in offset_tests:

    print(
        f"Offset {item['offset']} | "
        f"equality={item['exact_equality']:.6f} | "
        f"Jaccard={item['mismatch_mask_jaccard']}"
    )

print(
    f"\nRuntime: {report['runtime_seconds']} seconds"
)

print("\nEXPERIMENT 041 COMPLETED")

