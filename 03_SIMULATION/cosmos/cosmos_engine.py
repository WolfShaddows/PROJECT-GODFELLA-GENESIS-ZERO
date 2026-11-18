"""
PROJECT GODFELLA
COSMOS ENGINE 0.2
Physical Time Calibration

Reference model: Flat Lambda-CDM.
This is a mathematical approximation, not a complete universe.
"""

from dataclasses import dataclass
from pathlib import Path
import csv
import json

import numpy as np
from scipy.integrate import quad


@dataclass(frozen=True)
class Cosmology:
    H0: float = 67.4
    omega_m: float = 0.315
    omega_r: float = 9.0e-5
    omega_lambda: float = 0.68491

    @property
    def omega_k(self):
        return 1.0 - (
            self.omega_m +
            self.omega_r +
            self.omega_lambda
        )


MPC_KM = 3.085677581491367e19
SECONDS_PER_YEAR = 365.25 * 24 * 3600
SECONDS_PER_GYR = SECONDS_PER_YEAR * 1e9


def e_squared(a, model):
    if a <= 0:
        raise ValueError("Scale factor must be positive")

    return (
        model.omega_r / a**4 +
        model.omega_m / a**3 +
        model.omega_k / a**2 +
        model.omega_lambda
    )


def expansion_rate(a, model):
    value = e_squared(a, model)

    if value <= 0:
        raise ValueError("Invalid expansion rate")

    return model.H0 * np.sqrt(value)


def hubble_seconds(model):
    return model.H0 / MPC_KM


def cosmic_age_gyr(a, model):
    """
    Age from the mathematical lower limit a=0
    within the classical Lambda-CDM model.
    """

    if not 0 < a <= 1:
        raise ValueError("Scale factor must be in (0, 1]")

    def integrand(x):
        if x == 0:
            return 0.0

        return 1.0 / (
            x * np.sqrt(e_squared(x, model))
        )

    integral, error = quad(
        integrand,
        0.0,
        a,
        epsabs=1e-11,
        epsrel=1e-11,
        limit=300
    )

    age_seconds = integral / hubble_seconds(model)

    return age_seconds / SECONDS_PER_GYR


def density_fractions(a, model):
    total = e_squared(a, model)

    radiation = model.omega_r / a**4 / total
    matter = model.omega_m / a**3 / total
    curvature = model.omega_k / a**2 / total
    dark_energy = model.omega_lambda / total

    return {
        "radiation": radiation,
        "matter": matter,
        "curvature": curvature,
        "dark_energy": dark_energy
    }


def run_simulation(model, samples=500):

    scale_factors = np.geomspace(
        1e-4,
        1.0,
        samples
    )

    results = []

    for a in scale_factors:

        fractions = density_fractions(a, model)

        results.append({
            "scale_factor": float(a),
            "age_gyr": cosmic_age_gyr(float(a), model),
            "hubble_km_s_mpc": float(
                expansion_rate(float(a), model)
            ),
            **fractions
        })

    return results


def save_results(results, output_dir):

    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "cosmological_history.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )

        writer.writeheader()
        writer.writerows(results)

    return csv_path


def main():

    model = Cosmology()

    output_dir = Path(__file__).resolve().parent / "results"

    print("=" * 48)
    print("PROJECT GODFELLA - COSMOS ENGINE 0.2")
    print("=" * 48)

    results = run_simulation(model)

    present = results[-1]

    summary = {
        "model": "Flat Lambda-CDM",
        "H0_km_s_Mpc": model.H0,
        "omega_m": model.omega_m,
        "omega_r": model.omega_r,
        "omega_lambda": model.omega_lambda,
        "omega_k": model.omega_k,
        "age_gyr": present["age_gyr"],
        "samples": len(results),
        "status": "COMPLETED"
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "summary.json").open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(summary, file, indent=4)

    csv_path = save_results(results, output_dir)

    print("Model:", summary["model"])
    print("Samples:", summary["samples"])
    print("Cosmic age (Gyr):", round(present["age_gyr"], 5))
    print("Present matter fraction:",
          round(present["matter"], 6))
    print("Present radiation fraction:",
          round(present["radiation"], 8))
    print("Present dark energy fraction:",
          round(present["dark_energy"], 6))

    print("\nCSV:", csv_path)
    print("JSON:", output_dir / "summary.json")
    print("\nSIMULATION COMPLETED")


if __name__ == "__main__":
    main()
