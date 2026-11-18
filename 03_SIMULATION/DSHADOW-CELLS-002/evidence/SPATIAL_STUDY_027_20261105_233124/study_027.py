import json, csv, hashlib, sys
from pathlib import Path
from collections import Counter

root = Path.cwd()
out = Path(sys.argv[1])
files = [
    root / "evidence" / "UNIVERSE_EXPORT_20261105_112658" / "universe_snapshot.json",
    *sorted(root.glob("evidence/SPATIAL_STUDY_025_*/live_snapshot.json"))
]

def load_snapshot(path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    active = obj.get("active")
    if not isinstance(active, list):
        raise ValueError(f"No se encontró el array 'active' en {path}")
    coords = sorted(set(map(int, active)))
    return obj, coords, hashlib.sha256(raw).hexdigest()

def analyze(path, window=1000):
    obj, coords, digest = load_snapshot(path)
    if not coords:
        raise ValueError("Snapshot sin coordenadas activas")

    lo = min(coords)
    hi = max(coords)
    active_set = set(coords)
    rows = []

    for start in range(lo, hi + 1, window):
        end = min(start + window - 1, hi)
        count = sum(1 for x in coords if start <= x <= end)
        width = end - start + 1
        rows.append({
            "start": start, "end": end, "width": width,
            "active": count, "density": count / width
        })

    thirds = []
    span = hi - lo + 1
    for name, a, b in [
        ("left", lo, lo + span // 3 - 1),
        ("center", lo + span // 3, lo + 2 * span // 3 - 1),
        ("right", lo + 2 * span // 3, hi)
    ]:
        width = b - a + 1
        count = sum(1 for x in coords if a <= x <= b)
        thirds.append({
            "region": name, "start": a, "end": b,
            "width": width, "active": count,
            "density": count / width
        })

    name = path.parent.name
    csv_path = out / f"{name}_density_windows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    return {
        "snapshot": str(path),
        "generation": obj.get("generation"),
        "active_count": len(coords),
        "min": lo, "max": hi, "span": span,
        "global_density": len(coords) / span,
        "sha256": digest,
        "regions": thirds,
        "windows_csv": str(csv_path)
    }

results = []
for p in files:
    if p.exists():
        results.append(analyze(p))

if not results:
    raise SystemExit("No se encontraron snapshots históricos en las rutas esperadas.")

report = {
    "study": "027 - LIVE DENSITY PROFILE",
    "window_size": 1000,
    "snapshots": results
}
(out / "density_profile_report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)

with (out / "regional_density.csv").open("w", newline="", encoding="utf-8") as f:
    fields = ["generation", "region", "start", "end", "width", "active", "density"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in results:
        for region in r["regions"]:
            w.writerow({"generation": r["generation"], **region})

print(json.dumps(report, indent=2))
print("\n027 COMPLETE. Archivos guardados en:", out)
