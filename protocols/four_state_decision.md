# Four-state decision

Every round ends in exactly one of four states. Two of them are commonly collapsed into
each other, which is why this is a separate protocol rather than a paragraph.

| State | Means | Permitted wording |
| --- | --- | --- |
| **Difference** | The paired effect exceeds the noise term and the MDES | `A differs from B by Δ = …, t = …, n = …, MDES = …` |
| **Equivalence** | The confidence interval lies inside a margin declared before the run | `equivalent at δ = …` — **never** "the effect is zero" |
| **Undecided** | Neither criterion met | `criterion not reached` |
| **Void** | The instrument, the gate, or the domain of validity failed | no verdict in either direction; the reason is recorded |

## Difference and equivalence are different claims

A difference claim says an effect is larger than noise. An equivalence claim says an effect
is smaller than a margin you declared in advance. They need different criteria, different
`n`, and they cannot be swapped after the fact.

"Equivalent at δ = 0.05" is a statement about resolution. "The effect is zero" is a
statement about the world that no finite experiment supports. Write the first.

A criterion that passes the equivalence leg while the difference leg fails (or the reverse)
is **undecided**, not "basically equivalent" and not "a trend".

## Undecided is a real outcome

The grey band is common: the effect is too large for equivalence, too small or too noisy
for difference. Reporting it as a null is the most frequent way a negative result becomes a
wrong one. Reporting it as a trend is the second.

When a round lands here, the record should say what would resolve it: more seeds, a
different criterion object, or a different venue.

## Void is not a failure of the hypothesis

Void means the round cannot speak: the instrument could not fail, the control arm was
miswired, the sampling window ran past the trial boundary, the auxiliary gate was
constructively different across arms.

Two rules apply to void:

1. **It blocks both directions.** A void round may not be cited as evidence for or against.
2. **The reason must be recorded** in `records/diagnostics/`, because a broken measurement
   that is not written down will be used again.

★ A defect diagnosed *after* the run does not promote the round. If a pre-registered
auxiliary gate failed because it was built wrong, the verdict remains "criterion not
reached (gate failed)", and the diagnosis is recorded beside it. Re-scoring the same data
with a rewritten gate is exactly the move preregistration exists to prevent.

## Append-only records

A decision record is appended, never edited:

- the original threshold stays visible;
- a later re-reading is a new record that cites the old one;
- a roadmap change does not overwrite an old decision.

The research plan may move. The verdicts may not.

## What each state licenses

| State | May be cited as | May not be cited as |
| --- | --- | --- |
| Difference | a measured difference under stated conditions | a mechanism, without the instrument checks |
| Equivalence | resolution at δ | absence of an effect |
| Undecided | that the design did not resolve it | a null, or a trend |
| Void | nothing | anything, in either direction |

The blank record form is [`templates/decision_record_template.md`](templates/decision_record_template.md).
