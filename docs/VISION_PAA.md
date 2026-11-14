# Vision: persistent adaptive systems (PAA)

> **This document describes a direction, not an architecture.** Nothing here is
> implemented, validated, or claimed. Its purpose is to make the long-term motivation
> legible, so that the staged research plan can be read as progress toward something rather
> than as a sequence of unrelated experiments.

## The idea

A **Persistent Adaptive Agent** (PAA) is a conceptual figure for the kind of system this
research is ultimately curious about: one that

- perceives a changing world,
- maintains internal state that persists across experience,
- remembers what happened in a way that affects later behaviour,
- acts, and observes the consequences of acting,
- and can modify its own learning mechanisms in response.

The last item is the one that makes the figure interesting and the one furthest from
anything demonstrated here.

## Why it is a vision and not a plan

A plan has pass conditions. This does not, because the central terms do not yet have
measurable definitions:

- "persistent" — persisting over what, measured how, against what decay?
- "internal model" — what would a system without one fail at, that a system with one would
  pass, and that neither could pass by accident?
- "modify its own learning" — which parameter, changed by what signal, verified how?

Until those questions have answers that can be falsified, this stays a direction. Writing it
in more operational language would be inventing a research programme that does not exist
yet.

## What the current work contributes toward it

Each is a bounded, checkable question, and each is a prerequisite rather than an instance:

| Research question | Relation to the vision |
| --- | --- |
| What a local mechanism can represent | Bounds what "adapt its own learning" could even mean |
| Whether a write carries direction | Separates activity from learning, which the vision conflates if unchecked |
| Whether state survives a delay | The minimal form of persistence |
| Whether learning survives successive tasks | The minimal form of continual adaptation |
| Whether structure can adapt without collapse | The minimal form of self-modification |

None of these is a partial PAA. They are the questions that have to be settled before a PAA
claim could mean anything.

## What this document must not be used for

- As evidence that any capability above has been demonstrated.
- As a roadmap: the roadmap is `RESEARCH_ROADMAP.md`, and it is far more conservative.
- As a justification for scope. "It is all part of the vision" is not a reason to run an
  experiment without a criterion.

## On the substrate

Spiking neural networks are the current experimental substrate — they make time, locality
and cost explicit, which is useful for these questions. They are **not** an assumption that
spiking networks are sufficient for general intelligence. If the evidence points to another
substrate, or to a hybrid, the research should follow the evidence; the vision is not
committed to the implementation.
