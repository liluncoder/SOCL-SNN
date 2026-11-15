# SOCL-SNN

**Self-Organizing Continual Learning in Spiking Neural Networks**

An independent research project investigating local learning, synaptic credit assignment,
temporal information processing, and adaptive mechanisms in spiking neural networks.

The project explores how a neural system can learn from experience through mechanisms that
are **local** — that see only what a synapse or a cell can see — and what such mechanisms can
and cannot carry.

It is an ongoing experimental project. It does not claim general intelligence, human-like
cognition, or open-ended autonomous learning, and its scope is deliberately limited by
evidence, implementation maturity and available compute.

---

## Vision

The long-term target is a **persistent adaptive system**: one that keeps running, perceives,
maintains internal state, remembers experience, acts, and can modify its own learning
mechanisms over time. This is called PAA (Persistent Adaptive Agent) and it is a research
vision, not an architecture that exists here.

The project's own goal is narrower and has to be met first:

> **What can a local learning mechanism actually represent, carry and change — and where does
> that stop?**

That question drives everything below. It is pursued through mathematical analysis and
controlled computational experiments, in this order:

- What information can a local mechanism represent and transmit?
- Does credit assignment change synaptic updates *and* observable behaviour — two different
  questions that are often conflated?
- Can temporal and spatial information be integrated well enough to be read?
- Does learning survive successive experiences?
- Under what conditions can structure adapt without dismantling what works?

SNNs are the current substrate because they make time, locality and cost explicit. They are
not an assumption that spiking computation is sufficient. See
[`docs/VISION_PAA.md`](docs/VISION_PAA.md) and [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md).

## Roadmap

Research is organised as a sequence of gates. A gate is a question that has to be decided
before the next question is worth asking — not a milestone and not a code module.

| Gate | Research focus | Status |
| --- | --- | --- |
| 0 | Establish a task with sufficient experimental headroom | Active |
| 1 | Temporal and spatial integration | Planned |
| 2 | Longitudinal measurement of learning improvement | Not started |
| 3 | Cross-task integration and consolidation | Not started |
| 4 | Synaptic and connection-level plasticity | Frozen |
| 5 | Structural self-organization | Frozen |
| 6 | Self-modeling and higher-level integration | Conceptual |

A gate opens when the previous one has a **decision**, not when it has enough runs. Frozen and
conceptual gates do not open because a directory exists; the status changes by decision record
only. The table describes prerequisites and intended investigations, never completed
capabilities. See [`docs/RESEARCH_ROADMAP.md`](docs/RESEARCH_ROADMAP.md).

## What has been established

These results hold independently of whether the current task is solved. Each is a
statement about what this class of mechanism can and cannot do, and each is checkable from
source or from a recorded measurement.

1. **A scalar modulator cannot address synapses.** With one reward value per postsynaptic
   cell, flipping its sign flips the entire update exactly — `dw(+1) = −dw(−1)` holds bitwise
   at every event. The relative pattern over a cell's in-edges is unchanged, so the write
   carries no direction among them.

2. **Plasticity is distributed by edge count, not by relevance.** A pathway holding 0.42% of
   the synapses received 0.39% of the total weight change — proportional, with no preference
   for the edges that carry the answer.

3. **Opposite rewards produce nearly parallel writes.** Cosine similarity between the updates
   for reward +1 and −1 is about **+0.42**, not −1.

4. **A simplex weight budget forbids growth.** With per-cell budgets normalised on a simplex,
   `Σdw ≡ 0` follows algebraically: weights can be reallocated, never added.

5. **Structure does not bootstrap itself under a fixed topology.** Gradient flow converges
   inside the representable class, and no local criterion drives a change of topology.
   Recorded as an open problem, not as a capability.

6. **The task saturates before a learning effect has room.** In the venue used at the time,
   accuracy reached ≈0.94 at a 2× imbalance — the answer was carried by wiring, so there was
   nothing left for learning to improve.

7. **A readout window can invert a result.** Scoring the same configuration after its response
   had decayed returned the opposite answer: 0.03 versus 1.00 at two windows.

8. **The rule has no timing window.** An edge receives two independent terms, each evaluated at
   its own event: `+A₊·x_pre` when the postsynaptic cell spikes, `−A₋·y_post` when the
   presynaptic cell spikes. Their sum is unchanged when the two events are swapped — measured
   difference exactly zero. So per-edge credit reduces to `R·(A₊·x_pre − A₋·y_post)`: a
   comparison of rates, with no dependence on which came first. This is why "which input caused
   this spike" is not representable, and why adding traces cannot produce direction.

