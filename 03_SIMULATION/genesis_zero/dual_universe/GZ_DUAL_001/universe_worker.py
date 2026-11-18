from pathlib import Path
import argparse
import csv
import json
import time
import hashlib

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--universe", choices=["A", "B"], required=True)
parser.add_argument("--initial-state", required=True)
parser.add_argument("--steps", type=int, default=1000)
parser.add_argument("--seed", type=int, required=True)
args = parser.parse_args()

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / f"universe_{args.universe}"
OUT.mkdir(parents=True, exist_ok=True)

state = np.load(args.initial_state, allow_pickle=False).copy()
initial = state.copy()

rng = np.random.default_rng(args.seed)

DIFFUSION = 0.15
NOISE = 0.01
INTRODUCTION_STEP = 100
AMPLITUDE = 0.25
SIGMA = 5.0

def observe(step):
    return {
        "step": step,
        "minimum": float(np.min(state)),
        "maximum": float(np.max(state)),
        "mean": float(np.mean(state)),
        "std": float(np.std(state)),
        "variance": float(np.var(state)),
        "total": float(np.sum(state))
    }

def introduce():
    height, width = state.shape
    y, x = np.mgrid[0:height, 0:width]
    cy = (height - 1) / 2
    cx = (width - 1) / 2

    gaussian = np.exp(
        -((x - cx)**2 + (y - cy)**2) / (2 * SIGMA**2)
    )

    increment = AMPLITUDE * gaussian
    state[:] += increment

    return float(np.sum(increment))

print(f"UNIVERSE {args.universe} STARTED", flush=True)
print(f"Initial state shape: {state.shape}", flush=True)

records = [observe(0)]
introduced_amount = None

start = time.perf_counter()

for step in range(1, args.steps + 1):

    if args.universe == "B" and step == INTRODUCTION_STEP + 1:
        introduced_amount = introduce()
        print(
            f"External perturbation applied after cycle "
            f"{INTRODUCTION_STEP}; increment={introduced_amount:.8f}",
            flush=True
        )

    neighbors = (
        np.roll(state, 1, axis=0)
        + np.roll(state, -1, axis=0)
        + np.roll(state, 1, axis=1)
        + np.roll(state, -1, axis=1)
    ) / 4.0

    noise = rng.normal(0.0, NOISE, state.shape)

    state = state + DIFFUSION * (neighbors - state) + noise

    records.append(observe(step))

    if step % 100 == 0:
        print(
            f"Universe {args.universe}: "
            f"{step}/{args.steps} "
            f"variance={np.var(state):.8f}",
            flush=True
        )

elapsed = time.perf_counter() - start

with (OUT / "statistics.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)

np.save(OUT / "initial_state.npy", initial)
np.save(OUT / "final_state.npy", state)

summary = {
    "universe": args.universe,
    "seed": args.seed,
    "steps": args.steps,
    "initial_state_sha256": hashlib.sha256(
        initial.tobytes()
    ).hexdigest(),
    "final_state_sha256": hashlib.sha256(
        state.tobytes()
    ).hexdigest(),
    "introduction": {
        "applied": args.universe == "B",
        "after_cycle": INTRODUCTION_STEP if args.universe == "B" else None,
        "total_increment": introduced_amount
    },
    "initial": observe(0),
    "final": observe(args.steps),
    "elapsed_seconds": elapsed
}

(OUT / "summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print(f"UNIVERSE {args.universe} COMPLETED", flush=True)
print(json.dumps(summary, indent=2), flush=True)
