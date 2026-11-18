import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from genesis_engine import GenesisConfig, GenesisZero

config = GenesisConfig()
universe = GenesisZero(config)

initial = universe.state.copy()

for _ in range(config.steps):
    universe.evolve()

final = universe.state.copy()

results = ROOT / "results"
results.mkdir(exist_ok=True)

np.save(results / "initial_state.npy", initial)
np.save(results / "final_state.npy", final)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].imshow(initial, origin="lower", interpolation="nearest")
axes[0].set_title("GENESIS ZERO - Initial State")

axes[1].imshow(final, origin="lower", interpolation="nearest")
axes[1].set_title(f"GENESIS ZERO - Step {config.steps}")

for ax in axes:
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

fig.tight_layout()

output = results / "first_evolution.png"
fig.savefig(output, dpi=160)
plt.show()

print(f"\nINITIAL STATE: {results / 'initial_state.npy'}")
print(f"FINAL STATE:   {results / 'final_state.npy'}")
print(f"VISUALIZATION: {output}")
