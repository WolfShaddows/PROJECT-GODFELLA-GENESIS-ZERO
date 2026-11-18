from pathlib import Path
import hashlib
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 20261101
SHAPE = (128, 128)

rng = np.random.default_rng(SEED)
initial_state = rng.uniform(0.0, 1.0, SHAPE)

target = OUT / "shared_initial_state.npy"
np.save(target, initial_state)

digest = hashlib.sha256(target.read_bytes()).hexdigest()

print("GZ-DUAL-001 INITIAL STATE")
print("Shape:", initial_state.shape)
print("Seed:", SEED)
print("Minimum:", float(initial_state.min()))
print("Maximum:", float(initial_state.max()))
print("Mean:", float(initial_state.mean()))
print("Variance:", float(initial_state.var()))
print("SHA256:", digest)
print("File:", target)
print("INITIAL STATE PREPARED")
