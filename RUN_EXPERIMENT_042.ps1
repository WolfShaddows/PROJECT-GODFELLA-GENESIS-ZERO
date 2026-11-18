$ErrorActionPreference = "Stop"

# ============================================================
# EXPERIMENT 042
# THE 6400 OFFSET INVESTIGATION
#
# Offline forensic analysis.
# No engine restart.
# No simulation restart.
# No modification of frozen snapshot or source matrix.
# ============================================================

$Root = "C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002"

$MatrixPath = Join-Path $Root "evidence\SPACETIME_038_20261106_102543\038_spacetime_matrix.npz"

$SnapshotPath = Join-Path $Root "evidence\DEEP_UNIVERSE_035_20261106_084957\frozen_universe.json"

$SourceAnomalyReport = Join-Path $Root "evidence\SPATIOTEMPORAL_FORENSICS_041_20261106_140152\041_final_report.json"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$OutDir = Join-Path $Root "evidence\OFFSET_INVESTIGATION_042_$Timestamp"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$PythonScript = Join-Path $OutDir "042_offset_investigation.py"

$Transcript = Join-Path $OutDir "042_execution_transcript.txt"

Start-Transcript -Path $Transcript -Force | Out-Null

try {

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " EXPERIMENT 042 - THE 6400 OFFSET INVESTIGATION"
    Write-Host "============================================================"
    Write-Host ""

    if (-not (Test-Path $MatrixPath)) {
        throw "SOURCE MATRIX NOT FOUND: $MatrixPath"
    }

    if (-not (Test-Path $SnapshotPath)) {
        throw "FROZEN SNAPSHOT NOT FOUND: $SnapshotPath"
    }

    if (-not (Test-Path $SourceAnomalyReport)) {
        throw "EXPERIMENT 041 REPORT NOT FOUND: $SourceAnomalyReport"
    }

    $MatrixHashBefore = (Get-FileHash $MatrixPath -Algorithm SHA256).Hash
    $SnapshotHashBefore = (Get-FileHash $SnapshotPath -Algorithm SHA256).Hash

    Write-Host "[SOURCE] Matrix:"
    Write-Host $MatrixPath
    Write-Host ""

    Write-Host "[INTEGRITY] Matrix SHA256:"
    Write-Host $MatrixHashBefore
    Write-Host ""

    Write-Host "[INTEGRITY] Frozen snapshot SHA256:"
    Write-Host $SnapshotHashBefore
    Write-Host ""

    @'
import os
import json
import csv
import hashlib
import time
from pathlib import Path

import numpy as np

START = time.time()

MATRIX_PATH = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION"
    r"\DSHADOW-CELLS-002\evidence\SPACETIME_038_20261106_102543"
    r"\038_spacetime_matrix.npz"
)

OUT = Path(os.environ["GODFELLA_042_OUT"])
OUT.mkdir(parents=True, exist_ok=True)

TARGET_OFFSET = 6400
SECTOR_SIZE = 256
NEARBY_RADIUS = 256
NEARBY_STEP = 8
RANDOM_CONTROLS = 100
RANDOM_SEED = 42042

RULE110 = np.array([0, 1, 1, 1, 0, 1, 1, 0], dtype=np.uint8)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def scalar_from_npz(data, candidates):
    for key in candidates:
        if key in data.files:
            value = np.asarray(data[key]).reshape(-1)
            if value.size:
                return value[0].item()
    return None


def phi_binary(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()

    if a.size == 0:
        return None

    sa = a.std()
    sb = b.std()

    if sa == 0 or sb == 0:
        return None

    return float(np.corrcoef(a, b)[0, 1])


def binary_metrics(a, b):
    a = np.asarray(a, dtype=bool).ravel()
    b = np.asarray(b, dtype=bool).ravel()

    tp = int(np.count_nonzero(a & b))
    fp = int(np.count_nonzero(~a & b))
    fn = int(np.count_nonzero(a & ~b))
    tn = int(np.count_nonzero(~a & ~b))

    union = tp + fp + fn

    jaccard = tp / union if union else None
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    dice = (2 * tp) / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "jaccard": jaccard,
        "precision": precision,
        "recall": recall,
        "dice": dice,
        "exact_equal": bool(np.array_equal(a, b)),
        "total": int(a.size),
    }


