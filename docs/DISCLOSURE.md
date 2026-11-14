# Disclosure

What this repository publishes, what it deliberately does not, and the test used to decide.

The rule in one sentence: **publish the evidence chain, not the work log.** Full transparency
of process is not the goal and not a virtue; a public record that an outsider cannot audit is
worse than a smaller one they can.

## The readiness test

A record is ready to publish when an outsider can answer all four questions **from the public
material alone**:

1. **Why was it designed this way?** — the question, the arms, the reasoning for the control.
2. **Can the measurement be trusted?** — what the instrument does, what it was shown to do
   wrong, and what the control arm was expected to show.
3. **Did the intervention take effect?** — the fingerprint, the manipulation check, the
   invocation count.
4. **Can the core result be reproduced?** — code, config, seeds, and the analysis that turns
   one into the other.

If all four are answerable, **do not publish more**. Extra terminal output does not increase
trust; it buries the part that does. If any one is missing, the record is not ready — add the
evidence, not the volume.

## Three layers

### Layer 1 — public research record → `records/`

The audit trail. This is what makes a claim checkable after the fact.

| Item | In the repository |
| --- | --- |
| Preregistrations (question, arms, thresholds, `n`, MDES, forbidden wording) | verbatim |
| Run manifests (commit, seeds, config, log hash, fingerprints) | verbatim |
| Decisions (state, what it licenses, what it does not) | verbatim |
| Key diagnostics (what was wrong with the instrument, what it invalidated) | verbatim |
| Failure reasons | verbatim, in the diagnostic's own words |
| Decision history (revisions, freezes, re-openings) | verbatim, in order |

### Layer 2 — reproducible materials → `experiments/`, `tools/`, `results/`

What someone needs in order to re-run the key result rather than believe it.

| Item | In the repository |
| --- | --- |
| Experiment code | yes |
| Fixed configurations | yes, versioned |
| Seed sets | yes |
| Analysis scripts | yes — a number with no script behind it does not go in a decision |
| Curated result summaries | yes, in `results/summaries/` |
| Key raw data | *selectively* — the data the core claim rests on, or its archive hash and location |

Raw data is where "public" stops being free: a run can be gigabytes. The rule is that the
**claim** must be reproducible, and the archive must be identifiable by hash. Not every dump
needs to be in Git.

### Layer 3 — internal working material → not published

- repeated logs and per-tick dumps;
- scratch scripts and abandoned attempts;
- unprocessed intermediates;
- environment caches and temporary artefacts;
- personal notes and reasoning drafts.

★ **One exception, and it matters.** If an internal file is the *only* original evidence for a
claim, it cannot be discarded for being untidy. It gets one traceable copy — hashed, located,
and named from the manifest — even if it stays outside the repository. "It was messy" is not
a reason to lose the only record of what happened.

## Failed experiments leave traces

A negative round is not an embarrassment to be omitted; it is the part that stops the same
explanation being tried again. Every failed round that reached a decision gets a record, and
the record answers five questions:

1. **What was being tested?** — the hypothesis and the criterion it had to meet.
2. **What was observed?** — the readings, including the ones that were inconvenient.
3. **Why did it not pass?** — the criterion missed, or the instrument void.
4. **What does it rule out?** — the explanation that can now be dropped.
5. **What changed afterwards?** — the next round, or the abandonment of the line.

A summary is acceptable **for the raw output** (nobody needs every line), but not for the
diagnosis: the reasoning behind a failure is the reusable part. Template:
`records/diagnostics/_template.md`.

★ Two things this forbids:

- **Publishing only the rounds that worked.** A record whose failures are missing is not a
  record, it is a highlight reel.
- **Dressing a failure as a success.** "The criterion was not reached" stays that. Rewriting
  it as "we learned a lot about the dynamics" is the same act as editing the threshold.

## What this repository is not

It is not a volume competition. Adding logs, figures and files to make the tree look
substantial works against the only thing a public research repository is for: letting a
stranger check whether a claim holds.

A small, complete, checkable record beats a large one that has to be believed.

## Where the policy is applied

- `records/` — layer 1. Each file states its own applicability conditions.
- `experiments/<gate>/configs|code|analysis`, `tools/`, `results/summaries/` — layer 2.
- `MIGRATION.md` — which historical material moves into layer 1, and in what form.
- `docs/PROVENANCE.md` — what is deliberately absent, so absence is not mistaken for
  completeness.
