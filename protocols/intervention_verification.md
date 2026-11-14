# Intervention verification

Two experiments can differ in their setup and be identical in what the system experienced.
Verifying the intervention means proving, with a number, that the manipulation reached the
mechanism it was aimed at — before any outcome is interpreted.

A null result whose intervention never arrived is not a null. It is a failed experiment
that looks like one.

## 1. Weight fingerprint

The cheapest reliable check, when the intervention is supposed to change synaptic weights:
hash the weight vector at a fixed seed, once per arm, and compare.

| Observation | Conclusion |
| --- | --- |
| Same seed, different arms ⇒ **different** hashes | The intervention reached the weights |
| Same seed, different arms ⇒ **identical** hashes | The intervention did not reach the weights, whatever the output says |
| Same seed, same arm, before vs after code change ⇒ **identical** hash | The change was inert (this is what you want for a refactor) |

The hash is a fingerprint, not a proof of direction: it establishes arrival, not effect.
Direction is a separate reading.

## 2. Inert defaults

A new switch must reproduce the previous behaviour exactly when untouched, and that must be
checked, not assumed:

1. Run the old configuration with the new code, same seed.
2. Compare the fingerprint against the stored one.
3. If it moved, the "inert" switch is not inert.

This is the rule that makes a codebase of chained experiments usable: every change carries
a bitwise regression test against the previous batch.

## 3. One axis per round

Change one thing. If two things changed, the result cannot attribute the difference, and a
follow-up round is needed to find out — which is exactly the cost the rule avoids.

If a second change is unavoidable (a bug fix plus the intended change), run the bug fix
alone first as its own round, even when it feels like a formality.

## 4. Count the mechanism's own invocation

For interventions that are supposed to be exercised during the run, log a counter for the
number of times the mechanism actually fired.

If the counter is zero, the effect cannot be attributed to that mechanism regardless of how
large it is. A path that is configured on and never called looks exactly like a path that
is working well — from the outside.

This class of bug is common enough to be a rule: **a mechanism that is nominally on but
never invoked will silently produce a real-looking effect from whatever else is running.**

## 5. Condition, not just number

Every reported number carries the condition it was obtained under: which arm, which frozen
pathway, which safe-side probability, which readout mode. Two accuracies with the same
value under different conditions are not comparable, and a number without its condition is
not reusable.

## Checklist

- [ ] Same-seed fingerprint differs between arms (arrival)
- [ ] Same-seed fingerprint unchanged by the refactor (inertness)
- [ ] Only one axis differs from the previous round
- [ ] Invocation counter for any mechanism to which an effect is attributed
- [ ] The condition is recorded next to the number

When any of these fails, the round is void and the reason goes to `records/diagnostics/`.
