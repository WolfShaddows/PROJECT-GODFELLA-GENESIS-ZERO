import json
import csv
import hashlib
from pathlib import Path
from collections import Counter

import numpy as np

snapshot = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json")
out = Path(r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_018B")

raw = snapshot.read_bytes()
digest_before = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

active = np.array(sorted(set(data["active"])), dtype=np.int64)

if len(active) != len(data["active"]):
    raise ValueError("Se detectaron coordenadas duplicadas.")

if len(active) < 2:
    raise ValueError("No hay suficientes coordenadas.")

# Reconstrucción de componentes y gaps en orden espacial.
distances = np.diff(active)
breaks = np.where(distances > 1)[0]

components = []
gaps = []

start = 0

for idx in breaks:
    components.append(int(idx + 1 - start))
    gaps.append(int(distances[idx] - 1))
    start = int(idx + 1)

components.append(int(len(active) - start))

# Secuencia de componentes.
with (out / "component_sequence.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["component_index", "start_coordinate", "length"])
    start = 0
    for i, length in enumerate(components):
        writer.writerow([i, int(active[start]), length])
        start += length
        if i < len(gaps):
            start += gaps[i]

# Secuencia de gaps.
with (out / "gap_sequence.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["gap_index", "length"])
    for i, length in enumerate(gaps):
        writer.writerow([i, length])

# Pares componente-gap consecutivos.
with (out / "component_gap_pairs.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["pair_index", "component_length", "following_gap"])
    for i, (component, gap) in enumerate(zip(components[:-1], gaps)):
        writer.writerow([i, component, gap])

# Autocorrelación espacial de la ocupación binaria.
minimum = int(active[0])
maximum = int(active[-1])
span = maximum - minimum + 1

occupancy = np.zeros(span, dtype=np.float64)
occupancy[active - minimum] = 1.0

p = float(occupancy.mean())
variance = p * (1.0 - p)

if variance == 0:
    raise ValueError("La ocupación no presenta variación.")

autocorrelation = []

for lag in range(1, 257):
    left = occupancy[:-lag]
    right = occupancy[lag:]

    covariance = float(np.mean(left * right) - p * p)
    correlation = covariance / variance

    autocorrelation.append({
        "lag": lag,
        "correlation": correlation,
        "joint_active_fraction": float(np.mean(left * right))
    })

with (out / "spatial_autocorrelation.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["lag", "correlation", "joint_active_fraction"]
    )
    writer.writeheader()
    writer.writerows(autocorrelation)

# Frecuencias y transiciones de secuencias.
component_counts = Counter(components)
gap_counts = Counter(gaps)

component_transitions = Counter(zip(components[:-1], components[1:]))
gap_transitions = Counter(zip(gaps[:-1], gaps[1:]))

report = {
    "experiment": "018B_SPATIAL_SEQUENCES_AND_AUTOCORRELATION",
    "rule": data["rule"],
    "generation": data["generation"],
    "active_cells": int(len(active)),
    "spatial_span": int(span),
    "minimum_coordinate": minimum,
    "maximum_coordinate": maximum,
    "component_count": len(components),
    "gap_count": len(gaps),
    "component_length_sum": int(sum(components)),
    "gap_length_sum": int(sum(gaps)),
    "occupancy_density": p,
    "component_length_frequencies": dict(sorted(component_counts.items())),
    "gap_length_frequencies": dict(sorted(gap_counts.items())),
    "most_common_component_transitions": [
        {"from": int(a), "to": int(b), "count": int(n)}
        for (a, b), n in component_transitions.most_common(20)
    ],
    "most_common_gap_transitions": [
        {"from": int(a), "to": int(b), "count": int(n)}
        for (a, b), n in gap_transitions.most_common(20)
    ],
    "strongest_positive_correlations": sorted(
        autocorrelation,
        key=lambda x: x["correlation"],
        reverse=True
    )[:15],
    "strongest_negative_correlations": sorted(
        autocorrelation,
        key=lambda x: x["correlation"]
    )[:15],
    "snapshot_sha256_before": digest_before,
    "interpretation": (
        "Descriptive spatial analysis. Autocorrelation and repeated transitions "
        "do not by themselves establish a causal mechanism or glider structure."
    )
}

(out / "spatial_018B_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

digest_after = hashlib.sha256(snapshot.read_bytes()).hexdigest()

if digest_before != digest_after:
    raise RuntimeError("El hash del snapshot cambió durante el análisis.")

print("\n=== DSHADOW | EXPERIMENTO 018-B ===")
print("Generación:", data["generation"])
print("Celdas activas:", len(active))
print("Componentes:", len(components))
print("Gaps:", len(gaps))
print("Extensión espacial:", span)
print("Densidad:", round(p * 100, 9), "%")

print("\n15 correlaciones espaciales más positivas:")
for item in report["strongest_positive_correlations"]:
    print(item["lag"], round(item["correlation"], 8))

print("\n15 correlaciones espaciales más negativas:")
for item in report["strongest_negative_correlations"]:
    print(item["lag"], round(item["correlation"], 8))

print("\nTransiciones más frecuentes entre componentes:")
for item in report["most_common_component_transitions"][:10]:
    print(item)

print("\nTransiciones más frecuentes entre gaps:")
for item in report["most_common_gap_transitions"][:10]:
    print(item)

print("\nHash original:", digest_before)
print("Hash final:  ", digest_after)
print("Integridad del snapshot:", digest_before == digest_after)
print("\nAnálisis terminado.")
