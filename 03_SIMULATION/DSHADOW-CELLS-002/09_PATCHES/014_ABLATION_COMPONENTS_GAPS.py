import os
import json
import csv
import hashlib
from pathlib import Path
from collections import Counter

import numpy as np

EXPORT = Path(os.environ["DSHADOW_EXPORT"])
SNAPSHOT = EXPORT / "universe_snapshot.json"

REPLICATES = 5000
MAX_LAG = 128
TRAIN_SIZE = REPLICATES // 2
SEEDS = {
    "components": 20261108,
    "gaps": 20261109,
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def extract_cells(data):
    candidates = (
        "active_cells", "active",
        "cells",
        "positions",
        "active_positions",
        "universe",
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in candidates:
            value = data.get(key)
            if isinstance(value, list):
                return value

    raise ValueError(
        "No se pudo localizar la lista de celdas activas. "
        f"Claves disponibles: {list(data.keys()) if isinstance(data, dict) else type(data)}"
    )

def normalize_cells(raw):
    result = []

    for item in raw:
        if isinstance(item, (int, float)):
            result.append(int(item))
        elif isinstance(item, dict):
            found = False
            for key in ("x", "position", "pos", "coordinate"):
                if key in item:
                    result.append(int(item[key]))
                    found = True
                    break
            if not found:
                raise ValueError(f"Formato de celda desconocido: {item}")
        elif isinstance(item, (list, tuple)) and item:
            result.append(int(item[0]))
        else:
            raise ValueError(f"Formato de celda no reconocido: {item}")

    return sorted(set(result))

def extract_runs_and_gaps(cells):
    runs = []
    gaps = []

    start = cells[0]
    previous = cells[0]
    current_length = 1

    for x in cells[1:]:
        distance = x - previous

        if distance == 1:
            current_length += 1
        else:
            runs.append(current_length)
            gaps.append(distance - 1)
            current_length = 1

        previous = x

    runs.append(current_length)
    return np.asarray(runs, dtype=np.int64), np.asarray(gaps, dtype=np.int64)

def build_binary(runs, gaps, span):
    if len(runs) != len(gaps) + 1:
        raise ValueError("La cantidad de componentes y gaps no es consistente.")

    starts = np.empty(len(runs), dtype=np.int64)
    starts[0] = 0

    if len(gaps):
        starts[1:] = np.cumsum(runs[:-1] + gaps)

    binary = np.zeros(span, dtype=np.float64)

    for start, length in zip(starts, runs):
        binary[start:start + length] = 1.0

    return binary

def autocorrelation(binary, fft_size):
    transformed = np.fft.rfft(binary, n=fft_size)
    power = transformed * np.conjugate(transformed)
    counts = np.fft.irfft(power, n=fft_size)[:MAX_LAG + 1]

    return counts[1:] / counts[0]

def save_csv(path, observed, null_mean, null_sd, z_scores, p_values, adjusted):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lag",
            "observed_correlation",
            "null_mean",
            "null_std",
            "z_score",
            "empirical_p",
            "bonferroni_significant",
        ])

        for i in range(MAX_LAG):
            writer.writerow([
                i + 1,
                float(observed[i]),
                float(null_mean[i]),
                float(null_sd[i]),
                float(z_scores[i]),
                float(p_values[i]),
                bool(adjusted[i]),
            ])

