import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

SOURCE = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
BASE = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001")
OUTPUT = BASE / "transition_analysis"

OUTPUT.mkdir(parents=True, exist_ok=True)

PERIOD_FILE = BASE / "GZ_LIFE_001_PERIOD_ANALYSIS.csv"
WINDOW = 300

with PERIOD_FILE.open(encoding="utf-8-sig", newline="") as f:
    periods = {
        int(row["rule"]): row
        for row in csv.DictReader(f)
    }

print("=== GZ-LIFE-001 | TRANSITION ANALYSIS ===")
print("Window:", WINDOW, "cycles before and after")
print("Original trajectories: READ ONLY\n")

for rule in [109, 137, 67]:

    with np.load(SOURCE / f"rule_{rule:03d}.npz") as data:
        trajectory = np.unpackbits(
            data["trajectory"],
            axis=1,
            count=256,
            bitorder="big"
        )

    start = int(periods[rule]["transient_length"])
    period = int(periods[rule]["period"])

    before_start = max(0, start - WINDOW)
    before_end = start

    after_start = start
    after_end = min(len(trajectory), start + WINDOW)

    before = trajectory[before_start:before_end]
    after = trajectory[after_start:after_end]

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))

    axes[0].imshow(
        before,
        aspect="auto",
        interpolation="nearest",
        origin="lower"
    )
    axes[0].set_title(
        f"Rule {rule} | BEFORE periodic regime "
        f"| Cycles {before_start}-{before_end - 1}"
    )
    axes[0].set_xlabel("Spatial position")
    axes[0].set_ylabel("Relative cycle")

    axes[1].imshow(
        after,
        aspect="auto",
        interpolation="nearest",
        origin="lower"
    )
    axes[1].set_title(
        f"Rule {rule} | AFTER periodic regime begins "
        f"| Cycles {after_start}-{after_end - 1}"
    )
    axes[1].set_xlabel("Spatial position")
    axes[1].set_ylabel("Relative cycle")

    fig.suptitle(
        f"GZ-LIFE-001 | Rule {rule} "
        f"| Transient: {start} | Period: {period}"
    )

    fig.tight_layout()

    output = OUTPUT / f"GZ_LIFE_001_RULE_{rule:03d}_TRANSITION.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)

    print(f"RULE {rule}")
    print("  Before:", before.shape)
    print("  After:", after.shape)
    print("  Period:", period)
    print("  Image:", output)

print("\nTRANSITION ANALYSIS COMPLETED")
print("Original trajectories unchanged.")