def write_csv(path, rows):
    if not rows:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def validate_rule110(matrix):
    previous = matrix[:-1]
    current = matrix[1:]

    left = previous[:, :-2]
    center = previous[:, 1:-1]
    right = previous[:, 2:]

    index = (left << 2) | (center << 1) | right
    predicted = RULE110[index]

    observed = current[:, 1:-1]

    errors = int(np.count_nonzero(predicted != observed))
    total = int(observed.size)

    return {
        "checked": total,
        "errors": errors,
        "error_rate": errors / total if total else None,
        "valid": errors == 0,
    }


def anomaly_mask(matrix):
    # Exact definition used in experiment 041.
    #
    # M[t,x] = matrix[t,x] != matrix[t+1,x-4]
    #
    # The first four columns are excluded.

    mask = np.zeros(
        (matrix.shape[0] - 1, matrix.shape[1]),
        dtype=np.uint8
    )

    mask[:, 4:] = (
        matrix[:-1, 4:] != matrix[1:, :-4]
    ).astype(np.uint8)

    return mask


def offset_analysis(mask, offset):
    width = mask.shape[1]

    if offset <= 0 or offset >= width:
        raise ValueError("Invalid offset")

    a = mask[:, :-offset]
    b = mask[:, offset:]

    return binary_metrics(a, b)


def original_state_analysis(matrix, offset):
    a = matrix[:, :-offset]
    b = matrix[:, offset:]

    metrics = binary_metrics(a, b)

    metrics["raw_equality"] = float(np.mean(a == b))
    metrics["phi"] = phi_binary(a, b)

    return metrics


def per_generation_analysis(mask, offset):
    rows = []

    for t in range(mask.shape[0]):
        a = mask[t, :-offset]
        b = mask[t, offset:]

        m = binary_metrics(a, b)

        rows.append({
            "generation_index": t,
            "left_anomalies": int(a.sum()),
            "right_anomalies": int(b.sum()),
            "tp": m["tp"],
            "fp": m["fp"],
            "fn": m["fn"],
            "jaccard": m["jaccard"],
            "dice": m["dice"],
            "exact_equal": m["exact_equal"],
        })

    return rows


def temporal_signature_analysis(mask, offset):
    a = mask[:, :-offset]
    b = mask[:, offset:]

    # Each spatial coordinate has a temporal signature.
    equal_columns = np.all(a == b, axis=0)

    hamming = np.count_nonzero(a != b, axis=0)

    return {
        "positions_compared": int(a.shape[1]),
        "exact_temporal_signature_matches": int(equal_columns.sum()),
        "exact_temporal_signature_fraction": float(equal_columns.mean()),
        "mean_temporal_hamming_distance": float(hamming.mean()),
        "max_temporal_hamming_distance": int(hamming.max()),
        "min_temporal_hamming_distance": int(hamming.min()),
    }


def sector_analysis(mask):
    width = mask.shape[1]

    sectors = []

    for start in range(0, width, SECTOR_SIZE):
        end = min(start + SECTOR_SIZE, width)

        block = mask[:, start:end]

        sectors.append({
            "sector": start // SECTOR_SIZE,
            "start": start,
            "end": end,
            "width": end - start,
            "anomalies": int(block.sum()),
            "active_positions": int(np.count_nonzero(block.sum(axis=0))),
            "active_generations": int(np.count_nonzero(block.sum(axis=1))),
            "density": float(block.mean()),
        })

    return sectors


