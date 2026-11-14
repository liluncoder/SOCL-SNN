# protocols/

The project's **Experimental Protocol**: how an experiment is specified, validated,
executed, analysed and decided.

This is an internal working protocol, not a published method. It is not named after
anybody and it does not claim novelty. It is simply the set of rules this project holds
itself to, written down so that a reader can check whether a given result followed them.

Each document here is a contract for one link in the chain that a result has to pass
through:

| Document | The question it answers |
| --- | --- |
| [`preregistration.md`](preregistration.md) | What must be written down before a run, and what may not be changed after it |
| [`instrument_validation.md`](instrument_validation.md) | How a measurement is shown to be capable of failing before it is trusted |
| [`intervention_verification.md`](intervention_verification.md) | How to prove the manipulation actually reached the system |
| [`paired_analysis.md`](paired_analysis.md) | How two conditions are compared, and what a null has to carry |
| [`four_state_decision.md`](four_state_decision.md) | The four outcomes a round may end in, and the wording each one permits |

Templates: [`templates/`](templates/) — a preregistration form, an experiment report, and
a decision record.

## The eight steps

A round is not finished until all eight have been done. The order is the protocol; doing
them in a different order is what allows a result to be shaped by its own data.

1. **State the question** with the mechanism named, in one sentence.
2. **Preregister** the criterion, arms, measurement, threshold, `n`, MDES and the forbidden
   wording — before the run.
3. **Validate the instrument**: make it fail on purpose, and confirm the control arm sits
   where the null predicts.
4. **Verify the intervention** reaches the system, with a weight fingerprint rather than an
   assumption.
5. **Run** with one axis changed, the old batch bitwise unchanged.
6. **Analyse** paired by seed, with the effect quoted against seed noise and an MDES.
7. **Decide**: difference, equivalence, undecided, or void.
8. **Record** the decision append-only, with its applicability conditions.

## Why the order is the protocol

Every step exists because its absence produces a specific, attractive error:

- without (2), the threshold ends up where the data already is;
- without (3), a setup artefact is read as a mechanism;
- without (4), a manipulation that never reached the system produces a clean null;
- without (5), two changes are credited to whichever one the author prefers;
- without (6), a single seed carries a conclusion;
- without (7), "undecided" is written as "no effect";
- without (8), a later re-reading silently replaces an earlier verdict.

## What this protocol does not do

It governs **what you decided to measure**. It does not protect you from a measurement
that measures the wrong thing — that is `instrument_validation.md`, and the two are only
useful together.

It also has a real cost: writing a preregistration kills ideas that were never going to
work, and it does so at the point where you still like them. That is the function, not the
overhead.
