# Diagnostic record — <round id> — <what was wrong>

Copy to `records/diagnostics/YYYY-MM-DD_<round>_<defect>.md`.

This file exists because a failed or void round has to leave a usable trace: what was being
tested, what was seen, why it did not pass, what it rules out, and what changed. The raw
output may be summarised; **the diagnosis may not** — that is the part someone else can
reuse.

## 1. Identification

| Item | Value |
| --- | --- |
| Round | |
| Gate | |
| Preregistration | `experiments/gate<N>/preregistrations/…` |
| Decision record | `records/decisions/…` |
| Manifest | `records/manifests/…` |
| Date of the run | |
| Date of this diagnosis | |

## 2. What was being tested

The hypothesis, and the criterion it had to meet — with the threshold and the control arm, as
they were fixed before the run. Copy from the preregistration; do not restate from memory.

## 3. What was observed

The readings that mattered, in the numbers they were reported in. Include the ones that
argue against the conclusion. Note which numbers were later found to be artefacts, and mark
them as such rather than deleting them.

| Reading | Value | Later shown to be |
| --- | --- | --- |
| | | valid / artefact / unknown |

## 4. Why it did not pass

One of, or a combination of:

- **criterion not reached** — the instrument worked, the effect was not there or not large
  enough;
- **void — instrument** — the measurement could not have failed (see
  `protocols/instrument_validation.md`);
- **void — intervention** — the manipulation never reached the system, or was never invoked;
- **void — gate** — an auxiliary gate was constructively different across arms;
- **void — domain** — the run sat outside the mechanism's valid range (readout time, window,
  sampling).

State which, in that vocabulary. "It didn't work" is not a diagnosis.

## 5. What it rules out

The explanation that can now be dropped, stated so that a later reader does not try it again.
If it rules out nothing, say so — an uninformative failure is a result too.

## 6. What changed afterwards

- Next round, or the line's abandonment:
- Instrument change required before the question is asked again:
- Anything this reopens, citing the earlier record it contradicts:

## 7. Evidence location

| Item | Value |
| --- | --- |
| Raw output | location + sha256 (may be outside the repository) |
| Logs | location + sha256 |
| Weight fingerprints | per seed, per arm |

## 8. Wording discipline

- This record does **not** promote the round. A defect diagnosed after the fact leaves the
  pre-registered verdict standing.
- The round may not be cited in either direction.
- Do not rewrite "criterion not reached" as a lesson learned.
