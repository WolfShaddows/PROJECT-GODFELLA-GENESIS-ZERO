import json, hashlib, sys
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np

snapshot_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

GENERATIONS = 300
MOTIF_LENGTH = 9
MAX_SHIFT = 1
MIN_LIFETIME = 20

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

source_hash = sha(snapshot_path)
data = json.loads(snapshot_path.read_text(encoding="utf-8"))

active = np.asarray(data["active"], dtype=np.int64)
lo, hi = int(active.min()), int(active.max())
padding = GENERATIONS + 20
origin = lo - padding

state = np.zeros(hi-lo+1+2*padding, dtype=np.uint8)
state[active-origin] = 1

def evolve(s):
    left = np.zeros_like(s)
    right = np.zeros_like(s)
    left[1:] = s[:-1]
    right[:-1] = s[1:]
    return (
        ((left == 1) & (s == 1) & (right == 0)) |
        ((left == 1) & (s == 0) & (right == 1)) |
        ((left == 0) & (s == 1) & (right == 1)) |
        ((left == 0) & (s == 1) & (right == 0)) |
        ((left == 0) & (s == 0) & (right == 1))
    ).astype(np.uint8)

def scan(s):
    count = len(s)-MOTIF_LENGTH+1
    codes = np.zeros(count, dtype=np.uint16)
    for j in range(MOTIF_LENGTH):
        codes = (codes << 1) | s[j:j+count]
    result = defaultdict(list)
    for pos in np.flatnonzero(codes):
        result[int(codes[pos])].append(int(pos))
    return result

# Each track owns at most one occurrence in each generation.
next_id = 1
tracks = {}
previous = {}

def new_track(code, pos, generation):
    global next_id
    tid = next_id
    next_id += 1
    tracks[tid] = {
        "id": tid,
        "motif": format(code, f"0{MOTIF_LENGTH}b"),
        "start_generation": generation,
        "end_generation": generation,
        "positions": [pos],
        "displacements": [],
        "matched_steps": 0
    }
    return tid

previous_scan = scan(state)
for code, positions in previous_scan.items():
    for pos in positions:
        tid = new_track(code, pos, 0)
        previous[(code, pos)] = tid

generation_stats = []
event_counts = Counter()

print("STUDY 034 — SPACETIME TRACKING")
print(f"Initial generation: {data.get('generation')}")
print(f"Snapshot SHA256: {source_hash}")
print(f"Motif length: {MOTIF_LENGTH}")
print(f"Simulation: {GENERATIONS} generations")
print("Tracking with one-to-one matching...")

for gen in range(1, GENERATIONS+1):
    state = evolve(state)
    current_scan = scan(state)
    current = {}
    matched_previous = set()

    for code, positions in current_scan.items():
        old_positions = [
            (pos, tid) for (old_code, pos), tid in previous.items()
            if old_code == code
        ]

        # Candidate links sorted by smallest displacement.
        edges = []
        for new_pos in positions:
            for old_pos, tid in old_positions:
                shift = new_pos-old_pos
                if abs(shift) <= MAX_SHIFT:
                    edges.append((abs(shift), new_pos, old_pos, tid, shift))

        edges.sort()

        used_new = set()
        used_old = set()

        for _, new_pos, old_pos, tid, shift in edges:
            if new_pos in used_new or old_pos in used_old:
                continue

            used_new.add(new_pos)
            used_old.add(old_pos)
            matched_previous.add((code, old_pos))

            track = tracks[tid]
            track["positions"].append(new_pos)
            track["displacements"].append(shift)
            track["end_generation"] = gen
            track["matched_steps"] += 1
            current[(code, new_pos)] = tid

        # Unmatched current occurrences begin new tracks.
        for pos in positions:
            if pos not in used_new:
                tid = new_track(code, pos, gen)
                current[(code, pos)] = tid
                event_counts["births"] += 1

        event_counts["matches"] += len(used_new)
        event_counts["deaths"] += len(old_positions)-len(used_old)

    previous = current

    if gen % 25 == 0:
        active_tracks = len(set(current.values()))
        generation_stats.append({
            "generation": gen,
            "active_cells": int(state.sum()),
            "density": float(state.mean()),
            "tracked_occurrences": len(current),
            "active_track_ids": active_tracks
        })
        print(
            f"Generation {gen}: active={int(state.sum())}, "
            f"occurrences={len(current)}, tracks={active_tracks}"
        )

