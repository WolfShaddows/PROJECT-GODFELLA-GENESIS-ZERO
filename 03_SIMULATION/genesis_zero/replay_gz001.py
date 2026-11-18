import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from genesis_engine import GenesisConfig, GenesisZero

config = GenesisConfig()
universe = GenesisZero(config)

results = ROOT / "results"
frames_dir = results / "gz001_frames"
frames_dir.mkdir(parents=True, exist_ok=True)

history = []
snapshots = []

def record():
    stats = universe.observe()
    history.append(stats)

    if universe.step % 5 == 0 or universe.step == 0:
        snapshots.append(universe.state.copy())

record()

for _ in range(config.steps):
    universe.evolve()
    record()

with open(results / "gz001_cycle_statistics.csv",
          "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=history[0].keys())
    writer.writeheader()
    writer.writerows(history)

fig, ax = plt.subplots(figsize=(7, 7))

image = ax.imshow(
    snapshots[0],
    origin="lower",
    interpolation="nearest",
    vmin=min(np.min(s) for s in snapshots),
    vmax=max(np.max(s) for s in snapshots),
)

title = ax.set_title("GENESIS ZERO | Step 0")
ax.set_xlabel("X")
ax.set_ylabel("Y")
fig.colorbar(image, ax=ax, label="Field value")

def update(frame):
    image.set_data(snapshots[frame])
    title.set_text(f"GENESIS ZERO | Step {frame * 5}")
    return image, title

animation = FuncAnimation(
    fig,
    update,
    frames=len(snapshots),
    interval=100,
    blit=False
)

gif_path = results / "gz001_evolution.gif"
animation.save(gif_path, writer=PillowWriter(fps=10))

plt.close(fig)

print("GZ-001 REPLAY COMPLETED")
print("Cycles:", config.steps)
print("Frames:", len(snapshots))
print("Statistics:", results / "gz001_cycle_statistics.csv")
print("Animation:", gif_path)
