# 03 — Traps in this code

Constraints and silent failures that will make a run mean something other than what you
think. Every item here is verified against the source, with the line to read.

These are not style warnings. Each one produces a number that looks fine.

---

## 1. `norm_on = True` does not mean weights are normalised

`DEFAULT_CFG` sets `norm_on: True` (`01_substrate.py:73`), and the per-cell normaliser
call sits behind a gate (`:1269`):

```python
if self.syn_on:
    c = self.syn_cfg
    if c.get('norm_on') and (self.t - self.last_norm) >= float(c['norm_period']):
        self._normalize_weights()
```

But that block lives inside `_develop()` (`:1194`), and `_develop()` is only called from
one place (`:820`):

```python
if dev_on and (not energy_only) and (t - self.last_dev) >= period:
    self._develop()
```

So **the normaliser only runs when development runs**. Any stage that sets
`dev: {'on': False}` — stages 02 and 03 do, via `MEM_CFG` / `m2_cfg` — never normalises
anything, regardless of `norm_on`. Setting `energy_only` has the same effect while
leaving deaths and divisions partly active.

Before you attribute anything to "normalisation", check which of `dev.on` and
`energy_only` is set in the config you are actually running.

---

## 2. Distance and latency are coupled by default

`lr_per_unit_ms: 0.6` (`:62`) makes long-range synapses both stronger-reaching and
**slower**: the delay for a long-range edge is `lr_base_ms + lr_per_unit_ms × distance`
(`:489`). Local edges get a flat `local_ms`.

Consequence: any reading about distance — propagation order, synchrony, wavefront
arrival, "near neighbours respond together" — has a latency confound built into the
wiring, and the confound points the same way as the hypothesis.

`delay.decouple = True` gives every long-range edge the *mean* long-range distance
instead (`:490`), which removes the gradient. Stage 02 sets it in `MEM_CFG`; stage 01's
default is `False`.

If your question involves distance, run both settings.

---

## 3. The sampling window must fit inside the trial

`k · DEC_PERIOD ≤ ITI − RESET_DUR`. At defaults (`DEC_PERIOD = 100`, `RESET_DUR = 250`,
`ITI = 900`) that gives `k ≤ 6`.

`_run_once` asserts it in stage 02. **Do not remove the assertion.** The failure mode is
silent and looks like a real result: exceed the bound and the sampler reads activity from
the *next* trial, so the measurement is still non-empty, still reproducible, and
measures the wrong trial.

If you need a larger `k`, increase `ITI` first, and check that the assertion passes with
your intended `DEC_PERIOD`.

---

## 4. `Q` is `nan` below 20 edges

`modularity_report()` returns `nan` unless the binarised correlation graph has at least
20 edges, and the edge count depends on the threshold you binarise at and on the number
of stations. At small `--units` it simply cannot reach 20.

`nan` here means "graph too sparse", not "no modularity". The printout includes the
community count; check the edge count before drawing any conclusion. Reporting `nan`
indefinitely is also a choice — if a quantity cannot resolve at your network size, say so
and stop using it rather than reporting an absence.

---

## 5. Stage 04's CLI never runs anything but `task_off`

`build()` accepts five arms (`:51`), but every command-line call site passes
`arm='task_off'` (`:932`, `:1034`). So `--smoke`, `--p8-probe` and the calibration modes
all run the reward-free arm. That is deliberate — they are interface and calibration
checks, not experiments — but it means an accuracy printed by the CLI is a **baseline**,
not a learning result.

To run another arm, drive `build()` yourself; see [04_extend.md](04_extend.md) §3.

---

## 6. Fixed output filenames

`--report` and `--criteria` write to fixed paths under `report/`
(`_006_数量与发育_中间产物.txt`, `_006_验收判据_单种子.txt`, `01_substrate.py:1860`,
`:1921`). The directory is created if missing, but the names are not parameterised, so
**two runs in parallel overwrite each other** and the second one's numbers silently
replace the first's.

Run them sequentially, or copy the file out immediately after each run.

---

## 7. Filenames are the interface

Each stage loads its predecessor by literal filename with `importlib`:

| File | Loads | Line |
| --- | --- | --- |
| `02_working_memory.py` | `01_substrate.py` | `:20` |
| `03_memory_driven_action.py` | `02_working_memory.py` | `:19` |
| `04_task_environment.py` | `03_memory_driven_action.py` | `:26` |
| `05_prototype.py` | `tools/_dms_run.py` | `:11` |

Renaming a file, moving it into a package, or adding a `src/` layout breaks the chain at
load time. That is the one structural rule of this repository: **if you must rename,
grep for the literal string first**. Also note that importing a stage executes it, so
loading `04` loads `03`, `02` and `01` and builds a network at module import.

---

## 8. Smoke modes are not baselines

`--smoke` on stages 02–04 checks that fields exist and the mechanism does not collapse. It
prints its own disclaimer — no scientific claim — and the sample sizes are far too small
for any accuracy to mean anything. A smoke run is never a baseline, and its numbers must
not enter a report even as "roughly".

The one thing smoke is genuinely good for: catching a wiring error in an arm before you
spend an hour of seeds.

---

## 9. Determinism is per seed *and* per condition

Same seed and same flags give the same trajectory, including the weight vector digest.
That property is what makes an arm comparison meaningful: two arms that differ in digest
at the same seed prove the intervention reached the weights; two arms that agree prove it
did not.

Anything that changes the RNG consumption order — an extra sampling call, a new
diagnostic that draws random numbers, a different `n_trial` — changes the trajectory for
that seed. If you add a diagnostic, verify that the digest is unchanged before you trust
the comparison, and say so in the run record.

---

## 10. `n_trial` must be a multiple of the channel count in stage 02

The channel sequence is built by concatenating permutations of the four channels
(`02_working_memory.py:86`); if `n_trial` is not a multiple of 4, the tail is padded from
a fresh permutation, so the last few trials are not evenly balanced. Harmless for a long
run, misleading for a short one — and gate 0 (samples per class) will tell you if it went
wrong.

---

## 11. Stage 05 needs a module that is not here

`05_prototype.py:11` loads `tools/_dms_run.py` and subclasses `M.TaskNet` from it. The
file is not published, so the stage exits with an explanation. Everything before that
line is readable, and `build_proto()` (`:356`) shows the intended call surface — but the
dynamics live in the missing base, so reading the stage file alone will not tell you what
the network does.

See [`01_usage.md`](01_usage.md) → 05_prototype.py for the intended call surface, and
[`04_extend.md`](04_extend.md) §6(b) for the two honest ways to get the base back.
