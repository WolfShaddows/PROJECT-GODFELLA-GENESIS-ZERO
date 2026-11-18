from pathlib import Path
from collections import deque
import numpy as np
import pandas as pd

ROOT = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
OUT = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001/structural_tracking_v2")

RULES = (67, 109, 137)
CELLS = 256
MAX_SHIFT = 3
MIN_JACCARD = 0.50
MASK = (1 << CELLS) - 1

def unpack(packed):
    return np.unpackbits(
        packed, axis=1, count=CELLS, bitorder="big"
    ).astype(np.uint8)

def components_ring(state):
    active = np.flatnonzero(state)

    if len(active) == 0:
        return []

    if len(active) == CELLS:
        return [set(range(CELLS))]

    starts = [
        int(i) for i in active
        if state[(i - 1) % CELLS] == 0
    ]

    result = []

    for start in starts:
        component = set()
        pos = start

        while state[pos] == 1 and pos not in component:
            component.add(pos)
            pos = (pos + 1) % CELLS

        result.append(component)

    return result

def to_mask(component):
    value = 0
    for position in component:
        value |= 1 << position
    return value

def rotate_mask(value, shift):
    shift %= CELLS
    if shift == 0:
        return value
    return ((value << shift) | (value >> (CELLS - shift))) & MASK

def best_match(old_mask, new_mask):
    best = None

    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        shifted = rotate_mask(old_mask, shift)
        intersection = (shifted & new_mask).bit_count()
        union = (shifted | new_mask).bit_count()

        similarity = intersection / union if union else 1.0

        candidate = (
            similarity,
            intersection,
            -abs(shift),
            -shift,
            shift
        )

        if best is None or candidate[:4] > best[:4]:
            best = candidate

    return {
        "similarity": best[0],
        "intersection": best[1],
        "shift": best[4]
    }

def classify(old_components, new_components):
    old_masks = [to_mask(c) for c in old_components]
    new_masks = [to_mask(c) for c in new_components]

    adjacency = {}
    matches = []

    for i in range(len(old_masks)):
        adjacency[("P", i)] = []

    for j in range(len(new_masks)):
        adjacency[("C", j)] = []

    for i, old_mask in enumerate(old_masks):
        for j, new_mask in enumerate(new_masks):
            result = best_match(old_mask, new_mask)

            if result["similarity"] >= MIN_JACCARD:
                adjacency[("P", i)].append(("C", j))
                adjacency[("C", j)].append(("P", i))

                matches.append({
                    "previous_component": i,
                    "current_component": j,
                    **result,
                    "exact_overlap": result["intersection"] > 0,
                    "displacement_match": (
                        result["shift"] != 0 and
                        result["similarity"] >= MIN_JACCARD
                    )
                })

    visited = set()
    events = []

    for node in adjacency:
        if node in visited:
            continue

        if not adjacency[node]:
            visited.add(node)
            kind = "DISAPPEARANCE" if node[0] == "P" else "APPEARANCE"
            events.append((kind, 1 if node[0] == "P" else 0,
                           1 if node[0] == "C" else 0))
            continue

        queue = deque([node])
        visited.add(node)
        old_ids, new_ids = set(), set()

        while queue:
            current = queue.popleft()

            if current[0] == "P":
                old_ids.add(current[1])
            else:
                new_ids.add(current[1])

            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        old_n, new_n = len(old_ids), len(new_ids)

        if old_n == 1 and new_n == 1:
            kind = "ONE_TO_ONE_CANDIDATE"
        elif old_n == 1 and new_n > 1:
            kind = "SPLIT_CANDIDATE"
        elif old_n > 1 and new_n == 1:
            kind = "MERGE_CANDIDATE"
        else:
            kind = "COMPLEX_CANDIDATE"

        events.append((kind, old_n, new_n))

    return events, matches

event_rows = []
match_rows = []
transition_rows = []
summary_rows = []

for rule in RULES:
    print(f"\nAnalizando regla {rule}...")

    with np.load(ROOT / f"rule_{rule:03d}.npz",
                 allow_pickle=False) as data:
        states = unpack(data["trajectory"])

    seen = {}
    cycle_start = None
    period = None

    for index, state in enumerate(states):
        key = state.tobytes()
        if key in seen:
            cycle_start = seen[key]
            period = index - cycle_start
            break
        seen[key] = index

    if cycle_start is None:
        raise RuntimeError(f"No se detectó ciclo: regla {rule}")

    cycle = states[cycle_start:cycle_start + period]

    if len(cycle) != period:
        raise RuntimeError("Ciclo incompleto")

    totals = {}

    for t in range(period):
        next_t = (t + 1) % period

        old_components = components_ring(cycle[t])
        new_components = components_ring(cycle[next_t])

        events, matches = classify(old_components, new_components)

        counts = {}

        for kind, old_n, new_n in events:
            totals[kind] = totals.get(kind, 0) + 1
            counts[kind] = counts.get(kind, 0) + 1

            event_rows.append({
                "rule": rule,
                "transition": t,
                "event": kind,
                "previous_components": old_n,
                "current_components": new_n
            })

        for match in matches:
            match_rows.append({
                "rule": rule,
                "transition": t,
                **match
            })

        transition_rows.append({
            "rule": rule,
            "transition": t,
            "previous_components": len(old_components),
            "current_components": len(new_components),
            "candidate_matches": len(matches),
            **counts
        })

    summary_rows.append({
        "rule": rule,
        "transient": cycle_start,
        "period": period,
        "transitions_analyzed": period,
        **totals
    })

    print(f"  Período: {period}")
    print(f"  Eventos: {totals}")

pd.DataFrame(event_rows).to_csv(
    OUT / "GZ_LIFE_001_V2_EVENTS.csv", index=False
)

pd.DataFrame(match_rows).to_csv(
    OUT / "GZ_LIFE_001_V2_MATCHES.csv", index=False
)

pd.DataFrame(transition_rows).to_csv(
    OUT / "GZ_LIFE_001_V2_TRANSITIONS.csv", index=False
)

summary = pd.DataFrame(summary_rows)

summary.to_csv(
    OUT / "GZ_LIFE_001_V2_SUMMARY.csv", index=False
)

report = [
    "# GENESIS ZERO — GZ-LIFE-001",
    "## Structural Tracking V2",
    "",
    f"- Desplazamiento máximo: {MAX_SHIFT} células.",
    f"- Similitud Jaccard mínima: {MIN_JACCARD}.",
    "- Comparación circular sobre 256 posiciones.",
    "- Ciclos completos, incluida la transición de cierre.",
    "",
    "Las relaciones son candidatos geométricos, no identidades demostradas.",
    "Una coincidencia desplazada no demuestra continuidad física.",
    "Los eventos de división y fusión son candidatos basados en el grafo.",
    "",
    "## Resumen",
    "",
    summary.to_string(index=False),
    "",
    "Los datos originales permanecieron intactos."
]

(OUT / "GZ_LIFE_001_V2_REPORT.md").write_text(
    "\n".join(report), encoding="utf-8"
)

print("\n=== RESUMEN V2 ===")
print(summary.to_string(index=False))
print(f"\nResultados: {OUT}")
