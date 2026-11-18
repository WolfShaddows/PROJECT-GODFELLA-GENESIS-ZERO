import json
import hashlib
import math
import sys
import time
from pathlib import Path
from collections import Counter
import numpy as np

snapshot_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

MAX_PERIOD = 2048
MAX_ACF_LAG = 2048
PATTERN_MAX = 16
BLOCK_SIZE = 1000

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def entropy(counter, total):
    if total <= 0:
        return 0.0
    return -sum(
        (v/total) * math.log2(v/total)
        for v in counter.values() if v
    )

def safe_json(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)

def runs(bits):
    active = Counter()
    inactive = Counter()

    if len(bits) == 0:
        return active, inactive

    current = int(bits[0])
    length = 1

    for value in bits[1:]:
        value = int(value)
        if value == current:
            length += 1
        else:
            (active if current else inactive)[length] += 1
            current = value
            length = 1

    (active if current else inactive)[length] += 1
    return active, inactive

def run_summary(counter):
    n = sum(counter.values())
    cells = sum(k*v for k, v in counter.items())

    return {
        "count": n,
        "cells": cells,
        "mean": cells/n if n else 0,
        "median": (
            float(np.median(
                [k for k, v in counter.items() for _ in range(v)]
            )) if n < 1000000 and n else None
        ),
        "histogram": dict(sorted(counter.items()))
    }

def pattern_analysis(bits, k):
    count = len(bits)-k+1
    if count <= 0:
        return {}

    codes = np.zeros(count, dtype=np.uint32)

    for j in range(k):
        codes = (codes << 1) | bits[j:j+count]

    hist = np.bincount(codes, minlength=2**k)
    total = int(hist.sum())

    return {
        "entropy": entropy(
            {i: int(v) for i, v in enumerate(hist) if v},
            total
        ),
        "unique_patterns": int(np.count_nonzero(hist)),
        "frequencies": {
            format(i, f"0{k}b"): float(v/total)
            for i, v in enumerate(hist) if v
        }
    }

def autocorrelation(bits, max_lag):
    x = bits.astype(np.float64)
    n = len(x)
    mean = float(x.mean())
    centered = x-mean

    variance = float(np.dot(centered, centered)/n)

    if variance == 0:
        return {}

    # FFT-based autocorrelation.
    size = 1 << (2*n-1).bit_length()
    spectrum = np.fft.rfft(centered, size)
    raw = np.fft.irfft(spectrum*np.conjugate(spectrum), size)[:max_lag+1]

    result = {}

    for lag in range(max_lag+1):
        denom = (n-lag)*variance
        result[str(lag)] = float(raw[lag]/denom) if denom else None

    return result

def density_profile(bits, block_size):
    result = []

    for start in range(0, len(bits), block_size):
        block = bits[start:start+block_size]
        result.append({
            "start_index": start,
            "end_index": start+len(block)-1,
            "length": len(block),
            "active": int(block.sum()),
            "density": float(block.mean())
        })

    return result

