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

There is a second loader named `_dms_run.py` at `legacy/pipeline_v1/tools/_dms_run.py`. It is
not part of this directory's group: `05_prototype.py` resolves it as
`dirname(__file__)/tools/_dms_run.py`, so it has to live beside the pipeline it serves. See
`legacy/pipeline_v1/README.md`.

**Planned disambiguation.** Two files with the same name doing different jobs is a trap for
a later reader. When the legacy pipeline is next touched, the protocol utilities here move
to a subpackage with a name that cannot be confused with a loader (for example
`tools/protocol/…`), and the loader keeps its name in `legacy/`. The rename is deliberately
postponed: the pipeline's behaviour has been verified against the current paths, and a
cosmetic rename is not worth re-verifying experiments for. Until then, always read the path,
not the filename.

## Rule

A utility here must be usable without importing the model. If it needs the network, it
belongs in the experiment, not in `tools/`.
