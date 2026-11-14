# results/

Curated result summaries — the small number of numbers that are safe to quote, with the
conditions they were obtained under.

This directory is deliberately thin. It is **not** where experiments write their output,
and it is **not** a substitute for the decision records.

## What belongs here

- A summary of a decided round, in one page, citing `records/decisions/…`
- A figure whose source script is in `experiments/gate<N>/analysis/`
- A table that a reader could check against a decision record

## What does not belong here

- Raw logs, per-round dumps, weight archives — those go outside Git, referenced by a
  manifest in `records/manifests/`
- Numbers without a decision record behind them
- Numbers without their conditions (venue, arm, frozen pathways, readout mode, `n`, MDES)
- Anything from a round whose state is `void`

## Naming

`summaries/YYYY-MM-DD_<round>_<slug>.md`, with a header block:

```
Round:     |  State: difference / equivalence / not reached / void
Decision:  records/decisions/…
Conditions: task, network size, frozen pathways, readout mode, n, MDES
```

## Rule

A summary may be shorter than the decision, never stronger. If a summary contains a claim
the decision does not license, the summary is wrong — the decision is the record.
