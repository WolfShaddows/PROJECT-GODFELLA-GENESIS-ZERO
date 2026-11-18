import csv
import numpy as np
from pathlib import Path

SOURCE = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
OUTPUT = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001")

def morphology(state):
    active = int(state.sum())

    if active == 0:
        return 0, 0, 0

    if active == len(state):
        return active, 1, len(state)

    previous = np.roll(state, 1)
    starts = (state == 1) & (previous == 0)
    components = int(starts.sum())

    doubled = np.concatenate((state, state))
    longest = current = 0

    for value in doubled:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    longest = min(longest, len(state))
    return active, components, longest


def analyze_rule(rule):
    path = SOURCE / f"rule_{rule:03d}.npz"

    with np.load(path) as data:
        trajectory = np.unpackbits(
            data["trajectory"],
            axis=1,
            count=256,
            bitorder="big"
        )

    unique_states = set()
    first_repeat = None

    active_values = []
    component_values = []
    longest_values = []

    for cycle, state in enumerate(trajectory):
        key = state.tobytes()

        if key in unique_states and first_repeat is None:
            first_repeat = cycle
        unique_states.add(key)

        active, components, longest = morphology(state)

        active_values.append(active)
        component_values.append(components)
        longest_values.append(longest)

    return {
        "rule": rule,
        "cycles_recorded": len(trajectory),
        "unique_global_states": len(unique_states),
        "repeated_global_states": len(trajectory) - len(unique_states),
        "first_repeated_state_cycle": first_repeat,
        "mean_active_cells": float(np.mean(active_values)),
        "min_active_cells": int(np.min(active_values)),
        "max_active_cells": int(np.max(active_values)),
        "mean_components": float(np.mean(component_values)),
        "max_components": int(np.max(component_values)),
        "mean_longest_run": float(np.mean(longest_values)),
        "max_longest_run": int(np.max(longest_values)),
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    results = []

    print("=== GENESIS ZERO | GZ-LIFE-001 ===")
    print("Observational census: 256 elementary cellular automata")
    print("Original trajectories: READ ONLY\n")

    for rule in range(256):
        result = analyze_rule(rule)
        results.append(result)

        if (rule + 1) % 32 == 0:
            print(f"Processed: {rule + 1}/256")

    csv_path = OUTPUT / "GZ_LIFE_001_CENSUS.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    report_path = OUTPUT / "GZ_LIFE_001_CENSUS_REPORT.md"

    total_unique = sum(r["unique_global_states"] for r in results)
    total_repeated = sum(r["repeated_global_states"] for r in results)

    with report_path.open("w", encoding="utf-8") as f:
        f.write("# GZ-LIFE-001 — Observational Census\n\n")
        f.write("- Rules analyzed: 256\n")
        f.write("- Recorded states per rule: 10,001\n")
        f.write("- Original trajectories: read-only\n")
        f.write("- No selection, reward, or intervention performed.\n\n")
        f.write("## Aggregate observations\n\n")
        f.write(f"- Total unique states across rule-level counts: {total_unique}\n")
        f.write(f"- Total repeated state occurrences: {total_repeated}\n\n")
        f.write("## Interpretation limits\n\n")
        f.write("- A repeated global state does not establish reproduction.\n")
        f.write("- A connected active run is a spatial measurement, not an organism.\n")
        f.write("- These measurements do not establish persistence of an individual structure.\n")
        f.write("- No claim of digital life is made by this census.\n\n")
        f.write("## Per-rule results\n\n")
        f.write("| Rule | Unique states | Repeated occurrences | First repeat | Mean components | Mean longest run |\n")
        f.write("|---:|---:|---:|---:|---:|---:|\n")

        for r in results:
            f.write(
                f"| {r['rule']} | {r['unique_global_states']} "
                f"| {r['repeated_global_states']} "
                f"| {r['first_repeated_state_cycle']} "
                f"| {r['mean_components']:.3f} "
                f"| {r['mean_longest_run']:.3f} |\n"
            )

    print("\nCENSUS COMPLETED")
    print("Rules analyzed:", len(results))
    print("Unique states (sum of per-rule counts):", total_unique)
    print("Repeated occurrences:", total_repeated)
    print("\nGenerated:")
    print(csv_path)
    print(report_path)


if __name__ == "__main__":
    main()
