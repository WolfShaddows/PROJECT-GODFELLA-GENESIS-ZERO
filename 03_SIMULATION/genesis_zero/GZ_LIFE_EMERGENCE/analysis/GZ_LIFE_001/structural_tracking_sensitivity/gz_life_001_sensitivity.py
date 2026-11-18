import csv
import json
import time
import hashlib
import numpy as np
from pathlib import Path
from collections import Counter, deque

RAW = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
OUT = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001/structural_tracking_sensitivity")

RULES = {
    67: (702, 512),
    109: (1482, 2760),
    137: (1058, 960),
}

CONFIGS = [
    ("A", 0, 0.50),
    ("B", 1, 0.50),
    ("C", 3, 0.50),
    ("D", 5, 0.50),
    ("E", 3, 0.70),
    ("F", 3, 0.90),
]

N = 256
FULL_MASK = (1 << N) - 1


def load_trajectory(rule):
    path = RAW / f"rule_{rule:03d}.npz"

    with np.load(path, allow_pickle=False) as data:
        packed = data["trajectory"]
        trajectory = np.unpackbits(
            packed, axis=1, count=N, bitorder="big"
        )
        final_state = data["final_state"]

    if trajectory.shape != (10001, N):
        raise ValueError(f"Unexpected trajectory shape for rule {rule}")

    if not np.array_equal(trajectory[-1], final_state):
        raise ValueError(f"Final state mismatch for rule {rule}")

    return trajectory


def components_as_masks(state):
    active = np.flatnonzero(state)

    if len(active) == 0:
        return []

    active_set = set(int(x) for x in active)
    unseen = set(active_set)
    result = []

    while unseen:
        start = unseen.pop()
        component = [start]
        queue = [start]

        while queue:
            cell = queue.pop()

            for neighbor in ((cell - 1) % N, (cell + 1) % N):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
                    component.append(neighbor)

        mask = 0
        for cell in component:
            mask |= 1 << cell

        result.append(mask)

    return result


def rotate_mask(mask, shift):
    shift %= N
    if shift == 0:
        return mask
    return ((mask << shift) | (mask >> (N - shift))) & FULL_MASK


def best_jaccard(a, b, max_shift):
    best = 0.0
    best_shift = 0
    best_intersection = 0

    for shift in range(-max_shift, max_shift + 1):
        shifted = rotate_mask(a, shift)
        intersection = (shifted & b).bit_count()
        union = (shifted | b).bit_count()

        score = intersection / union if union else 1.0

        if score > best:
            best = score
            best_shift = shift
            best_intersection = intersection

    return best, best_shift, best_intersection


