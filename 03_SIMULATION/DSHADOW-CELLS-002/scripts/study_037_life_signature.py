import json
import hashlib
import sys
import time
from pathlib import Path
from collections import defaultdict
import numpy as np

SNAPSHOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

PERIOD = 160
GENERATIONS = 500
MIN_LIFETIME = 20
MAX_TRACK_SHIFT = 1

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def evolve(s):
    left = np.zeros_like(s)
    right = np.zeros_like(s)
    left[1:] = s[:-1]
    right[:-1] = s[1:]

    # Rule 110:
    # 111=0, 110=1, 101=1, 100=0,
    # 011=1, 010=1, 001=1, 000=0
    return (
        ((left == 1) & (s == 1) & (right == 0)) |
        ((left == 1) & (s == 0) & (right == 1)) |
        ((left == 0) & (s == 1) & (right == 1)) |
        ((left == 0) & (s == 1) & (right == 0)) |
        ((left == 0) & (s == 0) & (right == 1))
    ).astype(np.uint8)

def find_longest_periodic_region(bits, period):
    equal = bits[:-period] == bits[period:]
    padded = np.concatenate(([False], equal, [False]))
    changes = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)

    if len(starts) == 0:
        raise RuntimeError("No exact periodic region found.")

    runs = [
        (int(start), int(end))
        for start, end in zip(starts, ends)
    ]

    return max(runs, key=lambda x: x[1]-x[0]), runs

def defect_runs(mask):
    positions = np.flatnonzero(mask)
    if len(positions) == 0:
        return []

    groups = []
    start = previous = int(positions[0])

    for p in positions[1:]:
        p = int(p)
        if p > previous+1:
            groups.append((start, previous))
            start = p
        previous = p

    groups.append((start, previous))
    return groups

