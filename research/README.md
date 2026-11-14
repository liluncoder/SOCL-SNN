# research/

Theory and manuscripts. Kept separate from `experiments/` on purpose.

An experiment log answers "what did this round show". A manuscript answers "what does this
line of work claim, and under what limits". Merging the two produces the two failure modes
this split exists to prevent: a paper conclusion that is really one round's log, and a
round's log that gets quoted as if it were a paper.

## `theory/`

Mathematical analysis: definitions, derivations, representability arguments, bounds.

| Directory | Scope |
| --- | --- |
| `credit_assignment/` | What a given update rule can and cannot represent; dimension and locality arguments |
| `learning_dynamics/` | Stability, convergence, plasticity rules as dynamical systems |
| `structural_adaptation/` | Growth, pruning, and what "structure" would have to mean to be measured |

Theory here is expected to be **falsifiable from source code or from a stated measurement**
— a claim that cannot be checked is not admitted, and an analogy is not a definition.

## `papers/`

Manuscript drafts, candidate research lines, and their reference lists.

| Directory | Line |
| --- | --- |
| `candidate1/` | Representational limits of low-dimensional global modulatory credit assignment |
| `candidate2/` | Sign reversals and edge-level decomposition of synaptic updates |

Status: the manuscripts are **not yet published here**. When they are added, they are added
verbatim — a manuscript's claims and limits are not edited to match a later roadmap. If a
later round contradicts a manuscript, the manuscript stays and the contradiction is
recorded.

## What does not belong in this directory

- Run configurations, preregistrations, decisions — `experiments/` and `records/`
- Numbers quoted without the decision record they came from
- A claim that a roadmap change has made "no longer needed" — old claims are annotated, not
  removed
