import json
import hashlib
import time
import csv
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002")
SNAPSHOT = ROOT / "evidence" / "DEEP_UNIVERSE_035_20261106_084957" / "frozen_universe.json"
OUT = Path(__file__).resolve().parent

PERIOD = 160
GENERATIONS = 500
PAD = GENERATIONS + 10
FRONTIER_WIDTH = 8192

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


def longest_true_run(mask):
    padded = np.concatenate(([False], mask, [False]))
    changes = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1) - 1

    if len(starts) == 0:
        return None

    lengths = ends - starts + 1
    k = int(np.argmax(lengths))
    return int(starts[k]), int(ends[k]), int(lengths[k])


def main():
    started = time.time()
    before_hash = sha256(SNAPSHOT)

    print("=" * 72)
    print("PROJECT GODFELLA - EXPERIMENT 037-R1")
    print("PHASE-CORRECTED PERIODIC BACKGROUND / DYNAMIC FRONTIER")
    print("=" * 72)

    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    active = np.asarray(data["active"], dtype=np.int64)
    generation = int(data["generation"])

    if active.size == 0:
        raise RuntimeError("El snapshot no contiene celdas activas.")

    min_coord = int(active.min())
    max_coord = int(active.max())
    span = max_coord - min_coord + 1

    print(f"Snapshot generation : {generation}")
    print(f"Active cells        : {len(active)}")
    print(f"Coordinate range    : {min_coord} .. {max_coord}")
    print(f"Spatial span        : {span}")

    bits = np.zeros(span, dtype=np.uint8)
    bits[active - min_coord] = 1

    # Buscar igualdad exacta a distancia 160.
    equal = bits[:-PERIOD] == bits[PERIOD:]
    run = longest_true_run(equal)

    if run is None:
        raise RuntimeError("No se encontró ningún tramo periódico exacto.")

    core_start, core_end, core_length = run
    core_region_end = core_end + PERIOD

    motif = bits[core_start:core_start + PERIOD].copy()
    anchor_coord = min_coord + core_start

    print("\n--- PERIODIC CORE ---")
    print(f"Period              : {PERIOD}")
    print(f"Comparison interval : {core_start} .. {core_end}")
    print(f"Periodic region     : {core_start} .. {core_region_end}")
    print(f"Comparison length   : {core_length}")
    print(f"Anchor coordinate   : {anchor_coord}")
    print(f"Motif               : {''.join(map(str, motif.tolist()))}")

    # Verificación exacta de fase en toda la región.
    coords = np.arange(core_start, core_region_end + 1)
    expected = motif[(coords - core_start) % PERIOD]

    phase_errors = int(np.count_nonzero(bits[coords] != expected))

    if phase_errors != 0:
        raise RuntimeError(
            f"Error de fase: {phase_errors} discrepancias iniciales."
        )

    print("Initial phase check : PASS (0 mismatches)")

    # Universo real con padding para evitar efectos de borde durante 500 pasos.
    actual = np.zeros(span + 2 * PAD, dtype=np.uint8)
    actual[PAD:PAD + span] = bits

    # Fondo periódico independiente: anillo de 160 celdas.
    ether = motif.copy()

    frontier_start = max(core_region_end + 1, span - FRONTIER_WIDTH)
    frontier_start = min(frontier_start, span)

    print("\n--- DYNAMIC SIMULATION ---")
    print(f"Generations         : {GENERATIONS}")
    print(f"Frontier start      : {frontier_start}")
    print(f"Frontier width      : {span - frontier_start}")
    print("Tracking method     : vectorized / linear")
    print("Pairwise matching   : DISABLED")

    rows = []
    total_core_mismatches = 0
    max_core_mismatches = 0

    for t in range(GENERATIONS + 1):

        # Región segura: se reduce un sitio por lado por generación.
        safe_lo = core_start + t
        safe_hi = core_region_end - t

        if safe_lo <= safe_hi:
            absolute_indices = np.arange(safe_lo, safe_hi + 1)
            actual_segment = actual[
                PAD + safe_lo:PAD + safe_hi + 1
            ]

            ether_indices = (absolute_indices - core_start) % PERIOD
            ether_segment = ether[ether_indices]

            mismatches = int(
                np.count_nonzero(actual_segment != ether_segment)
            )
        else:
            mismatches = -1

        if mismatches >= 0:
            total_core_mismatches += mismatches
            max_core_mismatches = max(max_core_mismatches, mismatches)

        # Métricas de la frontera no periódica.
        f_lo = max(frontier_start, 0)
        f_hi = span

        if f_lo < f_hi:
            frontier = actual[PAD + f_lo:PAD + f_hi]
            frontier_active = int(frontier.sum())
            frontier_density = float(frontier.mean())
            frontier_runs = int(
                np.count_nonzero(
                    (frontier == 1)
                    & np.concatenate(([True], frontier[:-1] == 0))
                )
            )
        else:
            frontier_active = 0
            frontier_density = 0.0
            frontier_runs = 0

        rows.append({
            "generation_step": t,
            "core_mismatches": mismatches,
            "safe_core_length": max(0, safe_hi - safe_lo + 1),
            "frontier_active": frontier_active,
            "frontier_density": frontier_density,
            "frontier_runs": frontier_runs,
            "universe_active": int(actual.sum())
        })

        if t % 50 == 0:
            print(
                f"Step {t:03d}/{GENERATIONS} | "
                f"core mismatches={mismatches} | "
                f"frontier active={frontier_active} | "
                f"density={frontier_density:.6f}"
            )

        if t == GENERATIONS:
            break

        actual = rule110(actual)

        # Evolución del fondo periódico en un anillo de 160 celdas.
        left = np.roll(ether, 1)
        center = ether
        right = np.roll(ether, -1)

        neighborhood = (
            (left << 2) | (center << 1) | right
        )
        ether = LUT[neighborhood]

    # Exportar métricas.
    csv_path = OUT / "037_r1_timeseries.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    final_hash = sha256(SNAPSHOT)
    snapshot_unchanged = before_hash == final_hash

    result = {
        "experiment": "037-R1",
        "status": "COMPLETED",
        "source_generation": generation,
        "source_active_cells": int(len(active)),
        "source_span": int(span),
        "period": PERIOD,
        "periodic_comparison_start_index": core_start,
        "periodic_comparison_end_index": core_end,
        "periodic_region_end_index": core_region_end,
        "periodic_region_length": core_region_end - core_start + 1,
        "phase_anchor_coordinate": anchor_coord,
        "initial_phase_mismatches": phase_errors,
        "simulation_generations": GENERATIONS,
        "total_core_mismatches": total_core_mismatches,
        "maximum_core_mismatches": max_core_mismatches,
        "final_core_mismatches": rows[-1]["core_mismatches"],
        "frontier_start_index": frontier_start,
        "frontier_width": span - frontier_start,
        "frontier_initial_density": rows[0]["frontier_density"],
        "frontier_final_density": rows[-1]["frontier_density"],
        "frontier_initial_active": rows[0]["frontier_active"],
        "frontier_final_active": rows[-1]["frontier_active"],
        "snapshot_sha256_before": before_hash,
        "snapshot_sha256_after": final_hash,
        "snapshot_unchanged": snapshot_unchanged,
        "elapsed_seconds": round(time.time() - started, 3),
        "interpretation": (
            "This experiment validates periodic-background phase alignment "
            "and measures the non-periodic frontier. It does not by itself "
            "identify gliders, reproduction, or life."
        )
    }

    json_path = OUT / "037_r1_report.json"
    json_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 72)
    print("EXPERIMENT 037-R1 COMPLETED")
    print("=" * 72)
    print(f"Initial phase check       : {phase_errors}")
    print(f"Maximum core mismatches   : {max_core_mismatches}")
    print(f"Final core mismatches     : {rows[-1]['core_mismatches']}")
    print(f"Snapshot unchanged        : {snapshot_unchanged}")
    print(f"Elapsed seconds           : {result['elapsed_seconds']}")
    print(f"Report                    : {json_path}")
    print(f"Time series               : {csv_path}")

    if not snapshot_unchanged:
        raise RuntimeError("El SHA256 del snapshot cambió.")

    if phase_errors != 0 or max_core_mismatches != 0:
        print("WARNING: periodic-core validation requires investigation.")
    else:
        print("PERIODIC CORE VALIDATION: PASS")

    print("\nNota: PASS valida el fondo periódico; no demuestra vida.")
    print("El análisis de candidatos dinámicos será una fase separada.")


if __name__ == "__main__":
    main()
