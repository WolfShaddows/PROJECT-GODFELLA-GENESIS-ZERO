import os
import json
import csv
import hashlib
from pathlib import Path

import numpy as np

OLD_PATH = Path(os.environ["DSHADOW_OLD_SNAPSHOT"])
NEW_PATH = Path(os.environ["DSHADOW_NEW_SNAPSHOT"])
PREVIOUS_REPORT = Path(os.environ["DSHADOW_PREVIOUS_REPORT"])
OUT = Path(os.environ["DSHADOW_OUTPUT"])

PERIOD = 160

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_snapshot(path):
    raw = path.read_bytes()
    data = json.loads(raw)

    if int(data["rule"]) != 110:
        raise ValueError(f"Regla inesperada en {path}")

    active = np.asarray(data["active"], dtype=np.int64)
    active.sort()

    if len(active) == 0:
        raise ValueError("Snapshot vacío.")

    if len(np.unique(active)) != len(active):
        raise ValueError("Coordenadas duplicadas.")

    minimum = int(active[0])
    maximum = int(active[-1])

    state = np.zeros(
        maximum - minimum + 1,
        dtype=np.uint8
    )

    state[active - minimum] = 1

    return {
        "data": data,
        "state": state,
        "minimum": minimum,
        "maximum": maximum,
        "sha256": sha256(path)
    }

old = load_snapshot(OLD_PATH)
new = load_snapshot(NEW_PATH)

previous = json.loads(PREVIOUS_REPORT.read_text(encoding="utf-8"))

segment = previous["longest_exact_segment"]

if segment is None:
    raise ValueError("El experimento 025 no contiene un segmento exacto.")

start_coord = int(segment["start"])
end_coord = int(segment["end"])

if int(segment["length"]) != end_coord - start_coord + 1:
    raise ValueError("Longitud del segmento inconsistente.")

minimum = new["minimum"]
state = new["state"]

start_index = start_coord - minimum
end_index = end_coord - minimum

if start_index < 0 or end_index + PERIOD >= len(state):
    raise ValueError("El segmento no cabe en el snapshot.")

# Confirmar que el segmento original sigue siendo exacto.
left = state[start_index:end_index + 1]
right = state[
    start_index + PERIOD:end_index + PERIOD + 1
]

initial_mismatches = int(
    np.count_nonzero(left != right)
)

if initial_mismatches != 0:
    raise ValueError(
        f"El segmento ya no es exacto: {initial_mismatches} discrepancias."
    )

# Región completa: incluye el segmento y su copia desplazada.
region_start = start_index
region_end = end_index + PERIOD

region = state[region_start:region_end + 1]

# Evaluar todos los períodos entre 1 y 160.
period_results = []

for p in range(1, PERIOD + 1):
    mismatches = int(
        np.count_nonzero(region[:-p] != region[p:])
    )

    period_results.append({
        "period": p,
        "comparisons": len(region) - p,
        "mismatches": mismatches,
        "exact": mismatches == 0
    })

fundamental_candidates = [
    r["period"]
    for r in period_results
    if r["exact"]
]

fundamental_period = (
    min(fundamental_candidates)
    if fundamental_candidates else None
)

with (OUT / "period_exactness_001_160.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(period_results[0])
    )
    writer.writeheader()
    writer.writerows(period_results)

# Bloques completos de 160 alineados al inicio del segmento.
block_count = len(region) // PERIOD

blocks = []

for i in range(block_count):
    block = region[i * PERIOD:(i + 1) * PERIOD]
    blocks.append(block)

reference_block = blocks[0]

different_blocks = sum(
    not np.array_equal(block, reference_block)
    for block in blocks
)

with (OUT / "aligned_blocks_160.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    fields = [
        "block_number",
        "start_coordinate",
        "end_coordinate",
        "matches_reference",
        "active_cells"
    ]

    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for i, block in enumerate(blocks):
        writer.writerow({
            "block_number": i + 1,
            "start_coordinate": start_coord + i * PERIOD,
            "end_coordinate": start_coord + (i + 1) * PERIOD - 1,
            "matches_reference": bool(
                np.array_equal(block, reference_block)
            ),
            "active_cells": int(np.count_nonzero(block))
        })

