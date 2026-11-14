# records/

The evidence layer: what was preregistered, what was run, what was decided, and what went
wrong. Everything in `experiments/` is setup; everything here is what actually happened.

Nothing in this directory is edited after the fact. A corrected reading is a new file that
cites the old one.

## Layout

| Directory | Holds | Naming |
| --- | --- | --- |
| `manifests/` | One manifest per run: configuration, seed set, code version, weight fingerprints, environment, where the raw output lives | `YYYY-MM-DD_<round>_<slug>.yaml` |
| `decisions/` | The decision records, per `protocols/four_state_decision.md` | `YYYY-MM-DD_<round>_decision.md` |
| `diagnostics/` | Why a measurement was wrong: the defect, how it was found, what it invalidated | `YYYY-MM-DD_<round>_<defect>.md` |
| `changelog/` | Dated entries for any change to code that could move a number | `YYYY-MM.md` |

## Manifests, and why raw data is not necessarily here

Large runs produce large outputs. Git is the wrong place for them, and a repository that
tries to hold them stops being readable. What must be in Git is the ability to **trace**
the data, not the data:

```yaml
round: r42
code_commit: <sha>
config: experiments/gate0/configs/r42.yaml
seeds: [411, 421, 431]
weight_fingerprints:
  411: <hash>
  421: <hash>
environment: {python: "3.13", numpy: "1.26.4", os: "win32"}
raw_output:
  location: <path or storage id outside this repository>
  size: <bytes>
  sha256: <hash of the archive>
decision: records/decisions/2026-11-14_r42_decision.md
```

With that, a reader can tell whether a number came from a run, and can ask for the archive
by hash. Without it, the number is a rumour.

## What is forbidden here

- Editing a decision after it was recorded.
- Deleting a diagnostic because the defect was fixed.
- Replacing a record with a summary of it.

A fixed defect is still part of the history: the old decision was made with the broken
instrument, and that fact has to remain visible.
