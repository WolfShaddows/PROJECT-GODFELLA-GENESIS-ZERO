import json
import csv
import hashlib
import sys
from pathlib import Path
from math import sqrt

root = Path.cwd()
out = Path(sys.argv[1])

old_path = root / "evidence/UNIVERSE_EXPORT_20261105_112658/universe_snapshot.json"
new_candidates = sorted(root.glob("evidence/SPATIAL_STUDY_025_*/live_snapshot.json"))

if not old_path.exists() or not new_candidates:
    raise SystemExit("No se encontraron los snapshots necesarios.")

new_path = new_candidates[-1]

def load(path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    coords = set(map(int, obj["active"]))
    return {
        "path": str(path),
        "generation": obj.get("generation"),
        "coords": coords,
        "minimum": min(coords),
        "maximum": max(coords),
        "span": max(coords) - min(coords) + 1,
        "sha256": hashlib.sha256(raw).hexdigest()
    }

old = load(old_path)
new = load(new_path)

# Cada vector se orienta desde el borde derecho hacia el interior.
# distance=0 corresponde a la coordenada máxima.
def bit_at(snapshot, distance):
    return int((snapshot["maximum"] - distance) in snapshot["coords"])

def compare_region(a, b, length, side):
    if side == "right":
        va = [bit_at(a, d) for d in range(length)]
        vb = [bit_at(b, d) for d in range(length)]
    else:
        va = [
            int(a["minimum"] + d in a["coords"])
            for d in range(length)
        ]
        vb = [
            int(b["minimum"] + d in b["coords"])
            for d in range(length)
        ]

    matches = sum(x == y for x, y in zip(va, vb))
    mismatches = length - matches
    active_a = sum(va)
    active_b = sum(vb)
    intersection = sum(x == 1 and y == 1 for x, y in zip(va, vb))
    union = sum(x == 1 or y == 1 for x, y in zip(va, vb))

    mean_a = active_a / length
    mean_b = active_b / length

    covariance = sum(
        (x - mean_a) * (y - mean_b)
        for x, y in zip(va, vb)
    ) / length

    var_a = mean_a * (1 - mean_a)
    var_b = mean_b * (1 - mean_b)

    correlation = (
        covariance / sqrt(var_a * var_b)
        if var_a > 0 and var_b > 0 else None
    )

    return {
        "side": side,
        "length": length,
        "matches": matches,
        "mismatches": mismatches,
        "match_rate": matches / length,
        "active_old": active_a,
        "active_new": active_b,
        "density_old": mean_a,
        "density_new": mean_b,
        "jaccard": intersection / union if union else 1.0,
        "binary_pearson": correlation
    }, va, vb

def compare_period_blocks(va, vb, width=160):
    n = len(va) // width
    rows = []

    for i in range(n):
        start = i * width
        end = start + width
        a = va[start:end]
        b = vb[start:end]

        matches = sum(x == y for x, y in zip(a, b))

        rows.append({
            "block_index_from_edge": i,
            "distance_start": start,
            "distance_end": end - 1,
            "width": width,
            "matches": matches,
            "mismatches": width - matches,
            "match_rate": matches / width,
            "old_density": sum(a) / width,
            "new_density": sum(b) / width
        })

    return rows

lengths = [5000, 10000, 20000, 50000]
results = []
block_results = []

print("\n========== EXPERIMENTO 031 ==========")
print("OLD GENERATION:", old["generation"])
print("NEW GENERATION:", new["generation"])
print("OLD MAX:", old["maximum"])
print("NEW MAX:", new["maximum"])

for side in ["right", "left"]:
    common = min(old["span"], new["span"])

    for length in lengths:
        if length > common:
            continue

        summary, va, vb = compare_region(old, new, length, side)
        results.append(summary)

        print(f"\n{side.upper()} EDGE - {length} POSITIONS")
        print("Matches:", summary["matches"])
        print("Mismatches:", summary["mismatches"])
        print(f"Match rate: {summary['match_rate']:.9%}")
        print(f"Old density: {summary['density_old']:.9%}")
        print(f"New density: {summary['density_new']:.9%}")
        print("Jaccard:", summary["jaccard"])
        print("Binary Pearson:", summary["binary_pearson"])

        if side == "right":
            blocks = compare_period_blocks(va, vb, 160)
            block_results.extend([
                {"region_length": length, **r} for r in blocks
            ])

            if length == 50000:
                write_path = out / "right_edge_50000_period160.csv"
                with write_path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=blocks[0].keys())
                    w.writeheader()
                    w.writerows(blocks)

with (out / "region_comparisons.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=results[0].keys())
    w.writeheader()
    w.writerows(results)

with (out / "period160_block_comparisons.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=block_results[0].keys())
    w.writeheader()
    w.writerows(block_results)

report = {
    "study": "031 - RIGHT EDGE STRUCTURAL SIGNATURE",
    "orientation": "distance from corresponding edge toward interior",
    "snapshots": [
        {k: v for k, v in old.items() if k != "coords"},
        {k: v for k, v in new.items() if k != "coords"}
    ],
    "comparisons": results,
    "period160_block_comparisons": {
        "total_blocks": len(block_results),
        "exact_blocks": sum(r["mismatches"] == 0 for r in block_results),
        "different_blocks": sum(r["mismatches"] > 0 for r in block_results)
    }
}

(out / "study_031_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n========== PERIOD 160 ==========")
print("Compared blocks:", report["period160_block_comparisons"]["total_blocks"])
print("Exact blocks:", report["period160_block_comparisons"]["exact_blocks"])
print("Different blocks:", report["period160_block_comparisons"]["different_blocks"])

print("\n========== SNAPSHOT INTEGRITY ==========")
print(old["generation"], old["sha256"])
print(new["generation"], new["sha256"])

print("\n031 COMPLETE")
print("Evidence:", out)
