# Architecture

Two things are called "architecture" in a project like this, and they are worth separating:
the **research** architecture (how questions, protocols and records fit together) and the
**code** architecture (what runs). This document covers both, and is explicit about what
does not exist yet.

## Research architecture

```
docs/                    what the project is asking, and why
  ↓
protocols/               how a run is specified, validated, compared, decided
  ↓
experiments/gateN/       the setup for one research stage
  ↓
records/                 what was preregistered, run, decided, and what went wrong
  ↓
results/summaries/       the small set of numbers that are safe to quote
```

`research/` sits beside this chain rather than in it: theory constrains what an experiment
can show, and manuscripts state what a line of work claims. Neither is produced by a run.

## Code architecture

### The current state: five scripts, chained by filename

The working pipeline is five Python files at the repository root. Each loads the previous
one with `importlib` and a **literal filename**, and subclasses it:

```
01_substrate.py            Network      cells, synapses, energy, development, pruning
  └ 02_working_memory.py   MemNet       + slot pools, injection, hold/decay
      └ 03_memory_driven_action.py  ActNet   + action groups, frozen pathway
          └ 04_task_environment.py  TaskNet  + stimulus rounds, reward write, scoring
              └ 05_prototype.py     ProtoNet + modulation and feedback
```

`tools/_dms_run.py` is the loader stage 05 uses; it hands back the stage-04 module.

Consequences a contributor needs to know:

- **The filename is the interface.** Renaming a stage, moving it into a package, or adding a
  `src/` layout breaks the chain at load time. Grep for the literal string before renaming.
- **Importing a stage executes the chain.** Loading `04` loads `03`, `02` and `01` and
  builds a network. `--help` is therefore a real integration test.
- **No module is installed.** Everything is run as a script from the repository root.

`legacy/pipeline_v1/` holds a snapshot copy of the same five files, preserved as a
historical artifact. See `legacy/pipeline_v1/README.md`.

### Why there is no `src/socl_snn/` yet

The public code is five experiment scripts, not a stable package. Creating
`neurons/`, `synapses/`, `networks/` now would produce either mostly-empty directories, or a
rewrite of working experiment code to fit a layout that the research has not yet justified.

The extraction happens when a mechanism is **reused by more than one experiment** and its
interface has stopped moving. That is code evolution, not repository tidying — and it is not
a prerequisite for anything on the roadmap.

### Where new code goes

| Kind of code | Location |
| --- | --- |
| Gate-specific experiment logic | `experiments/gate<N>/code/` |
| Analysis that turns records into a decision | `experiments/gate<N>/analysis/` |
| Protocol machinery (logging, hashing, paired statistics) | `tools/` |
| Model machinery shared by several gates | `legacy/pipeline_v1/` until it stabilises, then considered for extraction |

`tools/` must not import the model. If a utility needs to know what a neuron is, it belongs
with the experiment.

## Tests

| Directory | What it protects |
| --- | --- |
| `tests/unit/` | Functions do what their signatures say |
| `tests/instrument/` | The measurement can fail; the control arm sits where the null predicts |
| `tests/regression/` | A change that claims to be inert really is inert (weight fingerprints) |

The regression tests are the ones that make a chained codebase usable: every change should
be able to prove that the previous batch is bitwise unchanged.

## Data

Git holds **traceability**, not raw output. Large runs live outside the repository, described
by a manifest in `records/manifests/` that records the configuration, seed set, code commit,
weight fingerprints, environment, size and checksum of the archive. `records/` and
`results/` have separate roles and must not be merged: one is evidence, the other is a
quotable summary.
