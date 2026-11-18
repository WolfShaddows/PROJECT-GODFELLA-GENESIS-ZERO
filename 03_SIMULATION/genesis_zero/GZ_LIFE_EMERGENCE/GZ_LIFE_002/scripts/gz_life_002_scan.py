import json
import csv
import hashlib
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[3]
SOURCE = BASE / "GZ_EMERGENCE_001" / "results" / "raw"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "derived"

OUT.mkdir(parents=True, exist_ok=True)

RULES = {
    67:  {"transient": 702,  "period": 512},
    109: {"transient": 1482, "period": 2760},
    137: {"transient": 1058, "period": 960},
}

WIDTH = 256
MAX_SHIFT = 3
JACCARD_THRESHOLD = 0.50


def load_trajectory(rule):
    path = SOURCE / f"rule_{rule:03d}.npz"

    with np.load(path, allow_pickle=False) as data:
        packed = data["trajectory"]

    trajectory = np.unpackbits(
        packed,
        axis=1,
        count=WIDTH,
        bitorder="big"
    )

    return trajectory.astype(np.uint8)


def components(state):
    active = np.flatnonzero(state)

    if len(active) == 0:
        return []

    if len(active) == WIDTH:
        return [active.tolist()]

    breaks = np.where(np.diff(active) > 1)[0]

    groups = np.split(active, breaks + 1)
    result = [g.tolist() for g in groups if len(g)]

    if len(result) > 1:
        if result[0][0] == 0 and result[-1][-1] == WIDTH - 1:
            merged = result[-1] + result[0]
            result = [merged] + result[1:-1]

    return result


def make_mask(indices):
    mask = 0
    for i in indices:
        mask |= 1 << int(i)
    return mask


def rotate_mask(mask, shift):
    shift %= WIDTH
    full = (1 << WIDTH) - 1

    if shift == 0:
        return mask

    return ((mask << shift) & full) | (mask >> (WIDTH - shift))


def shifted_jaccard(mask_a, mask_b):
    best = 0.0
    best_shift = 0

    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        shifted = rotate_mask(mask_a, shift)

        intersection = (shifted & mask_b).bit_count()
        union = (shifted | mask_b).bit_count()

        score = intersection / union if union else 0.0

        if score > best:
            best = score
            best_shift = shift

    return best, best_shift


def analyze_rule(rule, settings):
    trajectory = load_trajectory(rule)

    transient = settings["transient"]
    period = settings["period"]

    start = transient
    end = transient + (2 * period)

    if end >= len(trajectory):
        raise ValueError(
            f"Rule {rule}: insufficient trajectory length"
        )

    edges = []
    events = []
    transition_stats = []

    total_components = 0

    print(
        f"Rule {rule}: analyzing frames {start} to {end}"
    )

    for frame in range(start, end):
        old_components = components(trajectory[frame])
        new_components = components(trajectory[frame + 1])

        total_components += len(old_components)

        old_masks = [make_mask(c) for c in old_components]
        new_masks = [make_mask(c) for c in new_components]

        parent_children = {}
        child_parents = {}

        transition_edges = []

        for pi, old_mask in enumerate(old_masks):
            for ci, new_mask in enumerate(new_masks):

                score, shift = shifted_jaccard(
                    old_mask,
                    new_mask
                )

                if score >= JACCARD_THRESHOLD:
                    record = {
                        "rule": rule,
                        "transition": frame,
                        "parent_component": pi,
                        "child_component": ci,
                        "parent_size": old_mask.bit_count(),
                        "child_size": new_mask.bit_count(),
                        "jaccard": round(score, 6),
                        "shift": shift,
                        "size_delta": (
                            new_mask.bit_count() -
                            old_mask.bit_count()
                        ),
                        "size_ratio": round(
                            new_mask.bit_count() /
                            old_mask.bit_count(), 6
                        )
                    }

                    transition_edges.append(record)

                    parent_children.setdefault(pi, []).append(ci)
                    child_parents.setdefault(ci, []).append(pi)

        split_parents = [
            p for p, children in parent_children.items()
            if len(set(children)) >= 2
        ]

        merge_children = [
            c for c, parents in child_parents.items()
            if len(set(parents)) >= 2
        ]

        for edge in transition_edges:
            edges.append(edge)

        for parent in split_parents:
            events.append({
                "rule": rule,
                "transition": frame,
                "event": "SPLIT_CANDIDATE",
                "component": parent,
                "related_components": len(
                    set(parent_children[parent])
                )
            })

        for child in merge_children:
            events.append({
                "rule": rule,
                "transition": frame,
                "event": "MERGE_CANDIDATE",
                "component": child,
                "related_components": len(
                    set(child_parents[child])
                )
            })

        transition_stats.append({
            "rule": rule,
            "transition": frame,
            "previous_components": len(old_components),
            "current_components": len(new_components),
            "candidate_edges": len(transition_edges),
            "split_parents": len(split_parents),
            "merge_children": len(merge_children)
        })

    summary = {
        "rule": rule,
        "transient": transient,
        "period": period,
        "cycles_analyzed": 2,
        "transitions_analyzed": 2 * period,
        "mean_components": round(
            total_components / (2 * period), 6
        ),
        "candidate_edges": len(edges),
        "split_parent_events": sum(
            e["event"] == "SPLIT_CANDIDATE" for e in events
        ),
        "merge_child_events": sum(
            e["event"] == "MERGE_CANDIDATE" for e in events
        ),
        "jaccard_threshold": JACCARD_THRESHOLD,
        "max_shift": MAX_SHIFT
    }

    return summary, edges, events, transition_stats


all_summaries = []
all_edges = []
all_events = []
all_transitions = []

for rule, settings in RULES.items():
    summary, edges, events, transitions = analyze_rule(
        rule,
        settings
    )

    all_summaries.append(summary)
    all_edges.extend(edges)
    all_events.extend(events)
    all_transitions.extend(transitions)

    print("Summary:", summary)


def write_csv(name, rows):
    path = OUT / name

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)


write_csv("GZ_LIFE_002_LINEAGE_CANDIDATE_EDGES.csv", all_edges)
write_csv("GZ_LIFE_002_CANDIDATE_EVENTS.csv", all_events)
write_csv("GZ_LIFE_002_TRANSITION_SUMMARY.csv", all_transitions)
write_csv("GZ_LIFE_002_RULE_SUMMARY.csv", all_summaries)

metadata = {
    "experiment": "GZ-LIFE-002",
    "method": "Circular shifted Jaccard component association",
    "rules": list(RULES.keys()),
    "cycles_per_rule": 2,
    "width": WIDTH,
    "max_shift": MAX_SHIFT,
    "jaccard_threshold": JACCARD_THRESHOLD,
    "original_trajectories_modified": False,
    "interpretation": (
        "Geometric candidate associations only. "
        "Split candidates do not establish biological reproduction "
        "or hereditary information transmission."
    ),
    "outputs": {
        "candidate_edges": len(all_edges),
        "candidate_events": len(all_events),
        "transition_rows": len(all_transitions)
    }
}

(OUT / "GZ_LIFE_002_METADATA.json").write_text(
    json.dumps(metadata, indent=2),
    encoding="utf-8"
)

print("\nGZ-LIFE-002 SCAN COMPLETED")
print(json.dumps(metadata, indent=2))
