import json, csv, hashlib, sys
from pathlib import Path
from bisect import bisect_left, bisect_right
from statistics import mean, pstdev

out = Path(sys.argv[1])
root = Path.cwd()

files = [
    root / "evidence" / "UNIVERSE_EXPORT_20261105_112658" / "universe_snapshot.json",
    *sorted(root.glob("evidence/SPATIAL_STUDY_025_*/live_snapshot.json"))
]

def count_range(coords, a, b):
    return bisect_right(coords, b) - bisect_left(coords, a)

def density_rows(coords, lo, hi, width):
    rows = []
    for a in range(lo, hi + 1, width):
        b = min(a + width - 1, hi)
        n = count_range(coords, a, b)
        size = b - a + 1
        rows.append({
            "start": a,
            "end": b,
            "width": size,
            "active": n,
            "density": n / size
        })
    return rows

def analyze(path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    coords = sorted(set(map(int, obj["active"])))

    if not coords:
        raise ValueError(f"Snapshot vacío: {path}")

    lo, hi = coords[0], coords[-1]
    span = hi - lo + 1
    total = len(coords)

    # A. Bloques espaciales de 160 posiciones, anclados al mínimo.
    p160 = density_rows(coords, lo, hi, 160)

    # B. Ventanas de 1000 posiciones.
    p1000 = density_rows(coords, lo, hi, 1000)

    # C. 100 regiones normalizadas de igual extensión aproximada.
    normalized = []
    for i in range(100):
        a = lo + (i * span) // 100
        b = lo + ((i + 1) * span) // 100 - 1
        if b < a:
            continue
        n = count_range(coords, a, b)
        width = b - a + 1
        normalized.append({
            "bin": i,
            "start": a,
            "end": b,
            "width": width,
            "active": n,
            "density": n / width
        })

    # D. Comparación de extremos e interior: bandas del 10%.
    band = max(1, span // 10)
    regions = [
        ("left_10pct", lo, lo + band - 1),
        ("interior_80pct", lo + band, hi - band),
        ("right_10pct", hi - band + 1, hi)
    ]

    regional = []
    for name, a, b in regions:
        n = count_range(coords, a, b)
        width = b - a + 1
        regional.append({
            "region": name,
            "start": a,
            "end": b,
            "width": width,
            "active": n,
            "density": n / width
        })

    # E. Contraste de densidad por tercio.
    thirds = []
    for name, a, b in [
        ("left", lo, lo + span // 3 - 1),
        ("center", lo + span // 3, lo + 2 * span // 3 - 1),
        ("right", lo + 2 * span // 3, hi)
    ]:
        n = count_range(coords, a, b)
        width = b - a + 1
        thirds.append({
            "region": name,
            "start": a,
            "end": b,
            "width": width,
            "active": n,
            "density": n / width
        })

    densities160 = [r["density"] for r in p160]
    summary = {
        "snapshot": str(path),
        "generation": obj.get("generation"),
        "active_count": total,
        "min": lo,
        "max": hi,
        "span": span,
        "global_density": total / span,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "period160_block_count": len(p160),
        "period160_density_mean": mean(densities160),
        "period160_density_sd": pstdev(densities160),
        "period160_density_min": min(densities160),
        "period160_density_max": max(densities160),
        "period160_density_range": max(densities160) - min(densities160),
        "thirds": thirds,
        "edge_bands": regional,
        "normalized_profile": normalized,
        "profile160": p160,
        "profile1000": p1000
    }

    prefix = f"gen_{obj.get('generation', 'unknown')}"
    for key, rows in [
        ("period160", p160),
        ("windows1000", p1000),
        ("normalized100", normalized)
    ]:
        target = out / f"{prefix}_{key}.csv"
        with target.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    return summary

results = []
for path in files:
    if path.exists():
        results.append(analyze(path))

if len(results) < 2:
    raise SystemExit("Se necesitan los dos snapshots históricos para comparar.")

report = {
    "study": "028 - DENSITY ASYMMETRY AND PERIOD-160 PROFILE",
    "snapshots": results
}

(out / "study_028_report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

print("\n========== EXPERIMENTO 028 ==========")

for r in results:
    print(f"\nGENERATION: {r['generation']}")
    print(f"Global density: {r['global_density']:.9%}")
    print(f"Period-160 blocks: {r['period160_block_count']}")
    print(f"Mean block density: {r['period160_density_mean']:.9%}")
    print(f"Block density SD: {r['period160_density_sd']:.9%}")
    print(f"Block density range: {r['period160_density_range']:.9%}")

    print("\nTHIRDS")
    for x in r["thirds"]:
        print(f"  {x['region']:8s} {x['density']:.9%}")

    print("\nEDGE BANDS")
    for x in r["edge_bands"]:
        print(f"  {x['region']:15s} {x['density']:.9%}")

print("\n========== COMPARISON ==========")
for old, new in zip(results, results[1:]):
    print("Global density difference (percentage points):",
          (new["global_density"] - old["global_density"]) * 100)

    for a, b in zip(old["thirds"], new["thirds"]):
        print(f"{a['region']}: old={a['density']:.9%}, new={b['density']:.9%}")

print("\nSnapshot hashes:")
for r in results:
    print(r["generation"], r["sha256"])

print("\n028 COMPLETE")
print("Evidence:", out)
