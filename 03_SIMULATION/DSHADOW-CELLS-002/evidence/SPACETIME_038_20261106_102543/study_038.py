import json
import csv
import hashlib
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002")
SNAPSHOT = ROOT / "evidence" / "DEEP_UNIVERSE_035_20261106_084957" / "frozen_universe.json"
OUT = Path(__file__).resolve().parent

GENERATIONS = 500
PAD = GENERATIONS + 10
WINDOW = 8192
MAX_SHIFT = 8

LUT = np.array([0, 1, 1, 1, 0, 1, 1, 0], dtype=np.uint8)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rule110(state):
    out = np.zeros_like(state)
    neighborhood = (
        (state[:-2] << 2)
        | (state[1:-1] << 1)
        | state[2:]
    )
    out[1:-1] = LUT[neighborhood]
    return out


def shifted_correlation(a, b, shift):
    if shift > 0:
        x = a[:-shift]
        y = b[shift:]
    elif shift < 0:
        x = a[-shift:]
        y = b[:shift]
    else:
        x = a
        y = b

    if len(x) == 0:
        return 0.0

    return float(np.mean(x == y))


def main():
    start_time = time.time()
    original_hash = sha256(SNAPSHOT)

    print("=" * 72)
    print("PROJECT GODFELLA - EXPERIMENT 038")
    print("SPACETIME STRUCTURE DETECTION")
    print("=" * 72)

    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    active = np.asarray(data["active"], dtype=np.int64)
    generation = int(data["generation"])

    min_coord = int(active.min())
    max_coord = int(active.max())
    span = max_coord - min_coord + 1

    state = np.zeros(span + 2 * PAD, dtype=np.uint8)
    state[PAD:PAD + span] = 0
    state[PAD + active - min_coord] = 1

    frontier_start = max(529248, span - WINDOW)
    frontier_start = min(frontier_start, span)
    frontier_width = span - frontier_start

    if frontier_width < 100:
        raise RuntimeError("La frontera seleccionada es demasiado pequeña.")

    print(f"Snapshot generation : {generation}")
    print(f"Active cells        : {len(active)}")
    print(f"Universe span       : {span}")
    print(f"Frontier start      : {frontier_start}")
    print(f"Frontier width      : {frontier_width}")
    print(f"Simulation steps    : {GENERATIONS}")

    spacetime = np.zeros(
        (GENERATIONS + 1, frontier_width),
        dtype=np.uint8
    )

    metrics = []

    for t in range(GENERATIONS + 1):
        frontier = state[
            PAD + frontier_start:PAD + span
        ].copy()

        spacetime[t] = frontier

        active_count = int(frontier.sum())
        density = float(frontier.mean())

        transitions = int(
            np.count_nonzero(frontier[1:] != frontier[:-1])
        )

        active_runs = int(
            np.count_nonzero(
                (frontier == 1)
                & np.concatenate(([True], frontier[:-1] == 0))
            )
        )

        metrics.append({
            "generation_step": t,
            "absolute_generation": generation + t,
            "active_cells": active_count,
            "density": density,
            "active_runs": active_runs,
            "transitions": transitions
        })

        if t % 50 == 0:
            print(
                f"Step {t:03d}/{GENERATIONS} | "
                f"active={active_count} | "
                f"density={density:.6f} | "
                f"runs={active_runs}"
            )

        if t < GENERATIONS:
            state = rule110(state)

    print("\n--- SPACETIME CORRELATION ---")

    correlations = []

    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        values = [
            shifted_correlation(
                spacetime[t],
                spacetime[t + 1],
                shift
            )
            for t in range(GENERATIONS)
        ]

        correlations.append({
            "spatial_shift": shift,
            "mean_correlation": float(np.mean(values)),
            "std_correlation": float(np.std(values))
        })

    best = max(
        correlations,
        key=lambda x: x["mean_correlation"]
    )

    for item in correlations:
        print(
            f"Shift {item['spatial_shift']:+3d} | "
            f"correlation={item['mean_correlation']:.6f}"
        )

    print(
        f"\nBest average shift: {best['spatial_shift']:+d} "
        f"({best['mean_correlation']:.6f})"
    )

    # Recurrencia: comparar generaciones separadas por diferentes lapsos.
    print("\n--- TEMPORAL RECURRENCE ---")

    recurrence = []

    for lag in [1, 2, 5, 10, 20, 40, 80, 160]:
        if lag >= len(spacetime):
            continue

        values = np.mean(
            spacetime[:-lag] == spacetime[lag:],
            axis=1
        )

        recurrence.append({
            "lag": lag,
            "mean_similarity": float(values.mean()),
            "std_similarity": float(values.std())
        })

        print(
            f"Lag {lag:3d} | "
            f"similarity={values.mean():.6f}"
        )

    # Persistencia local: actividad de cada posición a través del tiempo.
    temporal_activity = spacetime.mean(axis=0)

    persistent = int(np.count_nonzero(temporal_activity >= 0.95))
    intermittent = int(
        np.count_nonzero(
            (temporal_activity > 0.05)
            & (temporal_activity < 0.95)
        )
    )
    mostly_inactive = int(
        np.count_nonzero(temporal_activity <= 0.05)
    )

    print("\n--- SPATIAL PERSISTENCE ---")
    print(f"Persistent active positions : {persistent}")
    print(f"Intermittent positions      : {intermittent}")
    print(f"Mostly inactive positions   : {mostly_inactive}")

    # Exportar series temporales.
    csv_path = OUT / "038_timeseries.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(metrics[0].keys())
        )
        writer.writeheader()
        writer.writerows(metrics)

    # Exportar correlaciones.
    corr_path = OUT / "038_shift_correlations.csv"

    with corr_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(correlations[0].keys())
        )
        writer.writeheader()
        writer.writerows(correlations)

    # Guardar matriz original para análisis posterior.
    np.savez_compressed(
        OUT / "038_spacetime_matrix.npz",
        spacetime=spacetime,
        frontier_start=frontier_start,
        source_generation=generation
    )

    # Mapa espacio-tiempo.
    plt.figure(figsize=(18, 9))
    plt.imshow(
        spacetime,
        aspect="auto",
        interpolation="nearest",
        origin="lower"
    )
    plt.title("PROJECT GODFELLA - Spacetime Evolution")
    plt.xlabel("Spatial position within frontier")
    plt.ylabel("Generation step")
    plt.tight_layout()
    plt.savefig(
        OUT / "038_spacetime_map.png",
        dpi=180
    )
    plt.close()

    # Actividad temporal por posición.
    plt.figure(figsize=(18, 5))
    plt.plot(temporal_activity)
    plt.title("Temporal Activity per Spatial Position")
    plt.xlabel("Spatial position within frontier")
    plt.ylabel("Fraction of active generations")
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(
        OUT / "038_spatial_persistence.png",
        dpi=180
    )
    plt.close()

    # Correlación según desplazamiento.
    plt.figure(figsize=(10, 5))
    plt.plot(
        [x["spatial_shift"] for x in correlations],
        [x["mean_correlation"] for x in correlations],
        marker="o"
    )
    plt.title("One-Step Spatial Shift Correlation")
    plt.xlabel("Spatial shift")
    plt.ylabel("Mean exact-match fraction")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(
        OUT / "038_shift_correlation.png",
        dpi=180
    )
    plt.close()

    final_hash = sha256(SNAPSHOT)
    unchanged = original_hash == final_hash

    report = {
        "experiment": "038",
        "status": "COMPLETED",
        "source_generation": generation,
        "source_active_cells": int(len(active)),
        "source_span": int(span),
        "simulation_generations": GENERATIONS,
        "frontier_start_index": frontier_start,
        "frontier_width": frontier_width,
        "initial_density": metrics[0]["density"],
        "final_density": metrics[-1]["density"],
        "best_one_step_shift": best,
        "shift_correlations": correlations,
        "temporal_recurrence": recurrence,
        "persistent_positions_95pct": persistent,
        "intermittent_positions": intermittent,
        "mostly_inactive_positions_5pct": mostly_inactive,
        "snapshot_sha256_before": original_hash,
        "snapshot_sha256_after": final_hash,
        "snapshot_unchanged": unchanged,
        "elapsed_seconds": round(time.time() - start_time, 3),
        "interpretation": (
            "Spacetime mapping and statistical correlations are descriptive. "
            "A preferred shift or recurrence is not sufficient evidence "
            "for a glider, replicator, organism, or life."
        )
    }

    report_path = OUT / "038_report.json"
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 72)
    print("EXPERIMENT 038 COMPLETED")
    print("=" * 72)
    print(f"Snapshot unchanged : {unchanged}")
    print(f"Elapsed seconds    : {report['elapsed_seconds']}")
    print(f"Report             : {report_path}")
    print(f"Spacetime map      : {OUT / '038_spacetime_map.png'}")

    if not unchanged:
        raise RuntimeError("El snapshot original cambió.")

    print("\nNo se declara vida ni gliders en esta fase.")


if __name__ == "__main__":
    main()
