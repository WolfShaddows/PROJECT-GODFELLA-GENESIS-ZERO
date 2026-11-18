import json
import csv
import hashlib
from pathlib import Path

import numpy as np

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json"
)

OUT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_023_R1"
)

START_COORD = -284870
END_LOWER_COORD = -39804
PERIOD = 160
GENERATIONS = 100

raw = SNAPSHOT.read_bytes()
hash_before = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

active = np.asarray(data["active"], dtype=np.int64)
active.sort()

if len(np.unique(active)) != len(active):
    raise ValueError("Coordenadas duplicadas.")

minimum = int(active[0])
maximum = int(active[-1])

span = maximum - minimum + 1

state = np.zeros(span, dtype=np.uint8)
state[active - minimum] = 1

start_index = START_COORD - minimum
end_index = END_LOWER_COORD - minimum

if start_index < 1 or end_index + PERIOD >= span - 1:
    raise ValueError("La región no tiene margen suficiente.")

# Verificación correcta:
# posiciones inferiores [-284870, -39804]
# comparadas con las posiciones desplazadas +160.
initial_left = state[start_index:end_index + 1]
initial_right = state[
    start_index + PERIOD:end_index + PERIOD + 1
]

initial_mismatches = int(
    np.count_nonzero(initial_left != initial_right)
)

if initial_mismatches != 0:
    raise ValueError(
        f"La igualdad inicial falla: {initial_mismatches} discrepancias."
    )

def rule110_step(values):
    padded = np.pad(values, (1, 1), constant_values=0)

    neighborhoods = (
        4 * padded[:-2] +
        2 * padded[1:-1] +
        padded[2:]
    )

    return ((110 >> neighborhoods) & 1).astype(np.uint8)

results = []

for generation in range(GENERATIONS + 1):

    # El extremo inferior y superior se contraen
    # por el radio 1 de Rule 110 en cada generación.
    lower = start_index + generation
    upper = end_index - generation

    if upper < lower:
        raise RuntimeError("El dominio verificable se agotó.")

    left = state[lower:upper + 1]
    right = state[
        lower + PERIOD:upper + PERIOD + 1
    ]

    mismatches = int(np.count_nonzero(left != right))

    results.append({
        "generation": generation,
        "start_coordinate": minimum + lower,
        "end_coordinate": minimum + upper,
        "compared_pairs": len(left),
        "mismatches": mismatches,
        "match_rate": float(np.mean(left == right)),
        "exact_period_160": mismatches == 0
    })

    if generation < GENERATIONS:
        state = rule110_step(state)

with (OUT / "periodicity_propagation.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(results[0])
    )
    writer.writeheader()
    writer.writerows(results)

report = {
    "experiment": "023_R1_PERIODICITY_PROPAGATION",
    "rule": data["rule"],
    "initial_generation": data["generation"],
    "period": PERIOD,
    "simulated_generations": GENERATIONS,
    "initial_region": {
        "start": START_COORD,
        "end_lower": END_LOWER_COORD,
        "paired_start": START_COORD + PERIOD,
        "paired_end": END_LOWER_COORD + PERIOD,
        "length": END_LOWER_COORD - START_COORD + 1
    },
    "initial_mismatches": initial_mismatches,
    "all_generations_exact": all(
        r["exact_period_160"] for r in results
    ),
    "first_failure": next(
        (r for r in results if not r["exact_period_160"]),
        None
    ),
    "initial_comparisons": results[0]["compared_pairs"],
    "final_comparisons": results[-1]["compared_pairs"],
    "final_mismatches": results[-1]["mismatches"],
    "results": results,
    "snapshot_sha256": hash_before
}

with (OUT / "experiment_023_r1_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot original cambió.")

print("\n=== DSHADOW | EXPERIMENTO 023-R1 ===")
print("Rule:", data["rule"])
print("Initial generation:", data["generation"])
print("Period:", PERIOD)

print("\nINITIAL VALIDATION")
print("Initial mismatches:", initial_mismatches)
print("Initial comparisons:", results[0]["compared_pairs"])

print("\nPROPAGATION")

for r in results:
    if r["generation"] % 10 == 0 or r["generation"] == GENERATIONS:
        print(r)

print("\nSUMMARY")
print("All generations exact:", report["all_generations_exact"])
print("First failure:", report["first_failure"])
print("Final comparisons:", results[-1]["compared_pairs"])
print("Final mismatches:", results[-1]["mismatches"])

print("\nINTEGRITY")
print("SHA256 before:", hash_before)
print("SHA256 after:", hash_after)
print("Integrity:", hash_before == hash_after)

print("\nExperiment 023-R1 completed.")
