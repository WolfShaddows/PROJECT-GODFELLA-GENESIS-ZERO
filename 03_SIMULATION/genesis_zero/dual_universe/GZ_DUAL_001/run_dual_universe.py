from pathlib import Path
import sys
import csv
import json
import hashlib
import platform
from datetime import datetime, timezone

import numpy as np
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parents[4]
ENGINE_DIR = PROJECT / "03_SIMULATION" / "genesis_zero"

sys.path.insert(0, str(ENGINE_DIR))

from genesis_engine import GenesisConfig, GenesisZero

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

STEPS = 1000
SEED_A = 20261102
SEED_B = 20261103

INTRODUCTION_STEP = 100
INTRODUCTION_AMPLITUDE = 0.25
INTRODUCTION_SIGMA = 5.0

config_a = GenesisConfig(
    width=128,
    height=128,
    seed=SEED_A,
    steps=STEPS,
    diffusion=0.15,
    noise_amplitude=0.01
)

config_b = GenesisConfig(
    width=128,
    height=128,
    seed=SEED_B,
    steps=STEPS,
    diffusion=0.15,
    noise_amplitude=0.01
)

universe_a = GenesisZero(config_a)
universe_b = GenesisZero(config_b)

# Paired initial condition: identical starting field.
initial_state = universe_a.state.copy()
universe_b.state = initial_state.copy()

initial_a = universe_a.state.copy()
initial_b = universe_b.state.copy()

def introduce_perturbation(state):
    height, width = state.shape
    y, x = np.mgrid[0:height, 0:width]
    cy = (height - 1) / 2
    cx = (width - 1) / 2

    gaussian = np.exp(
        -((x - cx)**2 + (y - cy)**2)
        / (2 * INTRODUCTION_SIGMA**2)
    )

    state += INTRODUCTION_AMPLITUDE * gaussian
    return float(np.sum(INTRODUCTION_AMPLITUDE * gaussian))

def record(label, engine):
    values = engine.observe()
    values["universe"] = label
    return values

rows = [
    record("A", universe_a),
    record("B", universe_b)
]

introduced_amount = None

print("GZ-DUAL-001 — PARALLEL PILOT")
print("Initializing independent universes...")
print("Grid: 128 x 128")
print("Cycles:", STEPS)
print("Initial states: identical")
print("Random generators: independent")
print("Universe A: no external introduction")
print("Universe B: scheduled localized perturbation")
print()

for cycle in range(1, STEPS + 1):

    if cycle == INTRODUCTION_STEP + 1:
        introduced_amount = introduce_perturbation(
            universe_b.state
        )
        print(
            f"Introduction applied to B after cycle "
            f"{INTRODUCTION_STEP}: "
            f"total increment={introduced_amount:.8f}"
        )

    universe_a.evolve()
    universe_b.evolve()

    rows.append(record("A", universe_a))
    rows.append(record("B", universe_b))

    if cycle % 100 == 0:
        print(
            f"Cycle {cycle}/{STEPS} | "
            f"A variance={np.var(universe_a.state):.8f} | "
            f"B variance={np.var(universe_b.state):.8f}"
        )

csv_path = OUT / "dual_universe_statistics.csv"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

np.save(OUT / "universe_a_initial.npy", initial_a)
np.save(OUT / "universe_b_initial.npy", initial_b)
np.save(OUT / "universe_a_final.npy", universe_a.state)
np.save(OUT / "universe_b_final.npy", universe_b.state)

fig, axes = plt.subplots(2, 3, figsize=(15, 9))

images = [
    (initial_a, "Shared initial state"),
    (universe_a.state, "Universe A — final"),
    (universe_b.state, "Universe B — final"),
    (universe_a.state - initial_a, "A — change from initial"),
    (universe_b.state - initial_b, "B — change from initial"),
    (universe_b.state - universe_a.state, "B minus A")
]

for ax, (data, title) in zip(axes.flat, images):
    im = ax.imshow(data, origin="lower", cmap="viridis")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046)

fig.suptitle("GENESIS ZERO — DUAL UNIVERSE GZ-DUAL-001")
fig.tight_layout()

image_path = OUT / "dual_universe_comparison.png"
fig.savefig(image_path, dpi=160)
plt.close(fig)

summary = {
    "experiment": "GZ-DUAL-001",
    "completed_utc": datetime.now(timezone.utc).isoformat(),
    "platform": platform.platform(),
    "python": platform.python_version(),
    "numpy": np.__version__,
    "grid": [128, 128],
    "cycles": STEPS,
    "initial_states_identical": bool(
        np.array_equal(initial_a, initial_b)
    ),
    "independent_random_seeds": [SEED_A, SEED_B],
    "introduction": {
        "universe": "B",
        "after_cycle": INTRODUCTION_STEP,
        "amplitude": INTRODUCTION_AMPLITUDE,
        "gaussian_sigma": INTRODUCTION_SIGMA,
        "total_increment": introduced_amount
    },
    "universe_a_final": universe_a.observe(),
    "universe_b_final": universe_b.observe(),
    "difference_final_mean": float(
        np.mean(universe_b.state - universe_a.state)
    ),
    "difference_final_std": float(
        np.std(universe_b.state - universe_a.state)
    ),
    "interpretation": (
        "Exploratory computational pilot. "
        "Different random streams mean that the final "
        "difference cannot be attributed solely to the "
        "external introduction. No physical energy or "
        "intelligence emergence is demonstrated."
    )
}

summary_path = OUT / "summary.json"
summary_path.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

manifest = OUT / "sha256_manifest.txt"

files = [
    Path(__file__),
    ENGINE_DIR / "genesis_engine.py",
    csv_path,
    image_path,
    summary_path,
    OUT / "universe_a_initial.npy",
    OUT / "universe_b_initial.npy",
    OUT / "universe_a_final.npy",
    OUT / "universe_b_final.npy"
]

with manifest.open("w", encoding="utf-8") as f:
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        f.write(f"{digest}  {path.name}\n")

print()
print("=== FINAL RESULTS ===")
print("A:", universe_a.observe())
print("B:", universe_b.observe())
print("B-A mean difference:", summary["difference_final_mean"])
print("B-A standard deviation:", summary["difference_final_std"])
print()
print("Results:", OUT)
print("Statistics:", csv_path)
print("Comparison image:", image_path)
print("Summary:", summary_path)
print("SHA-256 manifest:", manifest)
print()
print("GZ-DUAL-001 PILOT COMPLETED")
