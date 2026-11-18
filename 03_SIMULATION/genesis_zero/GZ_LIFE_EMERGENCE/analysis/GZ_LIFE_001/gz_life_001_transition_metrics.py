import csv
import numpy as np
from pathlib import Path

SOURCE = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
BASE = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001")

WINDOW = 300
RULES = [109, 137, 67]

with (BASE / "GZ_LIFE_001_PERIOD_ANALYSIS.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    periods = {int(r["rule"]): r for r in csv.DictReader(f)}


def morphology(state):
    active = int(state.sum())

    if active == 0:
        return active, 0, 0

    if active == len(state):
        return active, 1, len(state)

    starts = (state == 1) & (np.roll(state, 1) == 0)
    components = int(starts.sum())

    doubled = np.concatenate((state, state))
    longest = current = 0

    for value in doubled:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return active, components, min(longest, len(state))


def measure(window):
    values = np.array([morphology(s) for s in window])

    names = ["active_cells", "components", "longest_run"]
    result = {}

    for i, name in enumerate(names):
        result[name + "_mean"] = float(values[:, i].mean())
        result[name + "_std"] = float(values[:, i].std())
        result[name + "_min"] = int(values[:, i].min())
        result[name + "_max"] = int(values[:, i].max())

    return result


results = []

print("=== GZ-LIFE-001 | QUANTITATIVE TRANSITION ===")

for rule in RULES:
    with np.load(SOURCE / f"rule_{rule:03d}.npz") as data:
        trajectory = np.unpackbits(
            data["trajectory"],
            axis=1,
            count=256,
            bitorder="big"
        )

    start = int(periods[rule]["transient_length"])
    period = int(periods[rule]["period"])

    before = trajectory[max(0, start-WINDOW):start]
    after = trajectory[start:start+WINDOW]

    # Verificación exacta de un ciclo completo.
    cycle_a = trajectory[start:start+period]
    cycle_b = trajectory[start+period:start+2*period]

    cycle_verified = (
        len(cycle_a) == period
        and len(cycle_b) == period
        and np.array_equal(cycle_a, cycle_b)
    )

    before_stats = measure(before)
    after_stats = measure(after)

    result = {
        "rule": rule,
        "transient": start,
        "period": period,
        "exact_cycle_verified": cycle_verified
    }

    for key, value in before_stats.items():
        result["before_" + key] = value

    for key, value in after_stats.items():
        result["after_" + key] = value

    for metric in ["active_cells_mean", "components_mean", "longest_run_mean"]:
        a = before_stats[metric]
        b = after_stats[metric]
        result[metric + "_difference"] = b - a

    results.append(result)

    print(f"\nRULE {rule}")
    print("Exact periodic cycle verified:", cycle_verified)

    for metric in ["active_cells_mean", "components_mean", "longest_run_mean"]:
        a = before_stats[metric]
        b = after_stats[metric]
        print(f"{metric}: before={a:.4f} | after={b:.4f} | difference={b-a:.4f}")

output = BASE / "GZ_LIFE_001_TRANSITION_METRICS.csv"

with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print("\nCOMPARISON COMPLETED")
print("Saved:", output)
