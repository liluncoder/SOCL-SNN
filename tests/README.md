# tests/

Three kinds of test, because this project has three different things that can be wrong.

| Directory | Question it answers | Runs in |
| --- | --- | --- |
| `unit/` | Does a function do what its signature says? | milliseconds |
| `instrument/` | Can the measurement fail, and does the control arm sit where the null predicts? | seconds to minutes |
| `regression/` | Did this change move a number it was not supposed to move? | seconds to minutes |

`unit/` and `regression/` are ordinary tests. `instrument/` is the unusual one and the more
important one: it encodes the checks in `protocols/instrument_validation.md` as executable
assertions, so that "the measurement can fail" is a test result rather than a memory.

## What belongs where

**`unit/`** — pure functions, shape and dtype contracts, index arithmetic. Cheap, no
simulation.

**`instrument/`** — one test per validation check:

- break the mechanism, assert the reading moves;
- assert the control arm is within the null band;
- assert gate 0 (samples per class) for a fixed seed;
- assert that every registered assertion can be made to fail (meta-test: feed it an illegal
  value and expect the failure).

**`regression/`** — bitwise checks against stored fingerprints:

- same seed + same configuration ⇒ same weight fingerprint as the stored reference;
- a refactor that claims to be inert ⇒ fingerprint unchanged;
- a new switch at its default ⇒ old batch unchanged.

## Running

```bash
python -m pytest tests/ -q                    # if pytest is available
python tests/regression/test_pipeline_loads.py   # stdlib-only fallback, no pytest needed
```

Tests that cost more than a minute belong behind an opt-in flag, not in the default run.
A slow default suite stops being run, and a suite that is not run is not a test.

## Rule

A test that can only pass is not a test. For every new assertion added anywhere in this
repository, there must be a matching case that feeds it a value it must reject.
