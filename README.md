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

## Pre-registered criteria

Before running the development experiment in stage 01, four criteria were fixed, and a
fifth was added as a guard:

1. **Bimodal long-range weight distribution** — peak separation above 0.5 (rescaled to
   the actual weight range, see below).
2. **Mean long-range weight shifts by more than 20%** from its initial value.
3. **Modularity Q above 0.3.**
4. **Mean distance of long-range edges shrinks** — ratio below 0.9.
5. **Guard: near-vs-far firing-rate gap above 0.1.** Criteria 1–4 could in principle be
   satisfied by a network that has stopped doing anything at all. The guard checks that
   near neighbours actually fire more than distant ones, so a silent or homogenized
   network cannot "pass".

Criterion 1 as originally written (absolute separation > 0.5) turned out to be
unsatisfiable: the entire weight range after development is smaller than that. The code
therefore reports both the raw number and a threshold rescaled to the observed range,
and prints both verdicts rather than quietly loosening the criterion.

```bash
python 01_substrate.py --criteria --seed 7
```

The same script provides the controls used against it: `--nodev` (no birth/death) and
`--no-prune` (no synaptic pruning).

## Requirements

- Python 3.9 or newer
- NumPy
- No GPU, no deep-learning framework

## Running

Stages 01–04 run from a fresh clone. Paths are resolved relative to each file, so the
working directory does not matter.

```bash
python 01_substrate.py --criteria --seed 7
python 02_working_memory.py --smoke
python 03_memory_driven_action.py --smoke
python 04_task_environment.py --smoke
```

Every stage has `--help`. Stages 02 and 03 offer `--smoke` for a fast check that the
mechanism is not immediately broken; 01 offers `--nodev` and `--no-prune` as controls;
04 offers `--calib-task`, `--calib-p8` and `--choice-mode`.

Runs write to `slices/` and `report/`; both are git-ignored. The state slices are large
and are not tracked.

## Caveats

- **`05_prototype.py` cannot run here.** It imports `tools/_dms_run.py`, a framework
  module that belongs to the private working tree and is not published. The stage is
  included because it shows the direction the project was heading; it exits with an
  explanation instead of a stack trace. Everything upstream of it is self-contained.
- **Chinese comments and console output are original.** The code was written with
  Chinese inline commentary and Chinese console output, and that has been left intact
  rather than translated. Filenames and interface text are English.
- **Not packaged.** This is a research tree, not a library: no installable module, no
  tests, no stable API.

## Status

Active, slow, and mostly negative so far. Several arms exist specifically to fail —
`task_off`, `reward_zero`, `sham_B`, `no_slot` — because a result is only worth recording
if the control that should not work also does not work.
