# 02 — How to design a run with this code

The code gives you a network and a set of arms. It does not give you an experiment. What
turns a run into an experiment here is the order of operations: the criterion is written
before the run, the control arm is fixed at the same time, and the verdict is appended
afterwards and never edited.

This file is the method. It is deliberately result-free — copy the shape, not the
thresholds.

A blank form is in [`templates/pre-registration.md`](templates/pre-registration.md).

---

## 1. The loop

1. **Pre-register.** Write one file: the question, the arm under test, the control arm,
   the quantity you will read, the threshold, the number of seeds, the reading you
   expect, where you go if it fails, and what you may and may not write afterwards.
2. **Check the instrument, before spending seeds.** Does the quantity move when you
   deliberately break the mechanism? Does the control arm sit where it should? Does the
   knob you intend to turn actually connect to anything?
3. **Run.** Same flags, same seed set, across arms. Keep the raw output.
4. **Pair by seed.** Compute the per-seed difference, then summarise.
5. **Append a verdict.** New section, never an edit of the old threshold.

The reason for the order is simple: a threshold chosen after seeing the distribution is
a description of that distribution, not a test.

---

## 2. What goes into a pre-registration

The template has the fields; here is what each one is for.

**The question, in one sentence, with the mechanism named.** "Does the snapshot pool hold
the previous code after the cue is removed" — not "does working memory work".

**The arm under test and the control.** Name them by the exact strings the code accepts
(`two_pool`, `snap_off`, `local`, `task_off`, …), because a control that is not
constructively identical to the test arm is not a control. Same network, same seed set,
same trial count, same scoring window; only the intervention differs.

**The control must be the same system with the intervention withheld**, not a weaker
version of the mechanism. If the control is "a bit less of the thing", the comparison
measures dose, not presence, and you cannot distinguish "the mechanism matters" from
"more of anything helps".

**The quantity, with its units.** Which number, read at which time, over which window,
averaged over what. If the readout has a resolution — an accuracy over `n` scored
rounds has resolution `1/n` — write the resolution down next to the threshold.

**The threshold and where it came from.** If it is a constant from the literature, say
so; if it is a fraction of a model constant, say which one. A threshold in absolute
weight units is meaningless in a model whose weights live in a different range; if you
rescale, rescale by a **fixed** model constant, not by the observed min/max of the run
you are about to judge (that makes the threshold follow the data).

**`n`, and the minimum detectable effect.** Before the run:
`SE ≈ σ_Δ / √n`, `MDES ≈ k · SE` (quote the `k` you used). If the effect you are trying
to detect is smaller than your MDES, the run is **void before it starts** — do not run
it and do not report the null. The honest options are: add seeds, change the criterion's
object, or drop the question.

**The expected reading, written down.** A number or a range. If you cannot say what you
expect, you do not yet have a hypothesis; if you say only "it will be higher", you cannot
distinguish a surprise from a bug.

**The failure destination.** Where you go if it does not pass: back to the instrument,
back to the mechanism, or book it as a negative result. A pre-registration without this
becomes a licence to tune.

**What you may not write.** The most valuable field. Write the sentence you are not
allowed to produce — "this does not show that learning fails, only that this venue could
not measure it" — before the run, while you still have no stake in the outcome.

---

## 3. Seeds and pairing

- **Single seed does not count.** One seed can carry a result; the same statistic on a
  second seed can erase it. Two arms compared on one seed per arm is an anecdote.
- **Pair by seed.** Same seed, both arms, subtract. Report the per-seed differences, the
  sign count, the mean, and the SD of the differences.
- **Report the effect against seed noise**, not against zero. "Δ = X, SD = Y, X/Y = Z" is
  a statement about a mechanism; "p < 0.05" over 15 seeds is a statement about arithmetic.
- **Never pool SD across arms** to build the noise term. The pooled SD contains
  between-arm variance, which inflates the denominator and manufactures "no difference".
- **Do not drop seeds after looking at them.** If a seed is catastrophic, that is part of
  the distribution you are measuring; the fix is more seeds, decided in advance.

---

## 4. Sample gates

**Gate 0 — class balance.** Before any accuracy number: at least ~5 test samples per
class, enforced at sampling time with a resample-retry. Stages 02–04 already print this
statistic. An accuracy computed on an unbalanced test set moves when the sampling moves,
and you will attribute it to the mechanism.

**Empty gate = failure, not pass.** If a summary line reports "all rows passed", it must
also report the row count. A filter that selects nothing passes vacuously.

**A gate that has never failed is not a gate.** Before you trust an assertion, make it
fail on purpose once (a deliberately illegal parameter is the cheapest way). If it cannot
fail, it is a log line.

---

## 5. The null-hypothesis arm

Any reading of the form "X carries information about Y" — decoding accuracy, coupling,
correlation, mutual information — must first be shown to be ≈ 0 on an arm where the
proposed pathway is removed **but everything else is kept**.

Without that arm, the reading has at least three innocent explanations: the measurement
setup itself, a shorter path that bypasses the mechanism, and a feedback loop between the
agent's own output and its input. All three produce a stable, reproducible, entirely
spurious signal. If you cannot name the arm that would zero the reading, you do not have
a reading yet.

This is the single most expensive lesson available in this kind of work, because the fake
reading looks *better* than a real one: it is larger, more stable across seeds, and easier
to explain.

---

## 6. Readout design

- **When you read is part of what you read.** A mechanism with a slow build-up read too
  early looks broken, and the resulting "the mechanism fails" is a statement about your
  window. Before concluding a mechanism is absent at time `t`, check that the mechanism
  is supposed to have produced something by `t`.
- **Fix the readout time in the pre-registration.** Choosing it after seeing the result
  is choosing the result.
- **The code enforces one interface constraint for you** — the sampling window must fit
  inside the trial (`02_working_memory.py`, asserted in `_run_once`). Do not remove that
  assertion; it exists because the violation is silent (you read the next trial's
  activity).
- **Prefer a continuous readout to a thresholded one** when you have the choice. A
  discrete accuracy loses resolution exactly where the difference is small, and a
  saturated accuracy has no headroom to show an effect.

---

## 7. Three verdict states, not two

| State | Means | Wording |
| --- | --- | --- |
| **difference** | paired effect exceeds the noise term and the MDES | "A differs from B by Δ, t = …, n = …, MDES = …" |
| **equivalence** | the confidence interval sits inside a pre-declared margin `δ` | "equivalent at δ = …", **never** "the effect is zero" |
| **undecided** | neither criterion met | "criterion not reached" |

The third state is real and common. Collapsing it into "no effect" is the most frequent
way a negative result becomes a wrong one; collapsing it into "trend" is the second.

And a fourth, procedural state: **void**. The instrument was broken, the gate was
constructively defective, the run exceeded its domain of validity. A void run produces no
verdict in either direction, and the reason must be written down — otherwise the same
broken measurement gets used again.

---

## 8. Logging and provenance

- **Use `--log FILE` where the stage has it** (02–04). It writes UTF-8 from inside the
  process. Shell redirection on Windows PowerShell 5.1 re-encodes and mangles it.
- **Keep the raw output of every cell** you intend to cite, and put the run's parameters
  in the filename or in a header line. A number you cannot trace back to a command is a
  rumour.
- **Record the weight digest** when the question is "did the intervention reach the
  weights". Two arms that differ in digest at the same seed prove the write happened;
  two arms that agree prove it did not. `04_task_environment.py` computes one
  (`md5` over the weight vector) for exactly this purpose.
- **State the condition you ran under.** Flags like `--freeze-w` or `p_safe` change what
  the same accuracy means; a result without its condition is not reusable.