def pairwise_sector_analysis(mask):
    sectors = []

    for start in range(0, mask.shape[1], SECTOR_SIZE):
        end = min(start + SECTOR_SIZE, mask.shape[1])
        sectors.append(mask[:, start:end])

    results = []

    for i in range(len(sectors)):
        for j in range(i + 1, len(sectors)):

            a = sectors[i]
            b = sectors[j]

            if a.shape != b.shape:
                continue

            metrics = binary_metrics(a, b)

            results.append({
                "sector_a": i,
                "sector_b": j,
                "anomalies_a": int(a.sum()),
                "anomalies_b": int(b.sum()),
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "jaccard": metrics["jaccard"],
                "dice": metrics["dice"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "exact_equal": metrics["exact_equal"],
            })

    results.sort(
        key=lambda r: (
            -1 if r["jaccard"] is None else -r["jaccard"]
        )
    )

    return results


def nearby_offset_scan(mask):
    width = mask.shape[1]

    low = max(1, TARGET_OFFSET - NEARBY_RADIUS)
    high = min(width - 1, TARGET_OFFSET + NEARBY_RADIUS)

    rows = []

    for offset in range(low, high + 1, NEARBY_STEP):
        m = offset_analysis(mask, offset)

        rows.append({
            "offset": offset,
            "positions_compared_per_generation": width - offset,
            "tp": m["tp"],
            "fp": m["fp"],
            "fn": m["fn"],
            "jaccard": m["jaccard"],
            "dice": m["dice"],
            "exact_equal": m["exact_equal"],
        })

    rows.sort(
        key=lambda r: (
            -1 if r["jaccard"] is None else -r["jaccard"]
        )
    )

    return rows


def random_offset_controls(mask):
    rng = np.random.default_rng(RANDOM_SEED)

    width = mask.shape[1]

    candidates = np.arange(1, width)

    candidates = candidates[
        np.abs(candidates - TARGET_OFFSET) > NEARBY_RADIUS
    ]

    selected = rng.choice(
        candidates,
        size=min(RANDOM_CONTROLS, len(candidates)),
        replace=False
    )

    rows = []

    for offset in selected:
        m = offset_analysis(mask, int(offset))

        rows.append({
            "offset": int(offset),
            "positions_compared_per_generation": width - int(offset),
            "tp": m["tp"],
            "fp": m["fp"],
            "fn": m["fn"],
            "jaccard": m["jaccard"],
            "dice": m["dice"],
        })

    rows.sort(
        key=lambda r: (
            -1 if r["jaccard"] is None else -r["jaccard"]
        )
    )

    return rows


def spatial_profile_scan(mask):
    # This is a scan of the aggregate spatial anomaly profile.
    # It is NOT a scan of exact spacetime-mask repetitions.

    profile = mask.sum(axis=0).astype(np.float64)

    profile_centered = profile - profile.mean()

    denominator = np.dot(profile_centered, profile_centered)

    rows = []

    if denominator == 0:
        return rows

    for offset in range(1, len(profile)):
        a = profile_centered[:-offset]
        b = profile_centered[offset:]

        denom = np.sqrt(np.dot(a, a) * np.dot(b, b))

        if denom == 0:
            correlation = None
        else:
            correlation = float(np.dot(a, b) / denom)

        rows.append({
            "offset": offset,
            "profile_correlation": correlation,
        })

    rows.sort(
        key=lambda r: (
            -1 if r["profile_correlation"] is None
            else -r["profile_correlation"]
        )
    )

    return rows


def mismatch_coordinate_samples(mask, offset, limit=10000):
    a = mask[:, :-offset].astype(bool)
    b = mask[:, offset:].astype(bool)

    fp = np.argwhere((~a) & b)
    fn = np.argwhere(a & (~b))

    rows = []

    for t, x in fp[:limit]:
        rows.append({
            "generation_index": int(t),
            "left_global_index": int(x),
            "right_global_index": int(x + offset),
            "classification": "FP_RIGHT_ONLY",
        })

    for t, x in fn[:limit]:
        rows.append({
            "generation_index": int(t),
            "left_global_index": int(x),
            "right_global_index": int(x + offset),
            "classification": "FN_LEFT_ONLY",
        })

    return rows


def main():
    print("=" * 70)
    print("EXPERIMENT 042 - THE 6400 OFFSET INVESTIGATION")
    print("=" * 70)

    print("[1] Loading source matrix...")

    with np.load(MATRIX_PATH, allow_pickle=False) as data:
        print("[NPZ KEYS]", data.files)

        matrix = np.asarray(data["spacetime"], dtype=np.uint8)

        frontier_start = scalar_from_npz(
            data,
            ["frontier_start", "start_coordinate", "x_start"]
        )

        source_generation = scalar_from_npz(
            data,
            ["source_generation", "generation", "start_generation"]
        )

    if matrix.ndim != 2:
        raise RuntimeError("Matrix must be two-dimensional.")

    if not np.isin(matrix, [0, 1]).all():
        raise RuntimeError("Matrix contains values other than 0 and 1.")

    T, W = matrix.shape

    if W <= TARGET_OFFSET:
        raise RuntimeError("Matrix width is smaller than target offset.")

    if frontier_start is None:
        raise RuntimeError(
            "Missing frontier_start metadata. "
            "Cannot safely map matrix indices to global coordinates."
        )

    if source_generation is None:
        raise RuntimeError(
            "Missing source_generation metadata. "
            "Cannot safely map temporal indices."
        )

    print("[MATRIX SHAPE]", matrix.shape)
    print("[FRONTIER START]", frontier_start)
    print("[SOURCE GENERATION]", source_generation)
    print("[MATRIX SHA256]", sha256(MATRIX_PATH))

    print("[2] Validating Rule 110...")

    rule_check = validate_rule110(matrix)

    print(json.dumps(rule_check, indent=2))

    if not rule_check["valid"]:
        raise RuntimeError("Rule 110 validation failed.")

    print("[3] Reconstructing anomaly mask...")

    mask = anomaly_mask(matrix)

    print("[MASK SHAPE]", mask.shape)
    print("[MASK ANOMALIES]", int(mask.sum()))

    print("[4] Investigating offset 6400...")

    target_mask = offset_analysis(mask, TARGET_OFFSET)

    target_original = original_state_analysis(
        matrix,
        TARGET_OFFSET
    )

    target_temporal = temporal_signature_analysis(
        mask,
        TARGET_OFFSET
    )

    print("[TARGET MASK METRICS]")
    print(json.dumps(target_mask, indent=2))

    print("[ORIGINAL STATE METRICS]")
    print(json.dumps(target_original, indent=2))

    print("[TEMPORAL SIGNATURES]")
    print(json.dumps(target_temporal, indent=2))

    per_generation = per_generation_analysis(
        mask,
        TARGET_OFFSET
    )

    write_csv(
        OUT / "042_per_generation_6400.csv",
        per_generation
    )

    print("[5] Sector analysis...")

    sectors = sector_analysis(mask)

    write_csv(
        OUT / "042_sector_activity.csv",
        sectors
    )

    sector_pairs = pairwise_sector_analysis(mask)

    write_csv(
        OUT / "042_sector_pairwise_similarity.csv",
        sector_pairs
    )

    print("[6] Nearby offset scan...")

    nearby = nearby_offset_scan(mask)

    write_csv(
        OUT / "042_nearby_offset_scan.csv",
        nearby
    )

    print("[7] Random offset controls...")

    random_controls = random_offset_controls(mask)

    write_csv(
        OUT / "042_random_offset_controls.csv",
        random_controls
    )

    print("[8] Aggregate spatial profile scan...")

    profile_scan = spatial_profile_scan(mask)

    write_csv(
        OUT / "042_spatial_profile_scan.csv",
        profile_scan
    )

    print("[9] Exact mismatch coordinates...")

    mismatch_rows = mismatch_coordinate_samples(
        mask,
        TARGET_OFFSET
    )

    write_csv(
        OUT / "042_mismatch_coordinates.csv",
        mismatch_rows
    )

    # Per-generation exact-match statistics.
    exact_generations = sum(
        1 for row in per_generation if row["exact_equal"]
    )

    valid_jaccards = [
        row["jaccard"]
        for row in per_generation
        if row["jaccard"] is not None
    ]

    jaccard_values = np.asarray(valid_jaccards, dtype=np.float64)

    # Original binary-state comparisons by generation.
    original_rows = []

    for t in range(T):
        a = matrix[t, :-TARGET_OFFSET]
        b = matrix[t, TARGET_OFFSET:]

        metrics = binary_metrics(a, b)

        original_rows.append({
            "generation_index": t,
            "active_left": int(a.sum()),
            "active_right": int(b.sum()),
            "tp": metrics["tp"],
            "fp": metrics["fp"],
            "fn": metrics["fn"],
            "jaccard": metrics["jaccard"],
            "raw_equality": float(np.mean(a == b)),
            "phi": phi_binary(a, b),
        })

    write_csv(
        OUT / "042_original_state_per_generation.csv",
        original_rows
    )

    # Offset 6400 corresponds to sector 3 -> sector 28
    # because 6400 / 256 = 25.
    sector_offset = TARGET_OFFSET // SECTOR_SIZE

    sector_3 = mask[:, 3 * SECTOR_SIZE:4 * SECTOR_SIZE]
    sector_28 = mask[:, 28 * SECTOR_SIZE:29 * SECTOR_SIZE]

    sector_3_28 = binary_metrics(sector_3, sector_28)

    # Global coordinate mapping.
    global_left_start = int(frontier_start)
    global_right_start = int(frontier_start) + TARGET_OFFSET

    summary = {
        "experiment": "042",
        "title": "THE 6400 OFFSET INVESTIGATION",
        "matrix_shape": [int(T), int(W)],
        "matrix_sha256": sha256(MATRIX_PATH),
        "frontier_start": int(frontier_start),
        "source_generation": int(source_generation),
        "target_offset": TARGET_OFFSET,
        "offset_in_sectors": sector_offset,
        "sector_size": SECTOR_SIZE,
        "left_global_coordinate_start": global_left_start,
        "right_global_coordinate_start": global_right_start,
        "overlap_width": int(W - TARGET_OFFSET),
        "temporal_transitions": int(mask.shape[0]),
        "rule110_validation": rule_check,
        "anomaly_mask_total": int(mask.sum()),
        "target_mask_metrics": target_mask,
        "target_original_state_metrics": target_original,
        "target_temporal_signatures": target_temporal,
        "per_generation_exact_matches": int(exact_generations),
        "per_generation_total": int(len(per_generation)),
        "per_generation_jaccard_mean": (
            float(jaccard_values.mean())
            if len(jaccard_values) else None
        ),
        "per_generation_jaccard_min": (
            float(jaccard_values.min())
            if len(jaccard_values) else None
        ),
        "per_generation_jaccard_max": (
            float(jaccard_values.max())
            if len(jaccard_values) else None
        ),
        "sector_3_vs_sector_28": sector_3_28,
        "nearby_offsets_top_10": nearby[:10],
        "random_controls_top_10": random_controls[:10],
        "spatial_profile_top_10": profile_scan[:10],
        "mismatch_coordinate_rows_exported": len(mismatch_rows),
        "interpretation_guardrails": [
            "A high raw equality can be inflated by shared zeros.",
            "Jaccard measures overlap of positive anomaly positions.",
            "The anomaly mask is a comparison-disagreement mask, not a glider detector.",
            "A spatial offset is not a measured propagation velocity.",
            "The offset was selected after experiment 041 and therefore requires controls.",
            "A high anomaly-mask overlap does not prove identical underlying dynamics.",
        ],
    }

    with open(
        OUT / "042_final_report.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2)

    print("")
    print("=" * 70)
    print("EXPERIMENT 042 - FINAL RESULTS")
    print("=" * 70)

    print("TARGET OFFSET:", TARGET_OFFSET)
    print("SECTOR OFFSET:", sector_offset)
    print("OVERLAP WIDTH:", W - TARGET_OFFSET)
    print("MASK JACCARD:", target_mask["jaccard"])
    print("MASK DICE:", target_mask["dice"])
    print("MASK TP:", target_mask["tp"])
    print("MASK FP:", target_mask["fp"])
    print("MASK FN:", target_mask["fn"])
    print("EXACT GENERATIONS:", exact_generations, "/", len(per_generation))
    print("TEMPORAL SIGNATURE MATCHES:",
          target_temporal["exact_temporal_signature_matches"])
    print("ORIGINAL STATE JACCARD:", target_original["jaccard"])
    print("ORIGINAL STATE RAW EQUALITY:", target_original["raw_equality"])
    print("SECTOR 3 VS 28 JACCARD:", sector_3_28["jaccard"])

    print("")
    print("TOP 10 NEARBY OFFSETS")

    for row in nearby[:10]:
        print(row)

    print("")
    print("TOP 10 RANDOM CONTROLS")

    for row in random_controls[:10]:
        print(row)

    print("")
    print("TOP 10 SPATIAL PROFILE CORRELATIONS")

    for row in profile_scan[:10]:
        print(row)

    elapsed = time.time() - START

    summary["runtime_seconds"] = elapsed

    with open(
        OUT / "042_final_report.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2)

    print("")
    print("[OUTPUT]", OUT)
    print("[RUNTIME]", round(elapsed, 3), "seconds")
    print("[STATUS] ANALYSIS COMPLETED")


if __name__ == "__main__":
    main()
'@ | Set-Content -Path $PythonScript -Encoding UTF8

    $env:GODFELLA_042_OUT = $OutDir

    Write-Host ""
    Write-Host "[EXECUTION] Running Python forensic analysis..."
    Write-Host ""

    python $PythonScript

    if ($LASTEXITCODE -ne 0) {
        throw "Python analysis failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "[INTEGRITY] Checking original files..."

    $MatrixHashAfter = (Get-FileHash $MatrixPath -Algorithm SHA256).Hash
    $SnapshotHashAfter = (Get-FileHash $SnapshotPath -Algorithm SHA256).Hash

    $MatrixUnchanged = $MatrixHashBefore -eq $MatrixHashAfter
    $SnapshotUnchanged = $SnapshotHashBefore -eq $SnapshotHashAfter

    Write-Host ""
    Write-Host "MATRIX UNCHANGED: $MatrixUnchanged"
    Write-Host "SNAPSHOT UNCHANGED: $SnapshotUnchanged"

    Write-Host ""
    Write-Host "MATRIX SHA256 AFTER:"
    Write-Host $MatrixHashAfter

    Write-Host ""
    Write-Host "SNAPSHOT SHA256 AFTER:"
    Write-Host $SnapshotHashAfter

    if (-not $MatrixUnchanged -or -not $SnapshotUnchanged) {
        throw "INTEGRITY FAILURE: Original source files changed."
    }

    Write-Host ""
    Write-Host "============================================================"
    Write-Host " EXPERIMENT 042 COMPLETED"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "OUTPUT DIRECTORY:"
    Write-Host $OutDir

}
catch {

    Write-Host ""
    Write-Host "[FATAL ERROR]"
    Write-Host $_.Exception.Message
    throw

}
finally {

    Remove-Item Env:\GODFELLA_042_OUT -ErrorAction SilentlyContinue

    Stop-Transcript | Out-Null

}