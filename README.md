#

# SOCL-SNN

**Self-Organizing Continual Learning in Spiking Neural Networks**

SOCL-SNN is an independent research project investigating local learning, synaptic credit assignment, temporal information processing, and adaptive mechanisms in spiking neural networks.

The project explores how neural systems can learn from experience through local mechanisms, maintain useful internal states, and potentially adapt their own computational structures over time.

It is an ongoing experimental research project. It does not claim to have achieved general intelligence, human-like cognition, or open-ended autonomous learning.

## Research Motivation

Most conventional neural network experiments focus on learning a task under a fixed architecture and training procedure.

This project investigates a different set of questions:

- What information can local learning mechanisms actually represent and transmit?

- How does credit assignment affect synaptic updates and observable behavior?

- How can temporal and spatial information be integrated?

- Can learning remain effective across successive experiences?

- Under what conditions can network structure adapt without destabilizing learning?

These questions are investigated through mathematical analysis and controlled computational experiments.

## Current Research

The research is organized into a staged roadmap:

| Stage  | Research focus                                         | Status      |
| ------ | ------------------------------------------------------ | ----------- |
| Gate 0 | Establish a task with sufficient experimental headroom | Active      |
| Gate 1 | Temporal and spatial integration                       | Planned     |
| Gate 2 | Longitudinal measurement of learning improvement       | Not started |
| Gate 3 | Cross-task integration and consolidation               | Not started |
| Gate 4 | Synaptic and connection-level plasticity               | Frozen      |
| Gate 5 | Structural self-organization                           | Frozen      |
| Gate 6 | Self-modeling and higher-level integration             | Conceptual  |

The roadmap describes research prerequisites and intended investigations, not completed capabilities.

See docs/RESEARCH_ROADMAP.md.

## Experimental Methodology

Experiments follow a preregistered decision process.

The central principle is:

**Define the decision criteria before running an experiment, validate the measurement process, and append the resulting decision without rewriting the original criteria.**

The methodology includes:

1. Explicit hypotheses and experimental conditions.

2. Predefined measurements, thresholds, sample sizes, and minimum detectable effects.

3. Instrument validation and deliberate failure tests.

4. Verification that interventions actually affect the system.

5. One experimental variable changed at a time.

6. Paired, seed-level comparisons.

7. Four distinct outcomes: difference, equivalence, undecided, and void.

8. Append-only experimental records and explicit applicability conditions.

A failed instrument or invalid experimental setup is not interpreted as evidence for or against a mechanism.

See protocols/ for the detailed methodology.

## Research Findings and Publications

The project also investigates theoretical limits of learning mechanisms.

Current research outputs include:

- **Candidate 1:** Analysis of the representational limits of low-dimensional global modulatory credit assignment.

- **Candidate 2:** Investigation of sign reversals and edge-level synaptic update decomposition.

These are research manuscripts and candidate research directions. Their claims should be interpreted according to the evidence and limitations stated in the corresponding documents.

See research/papers/.

## Repository Organization

| Directory      | Purpose                                                      |
| -------------- | ------------------------------------------------------------ |
| `docs/`        | Research goals, roadmap, principles, and long-term vision    |
| `protocols/`   | Preregistration, measurement, validation, and decision rules |
| `research/`    | Theoretical analysis and manuscripts                         |
| `experiments/` | Experiment implementations organized by research stage       |
| `records/`     | Preregistrations, manifests, diagnostics, and decisions      |
| `legacy/`      | Earlier experimental prototypes preserved for reference      |
| `tests/`       | Instrument, unit, and regression tests                       |
| `tools/`       | Supporting utilities                                         |
| `results/`     | Curated result summaries                                     |

What is published, and what is deliberately withheld, is governed by
[docs/DISCLOSURE.md](docs/DISCLOSURE.md). The short version: the evidence chain is published
in full — preregistrations, decisions, key diagnostics, failure reasons — while raw work logs
are not. A test decides which is which: can an outsider, from the public material alone,
understand why the experiment was designed that way, judge whether the measurement is
trustworthy, check that the intervention took effect, and reproduce the core result?

## Legacy Prototype

Earlier development included a sequential prototype exploring:

- Energy-constrained spiking networks

- Working memory

- Memory-driven action

- Reward-modulated learning

- Adaptive network structures

These earlier experiments are preserved as historical research artifacts. They should not be confused with the current Gate-based research roadmap.

## Long-Term Vision

The long-term motivation is to investigate persistent adaptive computational systems that can perceive, maintain internal models, remember experience, act, and modify their own learning mechanisms.

PAA (Persistent Adaptive Agent) is a conceptual research direction for organizing these capabilities.

SNNs are the current research substrate, not an assumption that spiking neural networks alone are sufficient for general intelligence. Alternative or hybrid computational substrates may be considered as evidence develops.

PAA is a research vision, not an implemented or validated AGI architecture.

See docs/VISION_PAA.md.

## Research Principles

- Mathematical definitions before biological analogies.

- Falsifiable hypotheses before experiments.

- Measurement validation before interpretation.

- Preregistered criteria before execution.

- Reproducibility before performance claims.

- Explicit distinction between negative, undecided, and invalid results.

- Historical records are preserved rather than silently rewritten.

## Reproducibility

Each experiment should document its configuration, random seeds, code version, measurement definitions, instrument checks, analysis procedure, and final decision.

See individual experiment records for the exact conditions under which a result was obtained.

## Scope

SOCL-SNN is an independent, evolving research project. Its current scope is deliberately limited by experimental evidence, implementation maturity, and available computational resources.

The immediate objective is not to claim general intelligence, but to establish reliable and increasingly capable mechanisms through controlled, reproducible research.
