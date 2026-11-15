# Findings register

What this project has established, and how firmly. One line per claim, with the kind of
evidence behind it.

A claim enters this register only when it has three things: a criterion written before it was
checked, a check that could have failed, and a record that survives re-reading. Anything less
belongs in a log.

| # | Claim | Status | Evidence type | Notes |
| --- | --- | --- | --- | --- |
| 1 | A scalar modulator cannot address synapses: with one reward value per postsynaptic cell, `dw(+1) = −dw(−1)` holds bitwise at every event | Established | Bit-level identity over all update events | The relative pattern over a cell's in-edges is unchanged, so the write has no direction among them |
| 2 | Plasticity is distributed by edge count rather than by relevance | Established | Measured: a pathway holding 0.42% of synapses received 0.39% of the total weight change | The share tracks the edge count; no preference for the answer pathway |
| 3 | Opposite rewards produce nearly parallel writes | Established | Measured: cosine similarity ≈ +0.42 between the updates for +1 and −1 | This is what "large but direction-blind" looks like numerically |
| 4 | A simplex weight budget forbids growth (`Σdw ≡ 0`) | Established | Algebraic consequence of the normalisation step | Explains why structure cannot pay for itself in this substrate |
| 5 | Structure does not bootstrap under a fixed topology | Established as a limit, open as a problem | Analysis: gradient flow converges inside the representable class | Recorded as an open item, not a capability; see gate 5 |
| 6 | The task saturates before a learning effect has room | Established for the venue used | Measured dose–response: ≈0.94 at a 2× imbalance | Motivates gate 0 rather than any mechanism |
| 7 | A readout window can invert a result | Established | Two windows on one configuration: 0.03 vs 1.00 | The reason instrument validation is a separate protocol step, not a subsection of preregistration |
| 8 | Per-branch credit is representable | Established at the mechanism level | Two synapses on one cell, identical presynaptic trace, different branches: updates differ by exactly the branch-activity ratio | Representable is not the same as effective — whether it changes behaviour is still undecided |
| 9 | The update rule has no timing window | Established | Swapping the order of the two events leaves the edge update unchanged: difference exactly 0 | Per-edge credit reduces to `R·(A₊·x_pre − A₋·y_post)`, a rate comparison; no pair interaction, so causality has no sign |
| 10 | Order-dependent credit changes behaviour | Established for one venue | Paired, 10 seeds: accuracy 0.535 → 0.708, Δ = +0.173, t = 4.55, 8/10 seeds positive, against an MDES of 0.107 | Not a window artefact (τ 20 ms vs 1 ms: identical means) and not a step-size artefact (write matched to the old rule: Δ = +0.167). Cause is the remaining structural difference, not the window |

## What is not in this register yet

Two questions are under test and do not have a verdict:

- **Does per-branch credit change behaviour?** The mechanism is in place and the effect is
  measurable, but the paired design so far is undecided: the effect sits below the minimum
  detectable effect at the sample size used.
- **Why does it work?** Entry 10 shows the gain is real, and two controls exclude the obvious
  explanations: it survives a twentyfold shorter eligibility window and a sixfold smaller step.
  What is left is a structural difference — the two rules depress different edge sets (the old
  one acts on the spiking cell's outgoing edges, weighted by the target's trace) and only the
  new one spends its eligibility. Separating those two changes is the next experiment.

## Reading the register

Entries 1–5 are about limits; they constrain what can be built. Entries 6–7 are about
measurement; they constrain what can be believed. Entry 8 is the first positive mechanism
result, and it is deliberately the weakest claim in the table: *representable*, not *useful*.

A limit result is not a failure. It removes an explanation, which is the only thing that stops
the same explanation being tried again.

See `protocols/` for the criteria each entry had to meet, and `records/decisions/` for the
records behind them.
