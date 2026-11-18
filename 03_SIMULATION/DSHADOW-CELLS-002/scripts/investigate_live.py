import urllib.request
import json
import time
import csv
import os
import math
from datetime import datetime

API = "http://127.0.0.1:8765/api/state"
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                   "evidence", "LIVE_INVESTIGATION")

SAMPLES = 12
INTERVAL = 10
BINS = 256

os.makedirs(OUT, exist_ok=True)

def fetch():
    req = urllib.request.Request(API, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def analyze(state):
    positions = sorted(set(int(x) for x in state.get("positions", [])))
    if not positions:
        raise ValueError("API returned no cell positions")

    lo, hi = positions[0], positions[-1]
    span = max(1, hi - lo + 1)
    histogram = [0] * BINS

    for x in positions:
        index = min(BINS - 1, int((x - lo) / span * BINS))
        histogram[index] += 1

    occupied = sum(v > 0 for v in histogram)
    mean = len(positions) / BINS
    variance = sum((v - mean) ** 2 for v in histogram) / BINS
    gaps = []
    current = 0

    for value in histogram:
        current = current + 1 if value == 0 else 0
        gaps.append(current)

    jumps = [abs(histogram[i+1] - histogram[i]) for i in range(BINS-1)]

    return {
        "generation": state.get("generation"),
        "active_cells_api": state.get("active_cells"),
        "unique_positions": len(positions),
        "components": state.get("components"),
        "span_api": state.get("span"),
        "min_x": lo,
        "max_x": hi,
        "running": state.get("running"),
        "status": state.get("status"),
        "speed": state.get("speed"),
        "observer_elapsed": state.get("elapsed"),
        "history_samples": len(state.get("history", [])),
        "occupied_bins": occupied,
        "empty_bins": BINS - occupied,
        "longest_empty_run_bins": max(gaps, default=0),
        "mean_cells_per_bin": round(mean, 3),
        "density_stddev": round(math.sqrt(variance), 3),
        "density_cv": round(math.sqrt(variance) / mean, 5) if mean else 0,
        "largest_adjacent_density_jump": max(jumps, default=0),
        "histogram": histogram
    }

records = []

print("\nDSHADOW-CELLS 002 — LIVE INVESTIGATION")
print("READ-ONLY: no control commands will be sent.")
print(f"Samples: {SAMPLES} | Interval: {INTERVAL}s\n")

for i in range(SAMPLES):
    try:
        result = analyze(fetch())
        result["sample"] = i + 1
        result["timestamp"] = datetime.now().isoformat(timespec="seconds")
        records.append(result)

        print(
            f"[{i+1:02}/{SAMPLES}] "
            f"Gen={result['generation']} | "
            f"Active={result['unique_positions']:,} | "
            f"Components={result['components']:,} | "
            f"Occupied bins={result['occupied_bins']}/{BINS} | "
            f"Longest gap={result['longest_empty_run_bins']} | "
            f"Density CV={result['density_cv']}"
        )
    except Exception as exc:
        print(f"[{i+1:02}/{SAMPLES}] ERROR: {exc}")

    if i < SAMPLES - 1:
        time.sleep(INTERVAL)

if records:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(OUT, f"live_investigation_{stamp}.json")
    csv_path = os.path.join(OUT, f"live_investigation_{stamp}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    columns = [k for k in records[0] if k != "histogram"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{k: row.get(k) for k in columns} for row in records])

    print("\nINVESTIGATION COMPLETE")
    print("Samples:", len(records))
    print("First generation:", records[0]["generation"])
    print("Last generation:", records[-1]["generation"])
    print("Generation delta:",
          records[-1]["generation"] - records[0]["generation"])
    print("JSON:", json_path)
    print("CSV :", csv_path)
else:
    print("No valid samples collected.")