def classify_graph(previous, current, max_shift, threshold):
    old_count = len(previous)
    new_count = len(current)

    old_adj = [[] for _ in previous]
    new_adj = [[] for _ in current]
    match_count = 0

    for i, old_mask in enumerate(previous):
        for j, new_mask in enumerate(current):
            score, shift, intersection = best_jaccard(
                old_mask, new_mask, max_shift
            )

            if score >= threshold:
                old_adj[i].append(j)
                new_adj[j].append(i)
                match_count += 1

    visited_old = set()
    visited_new = set()
    events = Counter()
    event_rows = []

    # Connected components containing at least one edge.
    for start in range(old_count):
        if not old_adj[start] or start in visited_old:
            continue

        component_old = set()
        component_new = set()
        queue = deque([("old", start)])

        while queue:
            side, node = queue.popleft()

            if side == "old":
                if node in visited_old:
                    continue
                visited_old.add(node)
                component_old.add(node)

                for nxt in old_adj[node]:
                    if nxt not in visited_new:
                        queue.append(("new", nxt))
            else:
                if node in visited_new:
                    continue
                visited_new.add(node)
                component_new.add(node)

                for nxt in new_adj[node]:
                    if nxt not in visited_old:
                        queue.append(("old", nxt))

        a = len(component_old)
        b = len(component_new)

        if a == 1 and b == 1:
            label = "ONE_TO_ONE_CANDIDATE"
        elif a == 1 and b > 1:
            label = "SPLIT_CANDIDATE"
        elif a > 1 and b == 1:
            label = "MERGE_CANDIDATE"
        else:
            label = "COMPLEX_CANDIDATE"

        events[label] += 1
        event_rows.append((label, a, b))

    # Isolated previous components.
    for i in range(old_count):
        if i not in visited_old:
            events["DISAPPEARANCE"] += 1
            event_rows.append(("DISAPPEARANCE", 1, 0))

    # Isolated current components.
    for j in range(new_count):
        if j not in visited_new:
            events["APPEARANCE"] += 1
            event_rows.append(("APPEARANCE", 0, 1))

    return events, match_count, event_rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    all_summary = []
    all_transitions = []
    all_events = []

    print("GENESIS ZERO — STRUCTURAL SENSITIVITY")
    print("Original trajectories: READ ONLY")
    print("Configurations:", len(CONFIGS))
    print("Rules:", list(RULES))

    trajectories = {}

    for rule in RULES:
        print(f"\nLoading rule {rule}...")
        trajectories[rule] = load_trajectory(rule)

    for config, max_shift, threshold in CONFIGS:
        print(
            f"\nCONFIG {config}: max_shift={max_shift}, "
            f"Jaccard={threshold:.2f}"
        )

        for rule, (transient, period) in RULES.items():
            trajectory = trajectories[rule]
            cycle = trajectory[transient:transient + period]

            if len(cycle) != period:
                raise ValueError(f"Incomplete cycle for rule {rule}")

            component_states = [
                components_as_masks(state) for state in cycle
            ]

            totals = Counter()
            total_matches = 0
            started = time.time()

            for t in range(period):
                previous = component_states[t]
                current = component_states[(t + 1) % period]

                events, matches, event_rows = classify_graph(
                    previous, current, max_shift, threshold
                )

                totals.update(events)
                total_matches += matches

                transition_row = {
                    "config": config,
                    "max_shift": max_shift,
                    "jaccard_threshold": threshold,
                    "rule": rule,
                    "transition": t,
                    "previous_components": len(previous),
                    "current_components": len(current),
                    "candidate_edges": matches,
                }

                for label in (
                    "ONE_TO_ONE_CANDIDATE",
                    "SPLIT_CANDIDATE",
                    "MERGE_CANDIDATE",
                    "COMPLEX_CANDIDATE",
                    "APPEARANCE",
                    "DISAPPEARANCE",
                ):
                    transition_row[label] = events.get(label, 0)

                all_transitions.append(transition_row)

                for label, old_n, new_n in event_rows:
                    all_events.append({
                        "config": config,
                        "rule": rule,
                        "transition": t,
                        "event": label,
                        "previous_components": old_n,
                        "current_components": new_n,
                    })

            row = {
                "config": config,
                "max_shift": max_shift,
                "jaccard_threshold": threshold,
                "rule": rule,
                "transient": transient,
                "period": period,
                "transitions_analyzed": period,
                "candidate_edges_total": total_matches,
            }

            for label in (
                "ONE_TO_ONE_CANDIDATE",
                "SPLIT_CANDIDATE",
                "MERGE_CANDIDATE",
                "COMPLEX_CANDIDATE",
                "APPEARANCE",
                "DISAPPEARANCE",
            ):
                row[label] = totals.get(label, 0)

            all_summary.append(row)

            elapsed = time.time() - started
            print(
                f"  Rule {rule}: {period} transitions | "
                f"edges={total_matches} | "
                f"split={totals.get('SPLIT_CANDIDATE', 0)} | "
                f"merge={totals.get('MERGE_CANDIDATE', 0)} | "
                f"{elapsed:.1f}s"
            )

    def write_csv(filename, rows):
        if not rows:
            return
        with (OUT / filename).open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(rows)

    write_csv("GZ_LIFE_001_SENSITIVITY_SUMMARY.csv", all_summary)
    write_csv("GZ_LIFE_001_SENSITIVITY_TRANSITIONS.csv", all_transitions)
    write_csv("GZ_LIFE_001_SENSITIVITY_EVENTS.csv", all_events)

    report = {
        "experiment": "GZ-LIFE-001 Structural Tracking Sensitivity",
        "method": "Independent reconstruction using circular shifted Jaccard and bipartite connected components",
        "rules": list(RULES),
        "configurations": [
            {
                "config": c,
                "max_shift": s,
                "jaccard_threshold": j
            }
            for c, s, j in CONFIGS
        ],
        "summary_rows": len(all_summary),
        "transition_rows": len(all_transitions),
        "event_rows": len(all_events),
        "original_data_modified": False,
        "interpretation": (
            "All split/merge/complex classifications are geometric "
            "candidates, not demonstrated biological or digital reproduction."
        )
    }

    (OUT / "GZ_LIFE_001_SENSITIVITY_METADATA.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\nSENSITIVITY ANALYSIS COMPLETED")
    print("Output:", OUT.resolve())
    print("Summary rows:", len(all_summary))
    print("Transition rows:", len(all_transitions))
    print("Event rows:", len(all_events))


if __name__ == "__main__":
    main()