def run_model(name, original_runs, original_gaps, observed, span, active_count):
    print(f"\n--- MODELO {name.upper()} ---", flush=True)

    rng = np.random.default_rng(SEEDS[name])

    null = np.empty((REPLICATES, MAX_LAG), dtype=np.float64)
    original_run_multiset = Counter(original_runs.tolist())
    original_gap_multiset = Counter(original_gaps.tolist())

    for replica in range(REPLICATES):
        if name == "components":
            runs = rng.permutation(original_runs)
            gaps = original_gaps
        else:
            runs = original_runs
            gaps = rng.permutation(original_gaps)

        binary = build_binary(runs, gaps, span)

        if int(binary.sum()) != active_count:
            raise RuntimeError("Una réplica no conserva la población activa.")

        null[replica] = autocorrelation(binary, FFT_SIZE)

        if (replica + 1) % 250 == 0:
            print(
                f"{name}: {replica + 1}/{REPLICATES} réplicas",
                flush=True,
            )

    # Separación independiente: calibración y validación.
    training = null[:TRAIN_SIZE]
    validation = null[TRAIN_SIZE:]

    null_mean = training.mean(axis=0)
    null_sd = training.std(axis=0, ddof=1)

    safe_sd = np.where(null_sd == 0, np.finfo(float).eps, null_sd)

    observed_z = (observed - null_mean) / safe_sd
    validation_z = (validation - null_mean) / safe_sd

    observed_max_z = float(np.max(np.abs(observed_z)))
    validation_max_z = np.max(np.abs(validation_z), axis=1)

    global_exceedances = int(np.sum(validation_max_z >= observed_max_z))
    global_p = (global_exceedances + 1) / (len(validation_max_z) + 1)

    empirical_p = (
        1 + np.sum(
            np.abs(validation - null_mean)
            >= np.abs(observed - null_mean),
            axis=0,
        )
    ) / (len(validation) + 1)

    bonferroni = np.minimum(empirical_p * MAX_LAG, 1.0)
    significant = bonferroni < 0.05

    csv_path = EXPORT / f"ablation_{name}.csv"

    save_csv(
        csv_path,
        observed,
        null_mean,
        null_sd,
        observed_z,
        empirical_p,
        significant,
    )

    report = {
        "model": name,
        "replicas": REPLICATES,
        "training_replicas": TRAIN_SIZE,
        "validation_replicas": len(validation),
        "seed": SEEDS[name],
        "preserved_active_cells": active_count,
        "preserved_span": span,
        "preserved_components": len(original_runs),
        "preserved_run_size_multiset": True,
        "preserved_gap_size_multiset": True,
        "component_order_preserved": name == "gaps",
        "gap_order_preserved": name == "components",
        "observed_max_abs_z": observed_max_z,
        "global_max_statistic_p": float(global_p),
        "global_validation_exceedances": global_exceedances,
        "bonferroni_significant_lags": int(significant.sum()),
        "empirical_p_resolution": 1 / (len(validation) + 1),
        "top_lags": [],
        "csv": csv_path.name,
    }

    strongest = np.argsort(np.abs(observed_z))[::-1][:10]

    for i in strongest:
        report["top_lags"].append({
            "lag": int(i + 1),
            "observed": float(observed[i]),
            "null_mean": float(null_mean[i]),
            "z": float(observed_z[i]),
            "empirical_p": float(empirical_p[i]),
            "bonferroni_p": float(bonferroni[i]),
        })

    report_path = EXPORT / f"ablation_{name}_report.json"

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"\nModelo: {name}")
    print(f"Máximo |Z|: {observed_max_z:.4f}")
    print(f"Global max-statistic p: {global_p:.6f}")
    print(f"Lags significativos Bonferroni: {int(significant.sum())}/{MAX_LAG}")
    print(f"CSV: {csv_path}")
    print(f"Informe: {report_path}")

    return report

print("DSHADOW-CELLS-002 | EXPERIMENTO 014")
print("Ablación independiente de componentes y gaps")
print(f"Snapshot: {SNAPSHOT}")

if not SNAPSHOT.exists():
    raise FileNotFoundError(SNAPSHOT)

snapshot_hash_before = sha256(SNAPSHOT)

data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
cells = normalize_cells(extract_cells(data))

if not cells:
    raise ValueError("El snapshot no contiene celdas activas.")

min_x = min(cells)
max_x = max(cells)
span = max_x - min_x + 1
active_count = len(cells)

shifted = [x - min_x for x in cells]

runs, gaps = extract_runs_and_gaps(shifted)

if int(runs.sum()) != active_count:
    raise RuntimeError("La suma de componentes no coincide con la población.")

if int(runs.sum() + gaps.sum()) != span:
    raise RuntimeError("La suma de componentes y gaps no coincide con el span.")

original_binary = build_binary(runs, gaps, span)

if int(original_binary.sum()) != active_count:
    raise RuntimeError("La reconstrucción original no coincide con el snapshot.")

FFT_SIZE = 1 << (2 * span - 1).bit_length()

observed = autocorrelation(original_binary, FFT_SIZE)

print("\n=== CONFIGURACIÓN ===")
print(f"Celdas activas: {active_count}")
print(f"Span: {span}")
print(f"Componentes: {len(runs)}")
print(f"Gaps positivos: {len(gaps)}")
print(f"Réplicas por modelo: {REPLICATES}")
print(f"Lags: {MAX_LAG}")
print(f"SHA256 inicial: {snapshot_hash_before}")

reports = []

reports.append(
    run_model(
        "components",
        runs,
        gaps,
        observed,
        span,
        active_count,
    )
)

reports.append(
    run_model(
        "gaps",
        runs,
        gaps,
        observed,
        span,
        active_count,
    )
)

snapshot_hash_after = sha256(SNAPSHOT)

if snapshot_hash_before != snapshot_hash_after:
    raise RuntimeError("El snapshot cambió durante el análisis.")

summary = {
    "experiment": "014_ABLATION_COMPONENTS_GAPS",
    "snapshot": SNAPSHOT.name,
    "snapshot_sha256": snapshot_hash_before,
    "active_cells": active_count,
    "span": span,
    "components": len(runs),
    "positive_gaps": len(gaps),
    "replicas_per_model": REPLICATES,
    "max_lag": MAX_LAG,
    "validation_method": "Independent training/validation split",
    "models": reports,
    "snapshot_unchanged": True,
}

summary_path = EXPORT / "ablation_summary.json"

summary_path.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

print("\n=== EXPERIMENTO 014 COMPLETADO ===")
print(f"Snapshot intacto: {snapshot_hash_before == snapshot_hash_after}")
print(f"Resumen: {summary_path}")