def connected_tracks(frames):
    # Each defect run in each generation is a spacetime node.
    nodes = []
    frame_nodes = []

    for generation, runs in enumerate(frames):
        current = []
        for start, end in runs:
            current.append(len(nodes))
            nodes.append({
                "generation": generation,
                "start": start,
                "end": end
            })
        frame_nodes.append(current)

    parent = list(range(len(nodes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for t in range(1, len(frame_nodes)):
        previous = frame_nodes[t-1]
        current = frame_nodes[t]

        for a in previous:
            A = nodes[a]
            for b in current:
                B = nodes[b]

                # Causal adjacency: a defect can influence
                # positions at most one cell away per generation.
                if (
                    B["start"] <= A["end"]+1
                    and B["end"] >= A["start"]-1
                ):
                    union(a, b)

    groups = defaultdict(list)
    for i, node in enumerate(nodes):
        groups[find(i)].append(node)

    summaries = []

    for group in groups.values():
        generations = sorted(set(x["generation"] for x in group))
        positions = [
            (x["start"]+x["end"])/2
            for x in group
        ]

        first = min(x["generation"] for x in group)
        last = max(x["generation"] for x in group)

        summaries.append({
            "first_generation": first,
            "last_generation": last,
            "observed_generations": len(generations),
            "lifetime_span": last-first+1,
            "minimum_position": min(x["start"] for x in group),
            "maximum_position": max(x["end"] for x in group),
            "mean_position": float(np.mean(positions)),
            "position_start": positions[0],
            "position_end": positions[-1],
            "net_displacement": positions[-1]-positions[0],
            "number_of_defect_runs": len(group)
        })

    return sorted(
        summaries,
        key=lambda x: (
            x["lifetime_span"],
            x["number_of_defect_runs"]
        ),
        reverse=True
    )

started = time.time()
initial_hash = sha(SNAPSHOT)

data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
active = np.asarray(data["active"], dtype=np.int64)

if len(active) == 0:
    raise ValueError("Empty snapshot.")

lo = int(active.min())
hi = int(active.max())

state = np.zeros(hi-lo+1, dtype=np.uint8)
state[active-lo] = 1

# --------------------------------------------------
# 1. FIND PERIODIC BACKGROUND
# --------------------------------------------------

print("STUDY 037 — LIFE SIGNATURE DETECTION")
print(f"Initial generation: {data.get('generation')}")
print(f"Active cells: {len(active):,}")
print(f"Spatial span: {len(state):,}")
print("Finding exact period-160 region...")

(best_start, best_end), all_runs = find_longest_periodic_region(
    state, PERIOD
)

periodic_length = best_end-best_start

if periodic_length < 10000:
    raise RuntimeError(
        f"Periodic region too short: {periodic_length}"
    )

# Anchor the background at the first position of the
# longest exact periodic region.
background = state[best_start:best_start+PERIOD].copy()

# Confirm the selected region is exactly periodic.
for i in range(best_start, best_end):
    if state[i] != state[i+PERIOD]:
        raise RuntimeError("Periodicity verification failed.")

print(f"Periodic region: {best_start} to {best_end+PERIOD-1}")
print(f"Periodic length: {periodic_length:,}")
print(f"Reference motif: {''.join(map(str, background.tolist()))}")

# --------------------------------------------------
# 2. PREPARE FULL AND PERIODIC SYSTEMS
# --------------------------------------------------

actual = state.copy()
ether = np.tile(background, (len(state)+PERIOD-1)//PERIOD)[:len(state)]

# Both arrays use zero boundaries for the actual finite
# simulation. The ether is evolved periodically below.
# We only interpret differences inside the periodic core.

core_start = best_start
core_end = min(best_end+PERIOD, len(state))

# Track defects in the periodic region and a margin.
frames = []
generation_stats = []

print("\nSimulating offline spacetime evolution...")

for generation in range(GENERATIONS+1):

    # Compare actual universe against the evolved periodic reference.
    defect = actual != ether

    core_defect = defect[core_start:core_end]
    runs = defect_runs(core_defect)

    frames.append(runs)

    generation_stats.append({
        "generation": generation,
        "active_cells": int(actual.sum()),
        "density": float(actual.mean()),
        "defect_cells_in_core": int(core_defect.sum()),
        "defect_runs_in_core": len(runs)
    })

    if generation % 50 == 0:
        print(
            f"Generation {generation}: "
            f"active={int(actual.sum()):,}; "
            f"core defects={int(core_defect.sum()):,}; "
            f"defect runs={len(runs)}"
        )

    if generation == GENERATIONS:
        break

    actual = evolve(actual)

    # Evolve the periodic reference with circular boundaries.
    ether_left = np.roll(ether, 1)
    ether_right = np.roll(ether, -1)

    ether = (
        ((ether_left == 1) & (ether == 1) & (ether_right == 0)) |
        ((ether_left == 1) & (ether == 0) & (ether_right == 1)) |
        ((ether_left == 0) & (ether == 1) & (ether_right == 1)) |
        ((ether_left == 0) & (ether == 1) & (ether_right == 0)) |
        ((ether_left == 0) & (ether == 0) & (ether_right == 1))
    ).astype(np.uint8)

# --------------------------------------------------
# 3. TRACK DEFECT COMPONENTS IN SPACETIME
# --------------------------------------------------

print("\nTracking spacetime defect components...")

tracks = connected_tracks(frames)

long_lived = [
    t for t in tracks
    if t["lifetime_span"] >= MIN_LIFETIME
]

moving_candidates = [
    t for t in long_lived
    if abs(t["net_displacement"]) >= 5
]

# --------------------------------------------------
# 4. DETECT POSSIBLE BRANCHING
# --------------------------------------------------

branching = []

for t in range(1, len(frames)):
    previous = frames[t-1]
    current = frames[t]

    for a_start, a_end in previous:
        children = []

        for b_start, b_end in current:
            if (
                b_start <= a_end+1
                and b_end >= a_start-1
            ):
                children.append((b_start, b_end))

        if len(children) >= 2:
            branching.append({
                "generation": t,
                "parent_previous_run": [a_start, a_end],
                "child_runs": [list(x) for x in children],
                "child_count": len(children)
            })

# --------------------------------------------------
# 5. REPORT
# --------------------------------------------------

final_hash = sha(SNAPSHOT)

results = {
    "study": "037_LIFE_SIGNATURE_DETECTION",
    "rule": 110,
    "initial_generation": data.get("generation"),
    "simulated_generations": GENERATIONS,
    "snapshot_sha256_before": initial_hash,
    "snapshot_sha256_after": final_hash,
    "snapshot_unchanged": initial_hash == final_hash,
    "periodic_background": {
        "period": PERIOD,
        "region_start_index": best_start,
        "region_end_index": best_end+PERIOD-1,
        "region_length": periodic_length,
        "reference_motif": "".join(map(str, background.tolist())),
        "all_exact_periodic_runs": [
            {"start": a, "end": b, "length": b-a}
            for a, b in all_runs
        ]
    },
    "core": {
        "start_index": core_start,
        "end_index": core_end-1,
        "length": core_end-core_start
    },
    "generation_statistics": generation_stats,
    "spacetime_tracks": {
        "total": len(tracks),
        "long_lived": len(long_lived),
        "moving_candidates": len(moving_candidates),
        "top_tracks": tracks[:200],
        "moving_candidates_detail": moving_candidates[:200]
    },
    "branching_events": branching[:1000],
    "limitations": [
        "A connected defect component is not automatically a particle.",
        "Branching defect runs do not establish reproduction.",
        "The reference ether is an analytical background, not a biological environment.",
        "A self-reproducing structure requires verified copies with inherited organization.",
        "A 500-generation simulation is only an initial screening horizon."
    ],
    "runtime_seconds": time.time()-started
}

(OUT/"study_037_results.json").write_text(
    json.dumps(results, indent=2),
    encoding="utf-8"
)

lines = [
    "STUDY 037 — LIFE SIGNATURE DETECTION",
    "",
    f"Initial generation: {data.get('generation')}",
    f"Simulated generations: {GENERATIONS}",
    f"Period-160 region length: {periodic_length:,}",
    f"Reference motif: {''.join(map(str, background.tolist()))}",
    "",
    "SPACETIME RESULTS",
    f"Total defect tracks: {len(tracks)}",
    f"Long-lived tracks: {len(long_lived)}",
    f"Moving candidates: {len(moving_candidates)}",
    f"Branching events: {len(branching)}",
    "",
    "TOP 25 TRACKS"
]

for item in tracks[:25]:
    lines.append(
        f"g={item['first_generation']}-{item['last_generation']} "
        f"life={item['lifetime_span']} "
        f"x={item['minimum_position']}..{item['maximum_position']} "
        f"net={item['net_displacement']} "
        f"runs={item['number_of_defect_runs']}"
    )

lines += [
    "",
    "BRANCHING EVENTS: " + str(len(branching)),
    f"Snapshot unchanged: {initial_hash == final_hash}",
    f"SHA256: {final_hash}",
    "",
    "IMPORTANT: Candidates require further validation.",
    "No biological life or self-reproduction is established here."
]

(OUT/"study_037_report.txt").write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print("\n" + "\n".join(lines))
print(f"\nJSON: {OUT/'study_037_results.json'}")
print(f"REPORT: {OUT/'study_037_report.txt'}")
print(f"OUTPUT: {OUT}")
