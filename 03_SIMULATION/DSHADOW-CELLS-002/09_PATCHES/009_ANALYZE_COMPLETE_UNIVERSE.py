import json
import csv
import math
import statistics
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "evidence" / "UNIVERSE_EXPORT_20261105_112658"
SNAPSHOT = EXPORT / "universe_snapshot.json"
HISTORY = ROOT / "logs" / "observations.jsonl"

with SNAPSHOT.open("r", encoding="utf-8-sig") as f:
    data = json.load(f)

cells = sorted(set(map(int, data["active"])))

if len(cells) != len(data["active"]):
    raise RuntimeError("Se detectaron coordenadas duplicadas.")

n = len(cells)
lo, hi = cells[0], cells[-1]
span = hi - lo + 1

gaps = []
for a, b in zip(cells, cells[1:]):
    gaps.append(b - a - 1)

components = 1 + sum(g > 0 for g in gaps) if n else 0
occupied = span - sum(gaps)

def quantile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high-index) + ordered[high] * (index-low)

def histogram(sectors):
    counts = [0] * sectors
    for x in cells:
        index = min(sectors - 1, ((x - lo) * sectors) // span)
        counts[index] += 1

    mean = statistics.mean(counts)
    std = statistics.pstdev(counts)
    return {
        "sectors": sectors,
        "counts": counts,
        "mean": mean,
        "stddev": std,
        "cv": std / mean if mean else 0,
        "occupied_sectors": sum(c > 0 for c in counts),
        "empty_sectors": sum(c == 0 for c in counts),
        "minimum": min(counts),
        "maximum": max(counts)
    }

h256 = histogram(256)
h1024 = histogram(1024)

gap_counter = Counter(gaps)
largest_gaps = sorted(
    [{"gap": g, "left": cells[i], "right": cells[i+1]}
     for i, g in enumerate(gaps) if g > 0],
    key=lambda x: x["gap"],
    reverse=True
)[:100]

distance_values = [g + 1 for g in gaps]

edge_width = max(1, math.ceil(span * 0.05))
left_count = sum(x < lo + edge_width for x in cells)
right_count = sum(x > hi - edge_width for x in cells)

history_rows = []
if HISTORY.exists():
    with HISTORY.open("r", encoding="utf-8-sig") as f:
        for line in f:
            try:
                row = json.loads(line)
                history_rows.append(row)
            except json.JSONDecodeError:
                continue

history_rows.sort(key=lambda x: x.get("generation", 0))

def trend(field):
    values = [r[field] for r in history_rows if field in r]
    if len(values) < 2:
        return None
    return {
        "first": values[0],
        "last": values[-1],
        "change": values[-1] - values[0],
        "minimum": min(values),
        "maximum": max(values)
    }

report = {
    "experiment": data.get("experiment"),
    "run_id": data.get("run_id"),
    "rule": data.get("rule"),
    "seed": data.get("seed"),
    "generation": data.get("generation"),
    "population": {
        "active_cells": n,
        "unique_cells": n,
        "components": components,
        "occupied_coordinates": occupied,
        "minimum_x": lo,
        "maximum_x": hi,
        "spatial_span": span,
        "occupancy_ratio": n / span
    },
    "gaps": {
        "number_of_gaps": len(gaps),
        "nonzero_gaps": sum(g > 0 for g in gaps),
        "maximum": max(gaps, default=0),
        "mean": statistics.mean(gaps) if gaps else 0,
        "median": statistics.median(gaps) if gaps else 0,
        "p90": quantile(gaps, 0.90),
        "p95": quantile(gaps, 0.95),
        "p99": quantile(gaps, 0.99),
        "gap_frequency": {str(k): v for k, v in sorted(gap_counter.items())},
        "largest_gaps": largest_gaps
    },
    "inter_cell_distance": {
        "mean": statistics.mean(distance_values) if distance_values else None,
        "median": statistics.median(distance_values) if distance_values else None,
        "p95": quantile(distance_values, 0.95),
        "maximum": max(distance_values, default=None)
    },
    "spatial_density": {
        "256": {k:v for k,v in h256.items() if k != "counts"},
        "1024": {k:v for k,v in h1024.items() if k != "counts"}
    },
    "edges": {
        "edge_width_coordinates": edge_width,
        "leftmost_5pct_cells": left_count,
        "rightmost_5pct_cells": right_count
    },
    "historical_observations": {
        "records": len(history_rows),
        "generation": trend("generation"),
        "active": trend("active"),
        "components": trend("components"),
        "span": trend("span")
    }
}

with (EXPORT / "universe_analysis_report.json").open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

for name, result in [("256", h256), ("1024", h1024)]:
    with (EXPORT / f"spatial_density_{name}.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["sector", "x_start", "x_end", "active_cells"])
        for i, count in enumerate(result["counts"]):
            start = lo + (i * span // result["sectors"])
            end = lo + ((i + 1) * span // result["sectors"]) - 1
            writer.writerow([i, start, end, count])

with (EXPORT / "largest_gaps.csv").open(
    "w", newline="", encoding="utf-8-sig"
) as f:
    writer = csv.DictWriter(
        f, fieldnames=["gap", "left", "right"]
    )
    writer.writeheader()
    writer.writerows(largest_gaps)

with (EXPORT / "historical_observations.csv").open(
    "w", newline="", encoding="utf-8-sig"
) as f:
    fields = ["generation", "active", "components", "span", "min_x", "max_x"]
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(history_rows)

print("\n========== DSHADOW UNIVERSE ANALYSIS ==========")
print(f"Generation:             {data.get('generation')}")
print(f"Active cells:           {n:,}")
print(f"Components:             {components:,}")
print(f"Spatial span:           {span:,}")
print(f"Occupancy ratio:        {n/span:.6%}")
print(f"Nonzero gaps:           {sum(g > 0 for g in gaps):,}")
print(f"Largest empty gap:      {max(gaps, default=0):,}")
print(f"Mean gap:               {statistics.mean(gaps):.4f}")
print(f"256 occupied sectors:   {h256['occupied_sectors']}/256")
print(f"1024 occupied sectors:  {h1024['occupied_sectors']}/1024")
print(f"Density CV (256):       {h256['cv']:.6f}")
print(f"Density CV (1024):      {h1024['cv']:.6f}")
print(f"Historical records:     {len(history_rows):,}")
print("\nOUTPUT:")
print(EXPORT)
print("\nAnalysis completed.")
