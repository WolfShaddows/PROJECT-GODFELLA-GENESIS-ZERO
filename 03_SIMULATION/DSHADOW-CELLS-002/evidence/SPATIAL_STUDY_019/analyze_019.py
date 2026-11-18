import json
import csv
import hashlib
from pathlib import Path

import numpy as np

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json"
)

OUT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_019"
)

NULL_REPLICATES = 199
SEED = 20261119
MAX_LAG = 256
BLOCKS = 8

raw = SNAPSHOT.read_bytes()
hash_before = hashlib.sha256(raw).hexdigest()
data = json.loads(raw)

active = np.asarray(data["active"], dtype=np.int64)

if len(np.unique(active)) != len(active):
    raise ValueError("Coordenadas duplicadas.")

active.sort()

minimum = int(active[0])
maximum = int(active[-1])
span = maximum - minimum + 1

x = np.zeros(span, dtype=np.float64)
x[active - minimum] = 1.0

density = float(x.mean())
variance = float(x.var())

if variance == 0:
    raise ValueError("Varianza espacial nula.")

# Autocorrelación global:
# (mean(x[i]x[i+k]) - p²) / var(x)
def global_acf(values, max_lag):
    p = float(values.mean())
    var = float(values.var())
    result = []

    for lag in range(1, max_lag + 1):
        joint = float(np.mean(values[:-lag] * values[lag:]))
        result.append((joint - p*p) / var)

    return np.asarray(result)

# Correlación local:
# centra cada uno de los dos segmentos usando su propia media.
def local_acf(values, max_lag):
    result = []

    for lag in range(1, max_lag + 1):
        a = values[:-lag]
        b = values[lag:]

        a_centered = a - a.mean()
        b_centered = b - b.mean()

        denominator = np.sqrt(
            np.sum(a_centered**2) * np.sum(b_centered**2)
        )

        if denominator == 0:
            result.append(float("nan"))
        else:
            result.append(
                float(np.sum(a_centered*b_centered) / denominator)
            )

    return np.asarray(result)

global_values = global_acf(x, MAX_LAG)
local_values = local_acf(x, MAX_LAG)

# Detalle de distancias 140-180.
detail = []

for lag in range(140, 181):
    detail.append({
        "lag": lag,
        "global_acf": float(global_values[lag-1]),
        "local_acf": float(local_values[lag-1])
    })

with (OUT / "lag_140_180.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["lag", "global_acf", "local_acf"]
    )
    writer.writeheader()
    writer.writerows(detail)

# Ocho bloques espaciales contiguos.
block_results = []
block_edges = np.linspace(0, span, BLOCKS + 1, dtype=int)

for i in range(BLOCKS):
    start = int(block_edges[i])
    end = int(block_edges[i+1])
    block = x[start:end]

    if len(block) <= MAX_LAG:
        raise ValueError("Bloque demasiado pequeño.")

    acf = global_acf(block, min(MAX_LAG, len(block)-1))
    peak_lag = int(np.argmax(acf) + 1)

    block_results.append({
        "block": i + 1,
        "start_coordinate": minimum + start,
        "end_coordinate": minimum + end - 1,
        "positions": len(block),
        "density": float(block.mean()),
        "acf_at_160": float(acf[159]),
        "peak_lag_1_256": peak_lag,
        "peak_value": float(acf[peak_lag-1])
    })

with (OUT / "spatial_blocks.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(f, fieldnames=list(block_results[0]))
    writer.writeheader()
    writer.writerows(block_results)

# Controles aleatorios: densidad exactamente preservada.
# Se usa muestreo uniforme de posiciones sin reemplazo.
rng = np.random.default_rng(SEED)

observed_peak = float(np.max(global_values))
observed_peak_lag = int(np.argmax(global_values) + 1)

null_peaks = []
null_at_160 = []

for replica in range(NULL_REPLICATES):
    random_values = np.zeros(span, dtype=np.float64)
    selected = rng.choice(
        span,
        size=len(active),
        replace=False
    )
    random_values[selected] = 1.0

    null_acf = global_acf(random_values, MAX_LAG)

    null_peaks.append(float(np.max(null_acf)))
    null_at_160.append(float(null_acf[159]))

null_peaks = np.asarray(null_peaks)
null_at_160 = np.asarray(null_at_160)

p_global = (
    1 + int(np.count_nonzero(null_peaks >= observed_peak))
) / (NULL_REPLICATES + 1)

p_160 = (
    1 + int(np.count_nonzero(null_at_160 >= global_values[159]))
) / (NULL_REPLICATES + 1)

null_summary = {
    "replicates": NULL_REPLICATES,
    "seed": SEED,
    "null_type": "uniform random occupancy preserving active cell count",
    "observed_max_acf": observed_peak,
    "observed_max_lag": observed_peak_lag,
    "observed_acf_at_160": float(global_values[159]),
    "null_peak_mean": float(null_peaks.mean()),
    "null_peak_sd": float(null_peaks.std(ddof=1)),
    "null_peak_95_percentile": float(np.quantile(null_peaks, 0.95)),
    "empirical_p_global_max": p_global,
    "null_acf_160_mean": float(null_at_160.mean()),
    "null_acf_160_sd": float(null_at_160.std(ddof=1)),
    "empirical_p_lag_160": p_160
}

with (OUT / "null_model_summary.json").open("w", encoding="utf-8") as f:
    json.dump(null_summary, f, indent=2)

with (OUT / "autocorrelation_comparison.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.writer(f)
    writer.writerow(["lag", "global_acf", "local_acf"])

    for lag in range(1, MAX_LAG + 1):
        writer.writerow([
            lag,
            float(global_values[lag-1]),
            float(local_values[lag-1])
        ])

hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot original cambió.")

report = {
    "experiment": "019_SPATIAL_PEAK_VALIDATION",
    "rule": data["rule"],
    "generation": data["generation"],
    "active_cells": len(active),
    "span": span,
    "density": density,
    "snapshot_sha256": hash_before,
    "global_peak": {
        "lag": observed_peak_lag,
        "correlation": observed_peak
    },
    "global_acf_at_160": float(global_values[159]),
    "local_acf_at_160": float(local_values[159]),
    "lag_140_180": detail,
    "blocks": block_results,
    "null_model": null_summary,
    "snapshot_integrity_verified": True,
    "limitations": [
        "Only one historical snapshot was analyzed.",
        "Random controls preserve density and active-cell count, not component or gap distributions.",
        "199 replicas provide coarse empirical p-value resolution.",
        "Spatial blocks are descriptive and are not independent experiments."
    ]
}

with (OUT / "experiment_019_report.json").open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\n=== DSHADOW | EXPERIMENTO 019 ===")
print("Generation:", data["generation"])
print("Active cells:", len(active))
print("Span:", span)
print("Density:", round(density * 100, 9), "%")

print("\nGlobal peak:")
print("Lag:", observed_peak_lag)
print("ACF:", round(observed_peak, 8))

print("\nLag 160:")
print("Global ACF:", round(global_values[159], 8))
print("Local ACF:", round(local_values[159], 8))

print("\nBlocks:")
for b in block_results:
    print(b)

print("\nRandom null:")
print(json.dumps(null_summary, indent=2))

print("\nSnapshot SHA256:", hash_before)
print("Integrity:", hash_before == hash_after)
print("\nExperiment 019 completed.")
