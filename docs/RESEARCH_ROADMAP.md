# Research roadmap

The research is staged. A gate is a question that has to be decided before the next
question is worth asking — not a milestone, not a deliverable, and not a code module.

| Gate | Research focus | Status |
| --- | --- | --- |
| 0 | Establish a task with sufficient experimental headroom | Active |
| 1 | Temporal and spatial integration | Planned |
| 2 | Longitudinal measurement of learning improvement | Not started |
| 3 | Cross-task integration and consolidation | Not started |
| 4 | Synaptic and connection-level plasticity | Frozen |
| 5 | Structural self-organization | Frozen |
| 6 | Self-modeling and higher-level integration | Conceptual |

This table is a pointer. The authoritative status of a gate is its latest decision record in
`records/decisions/`; the authoritative pass conditions are the gate's own preregistration,
not a sentence in this file.

## What each status means

**Active** — the gate is open, a criterion exists, and rounds are being run against it.

**Planned** — the question is accepted but its launching conditions are not yet written. No
runs, and no criterion that could be met or missed.

**Not started** — the question is named; nothing else exists. It becomes Planned when its
launching conditions are written and accepted.

**Frozen** — the line was stopped deliberately, and the reason is recorded. Frozen is not
"paused" and not "waiting for resources": no new runs, no new criteria, and nothing already
recorded may be re-read as evidence that the line works. A gate is unfrozen only by a
decision record that cites the freeze it lifts.

**Conceptual** — there is no measurable definition yet, so there is nothing to run and
nothing to claim.

## The ordering rule

1. **A gate opens when the previous gate has a decision**, not when it has enough runs.
   A pile of undecided rounds is not a prerequisite.
2. **A gate's criterion is written before its first run**, in
   `experiments/gate<N>/preregistrations/`, following `protocols/preregistration.md`.
3. **A gate that is Frozen or Conceptual does not open because a directory exists.** The
   roadmap status changes by decision record only.
4. **A roadmap revision does not overwrite a past decision.** When the plan moves, the old
   decision stays where it is and the new one is appended beside it.

## Why the order is enforced

The tempting order is to do the interesting gate first and let the prerequisites wait. That
produces results that cannot be interpreted: a behavioural claim made in a venue that could
not have shown an effect either way, or a learning claim made on a mechanism whose arrival
was never verified. Each gate exists because its absence produced, at some point, a result
that had to be withdrawn.

## Pass conditions

A gate's pass conditions are fixed in its own preregistration, before its first run, and
are not restated here. This table tracks status; the criterion lives with the experiment that
uses it.

What a gate's pass condition is expected to consist of, once migrated — this is the shape,
not the content:

| Field | Example of the form, not a value |
| --- | --- |
| Question | one sentence, mechanism named |
| Criterion | a quantity and a threshold, with the threshold's origin |
| Control | the arm that should show nothing |
| `n` and MDES | the seed count and the effect this design could detect |
| Failure destination | where the work goes if the criterion is missed |
| Date and status | when it was fixed, and whether it is active, planned or frozen |

Gate 0's current state and what it needs are in `experiments/gate0/README.md`. Gates 1–6
each have a `STATUS.md` stating what would have to be true before anything runs.
