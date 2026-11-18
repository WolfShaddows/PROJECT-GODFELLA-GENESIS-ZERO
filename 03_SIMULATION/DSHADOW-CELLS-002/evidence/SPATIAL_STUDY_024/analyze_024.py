import json
import csv
import hashlib
from pathlib import Path

import numpy as np

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json"
)

OUT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_024"
)

START_COORD = -284870
END_LOWER_COORD = -39804
PERIOD = 160
GENERATIONS = 200

raw = SNAPSHOT.read_bytes()
hash_before = hashlib.sha256(raw).hexdigest()

data = json.loads(raw)

active = np.asarray(data["active"], dtype=np.int64)
active.sort()

if len(np.unique(active)) != len(active):
    raise ValueError("Hay coordenadas duplicadas.")

minimum = int(active[0])
maximum = int(active[-1])
span = maximum - minimum + 1

state = np.zeros(span, dtype=np.uint8)
state[active - minimum] = 1

start_index = START_COORD - minimum
end_index = END_LOWER_COORD - minimum

if start_index < 1 or end_index + PERIOD >= span - 1:
    raise ValueError("La región no tiene margen suficiente.")

# Validar la periodicidad inicial.
initial_left = state[start_index:end_index + 1]
initial_right = state[
    start_index + PERIOD:end_index + PERIOD + 1
]

initial_mismatches = int(
    np.count_nonzero(initial_left != initial_right)
)

if initial_mismatches != 0:
    raise ValueError(
        f"Falló la validación inicial: {initial_mismatches} discrepancias."
    )

def rule110_step(values):
    padded = np.pad(values, (1, 1), constant_values=0)

    neighborhoods = (
        4 * padded[:-2] +
        2 * padded[1:-1] +
        padded[2:]
    )

    return ((110 >> neighborhoods) & 1).astype(np.uint8)

def find_runs(mask):
    indexes = np.flatnonzero(mask)

    if len(indexes) == 0:
        return []

    breaks = np.where(np.diff(indexes) > 1)[0] + 1
    groups = np.split(indexes, breaks)

    return [
        (int(group[0]), int(group[-1]), len(group))
        for group in groups
    ]

summary_rows = []
run_rows = []

for generation in range(GENERATIONS + 1):

    # Comparamos todas las parejas válidas x y x+160.
    comparison_length = span - PERIOD

    left = state[:comparison_length]
    right = state[PERIOD:]

    mismatch_mask = left != right

    total_mismatches = int(np.count_nonzero(mismatch_mask))
    runs = find_runs(mismatch_mask)

    # Dominio interior garantizado por localidad.
    safe_start = start_index + generation
    safe_end = end_index - generation

    if safe_end < safe_start:
        raise RuntimeError("Se agotó el dominio interior.")

    safe_mismatches = int(
        np.count_nonzero(
            mismatch_mask[safe_start:safe_end + 1]
        )
    )

    # Fronteras de discrepancias más próximas al dominio interior.
    left_runs = [
        r for r in runs
        if r[1] < safe_start
    ]

    right_runs = [
        r for r in runs
        if r[0] > safe_end
    ]

    nearest_left = max(
        left_runs,
        key=lambda r: r[1],
        default=None
    )

    nearest_right = min(
        right_runs,
        key=lambda r: r[0],
        default=None
    )

    left_front = (
        minimum + nearest_left[1]
        if nearest_left else None
    )

    right_front = (
        minimum + nearest_right[0]
        if nearest_right else None
    )

    summary_rows.append({
        "generation": generation,
        "total_comparisons": comparison_length,
        "total_mismatches": total_mismatches,
        "mismatch_runs": len(runs),
        "safe_region_start": minimum + safe_start,
        "safe_region_end": minimum + safe_end,
        "safe_region_length": safe_end - safe_start + 1,
        "safe_region_mismatches": safe_mismatches,
        "nearest_left_mismatch_end": left_front,
        "nearest_right_mismatch_start": right_front,
        "safe_region_exact": safe_mismatches == 0
    })

    for run_number, (run_start, run_end, run_length) in enumerate(
        runs, start=1
    ):
        run_rows.append({
            "generation": generation,
            "run_number": run_number,
            "start_coordinate": minimum + run_start,
            "end_coordinate": minimum + run_end,
            "length": run_length
        })

    if generation % 10 == 0 or generation == GENERATIONS:
        print({
            "generation": generation,
            "total_mismatches": total_mismatches,
            "mismatch_runs": len(runs),
            "safe_region_mismatches": safe_mismatches,
            "safe_region_exact": safe_mismatches == 0,
            "left_front": left_front,
            "right_front": right_front
        })

    if generation < GENERATIONS:
        state = rule110_step(state)

# Exportar resumen por generación.
with (OUT / "boundary_summary.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(summary_rows[0])
    )
    writer.writeheader()
    writer.writerows(summary_rows)

# Exportar todos los segmentos de discrepancias.
with (OUT / "boundary_mismatch_runs.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = [
        "generation",
        "run_number",
        "start_coordinate",
        "end_coordinate",
        "length"
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(run_rows)

hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot original cambió.")

report = {
    "experiment": "024_PERIODICITY_BOUNDARY_ANALYSIS",
    "rule": data["rule"],
    "initial_generation": data["generation"],
    "period": PERIOD,
    "simulated_generations": GENERATIONS,
    "initial_periodic_region": {
        "start": START_COORD,
        "end_lower": END_LOWER_COORD,
        "length": END_LOWER_COORD - START_COORD + 1
    },
    "initial_mismatches": initial_mismatches,
    "total_mismatch_records": len(run_rows),
    "all_safe_regions_exact": all(
        row["safe_region_exact"] for row in summary_rows
    ),
    "first_safe_region_failure": next(
        (
            row for row in summary_rows
            if not row["safe_region_exact"]
        ),
        None
    ),
    "initial_summary": summary_rows[0],
    "final_summary": summary_rows[-1],
    "snapshot_sha256_before": hash_before,
    "snapshot_sha256_after": hash_after,
    "snapshot_integrity": hash_before == hash_after
}

with (OUT / "experiment_024_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

print("\n=== DSHADOW | EXPERIMENTO 024 ===")
print("Rule:", data["rule"])
print("Initial generation:", data["generation"])
print("Period:", PERIOD)
print("Simulated generations:", GENERATIONS)

print("\nINITIAL VALIDATION")
print("Initial mismatches:", initial_mismatches)

print("\nBOUNDARY ANALYSIS")
print("Mismatch records:", len(run_rows))
print("All safe regions exact:", report["all_safe_regions_exact"])
print("First safe-region failure:", report["first_safe_region_failure"])

print("\nFINAL GENERATION")
print(summary_rows[-1])

print("\nINTEGRITY")
print("SHA256 before:", hash_before)
print("SHA256 after:", hash_after)
print("Integrity:", report["snapshot_integrity"])

print("\nExperiment 024 completed.")
