import json
import csv
import math
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "evidence" / "UNIVERSE_EXPORT_20261105_112658"
SNAPSHOT = EXPORT / "universe_snapshot.json"
OUT = EXPORT / "RESEARCH_4_LINES"
OUT.mkdir(parents=True, exist_ok=True)

REPLICATES = 100
MAX_LAG = 128
SEED = 20261105

data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
cells = np.asarray(sorted(set(map(int, data["active"]))), dtype=np.int64)

minimum = int(cells[0])
maximum = int(cells[-1])
span = maximum - minimum + 1
n = len(cells)
density = n / span

# Vector binario del universo completo dentro de sus límites.
observed = np.zeros(span, dtype=np.float64)
observed[cells - minimum] = 1.0

# Padding para obtener autocorrelación lineal mediante FFT.
fft_size = 1 << (2 * span - 2).bit_length()

def pair_counts(binary):
    spectrum = np.fft.rfft(binary, n=fft_size)
    power = spectrum * np.conjugate(spectrum)
    correlation = np.fft.irfft(power, n=fft_size)
    return np.rint(correlation[:MAX_LAG + 1]).astype(np.int64)

observed_counts = pair_counts(observed)

lags = np.arange(1, MAX_LAG + 1)
pair_totals = span - lags

observed_joint = observed_counts[1:MAX_LAG + 1] / pair_totals
observed_corr = (
    observed_joint - density * density
) / (density * (1 - density))

rng = np.random.default_rng(SEED)

null_corr = np.empty((REPLICATES, MAX_LAG), dtype=np.float64)

for rep in range(REPLICATES):
    binary = np.zeros(span, dtype=np.float64)
    selected = rng.choice(span, size=n, replace=False)
    binary[selected] = 1.0

    counts = pair_counts(binary)
    joint = counts[1:MAX_LAG + 1] / pair_totals

    null_corr[rep] = (
        joint - density * density
    ) / (density * (1 - density))

    if (rep + 1) % 10 == 0:
        print(f"Referencias aleatorias: {rep + 1}/{REPLICATES}")

null_mean = null_corr.mean(axis=0)
null_sd = null_corr.std(axis=0, ddof=1)

z_scores = np.divide(
    observed_corr - null_mean,
    null_sd,
    out=np.zeros_like(observed_corr),
    where=null_sd > 0
)

# Prueba empírica bilateral por distancia.
p_values = (
    1 + np.sum(
        np.abs(null_corr - null_mean) >=
        np.abs(observed_corr - null_mean),
        axis=0
    )
) / (REPLICATES + 1)

# Corrección Bonferroni para las 128 distancias examinadas.
adjusted_p = np.minimum(p_values * MAX_LAG, 1.0)

rows = []

for i, lag in enumerate(lags):
    rows.append([
        int(lag),
        float(observed_corr[i]),
        float(null_mean[i]),
        float(null_sd[i]),
        float(z_scores[i]),
        float(p_values[i]),
        float(adjusted_p[i]),
        bool(adjusted_p[i] < 0.05)
    ])

csv_path = OUT / "random_null_comparison.csv"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "lag",
        "observed_correlation",
        "random_mean",
        "random_sd",
        "z_score",
        "empirical_p",
        "bonferroni_p",
        "significant_after_correction"
    ])
    writer.writerows(rows)

report = {
    "experiment": "DSHADOW-CELLS-002",
    "snapshot_generation": data.get("generation"),
    "active_cells": int(n),
    "spatial_span": int(span),
    "density": float(density),
    "replicates": REPLICATES,
    "random_seed": SEED,
    "tested_lags": MAX_LAG,
    "method": "Fixed-population random occupancy with linear FFT autocorrelation",
    "multiple_testing_correction": "Bonferroni",
    "significant_lags_after_correction": [
        int(lags[i]) for i in range(MAX_LAG)
        if adjusted_p[i] < 0.05
    ],
    "limitations": [
        "The null model preserves population and interval, but not Rule 110 dynamics.",
        "100 random replicates provide limited empirical p-value resolution.",
        "Bonferroni correction is conservative.",
        "This is a single-snapshot spatial comparison, not a temporal causal test."
    ]
}

(OUT / "random_null_report.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n=== RULE 110 VS RANDOM REFERENCE ===")
print(f"Snapshot generation: {data.get('generation')}")
print(f"Active cells:         {n:,}")
print(f"Spatial span:         {span:,}")
print(f"Density:              {density * 100:.6f}%")
print(f"Random replicates:    {REPLICATES}")
print(f"Tested distances:     {MAX_LAG}")
print(f"Significant lags after Bonferroni: {len(report['significant_lags_after_correction'])}")

print("\n=== STRONGEST DEVIATIONS ===")
ranked = sorted(rows, key=lambda r: abs(r[4]), reverse=True)

for row in ranked[:15]:
    print(
        f"lag={row[0]:3d} | observed={row[1]:+.4f} "
        f"| random={row[2]:+.4f} | z={row[4]:+.2f} "
        f"| p_adj={row[6]:.4f} | significant={row[7]}"
    )

print(f"\nCSV: {csv_path}")
print(f"Report: {OUT / 'random_null_report.json'}")
print("Snapshot, logs and live engine were not modified.")
