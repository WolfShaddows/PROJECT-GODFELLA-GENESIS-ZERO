import json
import csv
import hashlib
from pathlib import Path
from collections import Counter

import numpy as np

snapshot = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json")
out = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_018B_R1")

raw = snapshot.read_bytes()
hash_before = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

active = np.array(data["active"], dtype=np.int64)

if len(np.unique(active)) != len(active):
    raise ValueError("Hay coordenadas duplicadas.")

active.sort()

distances = np.diff(active)
breaks = np.where(distances > 1)[0]

components = []
gaps = []

start_index = 0

for idx in breaks:
    components.append({
        "start": int(active[start_index]),
        "end": int(active[idx]),
        "length": int(idx + 1 - start_index)
    })

    gaps.append(int(distances[idx] - 1))
    start_index = int(idx + 1)

components.append({
    "start": int(active[start_index]),
    "end": int(active[-1]),
    "length": int(len(active) - start_index)
})

component_lengths = [c["length"] for c in components]

# Secuencia de componentes: usa coordenadas reales.
with (out / "component_sequence.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["component_index", "start_coordinate", "end_coordinate", "length"])

    for i, c in enumerate(components):
        writer.writerow([i, c["start"], c["end"], c["length"]])

# Secuencia de gaps.
with (out / "gap_sequence.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["gap_index", "length"])

    for i, gap in enumerate(gaps):
        writer.writerow([i, gap])

# Pares componente-gap.
with (out / "component_gap_pairs.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["pair_index", "component_length", "following_gap"])

    for i, (component, gap) in enumerate(zip(component_lengths[:-1], gaps)):
        writer.writerow([i, component, gap])

# Autocorrelación espacial binaria.
minimum = int(active[0])
maximum = int(active[-1])
span = maximum - minimum + 1

occupancy = np.zeros(span, dtype=np.float64)
occupancy[active - minimum] = 1.0

p = float(occupancy.mean())
variance = p * (1.0 - p)

autocorrelation = []

for lag in range(1, 257):
    left = occupancy[:-lag]
    right = occupancy[lag:]

    joint = float(np.mean(left * right))
    correlation = (joint - p * p) / variance

    autocorrelation.append({
        "lag": lag,
        "correlation": correlation,
        "joint_active_fraction": joint
    })

with (out / "spatial_autocorrelation.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "lag", "correlation", "joint_active_fraction"
    ])
    writer.writeheader()
    writer.writerows(autocorrelation)

component_transitions = Counter(zip(component_lengths[:-1], component_lengths[1:]))
gap_transitions = Counter(zip(gaps[:-1], gaps[1:]))

report = {
    "experiment": "018B_SPATIAL_SEQUENCES_AND_AUTOCORRELATION_R1",
    "rule": data["rule"],
    "generation": data["generation"],
    "active_cells": len(active),
    "spatial_span": span,
    "component_count": len(components),
    "gap_count": len(gaps),
    "component_length_sum": sum(component_lengths),
    "gap_length_sum": sum(gaps),
    "occupancy_density": p,
    "component_length_frequencies": dict(sorted(Counter(component_lengths).items())),
    "gap_length_frequencies": dict(sorted(Counter(gaps).items())),
    "most_common_component_transitions": [
        {"from": int(a), "to": int(b), "count": int(n)}
        for (a, b), n in component_transitions.most_common(20)
    ],
    "most_common_gap_transitions": [
        {"from": int(a), "to": int(b), "count": int(n)}
        for (a, b), n in gap_transitions.most_common(20)
    ],
    "strongest_positive_correlations": sorted(
        autocorrelation, key=lambda x: x["correlation"], reverse=True
    )[:15],
    "strongest_negative_correlations": sorted(
        autocorrelation, key=lambda x: x["correlation"]
    )[:15],
    "snapshot_sha256": hash_before
}

(out / "spatial_018B_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

hash_after = hashlib.sha256(snapshot.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot cambió durante el análisis.")

if len(components) != 62181 or len(gaps) != 62180:
    raise RuntimeError("La reconstrucción no coincide con los controles previos.")

if sum(component_lengths) != len(active):
    raise RuntimeError("La suma de componentes no coincide con las celdas activas.")

print("\n=== DSHADOW | 018-B-R1 ===")
print("Generación:", data["generation"])
print("Celdas activas:", len(active))
print("Componentes:", len(components))
print("Gaps:", len(gaps))
print("Suma de componentes:", sum(component_lengths))
print("Densidad:", round(p * 100, 9), "%")

print("\nCorrelaciones positivas:")
for item in report["strongest_positive_correlations"]:
    print(item["lag"], round(item["correlation"], 8))

print("\nCorrelaciones negativas:")
for item in report["strongest_negative_correlations"]:
    print(item["lag"], round(item["correlation"], 8))

print("\nTransiciones de componentes:")
for item in report["most_common_component_transitions"][:10]:
    print(item)

print("\nTransiciones de gaps:")
for item in report["most_common_gap_transitions"][:10]:
    print(item)

print("\nSHA256 antes:", hash_before)
print("SHA256 después:", hash_after)
print("Integridad:", hash_before == hash_after)
print("\nAnálisis completado correctamente.")
