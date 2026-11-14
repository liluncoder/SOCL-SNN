# Preregistration — <round id> — <one-line question>

Copy this file to `experiments/gate<N>/preregistrations/<round>_<slug>.md` and fill every
field **before** the run. After the run, append a report; do not edit a filled field.

```
Stage / gate:          |  Round:              |  Date:
Code (version / commit):                    |  Unchanged since last round?  yes / no
Upstream (previous round and its decision):  |  Depends on:
```

## 1. Question

One sentence, with the mechanism named. Not "does memory work".

## 2. Arms

| Role | Identifier (exactly as the code accepts it) | Why this one |
| --- | --- | --- |
| Test | | |
| Control | | |

Constructively identical? — seed set / `n_trial` / scoring window / sampling / readout mode:

Is the control the same system with the intervention withheld (not a weaker version)?

What does the null-hypothesis arm remove, and what does it keep?

## 3. Measurement

| Item | Value |
| --- | --- |
| Quantity | |
| Read at (moment / round index) — fixed now | |
| Window | |
| Aggregated as | |
| Resolution (`1/n`) | |
| Continuous alternative, if any | |

## 4. Threshold

| Item | Value |
| --- | --- |
| Threshold | |
| Units | |
| Origin (literature constant / fraction of a fixed model constant / previous round) | |
| If rescaled: rescaled by which **fixed** constant | |

Is the threshold outside the observed spread? If the spread is unknown, say so and measure
the spread first — do not run the comparison yet.

## 5. `n` and MDES

```
n            =
σ_Δ (source) =
SE  ≈ σ/√n   =
MDES = k·SE  =            k =
```

Expected effect > MDES? If no ⇒ the round is **void before running**; record it and do not
run.

## 6. Pre-run checks (see protocols/instrument_validation.md)

- [ ] Deliberate failure: mechanism broken on purpose, reading moved
- [ ] Control arm sits where the null predicts
- [ ] Knob engagement: extreme value moves an independent quantity
- [ ] Gate 0: ≥5 test samples per class, row count printed
- [ ] Any new assertion has been made to fail once on purpose
- [ ] Null-hypothesis arm exists for any decoding / coupling reading

## 7. Expected reading

A number or a range. Written before the run.

## 8. Failure destination

If it does not pass: back to the instrument / back to the mechanism / booked as negative —
and specifically what would count as "the instrument is broken" rather than "the mechanism
fails".

## 9. Forbidden wording

The sentences I may not write afterwards:

- not "the effect is zero" if the criterion was equivalence at δ
- not "criterion passed" if the threshold sits inside the seed spread
- not …

## 10. Forbidden this round

- sweeping <knob> again
- choosing the readout moment after seeing results
- dropping seeds after seeing them
- re-scoring the same data with a rewritten criterion
