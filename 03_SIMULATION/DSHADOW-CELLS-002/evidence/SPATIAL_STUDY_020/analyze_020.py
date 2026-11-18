import json
import csv
import hashlib
from pathlib import Path

import numpy as np

SNAPSHOT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\UNIVERSE_EXPORT_20261105_112658\universe_snapshot.json"
)

OUT = Path(
    r"C:\Users\PC\Desktop\PROJECT GODFELLA\03_SIMULATION\DSHADOW-CELLS-002\evidence\SPATIAL_STUDY_020"
)

SEED = 20261120
REPLICATES = 199
TARGET_LAG = 160
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

x = np.zeros(span, dtype=np.uint8)
x[active - minimum] = 1

density = float(x.mean())

def match_rate(values, lag):
    a = values[:-lag]
    b = values[lag:]
    return float(np.mean(a == b))

def pearson_lag(values, lag):
    a = values[:-lag].astype(np.float64)
    b = values[lag:].astype(np.float64)

    a -= a.mean()
    b -= b.mean()

    denominator = np.sqrt(np.dot(a, a) * np.dot(b, b))

    if denominator == 0:
        return None

    return float(np.dot(a, b) / denominator)

def longest_equal_run(values, lag):
    equal = (values[:-lag] == values[lag:])
    padded = np.concatenate(([False], equal, [False]))
    changes = np.diff(padded.astype(np.int8))

    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]

    lengths = ends - starts

    if len(lengths) == 0:
        return 0

    return int(lengths.max())

# Desplazamientos 150-170.
lag_results = []

for lag in range(150, 171):
    lag_results.append({
        "lag": lag,
        "match_rate": match_rate(x, lag),
        "pearson": pearson_lag(x, lag),
        "longest_equal_run": longest_equal_run(x, lag),
        "compared_pairs": len(x) - lag
    })

with (OUT / "binary_matches_150_170.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "lag", "match_rate", "pearson",
            "longest_equal_run", "compared_pairs"
        ]
    )
    writer.writeheader()
    writer.writerows(lag_results)

# Coincidencia exacta en 160.
lag160 = TARGET_LAG
equal160 = (x[:-lag160] == x[lag160:])

# Regiones de ocho bloques.
edges = np.linspace(0, span, BLOCKS + 1, dtype=int)
block_results = []

for i in range(BLOCKS):
    start = int(edges[i])
    end = int(edges[i+1])
    block = x[start:end]

    block_results.append({
        "block": i + 1,
        "start_coordinate": minimum + start,
        "end_coordinate": minimum + end - 1,
        "positions": len(block),
        "density": float(block.mean()),
        "match_rate_160": match_rate(block, lag160),
        "pearson_160": pearson_lag(block, lag160),
        "longest_equal_run_160": longest_equal_run(block, lag160)
    })

with (OUT / "binary_blocks_160.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(block_results[0])
    )
    writer.writeheader()
    writer.writerows(block_results)

# Controles aleatorios: conserva exactamente el número de unos.
rng = np.random.default_rng(SEED)

null_match = []
null_pearson = []
null_max_match = []

for replica in range(REPLICATES):
    random_x = np.zeros(span, dtype=np.uint8)
    selected = rng.choice(span, size=len(active), replace=False)
    random_x[selected] = 1

    values = [
        match_rate(random_x, lag)
        for lag in range(150, 171)
    ]

    null_match.append(match_rate(random_x, TARGET_LAG))
    null_pearson.append(pearson_lag(random_x, TARGET_LAG))
    null_max_match.append(max(values))

null_match = np.asarray(null_match)
null_pearson = np.asarray(null_pearson)
null_max_match = np.asarray(null_max_match)

observed_match = match_rate(x, TARGET_LAG)
observed_pearson = pearson_lag(x, TARGET_LAG)
observed_max_match = max(r["match_rate"] for r in lag_results)

p_match = (
    1 + int(np.count_nonzero(null_match >= observed_match))
) / (REPLICATES + 1)

p_max = (
    1 + int(np.count_nonzero(null_max_match >= observed_max_match))
) / (REPLICATES + 1)

null_summary = {
    "replicates": REPLICATES,
    "seed": SEED,
    "null_model": "uniform random positions preserving active cell count",
    "observed_match_rate_160": observed_match,
    "observed_pearson_160": observed_pearson,
    "null_match_mean_160": float(null_match.mean()),
    "null_match_sd_160": float(null_match.std(ddof=1)),
    "null_match_95_percentile": float(np.quantile(null_match, 0.95)),
    "empirical_p_match_160": p_match,
    "observed_max_match_150_170": observed_max_match,
    "null_max_match_95_percentile": float(
        np.quantile(null_max_match, 0.95)
    ),
    "empirical_p_max_match_150_170": p_max
}

with (OUT / "null_comparison.json").open("w", encoding="utf-8") as f:
    json.dump(null_summary, f, indent=2)

# Resumen de segmentos idénticos en lag 160.
report = {
    "experiment": "020_BINARY_SPATIAL_MATCHING",
    "rule": data["rule"],
    "generation": data["generation"],
    "active_cells": len(active),
    "spatial_span": span,
    "density": density,
    "target_lag": TARGET_LAG,
    "compared_pairs_160": len(equal160),
    "matching_pairs_160": int(equal160.sum()),
    "nonmatching_pairs_160": int((~equal160).sum()),
    "match_rate_160": observed_match,
    "pearson_160": observed_pearson,
    "longest_equal_run_160": longest_equal_run(x, TARGET_LAG),
    "lag_results": lag_results,
    "blocks": block_results,
    "null_model": null_summary,
    "snapshot_sha256": hash_before
}

with (OUT / "experiment_020_report.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

hash_after = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

if hash_before != hash_after:
    raise RuntimeError("El snapshot original cambió.")

print("\n=== DSHADOW | EXPERIMENTO 020 ===")
print("Generation:", data["generation"])
print("Active cells:", len(active))
print("Span:", span)

print("\nMATCHING AT LAG 160")
print("Compared pairs:", len(equal160))
print("Matching pairs:", int(equal160.sum()))
print("Match rate:", round(observed_match, 9))
print("Pearson:", round(observed_pearson, 9))
print("Longest equal run:", longest_equal_run(x, TARGET_LAG))

print("\nLAGS 150-170")
for r in lag_results:
    print(
        r["lag"],
        round(r["match_rate"], 8),
        round(r["pearson"], 8),
        r["longest_equal_run"]
    )

print("\nBLOCKS")
for b in block_results:
    print(b)

print("\nRANDOM CONTROLS")
print(json.dumps(null_summary, indent=2))

print("\nSHA256 before:", hash_before)
print("SHA256 after:", hash_after)
print("Integrity:", hash_before == hash_after)

print("\nExperiment 020 completed.")
