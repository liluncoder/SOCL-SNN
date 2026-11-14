# tools/

Supporting utilities for the protocol — not for the model.

The distinction matters: `tools/` holds what the **experimental method** needs to run,
while model code belongs in `legacy/pipeline_v1/` (the current pipeline) or in
`experiments/gate<N>/code/` (gate-specific). Nothing here should know what a neuron is.

| Directory | Purpose |
| --- | --- |
| `logging/` | Run logs written UTF-8 from inside the process; parsing helpers for the summary lines |
| `hashing/` | Weight fingerprints, config hashes, archive checksums — the evidence used by `protocols/intervention_verification.md` |
| `analysis/` | Paired Δ, sign counts, effect size, MDES — the arithmetic of `protocols/paired_analysis.md` |

## Why these three

They correspond to the three things a decision record needs and that are easy to fake by
hand: **what was run**, **whether it arrived**, **how it was compared**.

Writing them once, here, is what makes it possible for a decision to be recomputed by
someone else instead of taken on trust.

## Note on `_dms_run.py`

`tools/_dms_run.py` is not part of this group. It is the loader used by
`05_prototype.py`, and it lives beside the pipeline it serves. See
`legacy/pipeline_v1/README.md`.

## Rule

A utility here must be usable without importing the model. If it needs the network, it
belongs in the experiment, not in `tools/`.
