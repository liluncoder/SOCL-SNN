# MIGRATION.md — artifacts that must be moved verbatim

> Temporary file. Delete it once the items below are in place.

This repository was restructured to a research-workflow layout. The documents and records in
the table below are **not** part of that restructure: they are historical material that has
to be copied across **unchanged**. Nothing in the current tree reproduces, summarises or
paraphrases them, and that is deliberate — this restructure was designed from the public
repository plus the research description, not from a file-by-file review of the private
archive.

## Rule

> Research direction may be updated. Old verdicts may not be overwritten.

Concretely, for every row: copy the original file, keep its wording, keep its thresholds and
dates, and do not merge several records into one summary. If a later plan contradicts one of
them, the record stays where it is and the contradiction is appended beside it.

## Items

| # | Artifact | Target path | State |
| --- | --- | --- | --- |
| 1 | NORTH_STAR v2 — original wording | `docs/NORTH_STAR.md` (replaces the placeholder section "Canon version") | **pending** |
| 2 | Gate 0–6 — original pass conditions and status | `experiments/gate<N>/STATUS.md` (replace the "Launching conditions: not yet written" text) | **pending** |
| 3 | `r72`, `r78`, `r79`, `r80` — failure and diagnostic records | `records/diagnostics/` | **pending** |
| 4 | `E2=甲` freeze decision | `records/decisions/` + referenced from `experiments/gate4/STATUS.md` | **pending** |
| 5 | Stage-3 launch-condition decision history | `records/decisions/` | **pending** |
| 6 | Candidate 1 — original theory draft | `research/papers/candidate1/` | **pending** |
| 7 | Candidate 2 — experimental basis | `research/papers/candidate2/` | **pending** |
| 8 | Per-round configuration, logs and weight fingerprints | `records/manifests/` (manifest + pointer to the archive) | **pending** |

## What is *not* pending

The following were written for this restructure and are not migrations. They may be edited
freely, and they carry no historical authority:

- `docs/RESEARCH_OVERVIEW.md`, `docs/RESEARCH_ROADMAP.md`, `docs/RESEARCH_PRINCIPLES.md`,
  `docs/ARCHITECTURE.md`, `docs/VISION_PAA.md`
- `protocols/` and its templates
- `records/`, `results/`, `research/`, `tests/`, `tools/`, `experiments/README.md` — the
  READMEs describing layout, not records
- `legacy/pipeline_v1/README.md`
- the per-gate `STATUS.md` files (their *status* line tracks the roadmap; their
  *launching conditions* are placeholders for item 2)

## Ordering

Copy in the order of the table. Items 1–2 first, because every other document refers to
them; item 8 last, because a manifest is only useful once the code version it names is
settled.

## Verification after migration

- [ ] `docs/NORTH_STAR.md` contains the v2 text, not a summary of it
- [ ] Every gate's pass conditions come from the original, with their original dates
- [ ] `r72`/`r78`/`r79`/`r80` are separate files, not one consolidated narrative
- [ ] The `E2=甲` decision is findable from `gate4/STATUS.md`
- [ ] No old verdict was edited while being copied
- [ ] No file in `records/` was regenerated from memory
