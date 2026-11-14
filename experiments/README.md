# experiments/

Experiments organized by **research stage**, not by code module.

A gate is a question that has to be answered before the next question is worth asking. It
is not a package, and a directory here is not evidence that the gate is open. Only `gate0/`
is currently maintained; the rest hold a single `STATUS.md` describing what would have to
be true before anything runs.

| Gate | Research focus | Status |
| --- | --- | --- |
| [0](gate0/) | Establish a task with sufficient experimental headroom | Active |
| [1](gate1/STATUS.md) | Temporal and spatial integration | Planned |
| [2](gate2/STATUS.md) | Longitudinal measurement of learning improvement | Not started |
| [3](gate3/STATUS.md) | Cross-task integration and consolidation | Not started |
| [4](gate4/STATUS.md) | Synaptic and connection-level plasticity | **Frozen** |
| [5](gate5/STATUS.md) | Structural self-organization | **Frozen** |
| [6](gate6/STATUS.md) | Self-modeling and higher-level integration | Conceptual |

`docs/RESEARCH_ROADMAP.md` holds the pass conditions and the ordering rule between gates.
The status column above is a pointer, not the record — the record is the decision in
`records/decisions/`.

★ A gate's `STATUS.md` **points at** the roadmap rather than restating its pass conditions.
One copy, so there is no second version to drift.

## Directory convention

Each open gate has four subdirectories:

| Subdirectory | Holds | Does not hold |
| --- | --- | --- |
| `preregistrations/` | The frozen criterion for each round: question, arms, threshold, `n`, MDES, forbidden wording | Results, or criteria edited after the run |
| `configs/` | The exact configuration of each run, versioned | Defaults that were never used |
| `code/` | Code specific to this gate | Shared machinery — that belongs in `tools/` |
| `analysis/` | Scripts that turn records into a decision | Ad-hoc notebooks whose output is quoted without a script |

## The path a stranger should be able to trace

This is the point of the layout. For any result in this repository, a reader should be able
to walk the chain without asking anyone:

```
docs/               what question, and why it is worth asking
  ↓
experiments/gateN/preregistrations/
                    the criterion, written before the run, with its thresholds
  ↓
protocols/instrument_validation.md
                    how the measurement was shown to be able to fail
  ↓
experiments/gateN/configs/ + records/manifests/
                    the exact configuration, seed set, environment, weight fingerprint
  ↓
protocols/paired_analysis.md
                    how the comparison was computed
  ↓
records/decisions/
                    the decision, its state, and what it does not license
```

If any link is missing, the result is not citable — it is an observation. `protocols/` is
the contract for each link; `records/` is where the filled links live.

## Two rules about status

1. **A gate's status changes only by a decision record**, not by adding files, not by a
   roadmap edit. Frozen gates stay frozen until a record lifts them.
2. **An old decision is never overwritten by a new plan.** When the roadmap changes, the
   previous decision stays where it is and the new one is appended beside it.
