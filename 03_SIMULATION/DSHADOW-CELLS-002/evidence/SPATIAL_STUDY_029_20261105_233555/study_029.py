import json, csv, hashlib, sys
from pathlib import Path
from bisect import bisect_left, bisect_right
from statistics import mean, pstdev

root = Path.cwd()
out = Path(sys.argv[1])

files = [
    root / "evidence/UNIVERSE_EXPORT_20261105_112658/universe_snapshot.json",
    *sorted(root.glob("evidence/SPATIAL_STUDY_025_*/live_snapshot.json"))
]

def count(coords, a, b):
    return bisect_right(coords, b) - bisect_left(coords, a)

def profile(coords, lo, hi, width):
    rows = []
    for a in range(lo, hi + 1, width):
        b = min(a + width - 1, hi)
        n = count(coords, a, b)
        size = b - a + 1
        rows.append({
            "start": a,
            "end": b,
            "center": (a + b) / 2,
            "width": size,
            "active": n,
            "density": n / size
        })

    for i, row in enumerate(rows):
        row["gradient"] = (
            rows[i + 1]["density"] - row["density"]
            if i + 1 < len(rows) else None
        )
    return rows

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

def analyze(path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    coords = sorted(set(map(int, obj["active"])))

    lo, hi = coords[0], coords[-1]
    span = hi - lo + 1
    global_density = len(coords) / span

    # Perfiles completos.
    p100 = profile(coords, lo, hi, 100)
    p1000 = profile(coords, lo, hi, 1000)

    # Extremos: 20% de cada lado.
    edge = span // 5
    left_end = lo + edge - 1
    right_start = hi - edge + 1

    left100 = [r for r in p100 if r["start"] <= left_end]
    right100 = [r for r in p100 if r["end"] >= right_start]

    left1000 = [r for r in p1000 if r["start"] <= left_end]
    right1000 = [r for r in p1000 if r["end"] >= right_start]

    # Referencia interior: 20%-80%.
    interior_start = lo + span // 5
    interior_end = lo + (4 * span) // 5 - 1
    interior_n = count(coords, interior_start, interior_end)
    interior_density = interior_n / (interior_end - interior_start + 1)

    # Diferencia de densidad entre cada extremo y el interior.
    def stats(rows):
        vals = [r["density"] for r in rows]
        return {
            "windows": len(vals),
            "mean": mean(vals),
            "sd": pstdev(vals),
            "min": min(vals),
            "max": max(vals)
        }

    # Transición: primera ventana de 1000 que queda a más de
    # 0.5 puntos porcentuales por debajo de la densidad interior.
    threshold = interior_density - 0.005

    def transition(rows, direction):
        ordered = rows if direction == "left" else list(reversed(rows))
        selected = [r for r in ordered if r["density"] < threshold]

        if not selected:
            return None

        first = selected[0]
        return {
            "first_low_window_start": first["start"],
            "first_low_window_end": first["end"],
            "first_low_window_density": first["density"],
            "threshold": threshold
        }

    prefix = f"gen_{obj.get('generation', 'unknown')}"

    write_csv(out / f"{prefix}_profile100.csv", p100)
    write_csv(out / f"{prefix}_profile1000.csv", p1000)
    write_csv(out / f"{prefix}_left_edge100.csv", left100)
    write_csv(out / f"{prefix}_right_edge100.csv", right100)

    result = {
        "generation": obj.get("generation"),
        "snapshot": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "minimum": lo,
        "maximum": hi,
        "span": span,
        "active": len(coords),
        "global_density": global_density,
        "interior_density": interior_density,
        "interior_coordinates": [interior_start, interior_end],
        "edge_width": edge,
        "left_20pct": stats(left100),
        "right_20pct": stats(right100),
        "left_20pct_1000": stats(left1000),
        "right_20pct_1000": stats(right1000),
        "left_minus_interior": stats(left1000)["mean"] - interior_density,
        "right_minus_interior": stats(right1000)["mean"] - interior_density,
        "right_minus_left": stats(right1000)["mean"] - stats(left1000)["mean"],
        "left_transition": transition(p1000, "left"),
        "right_transition": transition(p1000, "right"),
        "profile100": p100,
        "profile1000": p1000
    }

    return result

results = []
for path in files:
    if path.exists():
        results.append(analyze(path))

if len(results) < 2:
    raise SystemExit("No se encontraron ambos snapshots.")

report = {
    "study": "029 - EDGE DENSITY TRANSITION",
    "threshold_definition": "Interior density minus 0.005",
    "snapshots": results
}

(out / "study_029_report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

print("\n========== EXPERIMENTO 029 ==========")

for r in results:
    print(f"\nGENERATION: {r['generation']}")
    print(f"Global density: {r['global_density']:.9%}")
    print(f"Interior density: {r['interior_density']:.9%}")

    print("\nEDGE MEANS - WINDOWS OF 1000")
    print(f"Left:  {r['left_20pct_1000']['mean']:.9%}")
    print(f"Right: {r['right_20pct_1000']['mean']:.9%}")
    print(f"Right - Left: {r['right_minus_left']*100:.6f} pp")

    print("\nTRANSITIONS")
    print("Left:", r["left_transition"])
    print("Right:", r["right_transition"])

    print("\nEDGE PROFILE - WINDOWS OF 100")
    print("Left:", r["left_20pct"])
    print("Right:", r["right_20pct"])

print("\n========== PERSISTENCE ==========")
for a, b in zip(results, results[1:]):
    print("Generation pair:", a["generation"], "->", b["generation"])
    print("Left difference:", 
          (b["left_20pct_1000"]["mean"] -
           a["left_20pct_1000"]["mean"]) * 100, "pp")
    print("Right difference:",
          (b["right_20pct_1000"]["mean"] -
           a["right_20pct_1000"]["mean"]) * 100, "pp")

print("\nHashes:")
for r in results:
    print(r["generation"], r["sha256"])

print("\n029 COMPLETE")
print("Evidence:", out)
