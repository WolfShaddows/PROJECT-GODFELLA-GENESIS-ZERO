# PROJECT GODFELLA
# PARAMETER PROVENANCE REGISTER

Version: 1.0

Purpose:
Track the origin and scientific justification
of every parameter used by the simulation.

---

## CURRENT COSMOS ENGINE 0.2 PARAMETERS

| Parameter | Current value | Provenance |
|---|---:|---|
| H0 | 67.4 km/s/Mpc | Planck 2018 base Lambda-CDM |
| Omega_m | 0.315 | Planck 2018 base Lambda-CDM |
| Omega_r | 0.00009 | Existing engine assumption |
| Omega_lambda | 0.68491 | Existing engine assumption |
| Omega_k | 0.0 | Derived from flatness assumption |

IMPORTANT:

The radiation and dark energy values above
must be independently verified before reuse.

Omega_lambda is derived from the other density
parameters and the flatness assumption.

The listed values are not yet frozen for GENESIS ZERO.

---

## REQUIRED METADATA

Every future parameter must include:

- Parameter name.
- Physical definition.
- Numerical value.
- Unit.
- Uncertainty.
- Source.
- Cosmological model.
- Derivation method.
- Applicable scale or epoch.
- Implementation version.

---

## RULE

No parameter may be silently introduced.

No parameter may be adjusted to produce
a preferred experimental outcome.

Unverified parameters remain provisional.

---

CURRENT STATUS:

REFERENCE PARAMETERS: PROVISIONAL
PARAMETER VALIDATION: PENDING
INITIAL CONDITIONS: NOT FROZEN
SIMULATION: NOT STARTED
