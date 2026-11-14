# Gate 1 — Temporal and spatial integration

**Status: Planned.** No code, no preregistration, no run yet.

A directory existing at this path does **not** mean this gate is open. The gate opens
when its launching conditions are written down and accepted — before then there is
nothing to run.

## What this directory will hold when it opens

| Subdirectory | Contents |
| --- | --- |
| `preregistrations/` | The frozen criterion, arms, thresholds, `n`, MDES, and the "may not write" list |
| `configs/` | The exact configuration of every run, versioned |
| `code/` | Only the code that is specific to this gate; shared machinery belongs in `tools/` |
| `analysis/` | The scripts that produce the decision from the records in `records/` |

## Launching conditions

Not yet written. Until they exist, this gate stays closed and the roadmap status stays
"Planned".

See `docs/RESEARCH_ROADMAP.md` for the ordering rule between gates.
