# MIGRATION.md — the historical evidence chain

> **Keep this file until all eight items are in place.** It is the checklist for migrating
> the research record, not a description of the repository layout. When the last item is
> verified, replace this file with a one-paragraph note (or delete it) — and keep the
> migration commit in the history, so the move itself stays traceable.

## The rule

> **Migration is not summarisation.**

These eight items are the evidence chain of the project. Their value is that they say what
was believed at a given time, with the criterion that was actually used. A summary destroys
exactly that: it is written by someone who already knows how the story ended.

Therefore, for every item:

- keep the **original wording**, including hedges, self-criticism and typographical habits;
- keep the **date**, the **version** (e.g. `v2`), and the **applicability conditions**;
- keep the **verdict state** — a frozen decision stays frozen, a negative stays negative;
- do not merge several records into one narrative;
- do not "fix" an old inconsistency. If it conflicts with a later plan, the record stays and
  the conflict is noted beside it, not inside it.

A summary is allowed **in addition**, in `results/summaries/` or as a section that clearly
cites the original. It is never a substitute, and it never overwrites.

## The eight items

The target for each item is the **record**, not the raw material behind it — see
`docs/DISCLOSURE.md`: layer 1 is published in full, layer 2 selectively, layer 3 not at all.
For example, round `r72`'s diagnosis is migrated verbatim; its per-tick terminal output is
not, and is instead identified by hash and location.

| # | Item | Target | Preserve especially | State |
| --- | --- | --- | --- | --- |
| 1 | NORTH_STAR v2 — original text | `docs/NORTH_STAR.md` (replaces the placeholder section "Canon version") | version marker, original wording | **pending** |
| 2 | Gate 0–6 — original pass conditions and status | `docs/RESEARCH_ROADMAP.md` (the per-gate `STATUS.md` files then *point* to it rather than restating it) | thresholds, dates, frozen/active status | **pending** |
| 3 | `r72`, `r78`, `r79`, `r80` — failure and diagnostic records | `records/diagnostics/` (one file per round, using `_template.md`) | separate files, round IDs, the exact defect diagnosis, what each ruled out | **pending** |
| 4 | `E2=甲` freeze decision | `records/decisions/` (+ a pointer from `experiments/gate4/STATUS.md`) | the decision, its reason, its date | **pending** |
| 5 | Stage-3 launch-condition decision history | `records/decisions/` | every revision, in order, none dropped | **pending** |
| 6 | Candidate 1 — original theory draft | `research/papers/candidate1/` | full draft, not an abstract | **pending** |
| 7 | Candidate 2 — experimental basis | `research/papers/candidate2/` | the evidence it rests on, cited by round ID | **pending** |
| 8 | Per-round configuration, logs, weight fingerprints | `records/manifests/` | config + seeds + fingerprints + archive hash and location | **pending** |

★ **Items 6 and 7 need one decision before they are copied.** A manuscript that is under
review, or about to be submitted, is normally not posted publicly in full: many venues treat
that as prior publication. The options, in order of preference:

1. wait until the submission is public, then copy the draft verbatim;
2. publish the theory note (definitions, the bound, the boundary statement) without the
   manuscript, and keep the draft private until it is public;
3. publish the manuscript now, accepting the venue consequence.

Do not "lightly anonymise" a draft and call it published — that satisfies nobody.

## Per-item verification

Run these five checks **per item**, and record the result in the table below. An item is not
done because the file was copied; it is done because all five passed.

1. **Completeness** — is the original text there in full, including sections that no longer
   seem relevant? Compare length and headings against the source.
2. **Numbers** — thresholds, `n`, effect sizes, dates: identical to the source, not
   recomputed, not rounded.
3. **Identifiers** — round IDs (`r72`, `r78`, …), gate numbers, decision IDs: unchanged.
4. **Verdict state** — frozen stays frozen; "criterion not reached" stays that; nothing is
   promoted or demoted in transit.
5. **No dead links** — any path referenced inside the migrated text either still exists, or
   is annotated as `(historical path: …)`. Old paths are not silently rewritten, because a
   reader needs to know the record refers to a tree that has since moved.

### Verification log

| # | Date | Checked by | 1 complete | 2 numbers | 3 IDs | 4 state | 5 links | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |
| 4 | | | | | | | | |
| 5 | | | | | | | | |
| 6 | | | | | | | | |
| 7 | | | | | | | | |
| 8 | | | | | | | | |

## A ninth item that is not a migration, but must be settled

**Authorship and licensing.** `LICENSE` is MIT for the whole repository. That is only valid
if every line in it was written by the author, or is covered by a compatible licence.

What has been checked by static scan (2026-11-15):

- no third-party copyright, SPDX or licence headers anywhere in `legacy/`, `tests/` or
  `tools/`;
- no vendored code: the only imports across the whole tree are the Python standard library
  and NumPy;
- the model equations follow published work, but the implementations are local — equations
  and parameter values are not copyrightable expression, code is.

What a scan cannot check, and only the author can confirm:

- [ ] no block was copied from another project without its header (e.g. adapted from a
      tutorial, a paper's reference implementation, or a colleague's script);
- [ ] no code was produced under a different employer/institution agreement that restricts
      licensing;
- [ ] if any such block exists, it is either removed, rewritten, or accompanied by its
      original notice in a `NOTICE` file.

Until the three boxes are ticked, the MIT grant should be read as the author's intent rather
than as a completed legal audit.

See `docs/PROVENANCE.md` for the provenance record.

## After migration

- [ ] all eight items verified
- [ ] `experiments/gate*/STATUS.md` point at `docs/RESEARCH_ROADMAP.md` instead of restating
      pass conditions
- [ ] no file in `records/` was regenerated from memory
- [ ] this file replaced by a one-paragraph note or deleted
- [ ] the migration commits are left in the history — do not squash them away, they are the
      record of when the tree moved and what moved with it

Migration commits: `7458e3c` (layout + snapshot), `e9212c9` (pipeline moved into
`legacy/pipeline_v1/`).
