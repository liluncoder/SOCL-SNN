# Diagnostic record — r81 — the third factor never reaches the events it multiplies

## 1. Identification

| Item | Value |
| --- | --- |
| Round | r81 |
| Gate | 0 (task and measurement), blocking |
| Preregistration | none — this is a diagnostic, not a registered comparison |
| Decision record | `experiments/gate0/GATE0_CANDIDATE_DECISION.md` |
| Manifest | not applicable (diagnostic) |
| Date of the run | 2026-11-16 |
| Date of this diagnosis | 2026-11-16 |

## 2. What was being tested

Nothing was preregistered. The round began as "the venue needs a task whose correct edge
depends on the trial" (the conclusion of the previous round) and had to establish, before
building that task, that the arm could deliver a reward at all.

The property that must hold for a three-factor rule, stated so that it can fail:

> For a synapse whose event belongs to trial *n*, the scalar that multiplies its update is
> a function of trial *n*'s outcome — and of nothing else.

## 3. What was observed

Venue as used in every earlier round: `w_p8=0.05`, `p_safe=0.5`, window 20–70 ms,
`arm='local'`, seed 411, 3 trials (24 rounds). Raw output: `.workbuddy/runs/diag_delivery.log`.

### 3.1 When the events happen

`_decide()` — and therefore `_write_reward()` — runs at `r_t0 + win_t1` = 70 ms. The
stimulus is injected at 20–50 ms.

| Reading | Value | Later shown to be |
| --- | --- | --- |
| ACT-group spikes before the write, `eng_scale_scope='global'` | 322 / 757 = **42.5%** | valid |
| ACT-group spikes before the write, `eng_scale_scope='act'` | 341 / 770 = **44.3%** | valid |
| Carrier **edge-events** before the write, `global` | **43.4%** of 12 840 (pre-side 3 000, post-side 2 576) | valid |
| Carrier **edge-events** before the write, `act` | **43.9%** of 12 704 (pre-side 2 848, post-side 2 728) | valid |

Counting edge-events rather than spikes (a marker spike touches 8 carrier edges, an ACT spike
touches 8) does not change the picture: 43% of the plastic events on the hand-wired answer
pathway are scaled by the *previous* round's reward, and the rest occur after the readout they
are credited against. No event carries the outcome of the trial it belongs to.

### 3.2 The sign of the reward the events see

Mean normalized energy of the previous round's winner group minus its loser group, over the
stimulus window of the following round:

| Frame | rounds where the winner group has the larger reward | mean(win − lose) | \|d\| > 0.05 |
| --- | --- | --- | --- |
| `global` (the default everywhere in the record so far) | **4 / 23** | **−0.040** | 6 / 23 |
| `act` (`eng_scale_scope='act'`) | 17 / 23 | +0.204 | 18 / 23 |

Under the default frame the reward is not merely noisy: it is slightly *anti*-correlated
with the outcome. The mechanism is saturation, not noise. At the decision the write sets the
winner's energy to `med + s·r*·scale` and reads back exactly `+0.500`, while the untreated
group sits far above the population median and is clipped at `+1.000` — the winner is
rewarded less than the loser. Measured directly (`.workbuddy/runs/diag_reward_frame`):
`R(winner) = 0.500`, `R(loser) = 1.000` in every learned round of that run.

## 4. Why it did not pass

**void — instrument.** The measurement cannot fail in the intended direction, because the
delivered signal is not the outcome: it is the previous outcome, attenuated, and under the
default frame inverted. This is the definition the protocol asks for, and it applies to
every arm comparison in the record in which `arm='local'` was supposed to be reward-driven.

The three parts are separable and were each checked:

| Part | Source | Check |
| --- | --- | --- |
| The reward is read at the event | `_stdp_step` calls `_reward_of` for each event | source |
| The write happens after the stimulus window | `_write_reward` is called from `_decide`, at `win_t1` | source + §3.1 |
| The written value is not held, and the default frame inverts it | `_energy_tick` every 1 ms; global median far below the answer cells | §3.2 |

## 5. What it rules out

- It rules out the reading "`local` and `task_off` are indistinguishable, therefore a local
  reward has no effect here". The arm named `local` was not delivering a trial's outcome to
  that trial's events, so that comparison **has no verdict** — not a negative one.
- It rules out any venue built on `credit.at='event'` as a test of credit assignment,
  independently of how the task is wired. The previous round's conclusion (the answer is
  supplied by wiring) is true but was **not the binding constraint**; the binding constraint
  is upstream of it.
- It does **not** touch the structural results: `dw(+1) = −dw(−1)` bitwise, the rank-one
  decomposition, the absence of a timing window, the write being distributed by edge count.
  Those are statements about the *shape* of the update, which the change in §6 preserves.

## 6. What changed afterwards

- **`credit.at` switch added** (`01_substrate.py`, `04_task_environment.py`), default
  `'event'` = historical behaviour, weight fingerprint bitwise unchanged
  (`830136398b09fbed`, 7200 edges, `w_sum=1592.799952`).
- **`'decision'` mode**: one eligibility per edge accumulates during the round
  (`e -= A₋·y_post` on a spike's incoming edges, `e += A₊·x_pre` on its outgoing edges);
  at the decision the reward vector is applied as `dw = R_j · e_ij` and the eligibility is
  cleared at the start of every round. The reward is now `s·r*` for the chosen group and
  exactly zero everywhere else. The update is still a per-cell scalar times a per-edge
  eligibility, so the representational arguments are unchanged.
- **Validated** by `experiments/gate0/code/credit_delivery_check.py` — five checks, all
  passing: inert when off; no write between decisions; arrival on learned rounds; **credit
  confined to the chosen group, exact zero elsewhere**; probe rounds and `arm='task_off'`
  move nothing at all.
- A side effect worth recording: under `'decision'`, `task_off` is *exactly* a frozen
  network (`dw ≡ 0`). Under `'event'` it was not — it learned from the natural energy field.

## 7. Evidence location

| Item | Value |
| --- | --- |
| Reproducible measurement | `experiments/gate0/code/instrument_reward_delivery.py` |
| Delivery log | `.workbuddy/runs/r81_delivery.log` — sha256 `eb86472ecf17fdeb…` |
| Validation log | `.workbuddy/runs/r81_credit_check.log` — sha256 `de70d58a85cce809…` |
| Paired run rows | `.workbuddy/runs/r81_credit.jsonl` — sha256 `142d3a74be6d1ff3…` |
| Paired summary | `.workbuddy/runs/r81_summary.txt` — sha256 `63bc2c046a841f7d…` |
| Weight fingerprints | `event` mode `830136398b09fbed`; `decision` mode differs per arm by construction |

Raw output lives outside Git (`.workbuddy/` is untracked); the script that produces it is
tracked, so every number above can be regenerated rather than trusted.

## 8. Wording discipline

- This record does not promote r81. No arm comparison in the earlier rounds gains a verdict
  from it.
- The earlier "Δ = −0.0139, t = −0.35, undecided" is now **void — instrument**, not
  undecided. That is a downgrade, not an upgrade, and it is recorded here rather than in the
  old decision.
- The structural findings stand. Do not cite this record as evidence against them.
