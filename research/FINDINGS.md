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
| 10 | Accuracy here tracks write on the hand-wired pathway, not credit quality | Established, and it overturns the earlier reading of entry 9 | Same venue, same seeds: old rule 0.535 (carrier write 2.0), old rule ×0.16 0.704 (4.1), pair rule 0.708 (11.2), pair rule with shuffled assignment 0.865 (23.9), old rule ×4 0.826 (49) | Monotone in write, flat against specificity. Random assignment beats correct assignment. A blanket gain increase beats the mechanism |
| 11 | The third factor never reaches the event that earned it | Established | Measured: 42.5% of answer-path spikes precede the reward write and therefore carry the *previous* round's value; the other 57.5% follow the readout that scored them | The rule reads the reward at the event (`_stdp_step`), while the outcome is written at the decision (`_decide`, at `win_t1`). No event is scaled by the outcome of its own trial |
| 12 | Under the default frame the delivered reward is inverted, not noisy | Established | Measured over 23 rounds: the previous winner group has the larger reward in 4/23; mean(winner − loser) = −0.040. Cause: the write sets the winner to `med + s·r*·scale` (reads back +0.500) while the untreated group is clipped at +1.000 | `eng_scale_scope='act'` gives 17/23 and +0.204 — the frame is part of the defect. Saturation, not variance |
| 13 | Moving the third factor to the decision restores delivery without touching the representational results | Established | `credit.at='decision'`: credit lands on the chosen group with \|dw\| outside it exactly 0, probe rounds and the null arm write exactly nothing, off-switch fingerprint unchanged (`830136398b09fbed`) | The update is still `dw_ij = R_j·e_ij` — a per-cell scalar times a per-edge eligibility — so entries 1, 3, 8 and 9 are untouched. What changes is only *when* the scalar is read |

## What is not in this register yet

Three questions, none with a verdict:

- **Does per-branch credit change behaviour?** Previously "undecided — below the minimum
  detectable effect". It is now **void as an instrument**: the paired comparison ran on an arm
  that did not deliver a reward to the trial's own events (entries 11–12), so the comparison
  could not have shown the mechanism working. It has to be asked again on a working delivery,
  not re-read.
- **Does this venue test credit at all?** No. The answer travels along a hand-wired pathway, so
  accuracy is monotone in how much weight that pathway receives — and any change that delivers
  more write looks like a better mechanism. Shuffling the credit across edges *raises* accuracy;
  multiplying the old rule's gain by four raises it further. Until the correct edge depends on
  the trial rather than on the wiring, a gain here cannot be attributed to credit assignment.
- **Does a rule that receives the outcome of its own trial learn anything?** The delivery is now
  in place (entry 13), so this is answerable for the first time. It is not answered yet: the
  venue still supplies the answer, and the comparison that would answer it (exploratory, r81)
  is reported in `results/summaries/` without a gate verdict.

## Reading the register

Entries 1–5 are about limits; they constrain what can be built. Entries 6–7 and 11–12 are about
measurement; they constrain what can be believed. Entry 8 is the first positive mechanism
result, and it is deliberately the weakest claim in the table: *representable*, not *useful*.
Entry 13 is an instrument result dressed as a mechanism result, on purpose: it restores a
signal without changing what the rule can represent.

The order matters. Entry 12 was invisible for several rounds because entries 1–3 were being
measured correctly: a wrong signal and a right signal have the same *shape* of update, so the
structural results could not detect that the third factor was arriving from the wrong trial.
Measurement failures are found by looking at the signal, not at the update.

A limit result is not a failure. It removes an explanation, which is the only thing that stops
the same explanation being tried again.

See `protocols/` for the criteria each entry had to meet, and `records/decisions/` for the
records behind them.