# Summarize trajectories.
summaries = []
for track in tracks.values():
    positions = track["positions"]
    shifts = track["displacements"]
    lifetime = len(positions)
    net = positions[-1]-positions[0]
    mean_speed = net/(lifetime-1) if lifetime > 1 else 0
    shift_counts = dict(Counter(shifts))

    summaries.append({
        "id": track["id"],
        "motif": track["motif"],
        "start_generation": track["start_generation"],
        "end_generation": track["end_generation"],
        "lifetime_generations": lifetime,
        "start_position": positions[0]+origin,
        "end_position": positions[-1]+origin,
        "net_displacement": net,
        "mean_velocity": mean_speed,
        "step_counts": shift_counts,
        "candidate_long_lived": lifetime >= MIN_LIFETIME
    })

summaries.sort(
    key=lambda x: (x["lifetime_generations"], abs(x["net_displacement"])),
    reverse=True
)

long_lived = [x for x in summaries if x["candidate_long_lived"]]
moving = [x for x in long_lived if x["net_displacement"] != 0]

final_hash = sha(snapshot_path)

results = {
    "study": "034_SPACETIME_TRACKING",
    "rule": 110,
    "initial_generation": data.get("generation"),
    "simulated_generations": GENERATIONS,
    "motif_length": MOTIF_LENGTH,
    "one_to_one_matching": True,
    "max_shift_per_generation": MAX_SHIFT,
    "minimum_lifetime_candidate": MIN_LIFETIME,
    "initial_snapshot_sha256": source_hash,
    "final_snapshot_sha256": final_hash,
    "source_unchanged": source_hash == final_hash,
    "event_counts": dict(event_counts),
    "total_tracks_created": len(tracks),
    "long_lived_track_count": len(long_lived),
    "long_lived_nonstationary_count": len(moving),
    "generation_stats": generation_stats,
    "top_tracks": summaries[:100],
    "long_lived_tracks": long_lived[:500],
    "limitations": [
        "Tracks follow identical 9-bit windows, not complete physical structures.",
        "Greedy one-to-one matching resolves ambiguity deterministically, not biologically.",
        "Repeated backgrounds can create false trajectories.",
        "A mobile particle requires coherent spacetime structure beyond a local motif."
    ]
}

(out_dir/"study_034_results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

lines = [
    "STUDY 034 — SPACETIME TRACKING",
    f"Initial generation: {data.get('generation')}",
    f"Simulated generations: {GENERATIONS}",
    f"Total tracks created: {len(tracks)}",
    f"Long-lived tracks (>= {MIN_LIFETIME}): {len(long_lived)}",
    f"Long-lived nonstationary tracks: {len(moving)}",
    f"Matching events: {dict(event_counts)}",
    "",
    "TOP 25 TRACKS:"
]

for t in summaries[:25]:
    lines.append(
        f"ID={t['id']} motif={t['motif']} "
        f"life={t['lifetime_generations']} "
        f"net={t['net_displacement']} "
        f"velocity={t['mean_velocity']:.4f} "
        f"steps={t['step_counts']}"
    )

lines += [
    "",
    f"Snapshot unchanged: {source_hash == final_hash}",
    f"SHA256: {final_hash}",
    "",
    "NOTE: Local motif tracks are candidates, not proof of gliders or life."
]

(out_dir/"study_034_report.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)

print("\n"+"\n".join(lines))
print(f"\nJSON: {out_dir/'study_034_results.json'}")
print(f"REPORT: {out_dir/'study_034_report.txt'}")
