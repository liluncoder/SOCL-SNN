# records/

The evidence layer: what was preregistered, what was run, what was decided, and what went
wrong. Everything in `experiments/` is setup; everything here is what actually happened.

This is the audit trail: what was asked, what was run, what was decided. It is written so
that a claim can be checked after the fact, and it is kept small enough to stay readable —
repeated dumps and scratch output belong in a run log, not here.

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
the data, not the data.

## Every manifest links seven things

A manifest that is missing any of these is not a manifest — it is a note:

| # | Link | Why it is required |
| --- | --- | --- |
| 1 | **Git commit** | A conclusion belongs to a code version. Without this, a later change silently re-owns an old result. |
| 2 | **Experiment ID** (`r42`) | Ties the run to its preregistration and its decision. IDs are never reused. |
| 3 | **Random seeds** | The unit of a paired comparison. A run without its seed set cannot be re-run. |
| 4 | **Config file** | The exact parameters, versioned in `experiments/gate<N>/configs/`. |
| 5 | **Raw log hash** | Proves the archive is the archive that was analysed, not a later export. |
| 6 | **Weight fingerprint** | Proves the intervention arrived, at a fixed seed — see `protocols/intervention_verification.md`. |
| 7 | **Decision record** | The outcome, in `records/decisions/`. Left empty until decided; a manifest with no decision is a run, not a result. |

```yaml
experiment_id: r42
git_commit: <sha>
config: experiments/gate0/configs/r42.yaml
seeds: [411, 421, 431]
weight_fingerprints:            # 6 — one per seed, per arm
  411: {arm_a: <hash>, arm_b: <hash>}
  421: {arm_a: <hash>, arm_b: <hash>}
environment: {python: "3.13", numpy: "1.26.4", os: "win32"}
raw_output:                     # 5 — the archive, not its contents
  location: <path or storage id outside this repository>
  size: <bytes>
  sha256: <hash of the archive>
logs:
  location: <path>
  sha256: <hash>
decision: records/decisions/2026-11-14_r42_decision.md   # 7
```

With that, a reader can tell whether a number came from a run, reproduce it at the same
commit, and ask for the archive by hash. Without it, the number is a rumour.

A blank copy is at `records/manifests/_template.yaml`.

## Failure leaves a trace

A round that did not pass is not omitted, and it is not dressed as a lesson. Its diagnostic
(`records/diagnostics/`) answers five questions: what was tested, what was observed, why it
did not pass, what it rules out, and what changed afterwards.

The raw output of a failed round may be summarised. The **reasoning behind the failure may
not** — that is the part a later reader can reuse. Template:
`records/diagnostics/_template.md`.

★ Two things this forbids:

- publishing only the rounds that worked;
- rewriting "criterion not reached" as something better.

## What is forbidden here

- Editing a decision after it was recorded.
- Deleting a diagnostic because the defect was fixed.
- Replacing a record with a summary of it.
- Filling in a manifest from memory after the run. If the value was not recorded, it is
  unknown, and unknown has to be written as unknown.

A fixed defect is still part of the history: the old decision was made with the broken
instrument, and that fact has to remain visible.
