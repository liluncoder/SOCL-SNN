# legacy/pipeline_v1

A sequential prototype from the earlier phase of this project: energy-constrained spiking
networks, working memory, memory-driven action, reward-modulated learning.

**Status: historical snapshot.** These files are preserved as a research artifact. They are
not the current gate structure, and their results are not evidence for any gate on the
roadmap. They are kept runnable because several gate decisions were made against this
behaviour, and a baseline that cannot be re-run is not a baseline.

Run everything from this directory. Each stage resolves what it loads relative to its own
file, so the folder works as a unit wherever the repository sits.

## The five stages

```
01_substrate.py            Network      cells, synapses, energy, development, pruning
  └ 02_working_memory.py   MemNet       + slot pools, injection, hold/decay, WTA
      └ 03_memory_driven_action.py  ActNet  + action groups, frozen readout pathway
          └ 04_task_environment.py  TaskNet + stimulus rounds, reward write, scoring
              └ 05_prototype.py     ProtoNet + modulation and feedback
```

Each stage loads the previous one with `importlib` and a **literal filename**, then
subclasses it. `tools/_dms_run.py` is what stage 05 loads; it hands back the stage-04 module
and a weight-fingerprint helper.

★ There is a second `_dms_run.py` in this repository — the one at the root `tools/`
directory is the protocol-tools tree, not this loader. Same filename, different job. Always
read the path, not the name. The planned disambiguation is described in `tools/README.md`.

## Running

Requirements: Python 3.9+, NumPy. No GPU, no plotting library.

```bash
python 01_substrate.py --criteria --seed 11 --units 25 --ms 30000
python 01_substrate.py --nodev            # control: no birth or death
python 01_substrate.py --no-prune         # control: no synaptic pruning

python 02_working_memory.py --smoke
python 02_working_memory.py --trace-h --seeds 51
python 02_working_memory.py --seeds 51,61 --arms two_pool,snap_off,sham_B --trials 40

python 03_memory_driven_action.py --smoke
python 03_memory_driven_action.py --seeds 51 --arms memory,no_slot,freeze_off --freeze-w 1

python 04_task_environment.py --smoke      # interface assertions; makes no scientific claim
python 04_task_environment.py --calib-task

python 05_prototype.py -h
python 05_prototype.py --rounds 12                 # ~13 s
python 05_prototype.py --rounds 320 --mod-dim      # ~9 min
```

The stage-04 windows and the credit mode are chosen by the caller, not by the CLI. Always pass
`win_t0=20, win_t1=70` (the default 60–160 reads the response tail and inverts the answer) and
choose `credit_at` explicitly:

```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("t", "04_task_environment.py")
t = importlib.util.module_from_spec(spec); sys.modules["t"] = t; spec.loader.exec_module(t)
net = t.build(seed=411, arm="local", w_p8=0.01, n_trial=12,
              win_t0=20.0, win_t1=70.0, credit_at="decision")
t._run(net, 200.0 * 12 * 8 + 50.0)
print(net.acc_probe(), net.dw_abs_cum)
```

`credit_at='event'` is the historical behaviour and is kept for reproducibility;
`'decision'` is the rule actually described as three-factor (see trap 10).

Cost: one simulated second costs roughly 3–4 s of wall clock. Stage 05 costs about 1 s per
200 ms round.

Runs write to `report/`; both that and `slices/` are git-ignored.

## Traps in this code

Verified against the source; each one produces a number that looks fine.

1. **`norm_on = True` does not mean weights are normalised.** The normaliser is called only
   inside `_develop()`, which runs only when `dev.on` is set and `energy_only` is false.
   Stages 02 and 03 run with development off, so nothing is normalised there regardless of
   the flag.

2. **Distance and latency are coupled by default.** `delay.decouple` is `False`, so a
   long-range edge is also a slow edge. Any reading about spatial structure has a latency
   confound that points the same way as the hypothesis. Stage 02 sets `decouple: True`;
   stage 01 does not.

3. **The sampling window must fit inside the trial** (`k · DEC_PERIOD ≤ ITI − RESET_DUR`,
   asserted in stage 02). Do not remove the assertion: exceeding it reads the *next* trial's
   activity, silently.

4. **`Q` is `nan` below 20 binarised edges.** That is a sparsity limit of your `--units`, not
   an absence of structure.

5. **Stage 04's CLI only ever runs `arm='task_off'`.** All five arms exist in
   `build(..., arm=...)`; every command-line call site hard-codes `task_off`. Anything the
   CLI prints is a baseline, not a learning result.

6. **`--report` and `--criteria` write to fixed filenames** under `report/`. Two runs in
   parallel overwrite each other.

7. **Stage 05's `--mod-dim` gates the modulation path.** Without it, `R_abs*`, `inj_*`,
   `sc_med`, `wfb_*` are 0 or `NaN` by construction — set on an `else` branch, not a failure.

8. **`cfg['syn']` is shared between builds.** `task_cfg` hands the same nested dict to every
   network in a process, so mutating `net.syn_cfg` in place changes the next run too — measured
   as a geometric decay across seeds (dw 26 → 2.9 → 0.53 → 0.077) when a scale factor was
   applied per run. Rebind a copy before changing it.

9. **Do not add a plotting import at module level.** Importing stage 05 imports stage 01;
   a module-level `import matplotlib` would become a hard dependency of the whole chain.

10. **The reward a synapse sees is the previous trial's.** `_stdp_step` reads `_reward_of()`
   at the moment of each spike, but `_write_reward()` runs inside `_decide()`, at `win_t1` —
   after the stimulus window. So the events that decide a trial are scaled by the outcome of
   the trial before it, and the events that follow the decision are scaled by the outcome they
   did not cause. Measured at this venue: 42.5% of answer-pathway spikes precede the write.
   `task_off` is not a null learning arm for the same reason: it does not write a reward, but
   `_reward_of()` still returns the natural energy field, so it learns too. `credit.at='decision'`
   fixes the delivery (per-edge eligibility, applied at the decision); with it, `task_off` is
   exactly frozen.

11. **The default reward frame is saturated at the answer cells.** `eng_scale_scope='global'`
   normalises by the median and IQR of all 2500 cells, and the 16 answer cells sit far above
   that median. The write sets the winner to `median + s·r*·scale` (reads back exactly `+0.5`)
   while the untreated group stays clipped at `+1.0` — the winner is rewarded *less* than the
   loser. Measured over 23 rounds: the intended sign holds in 4/23, mean −0.040. With
   `eng_scale_scope='act'` it is 17/23 and +0.204.

## Extending it

- Subclass the last stage and add one mechanism. Do not copy a method to change two lines.
- Add config keys with defaults that reproduce the old behaviour exactly; new switches
  default off.
- Prove inertness with a weight fingerprint (same seed, unchanged hash), and prove arrival
  the same way (same seed, different arms, different hash).
- Keep an arm's control alongside it. An arm without a null is a different experiment.

See `docs/ARCHITECTURE.md` for where new code belongs, and `protocols/` for the rules a run
has to satisfy before its result counts.
