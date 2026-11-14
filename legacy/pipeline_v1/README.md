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

8. **Do not add a plotting import at module level.** Importing stage 05 imports stage 01;
   a module-level `import matplotlib` would become a hard dependency of the whole chain.

## Extending it

- Subclass the last stage and add one mechanism. Do not copy a method to change two lines.
- Add config keys with defaults that reproduce the old behaviour exactly; new switches
  default off.
- Prove inertness with a weight fingerprint (same seed, unchanged hash), and prove arrival
  the same way (same seed, different arms, different hash).
- Keep an arm's control alongside it. An arm without a null is a different experiment.

See `docs/ARCHITECTURE.md` for where new code belongs, and `protocols/` for the rules a run
has to satisfy before its result counts.
