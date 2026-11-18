import json
import csv
import hashlib
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

SOURCE = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION"
    r"\DSHADOW-CELLS-002\evidence\SPACETIME_038_20261106_102543"
    r"\038_spacetime_matrix.npz"
)

OUT = Path(__file__).resolve().parent

LUT = np.array([0, 1, 1, 1, 0, 1, 1, 0], dtype=np.uint8)

MAX_SHIFT = 4
TILE = 256
SPATIAL_LAGS = [2, 4, 8, 16, 32, 40, 80, 160, 320, 640, 800]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rule110_row(row):
    out = np.zeros_like(row)
    neighborhood = (
        (row[:-2] << 2)
        | (row[1:-1] << 1)
        | row[2:]
    )
    out[1:-1] = LUT[neighborhood]
    return out


def compare(a, b, shift):
    if shift > 0:
        x = a[:-shift]
        y = b[shift:]
    elif shift < 0:
        x = a[-shift:]
        y = b[:shift]
    else:
        x = a
        y = b

    if len(x) < 2:
        return 0.0, 0.0

    equality = float(np.mean(x == y))

    sx = float(np.std(x))
    sy = float(np.std(y))

    if sx == 0 or sy == 0:
        phi = 0.0
    else:
        phi = float(np.mean((x - x.mean()) * (y - y.mean())) / (sx * sy))

    return equality, phi


