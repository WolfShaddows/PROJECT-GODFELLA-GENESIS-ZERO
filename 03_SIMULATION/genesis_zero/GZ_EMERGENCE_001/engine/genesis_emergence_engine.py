import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

# ============================================================
# GZ-EMERGENCE-001 — ENGINE
# Exhaustive Elementary Cellular Automata
# ============================================================

PROJECT = "PROJECT GODFELLA"
EXPERIMENT = "GZ-EMERGENCE-001"

RULE_COUNT = 256
CELL_COUNT = 256
CYCLES = 10_000
INITIAL_SEED = 20261104

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
RAW = RESULTS / "raw"
METRICS = RESULTS / "metrics"
LOGS = BASE / "logs"

for folder in (RAW, METRICS, LOGS):
    folder.mkdir(parents=True, exist_ok=True)

if any(path.is_file() for path in RESULTS.rglob("*")):
    raise SystemExit(
        "ABORTED: Results directory is not empty. "
        "Refusing to overwrite experimental evidence."
    )

# ------------------------------------------------------------
# Reproducible initial state, shared by all 256 rules
# ------------------------------------------------------------

rng = np.random.default_rng(INITIAL_SEED)
initial_state = rng.integers(
    0, 2, size=CELL_COUNT, dtype=np.uint8
)

np.save(RAW / "shared_initial_state.npy", initial_state)

initial_hash = hashlib.sha256(
    initial_state.tobytes()
).hexdigest()

# ------------------------------------------------------------
# Elementary cellular automaton transition
# ------------------------------------------------------------

def evolve(state, rule):
    left = np.roll(state, 1)
    center = state
    right = np.roll(state, -1)

    neighborhood = (
        (left << 2) |
        (center << 1) |
        right
    )

    return ((rule >> neighborhood) & 1).astype(np.uint8)


# ------------------------------------------------------------
# Observational metrics
# ------------------------------------------------------------

def observe(state, previous):
    active = int(np.sum(state))
    density = active / len(state)

    if density in (0.0, 1.0):
        entropy = 0.0
    else:
        entropy = -(
            density * np.log2(density) +
            (1.0 - density) * np.log2(1.0 - density)
        )

    # Number of active spatial domains on a circular lattice.
    domains = int(np.sum(
        (state == 1) & (np.roll(state, 1) == 0)
    ))

    # Number of distinct 3-cell neighborhoods present.
    left = np.roll(state, 1)
    right = np.roll(state, -1)
    neighborhoods = (
        (left << 2) |
        (state << 1) |
        right
    )
    local_patterns = int(np.unique(neighborhoods).size)

    if previous is None:
        changes = 0
    else:
        changes = int(np.count_nonzero(state != previous))

    return (
        active,
        density,
        entropy,
        domains,
        local_patterns,
        changes
    )


