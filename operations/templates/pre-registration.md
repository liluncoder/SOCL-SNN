# Pre-registration template

Copy this into `report/` (or anywhere you keep run records), fill it in **before** the
run, and never edit a filled field afterwards. A verdict is appended as a new section.

```
==============================================================================
<STAGE> · <ROUND ID> — pre-registration
Date:                |  Code: <file> (unchanged? yes / what changed)
Upstream:            |  Previous round: <file> §<section>
==============================================================================

【0】Question (one sentence, mechanism named)
    ...

【1】This round changes exactly one thing
    ...
    (If it changes more than one, split the round.)

【2】Arms
    Test arm:      <exact arm string the code accepts>
    Control arm:   <exact arm string>
    Constructively identical?  same seed set / same n_trial / same window / same
    scoring — list them: ...
    Why this control and not another:
    ...

【3】Readout (what number, at what time, over what window, averaged over what)
    Quantity:      ...
    Read at:       <t or trial index>   (fixed now, not after the run)
    Aggregated:    mean over <n> ...
    Resolution:    1/<n> = ...
    Continuous alternative, if any: ...

【4】Threshold and where it came from
    Threshold:     ...
    Units:         ...
    Origin:        <literature constant / fraction of model constant / previous run>
    Rescaled?      no / yes, by <fixed model constant>
    Deliberately verify: does this threshold sit outside the observed spread?
    (If you do not know the spread yet, say so and run the spread first.)

【5】n, and the minimum detectable effect
    Seeds:         n = ...
    σ_Δ estimate:  <from a pilot or a previous round>   (pilots are not evidence)
    SE ≈ σ_Δ/√n =  ...
    MDES = k·SE =  ...   with k = ...
    Is the expected effect > MDES?   yes / no  ⇒  if no: VOID BEFORE RUNNING

【6】Controls before spending seeds
    [ ] Mechanism check: deliberately break it, quantity must move
    [ ] Control arm sits where the null predicts it should
    [ ] Null-hypothesis arm exists for any decoding/coupling reading
    [ ] Knob engagement: turn it to an extreme, confirm the manipulation check moves
    [ ] Gate 0: ≥5 test samples per class, row count printed
    [ ] Any assertion added this round has been made to fail once on purpose

【7】Expected reading (written before the run)
    ...

【8】Failure destination
    If it does not pass:  back to <instrument / mechanism>, specifically ...
    What would count as "the instrument is broken" rather than "the mechanism fails":

【9】What I may not write afterwards
    - not "the effect is zero" if the criterion was equivalence at δ
    - not "criterion passed" if the threshold sits inside the seed spread
    - not <your specific over-claim here>


【10】Forbidden this round
    - sweeping <knob> again
    - choosing the readout time after seeing results
    - dropping seeds after seeing them
    - re-scoring the same data with a rewritten criterion
==============================================================================
```

---

## After the run: verdict

Append, do not edit:

```
==============================================================================
<STAGE> · <ROUND ID> — verdict
Date:  |  Command actually run: ...
       |  Raw output: <path>

【Results】
  per-seed:  Δ = ... / ... / ...   mean ...   SD ...   same sign .../n
  effect vs seed noise:  mean/SD = ...
  MDES was ...   → powered? yes / no

【Criterion-by-criterion】
  | item | threshold | measured | verdict |

【State】 difference / equivalence at δ / criterion not reached / void
  If void: which gate, and why it was constructively defective

【Allowed wording】
  ...

【Not allowed】
  ...

【What this does NOT license】
  ...
==============================================================================
```

## Rules for the verdict

1. Never edit a threshold that was written before the run. If it was wrong, add a new
   criterion beside it and report both.
2. A defect diagnosed after the fact does not promote the shot. The pre-registered gate
   failed; that stands.
3. Quote the condition the run was made under, not just the number.
4. If `n` was short, write "not supported", never "falsified".
