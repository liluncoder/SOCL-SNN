# Provenance

Where the code and documents in this repository came from, and what that implies for the
licence.

## Code

| Part | Origin |
| --- | --- |
| `legacy/pipeline_v1/*.py` | Written by the project author across the sequential prototype phase. Five experiment scripts plus their loader. |
| `legacy/pipeline_v1/tools/_dms_run.py` | Written by the author as the loader for stage 05. Not an adaptation of a third-party tool. |
| `tests/` | Written for this repository. |
| `tools/` | Directory structure only; no implementation yet. |

## Static checks performed (2026-11-15)

- Search for third-party markers — `copyright`, `(c) <year>`, `licensed under`, `SPDX`,
  `all rights reserved`, `@author` — across `legacy/`, `tests/`, `tools/`: **none found**.
- Full import inventory across the same tree: the Python standard library plus NumPy.
  **No vendored code, no bundled third-party source file.**
- Model equations (Izhikevich-type cells, conductance synapses, STDP-style three-factor
  updates) follow published work. Equations and parameter values are not copyrightable
  expression; the implementations in this repository are local.

## What the scan cannot establish

A static scan detects copied *text*, not copied *lines*. Three questions remain open and can
only be answered by the author — they are tracked in `MIGRATION.md`:

1. no block was adapted from a tutorial, a paper's reference implementation, or a
   colleague's script without its notice;
2. no code was written under an agreement that restricts licensing;
3. if either is the case, the block is removed, rewritten, or accompanied by its original
   notice in a `NOTICE` file.

Until those are confirmed, `LICENSE` (MIT) records the author's intent for the code he wrote;
it should not be read as a completed legal audit of every line.

## Documents

`docs/`, `protocols/`, and the READMEs were written for this repository in 2026-11, drawing
on the project's own research practice. They describe a method, not a published result.

Historical research material — north-star text, gate conditions, round records, manuscripts
— is **not** in this repository yet. It is listed in `MIGRATION.md` and will be added
verbatim, with its original dates and wording.

## What is deliberately not here

- Raw experiment output and weight archives (too large; referenced by manifest).
- Manuscripts under review.
- Personal notes and working memory.

Their absence is a scope decision, not a claim of completeness. See `records/README.md` for
how a run that lives outside the repository is still made traceable.
