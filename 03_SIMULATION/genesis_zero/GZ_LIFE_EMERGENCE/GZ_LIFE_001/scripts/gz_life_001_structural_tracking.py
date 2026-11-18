from pathlib import Path
from collections import deque
import numpy as np
import pandas as pd

ROOT = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
OUT = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001/structural_tracking")

RULES = (67, 109, 137)
CELLS = 256

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
        i for i in active
        if state[(i - 1) % CELLS] == 0
    ]

    result = []

    for start in starts:
        component = set()
        pos = int(start)

        while state[pos] == 1 and pos not in component:
            component.add(pos)
            pos = (pos + 1) % CELLS

        result.append(component)

    return result

def classify_transition(previous, current):
    # Grafo bipartito: componentes anteriores y actuales.
    adjacency = {}
    previous_count = len(previous)
    current_count = len(current)

    for i in range(previous_count):
        adjacency[("P", i)] = []

    for j in range(current_count):
        adjacency[("C", j)] = []

    for i, old in enumerate(previous):
        for j, new in enumerate(current):
            if old.intersection(new):
                adjacency[("P", i)].append(("C", j))
                adjacency[("C", j)].append(("P", i))

    visited = set()
    events = []

    for node in adjacency:
        if node in visited:
            continue

        if not adjacency[node]:
            visited.add(node)

            if node[0] == "P":
                events.append(("DISAPPEARANCE", 1, 0))
            else:
                events.append(("APPEARANCE", 0, 1))

            continue

        queue = deque([node])
        visited.add(node)
        old_ids = set()
        new_ids = set()

        while queue:
            current_node = queue.popleft()

            if current_node[0] == "P":
                old_ids.add(current_node[1])
            else:
                new_ids.add(current_node[1])

            for neighbor in adjacency[current_node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        old_n = len(old_ids)
        new_n = len(new_ids)

        if old_n == 1 and new_n == 1:
            kind = "ONE_TO_ONE_OVERLAP"
        elif old_n == 1 and new_n > 1:
            kind = "SPLIT"
        elif old_n > 1 and new_n == 1:
            kind = "MERGE"
        else:
            kind = "COMPLEX_RECONFIGURATION"

        events.append((kind, old_n, new_n))

    return events

transition_rows = []
event_rows = []
summary_rows = []

for rule in RULES:
    print(f"\nAnalizando continuidad: regla {rule}")

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
        raise RuntimeError(f"No se detectó ciclo para regla {rule}")

    cycle = states[cycle_start:cycle_start + period]

    if len(cycle) != period:
        raise RuntimeError("Ciclo incompleto")

    totals = {
        "ONE_TO_ONE_OVERLAP": 0,
        "SPLIT": 0,
        "MERGE": 0,
        "COMPLEX_RECONFIGURATION": 0,
        "APPEARANCE": 0,
        "DISAPPEARANCE": 0
    }

    for t in range(period):
        next_t = (t + 1) % period

        old_components = components_ring(cycle[t])
        new_components = components_ring(cycle[next_t])

        events = classify_transition(
            old_components,
            new_components
        )

        counts = {name: 0 for name in totals}

        for kind, old_n, new_n in events:
            totals[kind] += 1
            counts[kind] += 1

            event_rows.append({
                "rule": rule,
                "cycle_transition": t,
                "next_cycle_state": next_t,
                "event": kind,
                "previous_components": old_n,
                "current_components": new_n
            })

        transition_rows.append({
            "rule": rule,
            "cycle_transition": t,
            "previous_components": len(old_components),
            "current_components": len(new_components),
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
    print(f"  Transiciones analizadas: {period}")
    print(f"  Eventos: {totals}")

pd.DataFrame(transition_rows).to_csv(
    OUT / "GZ_LIFE_001_COMPONENT_TRANSITIONS.csv",
    index=False
)

pd.DataFrame(event_rows).to_csv(
    OUT / "GZ_LIFE_001_LINEAGE_EVENTS.csv",
    index=False
)

summary = pd.DataFrame(summary_rows)

summary.to_csv(
    OUT / "GZ_LIFE_001_LINEAGE_SUMMARY.csv",
    index=False
)

report = [
    "# GENESIS ZERO — GZ-LIFE-001",
    "## Análisis de continuidad estructural",
    "",
    "Método: componentes conectados en anillo circular.",
    "Relación entre estados: intersección de células activas.",
    "",
    "Una relación uno a uno indica solapamiento, no identidad demostrada.",
    "Una división o fusión describe la estructura del grafo de solapamientos.",
    "La ausencia de solapamiento puede ocultar desplazamientos.",
    "",
    "## Resumen",
    "",
    summary.to_string(index=False),
    "",
    "## Límites",
    "",
    "- No se identificaron organismos.",
    "- No se demostró identidad estructural persistente.",
    "- Los patrones móviles sin solapamiento pueden contarse como desaparición y aparición.",
    "- Los eventos describen relaciones geométricas entre estados consecutivos.",
    "- Se incluyó la transición circular entre el último y primer estado del ciclo.",
    "",
    "Los datos originales permanecieron intactos."
]

(OUT / "GZ_LIFE_001_LINEAGE_REPORT.md").write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n=== RESUMEN DE CONTINUIDAD ===")
print(summary.to_string(index=False))
print(f"\nResultados guardados en: {OUT}")
