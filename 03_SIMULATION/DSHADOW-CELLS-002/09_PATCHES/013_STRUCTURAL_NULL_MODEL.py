import json
import csv
import time
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "evidence" / "UNIVERSE_EXPORT_20261105_112658"
SNAPSHOT = EXPORT / "universe_snapshot.json"
OUT = EXPORT / "RESEARCH_4_LINES"
OUT.mkdir(parents=True, exist_ok=True)

REPLICATES = 5000
MAX_LAG = 128
SEED = 20261107

data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
cells = np.asarray(sorted(set(map(int, data["active"]))), dtype=np.int64)

minimum = int(cells[0])
maximum = int(cells[-1])
span = maximum - minimum + 1
n = len(cells)
density = n / span

# Extraer componentes y separaciones positivas.
differences = np.diff(cells)
breaks = np.flatnonzero(differences > 1)

starts = np.r_[0, breaks + 1]
ends = np.r_[breaks, len(cells) - 1]

run_lengths = (ends - starts + 1).astype(np.int64)
positive_gaps = (cells[starts[1:]] - cells[ends[:-1]] - 1).astype(np.int64)

assert len(run_lengths) == len(positive_gaps) + 1
assert int(run_lengths.sum()) == n
assert int(positive_gaps.sum()) == span - n

# Reconstrucción de la configuración original.
def build_configuration(runs, gaps):
    positions = []
    cursor = 0

    for i, length in enumerate(runs):
        positions.extend(range(cursor, cursor + int(length)))
        cursor += int(length)

        if i < len(gaps):
            cursor += int(gaps[i])

    if cursor != span:
        raise ValueError(
            f"Extensión reconstruida incorrecta: {cursor} != {span}"
        )

    return positions

# Padding para autocorrelación lineal.
fft_size = 1 << (2 * span - 2).bit_length()
lags = np.arange(1, MAX_LAG + 1)
pair_totals = span - lags
denominator = density * (1 - density)

def correlation(binary):
    spectrum = np.fft.rfft(binary, n=fft_size)
    power = spectrum * np.conjugate(spectrum)
    counts = np.rint(
        np.fft.irfft(power, n=fft_size)[:MAX_LAG + 1]
    ).astype(np.int64)

    joint = counts[1:] / pair_totals
    return (joint - density**2) / denominator

observed = np.zeros(span, dtype=np.float64)
observed[cells - minimum] = 1.0
observed_corr = correlation(observed)

rng = np.random.default_rng(SEED)
null_corr = np.empty((REPLICATES, MAX_LAG), dtype=np.float64)

print("\n=== CONTROL ESTRUCTURAL DE RULE 110 ===")
print(f"Generación:             {data.get('generation')}")
print(f"Células:                {n:,}")
print(f"Extensión:              {span:,}")
print(f"Componentes:            {len(run_lengths):,}")
print(f"Separaciones positivas: {len(positive_gaps):,}")
print(f"Réplicas:               {REPLICATES:,}")
print("Se conservarán exactamente todos los tamaños de bloques y huecos.\n")

started = time.time()

for rep in range(REPLICATES):
    shuffled_runs = rng.permutation(run_lengths)
    shuffled_gaps = rng.permutation(positive_gaps)

    positions = build_configuration(shuffled_runs, shuffled_gaps)

    binary = np.zeros(span, dtype=np.float64)
    binary[positions] = 1.0

    null_corr[rep] = correlation(binary)

    if (rep + 1) % 250 == 0:
        print(
            f"{rep + 1:4d}/{REPLICATES} "
            f"| transcurrido: {time.time() - started:.1f} s"
        )

null_mean = null_corr.mean(axis=0)
null_sd = null_corr.std(axis=0, ddof=1)

observed_z = np.divide(
    observed_corr - null_mean,
    null_sd,
    out=np.zeros_like(observed_corr),
    where=null_sd > 0
)

null_z = np.divide(
    null_corr - null_mean,
    null_sd,
    out=np.zeros_like(null_corr),
    where=null_sd > 0
)

# Prueba global basada en el máximo desvío estandarizado.
observed_max_z = float(np.max(np.abs(observed_z)))
null_max_z = np.max(np.abs(null_z), axis=1)

global_p = (
    1 + np.count_nonzero(null_max_z >= observed_max_z)
) / (REPLICATES + 1)

# Pruebas empíricas por distancia.
p_values = (
    1 + np.sum(
        np.abs(null_corr - null_mean) >=
        np.abs(observed_corr - null_mean),
        axis=0
    )
) / (REPLICATES + 1)

adjusted_p = np.minimum(p_values * MAX_LAG, 1.0)

rows = []

for i, lag in enumerate(lags):
    rows.append([
        int(lag),
        float(observed_corr[i]),
        float(null_mean[i]),
        float(null_sd[i]),
        float(observed_z[i]),
        float(p_values[i]),
        float(adjusted_p[i])
    ])

csv_path = OUT / "structural_null_comparison.csv"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "lag",
        "observed_correlation",
        "structural_null_mean",
        "structural_null_sd",
        "z_score",
        "empirical_p",
        "bonferroni_p"
    ])
    writer.writerows(rows)

report = {
    "experiment": "DSHADOW-CELLS-002",
    "snapshot_generation": data.get("generation"),
    "active_cells": int(n),
    "spatial_span": int(span),
    "components": int(len(run_lengths)),
    "positive_gaps": int(len(positive_gaps)),
    "component_sizes_preserved": True,
    "positive_gap_sizes_preserved": True,
    "replicates": REPLICATES,
    "seed": SEED,
    "tested_lags": MAX_LAG,
    "observed_max_absolute_z": observed_max_z,
    "global_max_statistic_p": float(global_p),
    "global_test_significant_0_05": bool(global_p < 0.05),
    "bonferroni_significant_lags": [
        int(lags[i])
        for i in range(MAX_LAG)
        if adjusted_p[i] < 0.05
    ],
    "minimum_empirical_p": 1 / (REPLICATES + 1),
    "elapsed_seconds": time.time() - started,
    "limitations": [
        "The null model preserves component and positive-gap size distributions.",
        "It randomizes their spatial ordering.",
        "It does not preserve Rule 110 transition history.",
        "The test concerns one snapshot, not temporal causation."
    ]
}

(OUT / "structural_null_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n=== RESULTADO GLOBAL ===")
print(f"Máximo |Z| observado: {observed_max_z:.4f}")
print(f"p global:             {global_p:.6f}")
print(f"Significativo:        {global_p < 0.05}")
print(f"Lags Bonferroni:      {len(report['bonferroni_significant_lags'])}")

print("\n=== 15 MAYORES DESVIACIONES ===")
for row in sorted(rows, key=lambda x: abs(x[4]), reverse=True)[:15]:
    print(
        f"lag={row[0]:3d} | obs={row[1]:+.4f} "
        f"| control={row[2]:+.5f} | Z={row[4]:+.2f} "
        f"| p={row[5]:.5f} | p_adj={row[6]:.5f}"
    )

print(f"\nCSV: {csv_path}")
print(f"Informe: {OUT / 'structural_null_report.json'}")
print("Snapshot, logs y motor originales no fueron modificados.")
