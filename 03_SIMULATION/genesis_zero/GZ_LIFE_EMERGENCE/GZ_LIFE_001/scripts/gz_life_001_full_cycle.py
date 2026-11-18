from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
OUT = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001/full_cycle_analysis")

RULES = (67, 109, 137)
CELLS = 256

def unpack_trajectory(packed):
    return np.unpackbits(
        packed,
        axis=1,
        count=CELLS,
        bitorder="big"
    ).astype(np.uint8)

def detect_cycle(states):
    seen = {}
    for index, state in enumerate(states):
        key = state.tobytes()
        if key in seen:
            first = seen[key]
            return first, index - first, index
        seen[key] = index
    return None

def morphology(state):
    active = int(state.sum())

    if active == 0:
        return 0, 0

    if active == CELLS:
        return 1, CELLS

    previous = np.roll(state, 1)
    components = int(np.sum((state == 1) & (previous == 0)))

    doubled = np.concatenate((state, state))
    longest = 0
    current = 0

    for value in doubled:
        if value:
            current += 1
            longest = max(longest, min(current, CELLS))
        else:
            current = 0

    return components, longest

all_rows = []
summary_rows = []
report = []

for rule in RULES:
    path = ROOT / f"rule_{rule:03d}.npz"

    print(f"\nAnalizando regla {rule}...")

    with np.load(path, allow_pickle=False) as data:
        states = unpack_trajectory(data["trajectory"])
        stored_final = data["final_state"].astype(np.uint8)

    if not np.array_equal(states[-1], stored_final):
        raise RuntimeError(f"Regla {rule}: el estado final no coincide.")

    detected = detect_cycle(states)

    if detected is None:
        raise RuntimeError(f"Regla {rule}: no se detectó repetición.")

    transient, period, repeated_at = detected
    cycle = states[transient:transient + period]

    if len(cycle) != period:
        raise RuntimeError(f"Regla {rule}: ciclo incompleto.")

    next_cycle = states[transient + period:transient + 2 * period]

    verification_possible = len(next_cycle) == period
    exact_verified = (
        verification_possible and
        np.array_equal(cycle, next_cycle)
    )

    active_values = []
    component_values = []
    longest_values = []

    for offset, state in enumerate(cycle):
        active = int(state.sum())
        components, longest = morphology(state)

        active_values.append(active)
        component_values.append(components)
        longest_values.append(longest)

        all_rows.append({
            "rule": rule,
            "cycle_offset": offset,
            "trajectory_index": transient + offset,
            "active_cells": active,
            "components": components,
            "longest_circular_run": longest
        })

    active_values = np.asarray(active_values)
    component_values = np.asarray(component_values)
    longest_values = np.asarray(longest_values)

    summary_rows.append({
        "rule": rule,
        "transient": transient,
        "period": period,
        "repeated_at": repeated_at,
        "cycle_states": len(cycle),
        "exact_cycle_verified": exact_verified,
        "active_mean": active_values.mean(),
        "active_std": active_values.std(),
        "active_min": active_values.min(),
        "active_max": active_values.max(),
        "active_q25": np.quantile(active_values, 0.25),
        "active_median": np.median(active_values),
        "active_q75": np.quantile(active_values, 0.75),
        "components_mean": component_values.mean(),
        "components_std": component_values.std(),
        "components_min": component_values.min(),
        "components_max": component_values.max(),
        "longest_run_mean": longest_values.mean(),
        "longest_run_std": longest_values.std(),
        "longest_run_min": longest_values.min(),
        "longest_run_max": longest_values.max()
    })

    report.extend([
        f"## Regla {rule}",
        "",
        f"- Transitorio detectado: {transient}",
        f"- Período detectado: {period}",
        f"- Primera repetición: índice {repeated_at}",
        f"- Estados únicos del ciclo: {len(cycle)}",
        f"- Segundo ciclo completo disponible: {verification_possible}",
        f"- Verificación exacta de dos ciclos: {exact_verified}",
        f"- Actividad media: {active_values.mean():.4f}",
        f"- Componentes medios: {component_values.mean():.4f}",
        f"- Grupo circular más largo, media: {longest_values.mean():.4f}",
        "",
    ])

    print(
        f"  Transitorio={transient}, período={period}, "
        f"verificación={exact_verified}"
    )

pd.DataFrame(all_rows).to_csv(
    OUT / "GZ_LIFE_001_FULL_CYCLE_STATES.csv",
    index=False
)

summary = pd.DataFrame(summary_rows)
summary.to_csv(
    OUT / "GZ_LIFE_001_FULL_CYCLE_SUMMARY.csv",
    index=False
)

report_text = "\n".join([
    "# GENESIS ZERO — GZ-LIFE-001",
    "## Análisis cuantitativo de ciclos completos",
    "",
    "Las métricas describen estados del ciclo completo.",
    "Los componentes son grupos geométricos en un anillo circular de 256 celdas.",
    "No representan organismos ni entidades biológicas identificadas.",
    "",
    *report,
    "## Límites de interpretación",
    "",
    "- Persistencia geométrica no demuestra identidad estructural.",
    "- La repetición global demuestra periodicidad de la trayectoria.",
    "- Las métricas agregadas no demuestran reproducción.",
    "- Las diferencias descriptivas no demuestran adaptación.",
    "- Los ciclos analizados pertenecen a un sistema determinista finito.",
    "",
    "Los archivos originales no fueron modificados."
])

(OUT / "GZ_LIFE_001_FULL_CYCLE_REPORT.md").write_text(
    report_text,
    encoding="utf-8"
)

print("\n=== RESUMEN ===")
print(summary.to_string(index=False))
print(f"\nResultados guardados en: {OUT}")
