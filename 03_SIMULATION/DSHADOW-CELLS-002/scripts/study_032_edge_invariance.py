import json, hashlib, math, sys
from pathlib import Path
from collections import Counter

old_path = Path(sys.argv[1])
new_path = Path(sys.argv[2])
out_dir = Path(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    active = data["active"]
    if not active:
        raise ValueError(f"Snapshot sin celdas activas: {path}")
    active = set(map(int, active))
    lo, hi = min(active), max(active)
    bits = bytearray(1 if x in active else 0 for x in range(lo, hi + 1))
    return {
        "generation": data.get("generation"),
        "active_count": len(active),
        "minimum": lo,
        "maximum": hi,
        "bits": bits,
        "sha256": sha(path)
    }

def entropy(counts, total):
    if not total:
        return 0.0
    return -sum((n/total) * math.log2(n/total) for n in counts.values() if n)

def analyze(bits):
    n = len(bits)
    active = sum(bits)
    density = active / n if n else 0

    patterns = {}
    for k in range(2, 6):
        c = Counter()
        for i in range(n-k+1):
            word = 0
            for b in bits[i:i+k]:
                word = (word << 1) | b
            c[f"{word:0{k}b}"] += 1
        total = max(1, n-k+1)
        patterns[str(k)] = {
            "counts": dict(sorted(c.items())),
            "entropy_bits": entropy(c, total),
            "unique_patterns": len(c),
            "frequencies": {key: value/total for key, value in sorted(c.items())}
        }

    runs = {"active": Counter(), "inactive": Counter()}
    if n:
        current = bits[0]
        length = 1
        for b in bits[1:]:
            if b == current:
                length += 1
            else:
                runs["active" if current else "inactive"][length] += 1
                current, length = b, 1
        runs["active" if current else "inactive"][length] += 1

    run_stats = {}
    for name, counter in runs.items():
        total_runs = sum(counter.values())
        total_cells = sum(k*v for k, v in counter.items())
        run_stats[name] = {
            "run_count": total_runs,
            "mean_length": total_cells/total_runs if total_runs else 0,
            "histogram": dict(sorted(counter.items()))
        }

    acf = {}
    mean = density
    variance = mean * (1-mean)
    for lag in [1, 2, 3, 4, 5, 10, 20, 40, 80, 160, 262, 320]:
        if lag >= n or variance == 0:
            acf[str(lag)] = None
        else:
            cov = sum((bits[i]-mean)*(bits[i+lag]-mean)
                      for i in range(n-lag)) / (n-lag)
            acf[str(lag)] = cov / variance

    return {
        "length": n,
        "active_cells": active,
        "density": density,
        "binary_entropy_bits": entropy(Counter(bits), n),
        "patterns": patterns,
        "runs": run_stats,
        "autocorrelation": acf
    }

old = load(old_path)
new = load(new_path)

# Comparación a igual distancia del borde derecho.
# Ambos snapshots terminan en la coordenada 19.
WINDOW = 50000
regions = {
    "RIGHT_EDGE_50000": (0, WINDOW),
    "INTERIOR_1": (60000, 110000),
    "INTERIOR_2": (120000, 170000),
    "INTERIOR_3": (180000, 230000)
}

def extract(snapshot, distances):
    start, end = distances
    # Distancia 0 corresponde a la coordenada máxima.
    hi = snapshot["maximum"]
    lo = hi - end + 1
    upper = hi - start
    offset = lo - snapshot["minimum"]
    stop = upper - snapshot["minimum"] + 1
    bits = snapshot["bits"][offset:stop]
    if len(bits) != end-start:
        raise ValueError("Ventana incompleta o fuera del snapshot.")
    return bits

results = {
    "study": "032_EDGE_STATISTICAL_INVARIANCE",
    "method": {
        "window_size": WINDOW,
        "regions": regions,
        "pattern_lengths": [2, 3, 4, 5],
        "autocorrelation_lags": [1,2,3,4,5,10,20,40,80,160,262,320],
        "note": "Run histograms include runs cut by window boundaries; interpret edge runs as censored."
    },
    "snapshots": {}
}

for label, snap in [("historical", old), ("live", new)]:
    results["snapshots"][label] = {
        "generation": snap["generation"],
        "active_count": snap["active_count"],
        "minimum": snap["minimum"],
        "maximum": snap["maximum"],
        "sha256": snap["sha256"],
        "regions": {}
    }
    for region, distances in regions.items():
        bits = extract(snap, distances)
        results["snapshots"][label]["regions"][region] = analyze(bits)

# Comparación directa de las distribuciones de patrones.
comparisons = {}
for region in regions:
    a = results["snapshots"]["historical"]["regions"][region]
    b = results["snapshots"]["live"]["regions"][region]
    comparisons[region] = {
        "density_difference_percentage_points":
            (b["density"] - a["density"]) * 100,
        "binary_entropy_difference_bits":
            b["binary_entropy_bits"] - a["binary_entropy_bits"],
        "pattern_frequency_absolute_differences": {},
        "acf_differences": {}
    }
    for k in ["2", "3", "4", "5"]:
        fa, fb = a["patterns"][k]["frequencies"], b["patterns"][k]["frequencies"]
        keys = set(fa) | set(fb)
        comparisons[region]["pattern_frequency_absolute_differences"][k] = {
            key: abs(fa.get(key, 0)-fb.get(key, 0)) for key in sorted(keys)
        }
    for lag in a["autocorrelation"]:
        av, bv = a["autocorrelation"][lag], b["autocorrelation"][lag]
        comparisons[region]["acf_differences"][lag] = (
            abs(bv-av) if av is not None and bv is not None else None
        )

results["cross_snapshot_comparisons"] = comparisons

out_file = out_dir / "study_032_results.json"
out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

# Informe legible y compacto.
lines = [
    "STUDY 032 — EDGE STATISTICAL INVARIANCE",
    f"Historical generation: {old['generation']}",
    f"Live generation: {new['generation']}",
    f"Historical SHA256: {old['sha256']}",
    f"Live SHA256: {new['sha256']}",
    ""
]
for region in regions:
    lines.append(f"=== {region} ===")
    for label in ["historical", "live"]:
        r = results["snapshots"][label]["regions"][region]
        lines.append(
            f"{label}: density={r['density']:.6%}, "
            f"entropy={r['binary_entropy_bits']:.6f}"
        )
        lines.append(
            f"  active runs mean={r['runs']['active']['mean_length']:.4f}; "
            f"inactive runs mean={r['runs']['inactive']['mean_length']:.4f}"
        )
        lines.append(
            "  ACF: " + ", ".join(
                f"{k}={v:.4f}" for k,v in r["autocorrelation"].items()
                if v is not None
            )
        )
        for k in ["2", "3", "4", "5"]:
            lines.append(
                f"  {k}-bit patterns: entropy="
                f"{r['patterns'][k]['entropy_bits']:.5f}, "
                f"unique={r['patterns'][k]['unique_patterns']}"
            )
    lines.append(
        "Density change (pp): "
        f"{comparisons[region]['density_difference_percentage_points']:+.6f}"
    )
    lines.append("")

report = "\n".join(lines)
(out_dir / "study_032_report.txt").write_text(report, encoding="utf-8")
print(report)
print(f"\nJSON: {out_file}")
print(f"REPORT: {out_dir / 'study_032_report.txt'}")
print("\nIntegrity hashes recorded. Source snapshots were not modified.")
