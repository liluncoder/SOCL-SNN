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

The gate is open, and its criterion is not yet satisfied: the task's label does not depend
on the input in a way that leaves room for a learned improvement, and the baseline is
already high. Both are properties of the task, not of the learning rule. That is what this
gate exists to fix — see `docs/RESEARCH_ROADMAP.md` §Gate 0.
