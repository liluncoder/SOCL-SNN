# operations/

How to use this code, and how to run an experiment with it.

This folder documents the interface, not the results. If you want to know what the code
models, read the stage files themselves — they are self-contained and the comments in
the source are the primary documentation. This folder covers the parts that are not
obvious from reading a 2000-line file: what each stage expects, which flags actually
reach the mechanism, which constraints are silent, and how to set up a run whose result
you can defend.

## Read in this order

| File | Read it when |
| --- | --- |
| [`01_usage.md`](01_usage.md) | You want to run something. Per stage: what it computes, the entry point, the flags, the Python API, the shape of the output, and the runtime. |
| [`02_experiments.md`](02_experiments.md) | You want to design your own run. The pre-registration pattern this code was built around, control arms, seed pairing, sample-size gates, and what makes a reading valid. |
| [`03_traps.md`](03_traps.md) | Before you trust a number. Code-level constraints that will silently ruin a run — recording buffers, sampling windows, flags that never reach the mechanism. |
| [`04_extend.md`](04_extend.md) | You want to add a stage, an arm, or a knob without breaking the pipeline. |

Also here: [`templates/pre-registration.md`](templates/pre-registration.md) — a blank
form to copy before each run.

## The shape of the project

Five stages, each one a single file, each one adding one mechanism on top of the last:

```
01_substrate.py            cells, synapses, energy, birth/death, pruning
  └ 02_working_memory.py   + slot pools, injection, hold/decay, winner-take-all
      └ 03_memory_driven_action.py   + action groups, frozen readout pathway
          └ 04_task_environment.py   + stimulus rounds, reward write, probe scoring
              └ 05_prototype.py      + modulatory drive, feedback (via tools/_dms_run.py)
```

Stages are chained by **filename**, not by an installed package: each file loads its
predecessor with `importlib` and uses the literal name. That means a stage always runs on
the exact network the previous stage built, and it means renaming a file breaks the chain.

Requirements: Python 3.9+, NumPy, no GPU. Everything is CPU, single process, and the
cost is roughly 3–4× real time per simulated second at the default sizes — budget
minutes, not seconds.

## Conventions

- **`--help` on every stage.** It is accurate and it lists the override knobs.
- **Smoke modes** (`--smoke` on stages 02–04) check that fields exist and the mechanism
  does not immediately collapse. They print their own disclaimer: no scientific claim.
- **`--log FILE`** (stages 02–04) writes a UTF-8 log directly from inside the process.
  Prefer it over shell redirection: on Windows PowerShell 5.1, `>` re-encodes UTF-8 as
  gb2312 and then stores it as UTF-16, and the log comes out garbled.
- **`--seed`** controls everything. Same seed and same flags give the same trajectory,
  including the weight digest.
- Runs write to `slices/` and `report/`; both are git-ignored.