# ------------------------------------------------------------
# Integrity metadata
# ------------------------------------------------------------

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)

    with open(LOGS / "engine_execution.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ------------------------------------------------------------
# Experiment metadata
# ------------------------------------------------------------

metadata = {
    "project": PROJECT,
    "experiment": EXPERIMENT,
    "rules": RULE_COUNT,
    "cells_per_rule": CELL_COUNT,
    "cycles_per_rule": CYCLES,
    "total_rule_cycle_updates": RULE_COUNT * CYCLES,
    "initial_seed": INITIAL_SEED,
    "initial_state_sha256": initial_hash,
    "initial_state_shared_by_all_rules": True,
    "boundary_conditions": "periodic",
    "neighborhood": "left-center-right",
    "update_mode": "synchronous",
    "rule_selection": "all 256 elementary rules",
    "stochastic_noise": False,
    "perturbations_in_primary_runs": False,
    "python": sys.version,
    "platform": platform.platform(),
    "numpy": np.__version__,
    "status": "RUNNING"
}

with open(RESULTS / "experiment_metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

# ------------------------------------------------------------
# Main execution: all 256 rules, 10,000 cycles each
# ------------------------------------------------------------

log("GZ-EMERGENCE-001 START")
log(f"Initial state SHA256: {initial_hash}")
log(f"Rules: {RULE_COUNT} | Cells: {CELL_COUNT} | Cycles: {CYCLES}")

started = time.time()
completed = []
failures = []

for rule in range(RULE_COUNT):
    rule_started = time.time()

    try:
        state = initial_state.copy()
        previous = None

        trajectory = np.empty(
            (CYCLES + 1, CELL_COUNT),
            dtype=np.uint8
        )

        metric_rows = []

        # Cycle zero: initial condition.
        trajectory[0] = state
        metric_rows.append(observe(state, previous))

        for cycle in range(1, CYCLES + 1):
            previous = state.copy()
            state = evolve(state, rule)

            trajectory[cycle] = state
            metric_rows.append(observe(state, previous))

        # Pack each binary state into 32 bytes.
        packed_trajectory = np.packbits(
            trajectory,
            axis=1,
            bitorder="big"
        )

        raw_path = RAW / f"rule_{rule:03d}.npz"
        metrics_path = METRICS / f"rule_{rule:03d}.csv"

        np.savez_compressed(
            raw_path,
            trajectory=packed_trajectory,
            final_state=state,
            rule=np.array(rule, dtype=np.uint16),
            cycles=np.array(CYCLES, dtype=np.uint32),
            cells=np.array(CELL_COUNT, dtype=np.uint16),
            initial_state_sha256=np.array(initial_hash)
        )

        with open(metrics_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "cycle",
                "active_cells",
                "density",
                "binary_entropy_bits",
                "active_domains",
                "distinct_local_patterns",
                "changed_cells"
            ])

            for cycle, row in enumerate(metric_rows):
                writer.writerow([cycle, *row])

        completed.append(rule)

        elapsed = time.time() - rule_started
        log(
            f"RULE {rule:03d} COMPLETE | "
            f"{CYCLES} cycles | {elapsed:.2f}s"
        )

    except Exception as exc:
        failures.append({
            "rule": rule,
            "error": repr(exc)
        })

        log(f"RULE {rule:03d} FAILED: {repr(exc)}")

        # Preserve failure record and continue with remaining rules.
        failure_path = LOGS / f"rule_{rule:03d}_failure.json"
        with open(failure_path, "w", encoding="utf-8") as f:
            json.dump(failures[-1], f, indent=2)

# ------------------------------------------------------------
# Final status and evidence manifest
# ------------------------------------------------------------

elapsed_total = time.time() - started

status = {
    "experiment": EXPERIMENT,
    "rules_expected": RULE_COUNT,
    "rules_completed": len(completed),
    "rules_failed": len(failures),
    "completed_rule_ids": completed,
    "failures": failures,
    "cycles_per_completed_rule": CYCLES,
    "elapsed_seconds": elapsed_total,
    "status": (
        "COMPLETE"
        if len(completed) == RULE_COUNT and not failures
        else "INCOMPLETE"
    )
}

with open(RESULTS / "execution_summary.json", "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)

metadata["status"] = status["status"]
metadata["completed_rules"] = len(completed)
metadata["failed_rules"] = len(failures)
metadata["elapsed_seconds"] = elapsed_total

with open(RESULTS / "experiment_metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

manifest_path = RESULTS / "sha256_manifest.txt"

with open(manifest_path, "w", encoding="utf-8") as manifest:
    for path in sorted(RESULTS.rglob("*")):
        if path.is_file() and path != manifest_path:
            manifest.write(
                f"{sha256_file(path)}  {path.relative_to(BASE)}\n"
            )

log(f"EXECUTION STATUS: {status['status']}")
log(f"COMPLETED RULES: {len(completed)}/{RULE_COUNT}")
log(f"FAILED RULES: {len(failures)}")
log(f"TOTAL ELAPSED: {elapsed_total:.2f}s")
log("SHA256 MANIFEST GENERATED")
log("GZ-EMERGENCE-001 END")