def exact_periods(bits, maximum):
    n = len(bits)
    result = []

    for period in range(1, min(maximum, n//2)+1):
        # Compare every position for which a translated pair exists.
        mismatches = int(np.count_nonzero(
            bits[:-period] != bits[period:]
        ))

        if mismatches == 0:
            result.append({
                "period": period,
                "comparisons": n-period,
                "mismatches": 0
            })

    return result

def load_snapshot(path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if "active" not in data:
        raise ValueError("Snapshot does not contain 'active'.")

    active = np.asarray(data["active"], dtype=np.int64)

    if len(active) == 0:
        raise ValueError("Empty active set.")

    if len(np.unique(active)) != len(active):
        raise ValueError("Duplicate active coordinates detected.")

    lo = int(active.min())
    hi = int(active.max())

    bits = np.zeros(hi-lo+1, dtype=np.uint8)
    bits[active-lo] = 1

    return data, active, bits, lo, hi

started = time.time()
original_hash = sha256(snapshot_path)

data, active, bits, lo, hi = load_snapshot(snapshot_path)

n = len(bits)
active_count = int(bits.sum())
density = active_count/n

print("\n============================================")
print(" STUDY 035 — DEEP UNIVERSE FORENSIC ANALYSIS")
print("============================================")
print(f"Generation: {data.get('generation')}")
print(f"Rule: {data.get('rule', 'not declared in snapshot')}")
print(f"Active cells: {active_count:,}")
print(f"Coordinates: {lo:,} to {hi:,}")
print(f"Spatial span: {n:,}")
print(f"Density: {density:.9%}")
print(f"SHA256: {original_hash}")
print("\nAnalyzing structure...")

# --------------------------------------------------
# COMPONENTS AND GAPS
# --------------------------------------------------

active_runs, inactive_runs = runs(bits)

component_count = sum(active_runs.values())
gap_count = sum(inactive_runs.values())

components = run_summary(active_runs)
gaps = run_summary(inactive_runs)

# --------------------------------------------------
# PATTERN DISTRIBUTIONS
# --------------------------------------------------

patterns = {}

for k in range(1, PATTERN_MAX+1):
    patterns[str(k)] = pattern_analysis(bits, k)
    print(f"Pattern length {k}: "
          f"{patterns[str(k)]['unique_patterns']} observed patterns")

# --------------------------------------------------
# AUTOCORRELATION
# --------------------------------------------------

acf = autocorrelation(bits, MAX_ACF_LAG)

ranked_acf = sorted(
    [
        {"lag": int(k), "value": v}
        for k, v in acf.items()
        if int(k) > 0 and v is not None
    ],
    key=lambda x: abs(x["value"]),
    reverse=True
)

# --------------------------------------------------
# EXACT PERIOD SEARCH
# --------------------------------------------------

periods = exact_periods(bits, MAX_PERIOD)

# --------------------------------------------------
# SPATIAL PROFILE
# --------------------------------------------------

profile = density_profile(bits, BLOCK_SIZE)

# --------------------------------------------------
# REGIONAL ANALYSIS
# --------------------------------------------------

thirds = {}

for name, start, end in [
    ("left", 0, n//3),
    ("center", n//3, 2*n//3),
    ("right", 2*n//3, n)
]:
    section = bits[start:end]
    thirds[name] = {
        "start_index": start,
        "end_index": end-1,
        "length": len(section),
        "active": int(section.sum()),
        "density": float(section.mean())
    }

# --------------------------------------------------
# EDGE PROFILES
# --------------------------------------------------

edge_size = min(50000, n//2)

edges = {
    "left": bits[:edge_size],
    "right": bits[-edge_size:]
}

edge_results = {}

for name, section in edges.items():
    ar, ir = runs(section)

    edge_results[name] = {
        "length": len(section),
        "density": float(section.mean()),
        "active_runs": run_summary(ar),
        "inactive_runs": run_summary(ir),
        "patterns": {
            str(k): pattern_analysis(section, k)
            for k in range(1, 9)
        }
    }

# --------------------------------------------------
# COMPONENT / GAP RELATIONSHIPS
# --------------------------------------------------

component_lengths = []
gap_lengths = []

# Extract runs in coordinate order.
current = int(bits[0])
length = 1

for value in bits[1:]:
    value = int(value)

    if value == current:
        length += 1
    else:
        if current:
            component_lengths.append(length)
        else:
            gap_lengths.append(length)
        current = value
        length = 1

if current:
    component_lengths.append(length)
else:
    gap_lengths.append(length)

component_gap_pairs = []

for i in range(min(len(component_lengths), len(gap_lengths))):
    component_gap_pairs.append({
        "component_length": component_lengths[i],
        "following_gap_length": gap_lengths[i]
    })

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

final_hash = sha256(snapshot_path)

results = {
    "study": "035_DEEP_UNIVERSE_FORENSIC_ANALYSIS",
    "snapshot": {
        "file": str(snapshot_path),
        "generation": data.get("generation"),
        "rule": data.get("rule"),
        "minimum_coordinate": lo,
        "maximum_coordinate": hi,
        "spatial_span": n,
        "active_cells": active_count,
        "density": density,
        "sha256_before": original_hash,
        "sha256_after": final_hash,
        "integrity_verified": original_hash == final_hash
    },
    "structure": {
        "components": component_count,
        "gaps": gap_count,
        "component_lengths": components,
        "gap_lengths": gaps,
        "component_gap_pairs_sample": component_gap_pairs[:10000]
    },
    "regional_density": thirds,
    "edge_analysis": edge_results,
    "patterns": patterns,
    "autocorrelation": {
        "max_lag": MAX_ACF_LAG,
        "top_absolute_correlations": ranked_acf[:100],
        "all_lags": acf
    },
    "exact_periods": {
        "maximum_tested": MAX_PERIOD,
        "periods_found": periods
    },
    "density_profile": {
        "block_size": BLOCK_SIZE,
        "blocks": profile
    },
    "runtime_seconds": time.time()-started,
    "scientific_limitations": [
        "A single spatial snapshot cannot establish temporal persistence.",
        "Spatial periodicity does not prove life or reproduction.",
        "Autocorrelation peaks do not independently prove causal structure.",
        "Rule 110 dynamics require spacetime tracking for mobile structures.",
        "The analysis does not infer intelligence, agency, or biological life."
    ]
}

result_path = out_dir/"study_035_results.json"

result_path.write_text(
    json.dumps(results, indent=2, default=safe_json),
    encoding="utf-8"
)

# --------------------------------------------------
# HUMAN-READABLE REPORT
# --------------------------------------------------

lines = [
    "DSHADOW-CELLS-002",
    "STUDY 035 — DEEP UNIVERSE FORENSIC ANALYSIS",
    "",
    f"Generation: {data.get('generation')}",
    f"Rule: {data.get('rule')}",
    f"Active cells: {active_count:,}",
    f"Spatial span: {n:,}",
    f"Coordinates: {lo:,} to {hi:,}",
    f"Density: {density:.9%}",
    f"Components: {component_count:,}",
    f"Gaps: {gap_count:,}",
    "",
    "COMPONENT STATISTICS",
    f"Mean length: {components['mean']:.8f}",
    f"Median length: {components['median']}",
    f"Unique lengths: {len(components['histogram'])}",
    "",
    "GAP STATISTICS",
    f"Mean length: {gaps['mean']:.8f}",
    f"Median length: {gaps['median']}",
    f"Unique lengths: {len(gaps['histogram'])}",
    "",
    "REGIONAL DENSITY"
]

for name, value in thirds.items():
    lines.append(f"{name}: {value['density']:.9%}")

lines += [
    "",
    "EXACT PERIODS",
    str(periods),
    "",
    "TOP AUTOCORRELATION PEAKS"
]

for item in ranked_acf[:25]:
    lines.append(
        f"lag={item['lag']} correlation={item['value']:.9f}"
    )

lines += [
    "",
    "EDGE DENSITIES",
    f"Left: {edge_results['left']['density']:.9%}",
    f"Right: {edge_results['right']['density']:.9%}",
    "",
    "PATTERN ENTROPY"
]

for k, item in patterns.items():
    lines.append(
        f"{k} bits: entropy={item['entropy']:.9f}; "
        f"unique={item['unique_patterns']}"
    )

lines += [
    "",
    f"SHA256 integrity verified: {original_hash == final_hash}",
    f"Analysis time: {time.time()-started:.2f} seconds",
    "",
    "This is a spatial snapshot analysis, not proof of life."
]

report = "\n".join(lines)

(out_dir/"study_035_report.txt").write_text(
    report, encoding="utf-8"
)

# CSV exports
import csv

with open(out_dir/"density_profile.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=profile[0].keys())
    writer.writeheader()
    writer.writerows(profile)

with open(out_dir/"autocorrelation.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["lag", "correlation"])
    for lag, value in acf.items():
        writer.writerow([lag, value])

print("\n" + report)
print("\n============================================")
print(" STUDY 035 COMPLETED")
print("============================================")
print(f"JSON: {result_path}")
print(f"REPORT: {out_dir/'study_035_report.txt'}")
print(f"CSV: {out_dir/'density_profile.csv'}")
print(f"CSV: {out_dir/'autocorrelation.csv'}")
print(f"SHA256: {final_hash}")
