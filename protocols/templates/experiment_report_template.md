# Experiment report — <round id>

Written **after** the run, appended to the round's record. The preregistration is not
edited; this file reports what happened against it.

## 1. What was actually run

| Item | Value |
| --- | --- |
| Command | |
| Code version / commit | |
| Seed set | |
| Config file | `experiments/gate<N>/configs/…` |
| Records / manifest | `records/manifests/…` |
| Started / finished | |
| Hardware / environment | |

If any of these differ from the preregistration, say so here and treat the round
accordingly — a deviation is not automatically fatal, but it is never silent.

## 2. Instrument checks, as performed

| Check | Performed | Result |
| --- | --- | --- |
| Deliberate failure moved the reading | yes / no | |
| Control arm at the null position | | |
| Knob engagement | | |
| Gate 0 (samples per class, row count) | | |
| New assertions made to fail once | | |

## 3. Intervention verification

| Item | Value |
| --- | --- |
| Weight fingerprint, arm A | |
| Weight fingerprint, arm B | |
| Same seed ⇒ different fingerprints? | |
| Invocation count for the mechanism | |

## 4. Results

Per-seed table (one row per seed, one pair of columns per arm):

| seed | arm A | arm B | Δ |
| --- | --- | --- | --- |

Summary:

```
n        =
signs    = + / − / tie
mean(Δ)  =
SD(Δ)    =
mean/SD  =
t        =
MDES     =            k =
```

Subset vs whole-vector readings, if the mechanism reaches only part of the state:

| Reading | Denominator | Value |
| --- | --- | --- |

## 5. Deviations and incidents

Anything that went differently: a miswired arm, a crash, a NaN, a run that had to be
repeated. State whether it invalidates the round.

## 6. Pointer to the decision

`records/decisions/<date>_<round>_decision.md`
