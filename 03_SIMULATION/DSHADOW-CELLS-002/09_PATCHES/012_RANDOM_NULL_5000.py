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
SEED = 20261106

data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
cells = np.asarray(sorted(set(map(int, data["active"]))), dtype=np.int64)

minimum = int(cells[0])
maximum = int(cells[-1])
span = maximum - minimum + 1
n = len(cells)
density = n / span

observed = np.zeros(span, dtype=np.float64)
observed[cells - minimum] = 1.0

fft_size = 1 << (2 * span - 2).bit_length()

def pair_counts(binary):
    spectrum = np.fft.rfft(binary, n=fft_size)
    power = spectrum * np.conjugate(spectrum)
    result = np.fft.irfft(power, n=fft_size)
    return np.rint(result[:MAX_LAG + 1]).astype(np.int64)

lags = np.arange(1, MAX_LAG + 1)
pair_totals = span - lags
denominator = density * (1 - density)

observed_counts = pair_counts(observed)
observed_joint = observed_counts[1:] / pair_totals
observed_corr = (observed_joint - density**2) / denominator

rng = np.random.default_rng(SEED)
null_corr = np.empty((REPLICATES, MAX_LAG), dtype=np.float64)

started = time.time()

print("\n=== GENERANDO 5.000 REFERENCIAS ALEATORIAS ===")
print(f"Generación del snapshot: {data.get('generation')}")
print(f"Células: {n:,} | Extensión: {span:,}")
print(f"Distancias examinadas: {MAX_LAG}")
print("El motor y el snapshot permanecen intactos.\n")

for rep in range(REPLICATES):
    binary = np.zeros(span, dtype=np.float64)
    selected = rng.choice(span, size=n, replace=False)
    binary[selected] = 1.0

    counts = pair_counts(binary)
    joint = counts[1:] / pair_totals
    null_corr[rep] = (joint - density**2) / denominator

    if (rep + 1) % 250 == 0:
        elapsed = time.time() - started
        print(
            f"{rep + 1:4d}/{REPLICATES} "
            f"| transcurrido: {elapsed:.1f} s"
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

# Valores p empíricos bilaterales por distancia.
p_values = (
    1 + np.sum(
        np.abs(null_corr - null_mean) >=
        np.abs(observed_corr - null_mean),
        axis=0
    )
) / (REPLICATES + 1)

# Corrección Bonferroni.
adjusted_p = np.minimum(p_values * MAX_LAG, 1.0)

# Prueba global: máximo |Z| entre las 128 distancias.
observed_max_z = float(np.max(np.abs(observed_z)))
null_max_z = np.max(np.abs(null_z), axis=1)

global_p = (
    1 + np.count_nonzero(null_max_z >= observed_max_z)
) / (REPLICATES + 1)

rows = []

for i, lag in enumerate(lags):
    rows.append([
        int(lag),
        float(observed_corr[i]),
        float(null_mean[i]),
        float(null_sd[i]),
        float(observed_z[i]),
        float(p_values[i]),
        float(adjusted_p[i]),
        bool(adjusted_p[i] < 0.05)
    ])

csv_path = OUT / "random_null_comparison_5000.csv"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "lag", "observed_correlation", "random_mean",
        "random_sd", "z_score", "empirical_p",
        "bonferroni_p", "significant_bonferroni"
    ])
    writer.writerows(rows)

report = {
    "experiment": "DSHADOW-CELLS-002",
    "snapshot_generation": data.get("generation"),
    "active_cells": int(n),
    "spatial_span": int(span),
    "density": float(density),
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
        "The null model preserves population and interval, not Rule 110 dynamics.",
        "The test concerns one spatial snapshot.",
        "Statistical deviation does not establish its causal mechanism.",
        "The random reference assumes uniformly selected positions without replacement."
    ]
}

(OUT / "random_null_report_5000.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n=== RESULTADO GLOBAL ===")
print(f"Máximo |Z| observado: {observed_max_z:.4f}")
print(f"p global:             {global_p:.6f}")
print(f"Significativo global: {global_p < 0.05}")
print(f"Lags Bonferroni:      {len(report['bonferroni_significant_lags'])}")

print("\n=== 15 MAYORES DESVIACIONES ===")
for row in sorted(rows, key=lambda x: abs(x[4]), reverse=True)[:15]:
    print(
        f"lag={row[0]:3d} | obs={row[1]:+.4f} "
        f"| aleatorio={row[2]:+.5f} | Z={row[4]:+.2f} "
        f"| p={row[5]:.5f} | p_adj={row[6]:.5f}"
    )

print(f"\nCSV: {csv_path}")
print(f"Informe: {OUT / 'random_null_report_5000.json'}")
print("No se modificaron el snapshot, los logs ni el motor.")
