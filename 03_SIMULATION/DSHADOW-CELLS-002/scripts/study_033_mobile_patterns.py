import json, hashlib, sys, time
from pathlib import Path
from collections import defaultdict
import numpy as np

snapshot_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

GENERATIONS = 300
MOTIF_LENGTH = 9
MIN_PERSISTENCE = 5

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

original_hash = sha(snapshot_path)
data = json.loads(snapshot_path.read_text(encoding="utf-8"))

active = np.array(data["active"], dtype=np.int64)
lo, hi = int(active.min()), int(active.max())

# Margen suficiente para evitar que los límites artificiales afecten
# la región central durante las 300 generaciones.
padding = GENERATIONS + 20
origin = lo - padding
state = np.zeros(hi - lo + 1 + 2*padding, dtype=np.uint8)
state[active - origin] = 1

initial_state = state.copy()
n = len(state)

def evolve(s):
    left = np.zeros_like(s)
    right = np.zeros_like(s)
    left[1:] = s[:-1]
    right[:-1] = s[1:]

    # Regla 110 estándar: 111 110 101 100 011 010 001 000
    #                         0   1   1   0   1   1   1   0
    return (
        ((left == 1) & (s == 1) & (right == 0)) |
        ((left == 1) & (s == 0) & (right == 1)) |
        ((left == 0) & (s == 1) & (right == 1)) |
        ((left == 0) & (s == 1) & (right == 0)) |
        ((left == 0) & (s == 0) & (right == 1))
    ).astype(np.uint8)

def motif_codes(s, k):
    codes = np.zeros(len(s)-k+1, dtype=np.uint16)
    for j in range(k):
        codes = (codes << 1) | s[j:j+len(codes)]
    return codes

def scan_motifs(s):
    codes = motif_codes(s, MOTIF_LENGTH)
    positions = defaultdict(list)
    for pos in np.flatnonzero(codes):
        positions[int(codes[pos])].append(int(pos))
    return positions

def describe(code, k):
    return format(code, f"0{k}b")

print("STUDY 033 — TEMPORAL DYNAMICS & MOBILE PATTERN SCAN")
print(f"Initial generation: {data.get('generation')}")
print(f"Initial active cells: {len(active)}")
print(f"Spatial length: {n}")
print(f"Simulation generations: {GENERATIONS}")
print(f"Initial SHA256: {original_hash}")
print("Starting offline simulation...")

previous = scan_motifs(state)
tracks = {}
next_id = 0
generation_stats = []
candidate_events = []

for generation in range(1, GENERATIONS + 1):
    state = evolve(state)
    current = scan_motifs(state)

    # Seguimiento de ventanas idénticas de 9 bits.
    # Desplazamientos permitidos: -1, 0, +1 celdas por generación.
    current_tracks = {}

    for code, positions in current.items():
        previous_positions = previous.get(code, [])
        prev_set = set(previous_positions)

        for pos in positions:
            matched = None
            for shift in (-1, 0, 1):
                if pos-shift in prev_set:
                    matched = pos-shift
                    break

            if matched is not None:
                key = (code, pos)
                current_tracks[key] = True

                # Registrar recurrencia, no asumir que es un glider.
                candidate_events.append({
                    "generation": generation,
                    "motif": describe(code, MOTIF_LENGTH),
                    "previous_position": matched,
                    "current_position": pos,
                    "displacement": pos-matched
                })

    density = float(state.mean())
    generation_stats.append({
        "generation": generation,
        "active_cells": int(state.sum()),
        "density": density,
        "unique_9bit_patterns": len(current),
        "motif_occurrences": int(sum(len(v) for v in current.values()))
    })

    previous = current

    if generation % 25 == 0:
        print(
            f"Generation {generation}: "
            f"active={int(state.sum())}, "
            f"density={density:.6%}, "
            f"unique motifs={len(current)}, "
            f"recurrence events={len(candidate_events)}"
        )

# Agrupar recurrencias por motivo y desplazamiento.
summary = defaultdict(lambda: {"count": 0, "generations": set()})
for event in candidate_events:
    key = (event["motif"], event["displacement"])
    summary[key]["count"] += 1
    summary[key]["generations"].add(event["generation"])

ranked = []
for (motif, displacement), values in summary.items():
    ranked.append({
        "motif": motif,
        "displacement_per_generation": displacement,
        "recurrence_events": values["count"],
        "distinct_generations": len(values["generations"]),
        "candidate": len(values["generations"]) >= MIN_PERSISTENCE
    })

ranked.sort(
    key=lambda x: (x["distinct_generations"], x["recurrence_events"]),
    reverse=True
)

final_hash = sha(snapshot_path)

results = {
    "study": "033_TEMPORAL_DYNAMICS_MOBILE_PATTERN_SCAN",
    "rule": 110,
    "initial_generation": data.get("generation"),
    "simulated_generations": GENERATIONS,
    "motif_length": MOTIF_LENGTH,
    "maximum_tracked_speed": 1,
    "minimum_candidate_generations": MIN_PERSISTENCE,
    "initial_snapshot_sha256": original_hash,
    "final_snapshot_sha256": final_hash,
    "source_unchanged": original_hash == final_hash,
    "generation_stats": generation_stats,
    "candidate_motifs": ranked[:100],
    "recurrence_events": candidate_events[:10000],
    "interpretation": (
        "Repeated local motifs are screening candidates only. "
        "They are not proof of gliders, mobile particles, reproduction, "
        "or life. A true mobile structure requires coherent tracking "
        "of its full surrounding spacetime pattern."
    )
}

result_path = out_dir / "study_033_results.json"
result_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

report = [
    "STUDY 033 — TEMPORAL DYNAMICS",
    f"Initial generation: {data.get('generation')}",
    f"Simulated generations: {GENERATIONS}",
    f"Initial active cells: {len(active)}",
    f"Final active cells: {int(state.sum())}",
    f"Initial density: {generation_stats[0]['density']:.6%}",
    f"Final density: {float(state.mean()):.6%}",
    f"Total recurrence events: {len(candidate_events)}",
    f"Distinct motif/displacement combinations: {len(ranked)}",
    "",
    "TOP CANDIDATE MOTIFS:"
]

for item in ranked[:20]:
    report.append(
        f"{item['motif']} | speed={item['displacement_per_generation']} "
        f"| events={item['recurrence_events']} "
        f"| generations={item['distinct_generations']} "
        f"| candidate={item['candidate']}"
    )

report += [
    "",
    f"Source snapshot unchanged: {original_hash == final_hash}",
    f"SHA256: {final_hash}",
    "",
    "IMPORTANT: motif recurrence is not proof of a mobile particle."
]

(out_dir / "study_033_report.txt").write_text(
    "\n".join(report), encoding="utf-8"
)

print("\n" + "\n".join(report))
print(f"\nJSON: {result_path}")
print(f"REPORT: {out_dir / 'study_033_report.txt'}")
