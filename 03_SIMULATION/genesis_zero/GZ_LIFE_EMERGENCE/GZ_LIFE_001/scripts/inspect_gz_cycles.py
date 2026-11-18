from pathlib import Path
import numpy as np

root = Path("03_SIMULATION/genesis_zero/GZ_EMERGENCE_001/results/raw")

for rule in (67, 109, 137):
    path = root / f"rule_{rule:03d}.npz"
    print(f"\nREGLA {rule}: {path}")

    if not path.exists():
        print("ARCHIVO NO ENCONTRADO")
        continue

    with np.load(path, allow_pickle=False) as data:
        for key in data.files:
            arr = data[key]
            print(f"  {key}: shape={arr.shape}, dtype={arr.dtype}")
