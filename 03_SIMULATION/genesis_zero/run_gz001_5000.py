import csv
import sys
import hashlib
from pathlib import Path
from dataclasses import replace

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from genesis_engine import GenesisConfig, GenesisZero

# Same original configuration and rules.
base_config = GenesisConfig()
config = replace(base_config, steps=5000)

OUTPUT = ROOT / "results" / "gz001_5000"
CHECKPOINTS = OUTPUT / "checkpoints"
OUTPUT.mkdir(parents=True, exist_ok=True)
CHECKPOINTS.mkdir(parents=True, exist_ok=True)

universe = GenesisZero(config)

# Fixed histogram: 64 bins in [0, 1],
# plus underflow and overflow categories.
def value_entropy(state):
    values = state.ravel()

    underflow = np.count_nonzero(values < 0.0)
    overflow = np.count_nonzero(values > 1.0)

    inside = values[(values >= 0.0) & (values <= 1.0)]

    counts, _ = np.histogram(
        inside,
        bins=64,
        range=(0.0, 1.0)
    )

    counts = np.concatenate(([underflow], counts, [overflow]))
    probabilities = counts[counts > 0] / values.size

    return float(-np.sum(probabilities * np.log2(probabilities)))

history = []
snapshots = []

def observe():
    record = universe.observe()
    record["shannon_value_entropy_bits"] = value_entropy(universe.state)
    history.append(record)

    if universe.step % 50 == 0 or universe.step == 0:
        snapshots.append((universe.step, universe.state.copy()))

    if universe.step > 0 and universe.step % 1000 == 0:
        checkpoint = CHECKPOINTS / f"state_step_{universe.step:05d}.npy"
        np.save(checkpoint, universe.state)

observe()

for _ in range(config.steps):
    universe.evolve()
    observe()

# Save final state.
final_path = OUTPUT / "final_state_5000.npy"
np.save(final_path, universe.state)

# Save cycle-by-cycle statistics.
csv_path = OUTPUT / "cycle_statistics_5000.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=history[0].keys())
    writer.writeheader()
    writer.writerows(history)

# Evolution graphs.
steps = [r["step"] for r in history]
means = [r["mean"] for r in history]
variances = [r["variance"] for r in history]
entropies = [r["shannon_value_entropy_bits"] for r in history]

fig, axes = plt.subplots(3, 1, figsize=(12, 11))

axes[0].plot(steps, variances)
axes[0].set_title("GENESIS ZERO — Variance")
axes[0].set_ylabel("Variance")
axes[0].grid(True, alpha=0.3)

axes[1].plot(steps, means)
axes[1].set_title("GENESIS ZERO — Mean")
axes[1].set_ylabel("Mean")
axes[1].grid(True, alpha=0.3)

axes[2].plot(steps, entropies)
axes[2].set_title("GENESIS ZERO — Shannon Value Entropy")
axes[2].set_xlabel("Cycle")
axes[2].set_ylabel("Entropy (bits)")
axes[2].grid(True, alpha=0.3)

fig.suptitle("GZ-001 | Extended Observation | 5000 Cycles")
fig.tight_layout()

graph_path = OUTPUT / "evolution_analysis_5000.png"
fig.savefig(graph_path, dpi=160)
plt.close(fig)

# Animation: one frame every 50 cycles.
fig, ax = plt.subplots(figsize=(7, 7))

image = ax.imshow(
    snapshots[0][1],
    origin="lower",
    interpolation="nearest",
    vmin=min(float(s.min()) for _, s in snapshots),
    vmax=max(float(s.max()) for _, s in snapshots)
)

title = ax.set_title("GENESIS ZERO | Step 0")
ax.set_xlabel("X")
ax.set_ylabel("Y")
fig.colorbar(image, ax=ax, label="Field value")

def update(index):
    step, state = snapshots[index]
    image.set_data(state)
    title.set_text(f"GENESIS ZERO | Step {step}")
    return image, title

animation = FuncAnimation(
    fig,
    update,
    frames=len(snapshots),
    interval=100,
    blit=False
)

gif_path = OUTPUT / "evolution_5000.gif"
animation.save(gif_path, writer=PillowWriter(fps=10))
plt.close(fig)

# Record hashes of generated evidence.
evidence = [
    csv_path,
    final_path,
    graph_path,
    gif_path
]

manifest_path = OUTPUT / "sha256_manifest.txt"

with open(manifest_path, "w", encoding="utf-8") as f:
    for file in evidence:
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        f.write(f"{digest}  {file.name}\n")

# Summary.
first = history[0]
last = history[-1]

print("\n=== GENESIS ZERO | GZ-001 EXTENDED RUN ===")
print("Cycles:", config.steps)
print("Observations:", len(history))
print("Snapshots:", len(snapshots))
print("Grid:", config.width, "x", config.height)
print("Seed:", config.seed)

print("\nINITIAL STATE")
print("Mean:", first["mean"])
print("Variance:", first["variance"])
print("Entropy:", first["shannon_value_entropy_bits"])

print("\nFINAL STATE")
print("Mean:", last["mean"])
print("Variance:", last["variance"])
print("Entropy:", last["shannon_value_entropy_bits"])
print("Minimum:", last["minimum"])
print("Maximum:", last["maximum"])

print("\nEVIDENCE DIRECTORY:", OUTPUT)
print("Statistics:", csv_path)
print("Final state:", final_path)
print("Graph:", graph_path)
print("Animation:", gif_path)
print("Hashes:", manifest_path)

print("\nEXTENDED RUN COMPLETED")
