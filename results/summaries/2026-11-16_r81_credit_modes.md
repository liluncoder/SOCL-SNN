# r81 — credit delivery modes at the gate-0 venue

```
Round:      r81 (exploratory; the round's formal state is recorded in records/diagnostics/)
State:      exploratory — no verdict. Not difference, not equivalence, not reached, not void.
Decision:   none. The governing document is experiments/gate0/GATE0_CANDIDATE_DECISION.md
Conditions: 2500 E cells / 25 units, w_p8=0.01, window 20–70 ms, 12 trials, 8 seeds
            (411+10i), arms task_off vs local, credit.at ∈ {event, decision}
```

**Why this is not a result in either direction.** The run exists to check that the repaired
delivery changes anything at all. The venue still supplies the answer, so no accuracy
difference here can be attributed to credit assignment. Every difference is reported next to
the design's minimum detectable effect so it cannot be read as an effect.

## What was run

`experiments/gate0/code/paired_arms.py`, 8 seeds, 12 trials each, arms `task_off` (null) and
`local`, once per credit mode. Same seeds across arms and modes, so the difference is paired.

| credit | arm | n | acc | sd | carrier write | total credited write |
| --- | --- | --- | --- | --- | --- | --- |
| `event` (historical) | `task_off` | 8 | 0.602 | 0.100 | 5.1 | — |
| `event` (historical) | `local` | 8 | 0.620 | 0.071 | 2.4 | — |
| `decision` (repaired) | `task_off` | 8 | 0.544 | 0.055 | **0.0** | 0.00 |
| `decision` (repaired) | `local` | 8 | 0.568 | 0.078 | 0.5 | 2.47 |

Seed-paired difference against the null arm:

| credit | mean Δ | sd Δ | t | MDES (k=2.8) | signs +/−/= | seeds needed for δ=0.05 |
| --- | --- | --- | --- | --- | --- | --- |
| `event` | +0.0182 | 0.0915 | 0.56 | 0.0905 | 3/2/3 | 27 |
| `decision` | +0.0234 | 0.0734 | 0.90 | 0.0727 | 4/3/1 | 17 |

## What the numbers say

1. **The instrument now separates the arms by construction.** Under `decision`, the null arm's
   weight vector does not move at all (carrier write exactly 0, total credited write exactly 0),
   while the learning arm writes 2.47, of which 0.5 lands on the hand-wired answer pathway.
   Under `event` the ordering is *reversed*: the null arm writes **more** to the carrier (5.1)
   than the arm under test (2.4). Whatever the old arm comparison was measuring, it was not the
   difference between "rewarded" and "not rewarded".

2. **The behavioural difference is still below the design's noise floor.** +0.018 and +0.023,
   both far under MDES. By the project's four-state rule both are **undecided**, not "no
   effect". At the observed spread, δ=0.05 would need 17–27 seeds per mode.

3. **Only about a fifth of the repaired credit lands on the carrier** (0.5 of 2.47); the rest
   goes to the recurrent in-edges of the chosen group. So the repair does not simply amplify
   the wired pathway — it also perturbs whatever else drives the chosen group. That is why the
   effect did not grow, and it is the venue's confound showing up from the other side: where the
   answer is wired, "credit the answer" and "credit the noise" reach the same readout.

## What this changes

- It does **not** pass, fail, or promote Gate 0. The venue still supplies the answer.
- It does show the arm comparison is interpretable for the first time: the null arm is now
  frozen rather than "learning from the natural energy field".
- It sets the sample size for any future comparison at this venue: 17 seeds for δ=0.05 with the
  repaired delivery. A later claim quoting fewer seeds and a smaller effect is undecided unless
  it is paired and reports this MDES.

## Reproduction

```bash
python experiments/gate0/code/paired_arms.py --seeds first8 --arms task_off,local \
    --credit-at event    --w-p8 0.01 --trials 12 --out .workbuddy/runs/r81_credit.jsonl
python experiments/gate0/code/paired_arms.py --seeds first8 --arms task_off,local \
    --credit-at decision --w-p8 0.01 --trials 12 --out .workbuddy/runs/r81_credit.jsonl
python experiments/gate0/analysis/paired_summary.py --in .workbuddy/runs/r81_credit.jsonl
```

Wall clock: ~60 s per seed-arm. `first15` is accepted for a fuller sweep.
