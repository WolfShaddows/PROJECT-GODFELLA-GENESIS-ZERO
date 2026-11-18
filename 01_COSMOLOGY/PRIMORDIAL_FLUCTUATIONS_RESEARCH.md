# PRIMORDIAL FLUCTUATIONS — RESEARCH RECORD

Project: PROJECT GODFELLA
Status: RESEARCH — NOT FROZEN
Purpose: Establish the observational and theoretical basis
for a future primordial perturbation model.

---

## 1. Research objective

Investigate how primordial cosmological perturbations
can be represented without selecting initial conditions
according to a desired simulation outcome.

No perturbation distribution, random seed, spatial
realization, or numerical resolution is approved by
this document.

## 2. Observational reference

Primary reference:

Planck 2018 Results. X. Constraints on inflation.
Astronomy & Astrophysics, 641, A10.
DOI: 10.1051/0004-6361/201833887

Planck 2018 Results. VI. Cosmological parameters.
Astronomy & Astrophysics, 641, A6.
DOI: 10.1051/0004-6361/201833910

For the Planck TT,TE,EE+lowE+lensing base-Lambda-CDM
analysis, the scalar spectral index is:

ns = 0.9649 ± 0.0042
Confidence level: 68%

The primordial scalar spectrum is compatible with
a power-law parameterization in the analyzed model.

These are observationally constrained model parameters,
not a complete specification of a spatial realization.

## 3. Quantities requiring investigation

### 3.1 Primordial amplitude

Investigate the scalar amplitude As and its convention.

Record:
- numerical value
- pivot scale
- dataset combination
- confidence interval
- model assumptions

Do not substitute a guessed value.

### 3.2 Scalar spectral index

Investigate ns and its role in describing scale dependence.

The Planck reference above reports:

ns = 0.9649 ± 0.0042

This value is conditional on the stated cosmological model
and dataset combination.

### 3.3 Primordial power spectrum

Investigate the curvature perturbation spectrum:

P_R(k)

Determine:
- mathematical convention
- dimensional or dimensionless definition
- pivot scale
- spectral tilt
- possible running
- valid range of scales

Do not confuse primordial curvature power with
the late-time matter power spectrum.

### 3.4 Statistical realization

Investigate how a statistically specified spectrum
can produce spatial realizations.

Questions:
- What statistical assumptions are justified?
- Are perturbations treated as Gaussian?
- What observational constraints exist on non-Gaussianity?
- How are Fourier phases sampled?
- How is reproducibility recorded?
- What volume and boundary conditions are required?

No random generator or seed is selected.

### 3.5 Transfer to matter perturbations

Investigate the transfer from primordial curvature
perturbations to matter density perturbations.

Required physical components:
- radiation
- baryons
- cold dark matter
- neutrinos
- expansion history
- transfer functions

The transfer function must not be replaced by an
arbitrary visual or numerical pattern.

## 4. Neutrality requirements

The future implementation must not:

- insert galaxies or stars
- insert planets or biological systems
- impose preferred density peaks
- select random seeds because they produce interesting results
- alter initial conditions after inspecting outcomes
- introduce artificial evolutionary destinations

All assumptions, parameters, algorithms, and seeds
must be recorded before an experiment is launched.

## 5. Open questions

1. Which primordial spectrum convention will be used?
2. Which observational dataset combination will define
   the reference parameters?
3. What statistical assumptions are supported?
4. What spatial volume and resolution are defensible?
5. Which transfer-function implementation is appropriate?
6. How will numerical convergence be tested?
7. How will initial-condition provenance be preserved?

## 6. Current decision

NO INITIAL PERTURBATION MODEL APPROVED.

NO RANDOM SEED GENERATED.

NO STRUCTURE-FORMATION SIMULATION AUTHORIZED.

Research must precede implementation.

## 7. Scientific limitations

Planck constraints do not uniquely determine every
possible primordial realization.

A statistically compatible realization is not
a reconstruction of the exact initial state of
our universe.

A computational model is not a complete physical
description of the universe or its absolute origin.

## 8. Research status

Status: OPEN
Parameters frozen: NO
Initial conditions frozen: NO
Simulation launched: NO
Human intervention after launch: PROHIBITED
