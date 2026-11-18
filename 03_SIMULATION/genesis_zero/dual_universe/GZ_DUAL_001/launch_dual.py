from pathlib import Path
import subprocess
import sys
import csv
import json
import hashlib
import time
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"

INITIAL = OUT / "shared_initial_state.npy"
WORKER = ROOT / "universe_worker.py"

if not INITIAL.exists() or not WORKER.exists():
    raise FileNotFoundError("Initial state or worker is missing.")

# Preserve the exact initial state before launch.
initial_hash = hashlib.sha256(INITIAL.read_bytes()).hexdigest()

runs = [
    {
        "name": "A",
        "seed": "20261102",
        "log": OUT / "universe_A_stdout.log",
        "error": OUT / "universe_A_stderr.log"
    },
    {
        "name": "B",
        "seed": "20261103",
        "log": OUT / "universe_B_stdout.log",
        "error": OUT / "universe_B_stderr.log"
    }
]

processes = []

print("=" * 60)
print("GENESIS ZERO — GZ-DUAL-001")
print("PARALLEL EXPERIMENT LAUNCH")
print("=" * 60)
print("Initial state SHA-256:", initial_hash)
print("Universe A: no external introduction")
print("Universe B: localized perturbation after cycle 100")
print("Cycles per universe: 1000")
print()

start = time.perf_counter()

# Launch both independent Python processes before waiting for either.
for run in runs:
    command = [
        sys.executable,
        str(WORKER),
        "--universe", run["name"],
        "--initial-state", str(INITIAL),
        "--steps", "1000",
        "--seed", run["seed"]
    ]

    stdout_file = run["log"].open("w", encoding="utf-8")
    stderr_file = run["error"].open("w", encoding="utf-8")

    process = subprocess.Popen(
        command,
        stdout=stdout_file,
        stderr=stderr_file
    )

    processes.append({
        "name": run["name"],
        "process": process,
        "stdout": stdout_file,
        "stderr": stderr_file
    })

    print(f"UNIVERSE {run['name']} PROCESS STARTED — PID {process.pid}")

# Wait only after both processes have started.
failed = []

for item in processes:
    code = item["process"].wait()
    item["stdout"].close()
    item["stderr"].close()

    print(f"UNIVERSE {item['name']} EXIT CODE: {code}")

    if code != 0:
        failed.append(item["name"])

elapsed = time.perf_counter() - start

if failed:
    raise RuntimeError(
        "Universe process failure: " + ", ".join(failed)
    )

# Verify that the original initial condition was not modified.
final_initial_hash = hashlib.sha256(INITIAL.read_bytes()).hexdigest()

if initial_hash != final_initial_hash:
    raise RuntimeError("Initial state file changed during execution.")

A = np.load(OUT / "universe_A" / "final_state.npy")
B = np.load(OUT / "universe_B" / "final_state.npy")
IA = np.load(OUT / "universe_A" / "initial_state.npy")
IB = np.load(OUT / "universe_B" / "initial_state.npy")

if not np.array_equal(IA, IB):
    raise RuntimeError("The two initial states are not identical.")

# Load individual statistics and combine them for comparison.
with (OUT / "universe_A" / "statistics.csv").open(
    encoding="utf-8"
) as f:
    stats_a = list(csv.DictReader(f))

with (OUT / "universe_B" / "statistics.csv").open(
    encoding="utf-8"
) as f:
    stats_b = list(csv.DictReader(f))

if len(stats_a) != 1001 or len(stats_b) != 1001:
    raise RuntimeError("Unexpected observation count.")

comparison_csv = OUT / "dual_universe_comparison.csv"

fields = [
    "step",
    "A_mean", "B_mean",
    "A_variance", "B_variance",
    "A_std", "B_std",
    "mean_difference",
    "variance_difference"
]

with comparison_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for a, b in zip(stats_a, stats_b):
        writer.writerow({
            "step": int(a["step"]),
            "A_mean": float(a["mean"]),
            "B_mean": float(b["mean"]),
            "A_variance": float(a["variance"]),
            "B_variance": float(b["variance"]),
            "A_std": float(a["std"]),
            "B_std": float(b["std"]),
            "mean_difference": float(b["mean"]) - float(a["mean"]),
            "variance_difference": float(b["variance"]) - float(a["variance"])
        })

# Produce visual comparison.
fig, axes = plt.subplots(2, 3, figsize=(16, 10))

images = [
    (IA, "Shared initial state"),
    (A, "Universe A — final"),
    (B, "Universe B — final"),
    (A - IA, "A — change from initial"),
    (B - IB, "B — change from initial"),
    (B - A, "B minus A")
]

