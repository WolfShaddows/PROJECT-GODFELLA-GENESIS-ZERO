# DSHADOW-CELLS-002 — THE UNBOUNDED OBSERVATORY

## Start
From this directory:
`python engine\dshadow_engine.py`

Open `http://127.0.0.1:8765`.

The engine restores the most recent checkpoint automatically when one exists. To deliberately start fresh, use:
`python engine\dshadow_engine.py --fresh`

## Controls
- Start / Pause
- Single Generation (only while paused)
- Save Checkpoint
- Restore Latest
- New Universe (asks for confirmation and saves the current state first)
- Evolution speed slider: 1–500 requested generations per worker batch

## Visualization
- Live Universe: current active coordinates projected into the viewport.
- Space-Time Evolution: successive spatial samples from actual states.
- Evolution Trace: active-cell history.
- Research Event Log and checkpoint archive.

## Model and limits
Rule 110, one-dimensional binary elementary cellular automaton, synchronous updates, sparse representation of an unbounded integer lattice. The zero neighborhood remains zero, so finite-support states can be stored sparsely.

The lattice has no predefined spatial boundary and the run has no target generation count. Hardware memory, CPU time and storage remain finite. The speed control sets a requested batch size; it does not promise a fixed generations-per-second rate.

This is a computational experiment, not evidence of biological life. Persistence, recurrence, complexity or pattern resemblance alone do not establish reproduction, heredity or evolution by natural selection.
