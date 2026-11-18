import sys
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from genesis_engine import GenesisConfig, GenesisZero

config = GenesisConfig()
universe = GenesisZero(config)

states = [universe.state.copy()]
history = [universe.observe()]

# Reproduce the same deterministic trajectory.
for _ in range(config.steps):
    universe.evolve()
    states.append(universe.state.copy())
    history.append(universe.observe())

# Shared histogram boundaries across all cycles.
global_min = min(float(s.min()) for s in states)
global_max = max(float(s.max()) for s in states)

bins = 64
edges = np.linspace(global_min, global_max, bins + 1)

for index, state in enumerate(states):
    counts, _ = np.histogram(state, bins=edges)
    probabilities = counts[counts > 0] / state.size

    shannon_bits = -np.sum(
        probabilities * np.log2(probabilities)
    )

    history[index]["shannon_value_entropy_bits"] = float(shannon_bits)

results = ROOT / "results"
results.mkdir(exist_ok=True)

csv_path = results / "gz001_extended_analysis.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=history[0].keys()
    )
    writer.writeheader()
    writer.writerows(history)

steps = [item["step"] for item in history]
means = [item["mean"] for item in history]
variances = [item["variance"] for item in history]
entropies = [
    item["shannon_value_entropy_bits"]
    for item in history
]

fig, axes = plt.subplots(3, 1, figsize=(12, 11))

axes[0].plot(steps, variances)
axes[0].set_title("GENESIS ZERO — Variance")
axes[0].set_ylabel("Variance")
axes[0].grid(True, alpha=0.3)

axes[1].plot(steps, means)
axes[1].set_title("GENESIS ZERO — Mean")
axes[1].set_ylabel("Mean value")
axes[1].grid(True, alpha=0.3)

axes[2].plot(steps, entropies)
axes[2].set_title(
    "GENESIS ZERO — Shannon Entropy of Value Distribution"
)
axes[2].set_xlabel("Evolution cycle")
axes[2].set_ylabel("Entropy (bits)")
axes[2].grid(True, alpha=0.3)

fig.suptitle(
    "GZ-001 | Evolution Analysis | 500 Cycles",
    fontsize=15
)

fig.tight_layout()

plot_path = results / "gz001_evolution_analysis.png"
fig.savefig(plot_path, dpi=170)
plt.close(fig)

print("\n=== GZ-001 ANALYSIS COMPLETED ===")
print("Cycles:", len(history) - 1)
print("Observations:", len(history))
print("Histogram bins:", bins)
print("Histogram range:", global_min, global_max)

print("\nINITIAL")
print("Mean:", means[0])
print("Variance:", variances[0])
print("Shannon entropy:", entropies[0])

print("\nFINAL")
print("Mean:", means[-1])
print("Variance:", variances[-1])
print("Shannon entropy:", entropies[-1])

print("\nFILES")
print("CSV:", csv_path)
print("GRAPH:", plot_path)
