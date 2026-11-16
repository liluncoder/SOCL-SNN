# Decision record — r81

## 1. Identification

| Item | Value |
| --- | --- |
| Round | r81 |
| Gate | 0 (task and measurement) |
| Preregistration | none — the affected comparison was run as exploration, without one |
| Report | `records/diagnostics/2026-11-16_r81_reward_delivery.md`, `results/summaries/2026-11-16_r81_credit_modes.md` |
| Date of decision | 2026-11-16 |
| Decided by | the run's own instrument checks; no independent ratification claimed |

## 2. Criterion-by-criterion

| # | Item | Threshold | Measured | Verdict |
| --- | --- | --- | --- | --- |
| 1 | The reward a synapse sees belongs to the trial its event belongs to | every event | 42.5% of answer-pathway spikes and 43.4% of carrier edge-events precede the write; the rest follow the readout | void |
| 2 | The signed reward matches the outcome under the default frame | sign correct in most rounds | 4 / 23 rounds; mean(winner − loser) = −0.040 | void |
| 3 | `local` vs `task_off` behavioural difference at `w_p8=0.01`, 15 seeds | \|Δ\| ≥ MDES 0.1105 or equivalence at δ=0.05 | Δ = −0.0139, t = −0.35 (r80 run) | **reclassified void** — previously `criterion not reached` |

## 3. State

**void — instrument**, for the arm comparison, and for every result in the record that used
`arm='local'` as a reward-driven arm.

The rule reads the reward at each event; a trial's outcome is written at the decision, after
the stimulus window. So the events that decide a trial are scaled by the previous trial's
outcome, and the events after the decision are scaled by an outcome they did not cause.
Independently, the default energy frame saturates the answer cells, so the written value does
not even carry the intended sign at event time.

## 4. What this licenses

- "The delivery of the third factor in this implementation was defective in two separable
  ways — timing and frame — measured at the gate-0 venue with seed 411, `w_p8=0.05`,
  window 20–70 ms."
- "With `credit.at='decision'`, credit is confined to the chosen group (weight change outside
  it exactly zero), the null arm is exactly frozen, and the off-switch weight fingerprint is
  unchanged."
- "The structural results (scalar modulator cannot address synapses; rank-one update; no
  timing window; write distributed by edge count) are untouched, because the repaired rule is
  the same `R_j · e_ij` with the scalar read later."

## 5. What this does not license

- It does **not** license "a local reward has no behavioural effect here". That comparison
  has no verdict now; it is void, not negative.
- It does **not** license "the repaired delivery makes the mechanism work". The exploratory
  paired run gives +0.023 against MDES 0.073 — undecided.
- It does **not** close Gate 0. The venue still supplies the answer.
- It does **not** revive the retracted pair-rule effect (r80, entry 10 of the findings
  register). That reading was a write-volume effect, and this record does not change it.

## 6. Applicability conditions

| Condition | Value |
| --- | --- |
| Task / venue | gate-0 task venue, `w_p8` as stated per reading, `p_safe=0.5` |
| Network size / configuration | 2500 E cells, 25 units, 4 input channels, 2 action groups of 8 |
| Frozen pathways | none; `task_off` is the null |
| Readout mode and moment | spike count over 20–70 ms, `win_t1` decision |
| `n`, seed set | diagnostic 1 seed; paired run 8 seeds (411 + 10i) |
| MDES | 0.0905 (`event`), 0.0727 (`decision`), k = 2.8 |

## 7. Consequences

- Next round: implement and validate the candidate venue in
  `experiments/gate0/GATE0_CANDIDATE_DECISION.md` §6 — target is the conjunction of a cue and
  an instruction, the conjunction provided as infrastructure, only eight outgoing edges
  plastic from exact ties. Its five checks are listed there and none has been run.
- Anything this closes: the question "does an event-time three-factor rule learn here" is
  closed in the negative — it was never asked of a working instrument.
- Anything this reopens: the r80 arm comparison, which must be re-asked on `credit.at='decision'`
  before any statement about local reward is made. It reopens the question, not the verdict.

## 8. If void

Which check failed: the delivery check (criterion 1) and the frame check (criterion 2) in §2.
What the defect was: the third factor was sampled at the event rather than carried to the
outcome, and it was read from a frame in which the answer cells saturate.
How the instrument changed: `credit.at` switch with `'decision'` mode — one eligibility per
edge accumulated during the round, reward applied when the outcome is known, eligibility reset
at every round start. Five checks in `experiments/gate0/code/credit_delivery_check.py`, all
passing, including exact-zero credit outside the chosen group and an unchanged off-switch
fingerprint (`830136398b09fbed`). The question will be asked again on that mode, not on
`'event'`.
