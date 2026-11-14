# Research overview

SOCL-SNN is an independent research project investigating local learning, synaptic credit
assignment, temporal information processing, and adaptive mechanisms in spiking neural
networks.

The project asks how a neural system can learn from experience through mechanisms that are
**local** — that see only what a synapse or a cell can see — and what such mechanisms can and
cannot carry.

## The questions

**What information can a local learning mechanism represent and transmit?**

A local rule sees a pre-synaptic trace, a post-synaptic trace, and some third factor. The
question is how much of a credit signal that structure can express, and where the
representational ceiling binds. This is the most developed line in the project, and it is
answered by analysis as much as by simulation.

**How does credit assignment affect synaptic updates and observable behaviour?**

Two things that are often conflated: whether an update reaches the weights at all, and
whether it points anywhere useful. They need separate measurements — a large write with no
direction is a different finding from a small write with a direction, and both differ from
no write.

**How can temporal and spatial information be integrated?**

Information has to survive a delay, and it has to be bound to the right location. The
questions are whether a state persists long enough to be read, and whether the readout
happens at a moment when the mechanism has actually produced something.

**Can learning remain effective across successive experiences?**

Not merely "does one task get learned", but whether what is learned survives the next task
without being erased, and whether the measurement can tell consolidation apart from
interference.

**Under what conditions can network structure adapt without destabilising learning?**

Growth and pruning can produce structure; they can also dismantle the network that was
doing the work. The question is what makes the difference, and whether "structure" can be
defined well enough to be measured rather than eyeballed.

These questions are investigated through mathematical analysis and controlled computational
experiments. Where a question cannot yet be given a falsifiable form, it is recorded as a
conceptual direction rather than as an experiment — see `VISION_PAA.md`.

## How it is investigated

Three layers, deliberately separated:

| Layer | Artifact | What it answers |
| --- | --- | --- |
| Theory | `research/theory/` | What a rule can represent, before any run |
| Protocol | `protocols/` | How a run is specified, validated, compared, decided |
| Experiment | `experiments/`, `records/` | What was asked, what happened, what was concluded |

The separation is the point. A theoretical bound is checkable from source; an experimental
decision is checkable from a record. Merging them produces claims that cannot be checked
either way.

## Current research outputs

- **Candidate 1** — analysis of the representational limits of low-dimensional global
  modulatory credit assignment.
- **Candidate 2** — investigation of sign reversals and edge-level decomposition of
  synaptic updates.

Both are candidate research lines. Their claims are bounded by the evidence and the stated
limitations in the corresponding documents, not by this overview.

## What this project is not

It is not a claim that spiking networks are sufficient for general intelligence; the
spiking substrate is the current experimental setting, not an assumption. It is not a
benchmark entry: there is no leaderboard, and the experiments are designed to test
mechanisms, not to maximise a score.