def save_csv(path, rows):
    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    started = time.time()
    source_hash = sha256(SOURCE)

    print("=" * 72)
    print("PROJECT GODFELLA - EXPERIMENT 039")
    print("ANOMALY HUNT / STRUCTURE LOCALIZATION")
    print("=" * 72)

    loaded = np.load(SOURCE)

    matrix = loaded["spacetime"].astype(np.uint8)
    frontier_start = int(loaded["frontier_start"])
    source_generation = int(loaded["source_generation"])

    generations, width = matrix.shape

    print(f"Source generation : {source_generation}")
    print(f"Matrix dimensions : {generations} x {width}")
    print(f"Frontier index    : {frontier_start}")

    # --------------------------------------------------
    # 1. VALIDACIÓN DE LA REGLA 110
    # --------------------------------------------------

    print("\n--- 1. RULE 110 VALIDATION ---")

    rule_errors = 0
    checked = 0

    for t in range(generations - 1):
        predicted = rule110_row(matrix[t])

        actual = matrix[t + 1, 1:-1]
        expected = predicted[1:-1]

        errors = int(np.count_nonzero(actual != expected))

        rule_errors += errors
        checked += len(actual)

    rule_error_rate = rule_errors / max(checked, 1)

    print(f"Checked cells : {checked}")
    print(f"Rule errors   : {rule_errors}")
    print(f"Error rate    : {rule_error_rate:.12f}")

    # --------------------------------------------------
    # 2. CORRELACIÓN GLOBAL
    # --------------------------------------------------

    print("\n--- 2. GLOBAL SHIFT CORRELATION ---")

    global_rows = []

    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        eq_values = []
        phi_values = []

        for t in range(generations - 1):
            eq, phi = compare(
                matrix[t],
                matrix[t + 1],
                shift
            )

            eq_values.append(eq)
            phi_values.append(phi)

        global_rows.append({
            "shift": shift,
            "mean_equality": float(np.mean(eq_values)),
            "std_equality": float(np.std(eq_values)),
            "mean_phi": float(np.mean(phi_values)),
            "std_phi": float(np.std(phi_values))
        })

        item = global_rows[-1]

        print(
            f"Shift {shift:+3d} | "
            f"equality={item['mean_equality']:.6f} | "
            f"phi={item['mean_phi']:.6f}"
        )

    # --------------------------------------------------
    # 3. CORRELACIÓN LOCAL POR SECTORES
    # --------------------------------------------------

    print("\n--- 3. LOCAL ANOMALY MAP ---")

    tiles = []

    for start in range(0, width, TILE):
        end = min(start + TILE, width)

        if end - start < 32:
            continue

        for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
            eq_values = []
            phi_values = []

            for t in range(generations - 1):
                a = matrix[t, start:end]
                b = matrix[t + 1, start:end]

                eq, phi = compare(a, b, shift)

                eq_values.append(eq)
                phi_values.append(phi)

            tiles.append({
                "tile_start": start,
                "tile_end": end,
                "absolute_start": frontier_start + start,
                "absolute_end": frontier_start + end - 1,
                "shift": shift,
                "mean_equality": float(np.mean(eq_values)),
                "mean_phi": float(np.mean(phi_values))
            })

    # Determinar el mejor desplazamiento local.
    best_tiles = []

    for start in range(0, width, TILE):
        candidates = [
            x for x in tiles
            if x["tile_start"] == start
        ]

        if not candidates:
            continue

        best = max(candidates, key=lambda x: x["mean_phi"])

        minus_four = next(
            (x for x in candidates if x["shift"] == -4),
            None
        )

        best_tiles.append({
            "tile_start": best["tile_start"],
            "absolute_start": best["absolute_start"],
            "best_shift": best["shift"],
            "best_phi": best["mean_phi"],
            "minus_four_phi": minus_four["mean_phi"] if minus_four else None,
            "minus_four_equality": minus_four["mean_equality"] if minus_four else None
        })

    # --------------------------------------------------
    # 4. AUTOCORRELACIÓN ESPACIAL
    # --------------------------------------------------

    print("\n--- 4. SPATIAL PERIODICITY ---")

    spatial_rows = []

    for lag in SPATIAL_LAGS:
        if lag >= width:
            continue

        values = []

        for t in range(generations):
            a = matrix[t, :-lag]
            b = matrix[t, lag:]

            values.append(float(np.mean(a == b)))

        result = {
            "spatial_lag": lag,
            "mean_similarity": float(np.mean(values)),
            "std_similarity": float(np.std(values))
        }

        spatial_rows.append(result)

        print(
            f"Lag {lag:4d} | "
            f"similarity={result['mean_similarity']:.6f}"
        )

    # --------------------------------------------------
    # 5. DETECCIÓN DE VARIACIÓN TEMPORAL LOCAL
    # --------------------------------------------------

    print("\n--- 5. LOCAL ACTIVITY VARIATION ---")

    local_activity = []

    for start in range(0, width, TILE):
        end = min(start + TILE, width)

        block = matrix[:, start:end]

        density = float(block.mean())
        temporal_variation = float(
            np.mean(np.abs(np.diff(block.astype(np.int8), axis=0)))
        )

        local_activity.append({
            "tile_start": start,
            "absolute_start": frontier_start + start,
            "density": density,
            "temporal_variation": temporal_variation
        })

    # --------------------------------------------------
    # 6. EXPORTACIÓN
    # --------------------------------------------------

    save_csv(OUT / "039_global_correlations.csv", global_rows)
    save_csv(OUT / "039_local_shift_analysis.csv", tiles)
    save_csv(OUT / "039_best_local_shifts.csv", best_tiles)
    save_csv(OUT / "039_spatial_periodicity.csv", spatial_rows)
    save_csv(OUT / "039_local_activity.csv", local_activity)

    # Matriz de correlación phi por sector y desplazamiento.
    tile_starts = sorted(set(x["tile_start"] for x in tiles))
    shifts = list(range(-MAX_SHIFT, MAX_SHIFT + 1))

    heatmap = np.zeros((len(shifts), len(tile_starts)))

    for i, shift in enumerate(shifts):
        for j, start in enumerate(tile_starts):
            item = next(
                x for x in tiles
                if x["shift"] == shift
                and x["tile_start"] == start
            )
            heatmap[i, j] = item["mean_phi"]

    plt.figure(figsize=(18, 6))
    plt.imshow(
        heatmap,
        aspect="auto",
        interpolation="nearest",
        origin="lower",
        extent=[
            0,
            len(tile_starts),
            -MAX_SHIFT - 0.5,
            MAX_SHIFT + 0.5
        ]
    )
    plt.yticks(shifts)
    plt.colorbar(label="Mean phi correlation")
    plt.title("039 - Local Shift Correlation")
    plt.xlabel("Spatial tile")
    plt.ylabel("Shift")
    plt.tight_layout()
    plt.savefig(OUT / "039_local_shift_heatmap.png", dpi=180)
    plt.close()

    # Mapa de variación local.
    variation = np.array([
        x["temporal_variation"]
        for x in local_activity
    ])

    plt.figure(figsize=(18, 5))
    plt.plot(variation)
    plt.title("039 - Local Temporal Variation")
    plt.xlabel("Spatial tile")
    plt.ylabel("Mean cell variation")
    plt.tight_layout()
    plt.savefig(OUT / "039_local_variation.png", dpi=180)
    plt.close()

    # Comparación global de correlaciones.
    plt.figure(figsize=(10, 5))
    plt.plot(
        [x["shift"] for x in global_rows],
        [x["mean_phi"] for x in global_rows],
        marker="o"
    )
    plt.title("039 - Global Phi Correlation")
    plt.xlabel("Spatial shift")
    plt.ylabel("Mean phi correlation")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUT / "039_global_correlation.png", dpi=180)
    plt.close()

    # --------------------------------------------------
    # 7. INFORME FINAL
    # --------------------------------------------------

    best_global = max(global_rows, key=lambda x: x["mean_phi"])

    report = {
        "experiment": "039",
        "status": "COMPLETED",
        "source_generation": source_generation,
        "matrix_dimensions": [int(generations), int(width)],
        "frontier_start": frontier_start,
        "rule110_validation": {
            "checked_cells": checked,
            "errors": rule_errors,
            "error_rate": rule_error_rate
        },
        "global_correlations": global_rows,
        "best_global_phi_shift": best_global,
        "local_tile_count": len(tile_starts),
        "local_best_shifts": best_tiles,
        "spatial_periodicity": spatial_rows,
        "local_activity": local_activity,
        "source_sha256_before": source_hash,
        "source_sha256_after": sha256(SOURCE),
        "source_unchanged": source_hash == sha256(SOURCE),
        "elapsed_seconds": round(time.time() - started, 3),
        "interpretation": (
            "This experiment localizes correlations and spatial regularity. "
            "It does not identify gliders or living structures. "
            "Candidate regions require trajectory-level validation."
        )
    }

    report_path = OUT / "039_report.json"

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 72)
    print("EXPERIMENT 039 COMPLETED")
    print("=" * 72)
    print(f"Rule 110 errors       : {rule_errors}")
    print(f"Best global phi shift: {best_global['shift']}")
    print(f"Local sectors        : {len(tile_starts)}")
    print(f"Source unchanged     : {report['source_unchanged']}")
    print(f"Elapsed seconds      : {report['elapsed_seconds']}")
    print(f"Report               : {report_path}")

    if rule_errors:
        print("WARNING: Rule 110 validation failed.")
    else:
        print("RULE 110 VALIDATION: PASS")

    print("No organism or glider claim is made in this experiment.")


if __name__ == "__main__":
    main()
