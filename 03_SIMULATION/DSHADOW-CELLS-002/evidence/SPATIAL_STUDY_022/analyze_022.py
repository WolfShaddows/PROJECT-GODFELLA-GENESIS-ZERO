import json
import csv
import hashlib
from pathlib import Path

import numpy as np

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json"
)

OUT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_022"
)

START_COORD = -284870
END_LOWER_COORD = -39804
TARGET_PERIOD = 160
MAX_PERIOD = 160

raw = SNAPSHOT.read_bytes()
hash_before = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

active = np.asarray(data["active"], dtype=np.int64)
active.sort()

if len(np.unique(active)) != len(active):
    raise ValueError("Coordenadas duplicadas.")

minimum = int(active[0])
maximum = int(active[-1])

if START_COORD < minimum or END_LOWER_COORD + TARGET_PERIOD > maximum:
    raise ValueError("La región solicitada excede el snapshot.")

span = maximum - minimum + 1
x = np.zeros(span, dtype=np.uint8)
x[active - minimum] = 1

# El intervalo completo incluye también las posiciones desplazadas.
region_start = START_COORD - minimum
region_end = END_LOWER_COORD + TARGET_PERIOD - minimum

region = x[region_start:region_end + 1]

region_start_coord = START_COORD
region_end_coord = END_LOWER_COORD + TARGET_PERIOD

def period_metrics(values, period):
    left = values[:-period]
    right = values[period:]
    mismatches = int(np.count_nonzero(left != right))

    return {
        "period": period,
        "compared_pairs": len(left),
        "mismatches": mismatches,
        "match_rate": float(np.mean(left == right)),
        "exact": mismatches == 0
    }

# --------------------------------------------------
# 1. Comprobar períodos de 1 a 160.
# --------------------------------------------------

period_results = [
    period_metrics(region, p)
    for p in range(1, MAX_PERIOD + 1)
]

with (OUT / "period_exactness_001_160.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "period", "compared_pairs",
            "mismatches", "match_rate", "exact"
        ]
    )
    writer.writeheader()
    writer.writerows(period_results)

exact_periods = [
    r["period"] for r in period_results if r["exact"]
]

fundamental_period = min(exact_periods) if exact_periods else None

# --------------------------------------------------
# 2. Comparación de bloques de 160 alineados.
# --------------------------------------------------

block_size = TARGET_PERIOD
complete_blocks = len(region) // block_size
reference = region[:block_size]

block_results = []

for index in range(complete_blocks):
    start = index * block_size
    block = region[start:start + block_size]

    matches = int(np.count_nonzero(reference == block))

    block_results.append({
        "block_index": index,
        "start_coordinate": region_start_coord + start,
        "end_coordinate": region_start_coord + start + block_size - 1,
        "matching_bits": matches,
        "block_size": block_size,
        "match_rate": matches / block_size,
        "identical_to_reference": matches == block_size
    })

with (OUT / "aligned_blocks_160.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(block_results[0])
    )
    writer.writeheader()
    writer.writerows(block_results)

# --------------------------------------------------
# 3. Verificación de fase en ventanas sucesivas.
# --------------------------------------------------

phase_results = []
window_size = 10000

for start in range(0, len(region), window_size):
    window = region[start:start + window_size]

    if len(window) <= TARGET_PERIOD:
        continue

    metrics = period_metrics(window, TARGET_PERIOD)

    phase_results.append({
        "start_coordinate": region_start_coord + start,
        "end_coordinate": region_start_coord + start + len(window) - 1,
        "positions": len(window),
        "mismatches_at_160": metrics["mismatches"],
        "match_rate_at_160": metrics["match_rate"],
        "exact_at_160": metrics["exact"]
    })

with (OUT / "phase_windows_10000.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(phase_results[0])
    )
    writer.writeheader()
    writer.writerows(phase_results)

# --------------------------------------------------
# 4. Guardar patrón de referencia y resumen.
# --------------------------------------------------

reference_pattern = "".join(str(int(v)) for v in reference)

(OUT / "reference_pattern_160.txt").write_text(
    reference_pattern,
    encoding="utf-8"
)

report = {
    "experiment": "022_FUNDAMENTAL_PERIOD_AND_PHASE",
    "rule": data["rule"],
    "generation": data["generation"],
    "region_start": region_start_coord,
    "region_end": region_end_coord,
    "region_length": len(region),
    "region_density": float(region.mean()),
    "target_period": TARGET_PERIOD,
    "period_search": {
        "minimum_tested": 1,
        "maximum_tested": MAX_PERIOD,
        "exact_periods": exact_periods,
        "fundamental_period": fundamental_period
    },
    "aligned_blocks": {
        "block_size": block_size,
        "complete_blocks": complete_blocks,
        "identical_to_first_block": sum(
            b["identical_to_reference"] for b in block_results
        ),
        "nonidentical_to_first_block": sum(
            not b["identical_to_reference"] for b in block_results
        )
    },
    "phase_windows": {
        "window_size": window_size,
        "total_windows": len(phase_results),
        "exact_windows": sum(
            w["exact_at_160"] for w in phase_results
        ),
        "total_mismatches": sum(
            w["mismatches_at_160"] for w in phase_results
        )
    },
    "snapshot_sha256": hash_before
}

with (OUT / "experiment_022_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot original cambió.")

print("\n=== DSHADOW | EXPERIMENTO 022 ===")

print("\nREGION")
print("Start:", region_start_coord)
print("End:", region_end_coord)
print("Length:", len(region))
print("Density:", float(region.mean()))

print("\nEXACT PERIODS")
print(exact_periods)
print("Fundamental period:", fundamental_period)

print("\nPERIODS 1-160")
for result in period_results:
    if result["period"] <= 30 or result["period"] in [
        32, 40, 48, 64, 80, 96, 120, 128, 160
    ]:
        print(result)

print("\nALIGNED BLOCKS")
print("Complete blocks:", complete_blocks)
print("Identical to first:", report["aligned_blocks"]["identical_to_first_block"])
print("Different from first:", report["aligned_blocks"]["nonidentical_to_first_block"])

print("\nPHASE WINDOWS")
for result in phase_results:
    print(result)

print("\nINTEGRITY")
print("SHA256 before:", hash_before)
print("SHA256 after:", hash_after)
print("Integrity:", hash_before == hash_after)

print("\nExperiment 022 completed.")