# Guardar patrón de referencia.
pattern = "".join(str(int(v)) for v in reference_block)

(OUT / "reference_pattern_160.txt").write_text(
    pattern + "\n",
    encoding="utf-8"
)

# Comparar fase espacial absoluta con el snapshot histórico.
# Se buscan coordenadas múltiplos de 160 dentro de las regiones.
def aligned_pattern(snapshot, lower, upper):
    anchor = ((lower + PERIOD - 1) // PERIOD) * PERIOD

    index = anchor - snapshot["minimum"]

    if anchor + PERIOD - 1 > upper:
        raise ValueError("No existe bloque alineado completo.")

    return (
        anchor,
        snapshot["state"][index:index + PERIOD]
    )

old_anchor, old_pattern = aligned_pattern(
    old,
    -284870,
    -39804
)

new_anchor, new_pattern = aligned_pattern(
    new,
    start_coord,
    end_coord
)

direct_matches = int(
    np.count_nonzero(old_pattern == new_pattern)
)

# Evaluar también las 160 fases circulares posibles.
phase_scores = []

for shift in range(PERIOD):
    rotated = np.roll(old_pattern, shift)

    matches = int(
        np.count_nonzero(rotated == new_pattern)
    )

    phase_scores.append({
        "shift": shift,
        "matches": matches,
        "match_rate": matches / PERIOD
    })

phase_scores.sort(
    key=lambda r: r["matches"],
    reverse=True
)

with (OUT / "historical_pattern_comparison.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(phase_scores[0])
    )
    writer.writeheader()
    writer.writerows(phase_scores)

old_hash_before = sha256(OLD_PATH)
new_hash_before = sha256(NEW_PATH)

old_hash_after = sha256(OLD_PATH)
new_hash_after = sha256(NEW_PATH)

integrity = (
    old_hash_before == old_hash_after
    and new_hash_before == new_hash_after
)

if not integrity:
    raise RuntimeError("Falló la verificación SHA256.")

report = {
    "experiment": "026_FUNDAMENTAL_PERIOD_VALIDATION",
    "rule": 110,
    "old_generation": old["data"]["generation"],
    "new_generation": new["data"]["generation"],
    "source_segment": {
        "start": start_coord,
        "end": end_coord,
        "length": len(left)
    },
    "complete_region": {
        "start": start_coord,
        "end": end_coord + PERIOD,
        "length": len(region)
    },
    "initial_mismatches": initial_mismatches,
    "tested_periods": PERIOD,
    "exact_periods": fundamental_candidates,
    "fundamental_period": fundamental_period,
    "complete_blocks": block_count,
    "different_blocks": different_blocks,
    "all_blocks_identical": different_blocks == 0,
    "old_aligned_anchor": old_anchor,
    "new_aligned_anchor": new_anchor,
    "direct_phase_matches": direct_matches,
    "direct_phase_match_rate": direct_matches / PERIOD,
    "best_phase_comparison": phase_scores[0],
    "old_snapshot_sha256": old_hash_before,
    "new_snapshot_sha256": new_hash_before,
    "snapshot_integrity": integrity
}

with (OUT / "experiment_026_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

print("\n=== DSHADOW | EXPERIMENTO 026 ===")

print("\nSNAPSHOTS")
print("Old generation:", old["data"]["generation"])
print("New generation:", new["data"]["generation"])

print("\nREGION")
print("Start:", start_coord)
print("End:", end_coord + PERIOD)
print("Length:", len(region))
print("Initial mismatches:", initial_mismatches)

print("\nFUNDAMENTAL PERIOD")
print("Exact periods:", fundamental_candidates)
print("Fundamental period:", fundamental_period)

print("\nBLOCK VALIDATION")
print("Complete blocks:", block_count)
print("Different blocks:", different_blocks)
print("All identical:", different_blocks == 0)

print("\nHISTORICAL PATTERN")
print("Old anchor:", old_anchor)
print("New anchor:", new_anchor)
print("Direct phase matches:", direct_matches, "/", PERIOD)
print("Best phase comparison:", phase_scores[0])

print("\nINTEGRITY")
print("Old snapshot SHA256:", old_hash_before)
print("New snapshot SHA256:", new_hash_before)
print("Integrity:", integrity)

print("\nExperiment 026 completed.")