9. **Order-dependent credit is representable, and it changes behaviour.** Give each synapse one
   eligibility, armed by one cell's spike and spent by the other's, and the order decides the
   sign: the same edge moves `+0.010` when the presynaptic cell fired first and `−0.011` when
   the postsynaptic cell did, with an unpaired event leaving it untouched. In the task venue
   this raises accuracy from 0.537 to 0.713 — a paired effect of **+0.175** (t = 2.9 at five
   seeds, t = 4.6 at ten; 8 of 10 seeds positive), which clears the design's minimum detectable
   effect.

   Two controls constrain the explanation. Shrinking the eligibility window twentyfold leaves
   the effect unchanged, and scaling the learning rate down by 6× to match the old rule's total
   write leaves it at +0.167. So the gain is neither a window artefact nor a step-size artefact.
   What remains different between the two rules is *which* edges are depressed and the one-shot
   reset — that is the open question, stated in `research/FINDINGS.md`.

Findings 1, 3 and 4 are the formal content of **Candidate 1** (representational limits of
low-dimensional modulatory credit assignment); finding 2 is the measurement side of
**Candidate 2** (sign reversals and edge-level decomposition of synaptic updates). The full
register, with status and evidence type per entry, is in
[`research/FINDINGS.md`](research/FINDINGS.md).

## Bottlenecks

Four constraints, in the order they bind. A result that ignores the first two is not
interpretable, however large its effect.

**1. Credit has no dimension.** The update is a scalar multiple of the presynaptic trace, so
every synapse on a cell moves in the same proportion — findings 1–3. Until this changes, no
behavioural difference can be attributed to *learning* rather than to the wiring that was
already there. What would clear it: a credit variable that is not a function of activity
alone — timing-signed eligibility, per-branch eligibility, or a state-dependent reward.

**2. The task is solved by its own wiring.** The answer travels along a hand-wired pathway, so
accuracy saturates before a mechanism has anything to add — finding 6. What would clear it: a
venue where the mapping from cue to action is not already built in.

**3. Structure cannot pay for itself.** Under a simplex budget, connections can be
reallocated but not created, and no local criterion currently rewards keeping one — findings
4–5. This is why gates 4 and 5 are frozen rather than scheduled.

**4. The instrument can invert a result.** A readout taken after the response has decayed can
report the opposite of the truth — finding 7. There is no permanent fix; the check has to be
run every time, which is why it is a protocol step and not a paragraph.

The first two are why nothing has demonstrably learned yet. The third is why the roadmap does
not skip ahead. The fourth is why no number here is trusted twice without a check.

## Repository Organization

| Directory | Purpose |
| --- | --- |
| [`docs/`](docs/) | Goals, roadmap, principles, architecture, long-term vision |
| [`protocols/`](protocols/) | Preregistration, measurement, validation, decision rules |
| [`research/`](research/) | Findings register, theoretical analysis, manuscripts |
| [`experiments/`](experiments/) | Experiment setup organised by research stage |
| [`records/`](records/) | Preregistrations, manifests, diagnostics, decisions |
| [`legacy/`](legacy/) | Earlier prototype, preserved and still runnable |
| [`tests/`](tests/) | Unit, instrument and regression tests |
| [`tools/`](tools/) | Supporting utilities |
| [`results/`](results/) | Curated result summaries |

Each experiment is recorded as a question, a preregistered criterion, a configuration, a
result and a decision. A record is complete when someone who was not involved can follow it
end to end: why it was designed that way, whether the measurement can be trusted, whether the
intervention took effect, and how the result was computed.

## Legacy Prototype

Earlier development produced a sequential five-stage prototype: energy-constrained spiking
networks, working memory, memory-driven action, reward-modulated learning, and structural
development. It runs on NumPy alone, at roughly ten seconds of wall clock per simulated
second for 2500 cells.

It is preserved because several of the findings above were measured against it, and a
baseline that cannot be re-run is not a baseline. It is not the current gate structure. See
[`legacy/pipeline_v1/README.md`](legacy/pipeline_v1/README.md).

## Methodology

Experiments follow a preregistered decision process. The central rule:

> **Define the decision criteria before running, validate the measurement, and append the
> resulting decision without rewriting the original criteria.**

In practice:

1. Explicit hypothesis and experimental conditions.
2. Predefined measurement, threshold, sample size and minimum detectable effect.
3. Instrument validation — the measurement is made to fail on purpose before it is trusted.
4. Verification that the intervention reached the system, by weight fingerprint rather than
   assumption.
5. One experimental variable changed at a time.
6. Paired, seed-level comparison; effect quoted against seed noise.
7. Four outcomes: difference, equivalence, undecided, void.
8. Append-only records with explicit applicability conditions.

A broken instrument or an invalid setup is interpreted as **neither** evidence for nor against
a mechanism. Undecided is reported as undecided; "the design could not detect it" is not "it
is not there".

Underlying principles: mathematical definitions before biological analogies; falsifiable
hypotheses before experiments; measurement validation before interpretation; preregistered
criteria before execution; reproducibility before performance claims; negative, undecided and
invalid results kept distinct; historical records preserved rather than silently rewritten.

Every result is documented with its configuration, seeds, code version, measurement
definitions, instrument checks and final decision. See [`protocols/`](protocols/) for the full
protocol and [`docs/RESEARCH_PRINCIPLES.md`](docs/RESEARCH_PRINCIPLES.md) for the reasoning
behind each rule.
