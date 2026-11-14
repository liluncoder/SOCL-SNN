# SOCL-SNN

Self-organizing continual learning in spiking neural networks.

> An independent research project investigating self-organizing continual learning in
> spiking neural networks, with a focus on synaptic credit assignment, energy-constrained
> neuronal dynamics, memory, and adaptive network structures. An ongoing experimental
> prototype.

Everything here is exploratory. Nothing in this repository claims that cognition,
general learning, or open-ended capability has been achieved.

## Pipeline

A single line of experiments. Each stage loads the previous one directly through
`importlib`, so a stage always runs on the exact network the stage before it built —
there is no duplicated model definition to drift out of sync.

| Stage | File | What it does |
| --- | --- | --- |
| 01 | `01_substrate.py` | Spiking E/I network with a per-unit energy budget. Conductance synapses, short-term depression, AdEx or LIF cells. Energy is charged per spike, per unit of upkeep, and per synapse. Structural development: unit division, death by energy deficit, pruning of unused synapses. Carries the pre-registered acceptance criteria. |
| 02 | `02_working_memory.py` | Delay-period memory on top of the substrate. Slot pools A and B, injection units, hold/decay dynamics, winner-take-all between slots. Three arms: `two_pool`, `snap_off`, `sham_B`. |
| 03 | `03_memory_driven_action.py` | Readout from memory into an action pool. Three arms: `memory`, `no_slot`, `freeze_off`. |
| 04 | `04_task_environment.py` | Closed-loop task with reward-modulated plasticity — the credit-assignment stage. Five arms — `task_off`, `local`, `global_scalar`, `global_center`, `reward_zero` — to test whether the locality of the modulatory signal matters. |
| 05 | `05_prototype.py` | Prototype: modulatory drive, feedback projection, target sequences. **Archived, not runnable** — see *Caveats*. |

## What `--criteria` reports

Stage 01 can print five structural quantities, each for three arms (everything on;
plasticity off; normalisation off):

1. peak separation of the long-range weight distribution
2. relative change of the mean long-range weight
3. modularity Q
4. ratio of mean long-range edge distance to its initial value
5. near-minus-far firing-rate gap

```bash
python 01_substrate.py --criteria --seed 7
```

The thresholds that appear next to those numbers are constants in the source, and the
tally applies a "≥2 of 4 counts as a pass" convention. Both are conventions of this code,
not statistics — [`operations/02_experiments.md`](operations/02_experiments.md) describes
what to do instead.

★ Two things to check before reading the output. Criterion 1 is printed **twice**, raw
and rescaled by the model's weight ceiling, because the raw threshold is in absolute
weight units. Criterion 3 returns `nan` whenever the binarised correlation graph has too
few edges, which is a sparsity limit of your `--units`, not an absence of structure.

The same script provides the controls used against it: `--nodev` (no birth/death) and
`--no-prune` (no synaptic pruning).

## Requirements

- Python 3.9 or newer
- NumPy
- No GPU, no deep-learning framework

## Running

Stages 01–03 run from a fresh clone. Paths are resolved relative to each file, so the
working directory does not matter.

```bash
python 01_substrate.py --criteria --seed 7
python 02_working_memory.py --smoke
python 03_memory_driven_action.py --smoke
python 04_task_environment.py --smoke
```

Stage 04 runs from the command line only in its interface and calibration modes: the
five experimental arms exist in `build(..., arm=...)` but every CLI call site hard-codes
`arm='task_off'`. How to drive the other arms is in
[`operations/04_extend.md`](operations/04_extend.md) §3.

## Documentation

[`operations/`](operations/) is the manual for using this code: how to run each stage and
what it prints ([`01_usage.md`](operations/01_usage.md)), how to design and register your
own runs ([`02_experiments.md`](operations/02_experiments.md)), the code-level
constraints that will silently ruin a measurement ([`03_traps.md`](operations/03_traps.md)),
and how to add a stage or an arm ([`04_extend.md`](operations/04_extend.md)). A blank
pre-registration form is in
[`operations/templates/`](operations/templates/pre-registration.md).

Every stage has `--help`. Stages 02 and 03 offer `--smoke` for a fast check that the
mechanism is not immediately broken; 01 offers `--nodev` and `--no-prune` as controls;
04 offers `--calib-task`, `--calib-p8` and `--choice-mode`.

Runs write to `slices/` and `report/`; both are git-ignored. The state slices are large
and are not tracked.

## Caveats

- **`05_prototype.py` cannot run here.** It imports `tools/_dms_run.py`, a framework
  module that belongs to the private working tree and is not published. The stage is
  included because it shows the direction the project was heading; it exits with an
  explanation instead of a stack trace. Stages 01–03 are self-contained; stage 04 has
  all five arms in code but exposes only `task_off` on the command line.
- **Chinese comments and console output are original.** The code was written with
  Chinese inline commentary and Chinese console output, and that has been left intact
  rather than translated. Filenames and interface text are English.
- **Not packaged.** This is a research tree, not a library: no installable module, no
  tests, no stable API.

## Status

Work in progress. This repository publishes the code and the method, not the results —
the experiment archive stays private. Several arms (`task_off`, `reward_zero`, `sham_B`,
`no_slot`) are controls rather than conditions of interest: they exist so that a
mechanism can be separated from everything else that is also switched on.
