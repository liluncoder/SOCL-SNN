# Preregistration

A criterion written **before** the run, in a file, with the control arm and the threshold
fixed at the same time. After the run the file may only be appended to.

The purpose is narrow and worth stating plainly: preregistration does not make you more
likely to be right. It makes it impossible for the data to tell you, afterwards, what
question you asked.

## What a preregistration must contain

| Field | Why |
| --- | --- |
| **Question** | One sentence, mechanism named. "Does the snapshot pool still hold the previous code after the cue is removed", not "does working memory work". |
| **Test arm and control arm** | Written as the exact identifiers the code accepts. A control that differs in more than the intervention is not a control. |
| **Measurement** | Which number, read at which moment, over which window, averaged over what, and its resolution (`1/n` for an accuracy over `n` scored rounds). |
| **Threshold, and its origin** | A literature constant, or a fraction of a *fixed* model constant. Never a fraction of this run's observed range — that makes the threshold follow the data. |
| **`n`, and the minimum detectable effect** | `SE ≈ σ_Δ/√n`, `MDES ≈ k·SE` with the `k` quoted. If the effect you want is smaller than MDES, the round is void before it starts. |
| **Expected reading** | A number or a range. If you cannot write one, you have a curiosity, not a hypothesis. |
| **Failure destination** | Where you go if it does not pass: back to the instrument, back to the mechanism, or booked as a negative result. |
| **Forbidden wording** | The sentence you are not allowed to publish, written while you still have no stake in the outcome. |

The blank form is [`templates/preregistration_template.md`](templates/preregistration_template.md).

## The control arm is half the design

Three rules, in order of how often they are violated:

1. **The control is the same system with the intervention withheld**, not a weaker version
   of the mechanism. "Less of it" measures dose, and cannot separate "the mechanism
   matters" from "more of anything helps".
2. **Choose the arm that gives no answer at all**, not the arm that gives a weak answer.
   A weak-answer control cannot distinguish "the mechanism is necessary" from "the
   mechanism helps a bit".
3. **Constructively identical**: same seed set, same trial count, same scoring window, same
   sampling. An auxiliary gate whose window or count differs across arms can veto a main
   result for reasons unrelated to the hypothesis — and that has happened here, which is
   why the rule exists.

## MDES, before the run

Compute the noise term from the planned `n`, not from the run you are about to do:

```
SE   ≈ σ_Δ / √n                      σ_Δ from a pilot or a previous round
MDES ≈ k · SE                        quote k
```

If the threshold (or the effect you expect) is below MDES, the run is **void** — not
negative, void. Running it produces a number that looks like evidence and is actually a
statement about your budget. The honest options are: add seeds until MDES is small enough,
change the object of the criterion, or drop the question.

Pilot numbers never enter a criterion and are never cited as evidence.

## What may not be changed after the run

- The threshold. If it was wrong, add a **new** criterion beside it and report both.
- The measurement moment. Choosing it after seeing the result is choosing the result.
- The seed set. Removing a catastrophic seed is removing the tail of the distribution you
  are measuring.
- The arm definitions. If an arm was miswired, the round is void — the run measured
  something else.

## Why this is written down and not merely agreed

Because the failure it prevents is not dishonesty. After the run, every number acquires an
explanation: this one is noise, that one is the trend, the other one is a known artefact.
Each explanation may even be correct. The preregistration is the only record made by the
version of you who had not yet seen the data.