for ax, (data, title) in zip(axes.flat, images):
    im = ax.imshow(data, origin="lower", cmap="viridis")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046)

fig.suptitle("GENESIS ZERO — GZ-DUAL-001")
fig.tight_layout()

plot_path = OUT / "dual_universe_comparison.png"
fig.savefig(plot_path, dpi=160)
plt.close(fig)

# Plot statistical evolution.
steps = [int(row["step"]) for row in stats_a]
variance_a = [float(row["variance"]) for row in stats_a]
variance_b = [float(row["variance"]) for row in stats_b]
mean_a = [float(row["mean"]) for row in stats_a]
mean_b = [float(row["mean"]) for row in stats_b]

fig, axes = plt.subplots(2, 1, figsize=(12, 8))

axes[0].plot(steps, variance_a, label="Universe A")
axes[0].plot(steps, variance_b, label="Universe B")
axes[0].axvline(100, linestyle="--", label="B introduction after cycle 100")
axes[0].set_ylabel("Variance")
axes[0].set_title("Variance evolution")
axes[0].legend()
axes[0].grid(True)

axes[1].plot(steps, mean_a, label="Universe A")
axes[1].plot(steps, mean_b, label="Universe B")
axes[1].axvline(100, linestyle="--", label="B introduction after cycle 100")
axes[1].set_xlabel("Cycle")
axes[1].set_ylabel("Mean")
axes[1].set_title("Mean evolution")
axes[1].legend()
axes[1].grid(True)

fig.tight_layout()

stats_plot = OUT / "dual_universe_statistics.png"
fig.savefig(stats_plot, dpi=160)
plt.close(fig)

with (OUT / "universe_A" / "summary.json").open(encoding="utf-8") as f:
    summary_a = json.load(f)

with (OUT / "universe_B" / "summary.json").open(encoding="utf-8") as f:
    summary_b = json.load(f)

summary = {
    "experiment": "GZ-DUAL-001",
    "status": "COMPLETED",
    "parallel_processes": True,
    "process_ids": {
        item["name"]: item["process"].pid for item in processes
    },
    "elapsed_seconds": elapsed,
    "cycles_per_universe": 1000,
    "observations_per_universe": 1001,
    "initial_state_identical": True,
    "initial_state_sha256": initial_hash,
    "initial_state_unchanged_after_run": True,
    "universe_A": summary_a,
    "universe_B": summary_b,
    "final_difference": {
        "mean": float(np.mean(B - A)),
        "standard_deviation": float(np.std(B - A)),
        "maximum_absolute_difference": float(np.max(np.abs(B - A)))
    },
    "scientific_limitations": [
        "This is an abstract computational scalar-field model.",
        "The perturbation is a mathematical field increment, not physical energy.",
        "Independent noise streams mean differences cannot be attributed solely to the introduction.",
        "This experiment does not test or demonstrate intelligence emergence."
    ]
}

summary_path = OUT / "dual_universe_summary.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

# Hash evidence after completion.
evidence = [
    INITIAL,
    WORKER,
    ROOT / "launch_dual.py",
    OUT / "universe_A" / "statistics.csv",
    OUT / "universe_B" / "statistics.csv",
    OUT / "universe_A" / "final_state.npy",
    OUT / "universe_B" / "final_state.npy",
    comparison_csv,
    plot_path,
    stats_plot,
    summary_path
]

manifest = OUT / "sha256_manifest.txt"

with manifest.open("w", encoding="utf-8") as f:
    for path in evidence:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        f.write(f"{digest}  {path.relative_to(ROOT)}\n")

print()
print("=" * 60)
print("GZ-DUAL-001 — BOTH UNIVERSES COMPLETED")
print("=" * 60)
print("Elapsed seconds:", round(elapsed, 3))
print("Observations A:", len(stats_a))
print("Observations B:", len(stats_b))
print("Initial conditions identical:", np.array_equal(IA, IB))
print("Initial state preserved:", initial_hash == final_initial_hash)
print()
print("UNIVERSE A FINAL:")
print(json.dumps(summary_a["final"], indent=2))
print()
print("UNIVERSE B FINAL:")
print(json.dumps(summary_b["final"], indent=2))
print()
print("FINAL B-A MEAN:", summary["final_difference"]["mean"])
print("FINAL B-A STD:", summary["final_difference"]["standard_deviation"])
print()
print("VISUAL COMPARISON:", plot_path)
print("STATISTICAL EVOLUTION:", stats_plot)
print("COMBINED DATA:", comparison_csv)
print("SUMMARY:", summary_path)
print("EVIDENCE HASHES:", manifest)
print()
print("GZ-DUAL-001 PILOT COMPLETED SUCCESSFULLY")
