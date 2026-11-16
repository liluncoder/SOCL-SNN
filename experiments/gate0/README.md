# Gate 0 — a task with sufficient experimental headroom

**Status: Active.**

This is the only gate currently maintained. Its question is whether the research task has
enough headroom for a learning effect to be measurable at all: a baseline that is neither
already solved nor impossible, a readout that is not saturated, and a control condition
that can produce no answer.

## What is here

| Directory | Contents |
| --- | --- |
| `preregistrations/` | One file per round. The criterion, arms, threshold, `n`, MDES and the forbidden-wording list, frozen before the run. |
| `configs/` | One file per run configuration, named by round and purpose. |
| `code/` | Gate-specific code. The legacy pipeline in `legacy/pipeline_v1/` is reused by import, not copied. |
| `analysis/` | The scripts that compute the decision from records. A number that cannot be produced by a script here should not appear in a decision. |

## Naming

Round identifiers are sequential and never reused: `r01`, `r02`, … A round that is re-run
with a fixed bug keeps its number and gains a suffix (`r72b`), because a re-run is not a
new experiment — it is the same question with a corrected instrument, and the original
record stays intact.

A run is identified by `round + config + seed set`. The weight fingerprint and the
environment go in `records/manifests/`.

## Where the results live

Not here. Raw output and per-round records go to `records/`; curated summaries that are
safe to quote go to `results/summaries/`. This directory holds the **setup**, not the
outcome.

## Current state

The gate is open and its criterion is **not** satisfied, for two different reasons that were
previously conflated:

1. **The task does not leave room for a learned improvement.** Its label travels along a
   hand-wired pathway, so the baseline is set by the wiring strength rather than by learning —
   see the recorded dose–response and `research/FINDINGS.md` entry 10.
2. **Until r81 the instrument could not deliver a trial's outcome to that trial's events.**
   The rule reads the reward at each spike; the outcome is written at the decision, after the
   stimulus window. Measured: 42.5% of answer-pathway events carry the previous trial's
   outcome, and under the default energy frame the delivered value is inverted (4 of 23 rounds
   in the intended direction). Every arm comparison in the record that relied on
   `arm='local'` is **void as an instrument** because of this, not undecided.

The second is now repaired and validated (`credit.at='decision'`; see
`code/credit_delivery_check.py`). The first is not: the venue still has to make the correct
edge depend on the trial.

`GATE0_CANDIDATE_DECISION.md` records the audit, the new candidate venue (D: target is the
conjunction of a cue and an instruction, with the conjunction provided as infrastructure and
only eight outgoing edges plastic, starting in exact ties), and what is still undecided.
