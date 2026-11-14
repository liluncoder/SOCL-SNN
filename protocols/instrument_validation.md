# Instrument validation

Before a measurement is allowed to decide anything, it has to be shown that it **can fail**.

This is the part of the protocol that preregistration cannot cover. A preregistration fixes
what you intend to measure; it says nothing about whether the measurement works. A perfect
preregistration of a broken instrument produces a citable-looking result about nothing.

## The five checks

Run these before seeds are spent. They are cheap; skipping them is not.

### 1. Deliberate failure

Break the mechanism on purpose and confirm the reading moves.

A measurement that has never returned "negative" is not a test. Concretely: disable the
pathway the reading is supposed to reflect, or set its weight to zero, and check that the
number collapses to what the null predicts. If it does not move, the reading is not
sensitive to the mechanism — it is sensitive to something else.

**A gate that has never exited non-zero is a log line.** The same applies to assertions:
a new `assert` must be made to fail once, on purpose, before it is trusted.

### 2. Control-arm placement

The control arm must land where the null predicts, not merely differ from the test arm.

If the control is supposed to be at chance and it reads 0.35, the wiring is wrong, not the
mechanism. This check is what separates "the intervention had no effect" from "the arm
switch was ignored".

### 3. Engagement of the knob

Before using a continuous parameter as an experimental variable, turn it to an extreme and
confirm a *independent* quantity moves.

A knob that is set in the config but not read anywhere produces a beautiful, stable,
meaningless null. Two examples of a correct check: shrinking an evidence window should move
every arm's level (and it does, in this project) — that proves the window is connected,
even when the comparison of interest is unchanged by it.

### 4. Gate 0 — sampling

Before any accuracy number: at least ~5 test samples per class, enforced at sampling time
with a resample-retry, and the count printed.

An accuracy computed on an unbalanced test set moves when the sampling moves, and the
movement will be attributed to the mechanism. Print the row count next to "all passed":
a filter that selects nothing passes vacuously, and an empty gate is a **failure**, not a
pass.

### 5. The null-hypothesis arm

Any reading of the form "X carries information about Y" — decoding accuracy, coupling,
correlation, mutual information — must be shown ≈ 0 on an arm where the proposed pathway is
removed but everything else is kept.

Without that arm the reading has at least three innocent explanations, and all three are
reproducible:

- the measurement setup itself generates the signal;
- a shorter, unintended path bypasses the mechanism;
- a closed loop through the agent's own output feeds the input it is supposedly reading.

★ This is the most expensive lesson available in this kind of work, because the fake
reading is **better than the real one**: larger, more stable across seeds, easier to
explain. It is also why this document exists as a separate step rather than a subsection of
the preregistration.

## Ordering

Instrument validation happens **after** the preregistration and **before** the seeds. The
preregistration says what will be measured; the validation says the measuring device is
alive. Doing it the other way round — validating after seeing an effect — means you will
validate until the effect survives.

## What invalidates a round

- The deliberate-failure check did not move.
- The control arm is not where the null predicts and the cause was not found.
- Gate 0 was not met, or was met without printing the count.
- A new assertion was never made to fail.
- No null-hypothesis arm exists for a reading that needs one.

Any of these makes the round **void** rather than negative. The reason must be recorded in
`records/diagnostics/`, because the same broken instrument will otherwise be reused.
