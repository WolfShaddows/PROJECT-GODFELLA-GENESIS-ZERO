import json
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cosmos_engine import (
    Cosmology,
    e_squared,
    expansion_rate,
    cosmic_age_gyr,
    density_fractions,
    hubble_seconds,
    SECONDS_PER_GYR,
)

model = Cosmology()
results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append({
        "check": name,
        "status": status,
        "detail": detail
    })
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")

print("=" * 60)
print("PROJECT GODFELLA - COSMOS ENGINE 0.2")
print("INDEPENDENT NUMERICAL AUDIT")
print("=" * 60)

# 1. Density normalization
check(
    "Present density normalization",
    abs(
        model.omega_m +
        model.omega_r +
        model.omega_lambda +
        model.omega_k - 1.0
    ) < 1e-12,
    f"Sum = {model.omega_m + model.omega_r + model.omega_lambda + model.omega_k:.15f}"
)

# 2. Hubble normalization
h_today = expansion_rate(1.0, model)
check(
    "Hubble normalization at a=1",
    abs(h_today - model.H0) < 1e-10,
    f"H(1) = {h_today:.12f}; H0 = {model.H0:.12f}"
)

# 3. Positive expansion history
scale_factors = np.geomspace(1e-4, 1.0, 500)
e_values = np.array([e_squared(float(a), model) for a in scale_factors])
h_values = np.array([expansion_rate(float(a), model) for a in scale_factors])

check(
    "Positive E(a)^2 over sampled interval",
    bool(np.all(np.isfinite(e_values)) and np.all(e_values > 0)),
    f"Minimum E² = {np.min(e_values):.8e}"
)

# 4. Density fractions sum to unity
fraction_errors = []
for a in scale_factors:
    fractions = density_fractions(float(a), model)
    fraction_errors.append(abs(sum(fractions.values()) - 1.0))

max_fraction_error = max(fraction_errors)

check(
    "Density fractions sum to unity",
    max_fraction_error < 1e-10,
    f"Maximum absolute error = {max_fraction_error:.3e}"
)

# 5. Expansion rate behavior
check(
    "Expansion rate decreases toward present",
    bool(np.all(np.diff(h_values) < 0)),
    f"H(1e-4) = {h_values[0]:.6e}; H(1) = {h_values[-1]:.6f}"
)

# 6. Cosmic age monotonicity
ages = np.array([
    cosmic_age_gyr(float(a), model)
    for a in scale_factors
])

check(
    "Cosmic age increases with scale factor",
    bool(np.all(np.diff(ages) > 0)),
    f"Age at a=1e-4 = {ages[0]:.8e} Gyr; age at a=1 = {ages[-1]:.12f} Gyr"
)

# 7. Independent integration tolerance comparison
def independent_age(eps):
    def integrand(x):
        if x == 0:
            return 0.0
        return 1.0 / (x * np.sqrt(e_squared(x, model)))

    integral, error = quad(
        integrand,
        0.0,
        1.0,
        epsabs=eps,
        epsrel=eps,
        limit=500
    )

    return (
        integral /
        hubble_seconds(model) /
        SECONDS_PER_GYR
    )

age_loose = independent_age(1e-8)
age_tight = independent_age(1e-12)
age_engine = cosmic_age_gyr(1.0, model)

age_difference = abs(age_loose - age_tight)

check(
    "Integration tolerance stability",
    age_difference < 1e-7,
    f"1e-8 = {age_loose:.12f} Gyr; 1e-12 = {age_tight:.12f} Gyr; difference = {age_difference:.3e}"
)

check(
    "Engine age agrees with independent integration",
    abs(age_engine - age_tight) < 1e-7,
    f"Engine = {age_engine:.12f} Gyr; independent = {age_tight:.12f} Gyr"
)

# 8. Present-day fractions
present = density_fractions(1.0, model)

check(
    "Present-day fractions match model parameters",
    abs(present["matter"] - model.omega_m) < 1e-12
    and abs(present["radiation"] - model.omega_r) < 1e-12
    and abs(present["dark_energy"] - model.omega_lambda) < 1e-12,
    json.dumps(present, indent=2)
)

# Report
passed = sum(item["status"] == "PASS" for item in results)
failed = sum(item["status"] == "FAIL" for item in results)

report = {
    "audit": "COSMOS ENGINE 0.2",
    "audit_type": "numerical_consistency",
    "checks_passed": passed,
    "checks_failed": failed,
    "age_gyr": float(age_engine),
    "maximum_fraction_error": float(max_fraction_error),
    "integration_difference_gyr": float(age_difference),
    "results": results,
    "scientific_scope": [
        "Homogeneous flat Lambda-CDM background",
        "No primordial perturbations",
        "No structure formation",
        "No baryonic gas dynamics",
        "No chemistry",
        "No simulation of the absolute origin of the universe"
    ]
}

output = Path(__file__).resolve().parent / "audit_results"
output.mkdir(parents=True, exist_ok=True)

report_path = output / "cosmos_audit.json"
report_path.write_text(
    json.dumps(report, indent=4),
    encoding="utf-8"
)

print("=" * 60)
print(f"CHECKS PASSED: {passed}")
print(f"CHECKS FAILED: {failed}")
print(f"REPORT: {report_path}")
print("=" * 60)

if failed:
    raise SystemExit(1)
