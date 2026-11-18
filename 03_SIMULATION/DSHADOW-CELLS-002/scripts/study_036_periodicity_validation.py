import json
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

SNAPSHOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

SEED = 360036
NULL_REPS = 199
MAX_LAG = 2048
BASE_PERIOD = 160
WINDOW = 20000
WINDOW_STEP = 10000

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_bits(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    active = np.asarray(data["active"], dtype=np.int64)

    if len(active) == 0:
        raise ValueError("Snapshot vacío.")

    if len(np.unique(active)) != len(active):
        raise ValueError("Coordenadas activas duplicadas.")

    lo, hi = int(active.min()), int(active.max())
    bits = np.zeros(hi-lo+1, dtype=np.uint8)
    bits[active-lo] = 1

    return data, bits, lo, hi

def acf_fft(bits, max_lag):
    x = bits.astype(np.float64)
    n = len(x)
    centered = x - x.mean()
    variance = np.dot(centered, centered) / n

    if variance == 0:
        raise ValueError("Varianza nula.")

    size = 1 << (2*n-1).bit_length()
    spectrum = np.fft.rfft(centered, size)
    raw = np.fft.irfft(
        spectrum * np.conjugate(spectrum), size
    )[:max_lag+1]

    return np.array([
        raw[lag] / ((n-lag)*variance)
        for lag in range(max_lag+1)
    ])

def lag_match(bits, lag):
    a = bits[:-lag]
    b = bits[lag:]
    matches = int(np.count_nonzero(a == b))
    total = len(a)
    return {
        "lag": lag,
        "comparisons": total,
        "matches": matches,
        "mismatches": total-matches,
        "match_rate": matches/total,
        "acf": float(np.corrcoef(a, b)[0, 1])
    }

def region_analysis(bits, start, end, label):
    segment = bits[start:end]
    if len(segment) <= MAX_LAG:
        return None

    acf = acf_fft(segment, MAX_LAG)
    lags = list(range(BASE_PERIOD, MAX_LAG+1, BASE_PERIOD))

    return {
        "region": label,
        "start_index": start,
        "end_index": end-1,
        "length": len(segment),
        "density": float(segment.mean()),
        "acf_at_multiples": {
            str(lag): float(acf[lag]) for lag in lags
        },
        "acf_160": float(acf[160]),
        "acf_800": float(acf[800])
    }

started = time.time()
initial_hash = sha256(SNAPSHOT)
data, bits, lo, hi = load_bits(SNAPSHOT)

n = len(bits)
density = float(bits.mean())
active_count = int(bits.sum())

print("STUDY 036 — PERIODICITY DEEP VALIDATION")
print(f"Generation: {data.get('generation')}")
print(f"Length: {n:,}")
print(f"Active cells: {active_count:,}")
print(f"Density: {density:.9%}")
print(f"Snapshot SHA256: {initial_hash}")

# -------------------------------------------------
# 1. GLOBAL AUTOCORRELATION
# -------------------------------------------------

print("\n[1/6] Global autocorrelation...")

acf = acf_fft(bits, MAX_LAG)

multiples = list(range(BASE_PERIOD, MAX_LAG+1, BASE_PERIOD))

multiple_results = []

for lag in multiples:
    result = lag_match(bits, lag)
    result["acf_fft"] = float(acf[lag])
    multiple_results.append(result)

top_peaks = sorted(
    [
        {"lag": lag, "acf": float(acf[lag])}
        for lag in range(1, MAX_LAG+1)
    ],
    key=lambda x: x["acf"],
    reverse=True
)[:50]

# -------------------------------------------------
# 2. LOCAL WINDOWS
# -------------------------------------------------

print("[2/6] Local periodicity windows...")

local_results = []

for start in range(0, n-WINDOW+1, WINDOW_STEP):
    segment = bits[start:start+WINDOW]

    local_acf = acf_fft(segment, 800)

    local_results.append({
        "start_index": start,
        "end_index": start+WINDOW-1,
        "density": float(segment.mean()),
        "acf_160": float(local_acf[160]),
        "acf_320": float(local_acf[320]),
        "acf_800": float(local_acf[800]),
        "match_160": lag_match(segment, 160)["match_rate"],
        "match_800": lag_match(segment, 800)["match_rate"]
    })

# -------------------------------------------------
# 3. REGIONAL ANALYSIS
# -------------------------------------------------

print("[3/6] Regional periodicity...")

third = n//3

regions = {
    "LEFT_THIRD": (0, third),
    "CENTER_THIRD": (third, 2*third),
    "RIGHT_THIRD": (2*third, n),
    "FIRST_100K": (0, min(100000, n)),
    "MIDDLE_100K": (max(0, n//2-50000), min(n, n//2+50000)),
    "LAST_100K": (max(0, n-100000), n)
}

regional_results = {}

for name, (start, end) in regions.items():
    regional_results[name] = region_analysis(
        bits, start, end, name
    )

# -------------------------------------------------
# 4. DENSITY-PRESERVING RANDOM NULL
# -------------------------------------------------

print(f"[4/6] Density-preserving null ({NULL_REPS} permutations)...")

rng = np.random.default_rng(SEED)

observed_max = max(float(acf[lag]) for lag in multiples)
observed_mean = float(np.mean([acf[lag] for lag in multiples]))
observed_800 = float(acf[800])

null_max = []
null_mean = []
null_800 = []

for rep in range(NULL_REPS):
    shuffled = bits.copy()
    rng.shuffle(shuffled)

    null_acf = acf_fft(shuffled, MAX_LAG)
    values = np.array([null_acf[lag] for lag in multiples])

    null_max.append(float(values.max()))
    null_mean.append(float(values.mean()))
    null_800.append(float(null_acf[800]))

    if (rep+1) % 25 == 0:
        print(f"  Null simulations: {rep+1}/{NULL_REPS}")

null_max = np.asarray(null_max)
null_mean = np.asarray(null_mean)
null_800 = np.asarray(null_800)

p_max = (
    1 + int(np.count_nonzero(null_max >= observed_max))
) / (NULL_REPS+1)

p_mean = (
    1 + int(np.count_nonzero(null_mean >= observed_mean))
) / (NULL_REPS+1)

p_800 = (
    1 + int(np.count_nonzero(null_800 >= observed_800))
) / (NULL_REPS+1)

null_results = {
    "method": "uniform permutation preserving exact active-cell count",
    "seed": SEED,
    "replications": NULL_REPS,
    "tested_lags": multiples,
    "observed_max_acf": observed_max,
    "observed_mean_acf": observed_mean,
    "observed_acf_800": observed_800,
    "max_acf_null_mean": float(null_max.mean()),
    "max_acf_null_sd": float(null_max.std(ddof=1)),
    "max_acf_null_95": float(np.quantile(null_max, 0.95)),
    "mean_acf_null_mean": float(null_mean.mean()),
    "acf_800_null_mean": float(null_800.mean()),
    "acf_800_null_95": float(np.quantile(null_800, 0.95)),
    "p_max_empirical": p_max,
    "p_mean_empirical": p_mean,
    "p_800_empirical": p_800,
    "p_resolution": 1/(NULL_REPS+1)
}

# -------------------------------------------------
# 5. EXACT AND APPROXIMATE MATCHING
# -------------------------------------------------

print("[5/6] Match and mismatch analysis...")

match_summary = {}

for lag in multiples:
    item = lag_match(bits, lag)
    match_summary[str(lag)] = item

# -------------------------------------------------
# 6. INTEGRITY AND RESULTS
# -------------------------------------------------

print("[6/6] Writing evidence...")

final_hash = sha256(SNAPSHOT)

results = {
    "study": "036_PERIODICITY_DEEP_VALIDATION",
    "snapshot": {
        "generation": data.get("generation"),
        "minimum_coordinate": lo,
        "maximum_coordinate": hi,
        "length": n,
        "active_cells": active_count,
        "density": density,
        "sha256_before": initial_hash,
        "sha256_after": final_hash,
        "integrity_verified": initial_hash == final_hash
    },
    "parameters": {
        "base_period": BASE_PERIOD,
        "maximum_lag": MAX_LAG,
        "local_window": WINDOW,
        "local_window_step": WINDOW_STEP
    },
    "multiples_of_160": multiple_results,
    "top_global_acf_peaks": top_peaks,
    "local_windows": local_results,
    "regional_analysis": regional_results,
    "density_preserving_null": null_results,
    "match_summary": match_summary,
    "interpretation_limits": [
        "Uniform shuffling preserves density but destroys all spatial dependence.",
        "A significant result against this null does not prove a period-generating mechanism.",
        "Overlapping local windows are not independent observations.",
        "Autocorrelation peaks are not proof of mobile structures or life.",
        "The global exact-period search previously found no exact period up to 2048."
    ],
    "runtime_seconds": time.time()-started
}

result_path = OUT/"study_036_results.json"
result_path.write_text(
    json.dumps(results, indent=2),
    encoding="utf-8"
)

# CSV: global multiples
import csv

with open(OUT/"multiples_160.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=multiple_results[0].keys())
    writer.writeheader()
    writer.writerows(multiple_results)

# CSV: local windows
with open(OUT/"local_periodicity.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=local_results[0].keys())
    writer.writeheader()
    writer.writerows(local_results)

# Human-readable report
lines = [
    "DSHADOW-CELLS-002",
    "STUDY 036 — PERIODICITY DEEP VALIDATION",
    "",
    f"Generation: {data.get('generation')}",
    f"Active cells: {active_count:,}",
    f"Density: {density:.9%}",
    f"Snapshot integrity: {initial_hash == final_hash}",
    "",
    "MULTIPLES OF 160"
]

for item in multiple_results:
    lines.append(
        f"Lag {item['lag']:4}: "
        f"ACF={item['acf_fft']:.9f}; "
        f"match={item['match_rate']:.6%}; "
        f"mismatches={item['mismatches']:,}"
    )

lines += [
    "",
    "REGIONAL RESULTS"
]

for name, item in regional_results.items():
    if item:
        lines.append(
            f"{name}: density={item['density']:.6%}; "
            f"ACF160={item['acf_160']:.6f}; "
            f"ACF800={item['acf_800']:.6f}"
        )

lines += [
    "",
    "DENSITY-PRESERVING NULL",
    f"Replications: {NULL_REPS}",
    f"Observed max ACF: {observed_max:.9f}",
    f"Null max mean: {null_max.mean():.9f}",
    f"Null max 95th percentile: {np.quantile(null_max,0.95):.9f}",
    f"Empirical p max: {p_max:.6f}",
    f"Observed ACF 800: {observed_800:.9f}",
    f"Null ACF 800 mean: {null_800.mean():.9f}",
    f"Empirical p 800: {p_800:.6f}",
    "",
    "TOP GLOBAL PEAKS"
]

for item in top_peaks[:20]:
    lines.append(f"Lag {item['lag']}: {item['acf']:.9f}")

lines += [
    "",
    f"SHA256: {final_hash}",
    f"Runtime: {time.time()-started:.2f} seconds",
    "",
    "No causal mechanism or life claim is established by this experiment."
]

report = "\n".join(lines)
(OUT/"study_036_report.txt").write_text(report, encoding="utf-8")

print("\n" + report)
print(f"\nJSON: {result_path}")
print(f"REPORT: {OUT/'study_036_report.txt'}")
print(f"OUTPUT: {OUT}")
