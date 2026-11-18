import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

SOURCE = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")
OUTPUT = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001/space_time")

PERIOD_FILE = Path("03_SIMULATION/genesis_zero/GZ_LIFE_EMERGENCE/analysis/GZ_LIFE_001/GZ_LIFE_001_PERIOD_ANALYSIS.csv")

OUTPUT.mkdir(parents=True, exist_ok=True)

with PERIOD_FILE.open(encoding="utf-8-sig", newline="") as f:
    period_data = {
        int(row["rule"]): row
        for row in csv.DictReader(f)
    }

rules = [109, 137, 67]

print("=== GZ-LIFE-001 | SPACE-TIME OBSERVATION ===")
print("Original trajectories: READ ONLY\n")

for rule in rules:
    path = SOURCE / f"rule_{rule:03d}.npz"

    with np.load(path) as data:
        trajectory = np.unpackbits(
            data["trajectory"],
            axis=1,
            count=256,
            bitorder="big"
        )

    info = period_data[rule]
    transient = info["transient_length"]
    period = info["period"]

    fig, ax = plt.subplots(figsize=(16, 8))

    ax.imshow(
        trajectory,
        aspect="auto",
        interpolation="nearest",
        origin="lower",
        extent=[0, 256, 0, len(trajectory) - 1]
    )

    if transient != "":
        transient = int(transient)
        ax.axhline(
            transient,
            linestyle="--",
            linewidth=1.2,
            label=f"Cycle begins: {transient}"
        )
        ax.legend(loc="upper right")

    ax.set_title(
        f"GZ-LIFE-001 | Rule {rule} | "
        f"Transient: {transient} | Period: {period}"
    )
    ax.set_xlabel("Spatial position (256 cells)")
    ax.set_ylabel("Cycle")
    ax.set_xlim(0, 256)
    ax.set_ylim(0, len(trajectory) - 1)

    fig.tight_layout()

    output_file = OUTPUT / f"GZ_LIFE_001_RULE_{rule:03d}_SPACETIME.png"
    fig.savefig(output_file, dpi=160)
    plt.close(fig)

    print(f"Rule {rule}:")
    print("  Trajectory:", trajectory.shape)
    print("  Transient:", transient)
    print("  Period:", period)
    print("  Image:", output_file)

print("\nSPACE-TIME VISUALIZATION COMPLETED")
print("Original experimental data unchanged.")
