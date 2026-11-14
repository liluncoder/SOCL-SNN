# PAA — Persistent Adaptive Agent

> **Status: long-term research vision.** Not implemented, not validated, and not a roadmap.
> Nothing in this document opens a gate, licenses a claim, or describes existing behaviour.
> The operational plan is `RESEARCH_ROADMAP.md`; what this file does is make the long-term
> motivation legible.
>
> The sections *Overview* through *Scientific Scope* are the project's stable statement of
> PAA. They are reproduced here as written and should not be paraphrased — a vision document
> that gets rewritten every time the roadmap moves tells a reader nothing about what was
> intended.

## Overview

Persistent Adaptive Agent (PAA) is a long-term research vision for computational systems
capable of persistent operation, continuous adaptation, memory formation, environmental
modeling, and autonomous action.

Unlike conventional systems that primarily operate through fixed parameters and externally
initiated interactions, PAA explores architectures in which internal states, learned
parameters, memory representations, and computational structures can evolve through ongoing
interaction with an environment.

The central objective is to investigate how an intelligent system can accumulate experience,
use that experience to guide future behavior, and adapt its own computational organization
over time.

## Core Capabilities

PAA explores six interconnected capabilities:

1. **Perception:** Continuously acquire and interpret information from the environment.
2. **World Modeling:** Maintain internal representations of environmental states and predict
   possible outcomes.
3. **Memory:** Preserve, consolidate, and retrieve useful experiences.
4. **Planning and Action:** Select actions based on goals, internal models, and accumulated
   experience.
5. **Adaptive Neural Substrate:** Provide learnable computational mechanisms whose internal
   states, parameters, and potentially structures can change over time.
6. **Resource and Runtime Management:** Coordinate persistent execution, computational
   resources, learning processes, and structural adaptation.

These capabilities are conceptual architectural components. They are not claims that a
complete implementation currently exists.

The components need not all be realised by one neural network. They may be different
algorithms and computing systems cooperating through a unified state and information
interface; the shared interface, not the shared substrate, is what makes it one system.

## Multi-Timescale Adaptation

PAA investigates adaptation across multiple timescales:

- **Fast dynamics:** neural activity, transient internal states, and working memory.
- **Intermediate dynamics:** synaptic plasticity, experience accumulation, and memory
  consolidation.
- **Slow dynamics:** structural adaptation, module reorganization, and resource allocation.

The interaction between these timescales is an important research question, particularly
with respect to stability, continual learning, and long-term adaptation.

The reason to separate them is a design hypothesis, not a result: if everything adapts at the
same rate the system has no stable reference, and if nothing adapts it cannot accommodate a
changing environment. Which timescales, which stability conditions, and how the layers
interact are open questions that experiments would have to settle.

## Computational Substrate

PAA is not restricted to a single neural architecture.

Spiking Neural Networks (SNNs), Artificial Neural Networks (ANNs), and hybrid computational
systems are potential implementations of its adaptive substrate.

SOCL-SNN is a current research project investigating mechanisms that may contribute to this
broader vision, particularly local learning and adaptive neural computation.

```
                    PAA
          Persistent Adaptive Agent
                     |
        ---------------------------
        |            |            |
     Memory     World Model    Planning
        |            |            |
        ---------------------------
                     |
        Adaptive Neural Substrate
                     |
              SOCL-SNN (SNN)
                     |
          Local Learning Mechanisms
```

What should stay fixed is the research question, not the implementation. SNNs are the current
substrate because they make time, locality and cost explicit — useful properties for these
questions — not because spiking computation is assumed to be necessary.

## Research Questions

- How can a computational system maintain useful internal states during persistent operation?
- How can experience produce lasting changes in parameters, memory, and behavior?
- How can an agent build and update an internal model of its environment?
- How can learning and memory remain stable over long periods?
- Under what conditions can computational structures adapt autonomously?
- How can multiple adaptive mechanisms cooperate under limited computational resources?

## Scientific Scope

PAA is a long-term architectural research vision, not a validated AGI design.

Persistent operation, self-adaptation, memory, and self-modeling are computational research
objectives. They should not be interpreted as evidence of consciousness or subjective
experience.

Its architecture and implementation choices must evolve according to mathematical analysis,
controlled experiments, and reproducible evidence.

---

## Appendix A — capability progression

The vision implies an order: a capability that depends on another is not worth attempting
first. The progression below is **vision-level**, translated from the project's working note.
It is not an execution plan, it opens no gate, and passing one step would not confer the
next.

| Step | Capability | The verifiable question |
| --- | --- | --- |
| 1 | Persistent internal state | With input removed, does the internal state keep evolving as designed? |
| 2 | Online learning | Can the system update from new experience and improve on what follows? |
| 3 | Lasting memory | Can an important experience be retained and retrieved when needed? |
| 4 | World model | Can it predict environmental state and the consequences of its actions? |
| 5 | Autonomous planning | Can it choose actions from a goal and revise the plan on feedback? |
| 6 | Adaptive structure | Can it change its own organisation under a stated constraint? |
| 7 | Long-term integration | Do the capabilities hold together over long operation without degrading each other? |

Each step would need its own baseline, control, preregistered criterion and failure
condition — the same protocol as any gate, applied to a capability rather than to a
mechanism.

## Appendix B — where the vision meets the current work

The current repository does not implement PAA, and it does not attempt the steps above in
order. What it does is investigate the substrate-level questions that several of them rest
on. The mapping below names the **nearest current question**, not a delivered capability:

| PAA concern | Nearest current question | Where it is pursued |
| --- | --- | --- |
| Adaptive neural substrate | What can a local learning mechanism represent and carry? | theory; Candidate 1 |
| Whether adaptation reaches the system | Does an intervention reach the weights, and does it carry direction? | Candidate 2; gate 4 (frozen) |
| Persistent internal state | Does state survive a delay, and is it read at a moment it exists? | legacy pipeline, stage 02 |
| Continual adaptation | Does learning survive successive tasks? | gate 2, gate 3 (not started) |
| Structural adaptation | Can structure change without dismantling what works? | gate 5 (frozen) |
| Self-modeling | — no measurable definition yet | gate 6 (conceptual) |

★ Two things this table must not be read as: that the current work is a partial PAA, or that
a frozen gate is waiting to deliver its row. The right-hand column is mostly *not started*,
and that is the honest state.
