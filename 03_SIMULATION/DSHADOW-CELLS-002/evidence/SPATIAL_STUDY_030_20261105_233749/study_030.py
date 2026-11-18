import json
import csv
import hashlib
import sys
from pathlib import Path
from bisect import bisect_left, bisect_right
from statistics import mean, pstdev

root = Path.cwd()
out = Path(sys.argv[1])

files = [
    root / "evidence/UNIVERSE_EXPORT_20261105_112658/universe_snapshot.json",
    *sorted(root.glob("evidence/SPATIAL_STUDY_025_*/live_snapshot.json"))
]

WINDOWS = [100, 1000]
SUSTAINED_WINDOWS = 5
THRESHOLD_DROP = 0.005  # 0.5 puntos porcentuales bajo la referencia interior

def count_range(coords, a, b):
    return bisect_right(coords, b) - bisect_left(coords, a)

def make_edge_profile(coords, lo, hi, width, side):
    span = hi - lo + 1
    n_full = span // width
    rows = []

    for i in range(n_full):
        if side == "left":
            a = lo + i * width
            b = a + width - 1
            distance_start = i * width
        else:
            b = hi - i * width
            a = b - width + 1
            distance_start = i * width

        active = count_range(coords, a, b)

        rows.append({
            "side": side,
            "window_index": i,
            "distance_start": distance_start,
            "distance_end": distance_start + width - 1,
            "start": a,
            "end": b,
            "width": width,
            "active": active,
            "density": active / width
        })

    # Gradiente orientado desde el extremo hacia el interior.
    for i, row in enumerate(rows):
        if i + 1 < len(rows):
            row["gradient_inward"] = (
                rows[i + 1]["density"] - row["density"]
            )
        else:
            row["gradient_inward"] = None

    return rows

def find_sustained_drop(rows, baseline, threshold):
    cutoff = baseline - threshold

    for i in range(len(rows) - SUSTAINED_WINDOWS + 1):
        group = rows[i:i + SUSTAINED_WINDOWS]

        if all(r["density"] < cutoff for r in group):
            return {
                "first_window_index": i,
                "distance_start": group[0]["distance_start"],
                "distance_end": group[-1]["distance_end"],
                "first_coordinate_start": group[0]["start"],
                "first_coordinate_end": group[0]["end"],
                "last_coordinate_start": group[-1]["start"],
                "last_coordinate_end": group[-1]["end"],
                "mean_density": mean(r["density"] for r in group),
                "baseline_density": baseline,
                "cutoff_density": cutoff,
                "consecutive_windows": SUSTAINED_WINDOWS
            }

    return None

def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

def analyze(path):
    raw = path.read_bytes()
    obj = json.loads(raw)

    if not isinstance(obj.get("active"), list):
        raise ValueError(f"Missing active array: {path}")

    coords = sorted(set(map(int, obj["active"])))

    if not coords:
        raise ValueError(f"Empty snapshot: {path}")

    lo, hi = coords[0], coords[-1]
    span = hi - lo + 1
    total = len(coords)

    # Baseline interior: central 60% of the coordinate span.
    interior_start = lo + span // 5
    interior_end = lo + (4 * span) // 5 - 1
    interior_width = interior_end - interior_start + 1
    interior_active = count_range(coords, interior_start, interior_end)
    interior_density = interior_active / interior_width

    result = {
        "generation": obj.get("generation"),
        "snapshot": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "minimum": lo,
        "maximum": hi,
        "span": span,
        "active": total,
        "global_density": total / span,
        "interior_coordinates": [interior_start, interior_end],
        "interior_density": interior_density,
        "profiles": {}
    }

    prefix = f"gen_{obj.get('generation', 'unknown')}"

    for width in WINDOWS:
        for side in ["left", "right"]:
            rows = make_edge_profile(coords, lo, hi, width, side)

            densities = [r["density"] for r in rows]
            transition = find_sustained_drop(
                rows, interior_density, THRESHOLD_DROP
            )

            summary = {
                "window_width": width,
                "side": side,
                "full_windows": len(rows),
                "mean_density": mean(densities),
                "sd_density": pstdev(densities),
                "min_density": min(densities),
                "max_density": max(densities),
                "transition": transition
            }

            key = f"{side}_{width}"
            result["profiles"][key] = summary

            write_csv(
                out / f"{prefix}_{key}.csv",
                rows
            )

    return result

results = []

for path in files:
    if path.exists():
        results.append(analyze(path))

if len(results) < 2:
    raise SystemExit("Both historical snapshots are required.")

report = {
    "study": "030 - EDGE-ALIGNED DENSITY PROFILE",
    "window_widths": WINDOWS,
    "sustained_drop_windows": SUSTAINED_WINDOWS,
    "threshold_drop": THRESHOLD_DROP,
    "threshold_definition": "Interior density minus 0.005",
    "partial_windows": "Excluded",
    "snapshots": results
}

(out / "study_030_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n========== EXPERIMENTO 030 ==========")

for r in results:
    print(f"\nGENERATION: {r['generation']}")
    print(f"Global density: {r['global_density']:.9%}")
    print(f"Interior density: {r['interior_density']:.9%}")
    print(f"SHA256: {r['sha256']}")

    for key, s in r["profiles"].items():
        print(f"\nPROFILE {key}")
        print(f"Full windows: {s['full_windows']}")
        print(f"Mean density: {s['mean_density']:.9%}")
        print(f"SD: {s['sd_density']:.9%}")
        print(f"Min: {s['min_density']:.9%}")
        print(f"Max: {s['max_density']:.9%}")
        print("Sustained transition:", s["transition"])

print("\n========== CROSS-SNAPSHOT COMPARISON ==========")

for old, new in zip(results, results[1:]):
    print(f"\n{old['generation']} -> {new['generation']}")

    for key in old["profiles"]:
        a = old["profiles"][key]
        b = new["profiles"][key]

        print(
            key,
            "mean difference (pp):",
            (b["mean_density"] - a["mean_density"]) * 100
        )

        ta = a["transition"]
        tb = b["transition"]

        print("Old transition:", ta)
        print("New transition:", tb)

print("\n========== INTEGRITY ==========")
for r in results:
    print(r["generation"], r["sha256"])

print("\n030 COMPLETE")
print("Evidence:", out)
