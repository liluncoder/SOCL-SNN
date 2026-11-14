# 01 — Using each stage

Per stage: what it computes, how to call it, what the output looks like, what it costs,
and whether it runs from a clean checkout.

| Stage | Runs clean? | Note |
| --- | --- | --- |
| 01 substrate | yes | self-contained |
| 02 working memory | yes | |
| 03 memory → action | yes | |
| 04 task | interface only | the five arms are in `build()`, but the CLI hard-codes `task_off` |
| 05 prototype | no | needs `tools/_dms_run.py`, which is not published |

Cost rule of thumb at default sizes: one simulated second costs 3–4 s of wall clock. A
30 s simulation is ~2 min; a 3-arm criteria sweep at 30 s is ~5–6 min.

---

## 01_substrate.py

**What it computes.** A network of Izhikevich-type excitatory and inhibitory cells on a
fixed bank of slots. Each cell has an energy `E`; income is a fixed budget per station
per millisecond shared out by activation, and cost is charged per spike, per unit of
upkeep, and per outgoing synapse. Cells below the death threshold are marked dead, cells
above the division threshold split into a free slot on the same station, and synapses
that are rarely used are pruned. Synapses carry conductance kinetics with delays, and
weights are updated by a three-factor rule.

**Structure.** `class Network` (`:156`). All parameters live in `DEFAULT_CFG` (`:22`),
grouped by mechanism: `n_units` / `n_E` / `n_I` / `slot_grow`, `dt`, `seed`, `K` and
`w_ref` (in-degree and reference weights per `ee` / `ei` / `ie` / `ii`), `tau` and
`E_rev` (AMPA / GABA), `lr` (learning rate, topology, distance constant), `drive`
(tonic current, noise), `bg` (background Poisson input), `stim`, `std` (short-term
depression), and `dev` (development: budget, per-spike cost, upkeep, per-synapse cost,
death and division thresholds, pruning).

**Run it.**

```bash
python 01_substrate.py                      # interactive: count curve, birth/death, energy
python 01_substrate.py --headless           # same, no window
python 01_substrate.py --probe              # quick calibration
python 01_substrate.py --report             # development on / off, writes to report/
python 01_substrate.py --criteria           # five structural criteria, three arms
python 01_substrate.py --units 25 --ms 60000 --seed 11
```

Controls: `--nodev` (no birth or death — the previous stage's condition) and `--no-prune`
(no synaptic pruning). Overrides: `--units`, `--cells`, `--drive`, `--ms`.

**Output of `--criteria`.** Three blocks — A (everything on), B (plasticity off, delays
and death still on), C (plasticity on, normalisation off) — and for each one five
numbers with a pass/fail mark against a threshold:

| # | Quantity | Function |
| --- | --- | --- |
| ① | peak separation of the long-range weight distribution | `dev_criteria()` (`:1709`), using `peak_gap()` |
| ② | relative change of the mean long-range weight | `dev_criteria()` |
| ③ | modularity Q | `modularity_report()` |
| ④ | ratio of mean long-range edge distance to its initial value | `dev_criteria()` |
| ⑤ | near-minus-far firing-rate gap | `dev_criteria()` |

★ **Read ① twice.** It is printed as a raw separation *and* as a separation rescaled by
the model's weight ceiling (`w_max = 0.40`). The raw threshold is in absolute weight
units, which is only meaningful if your weight range is of order 1. Check which number
your threshold was written against before calling it a pass.

★ **③ depends on a minimum edge count.** `Q` is returned as `nan` unless the binarised
correlation graph has at least 20 edges, so `nan` means "the graph is too sparse at this
network size", not "there is no structure". The number of communities is printed next to
it; check the edge count before interpreting.

The tally prints "n/4 pass, ≥2 counts as a pass" — that rule is a convention, not a
statistical test. See [02_experiments.md](02_experiments.md) for what to do instead.

---

## 02_working_memory.py

**What it computes.** A delayed matching task on top of the substrate: a cue is injected
into one of four channels, then removed; after a delay the network must still carry
*which slot* and *which channel*. Four channels, four slots per pool, two pools on
separate stations, plus a binary snapshot mechanism that holds the previous trial's code.

**Structure.** `class MemNet(dev6.Network)` (`:69`). Layout constants at the top of the
file: 25 units, 8 injection cells per channel, 6 slots per pool per channel, 4 channels;
pool A on station 0, pool B on station 1. Timing constants: stimulus 30 ms, reset
250 ms, decision period 100 ms, inter-trial interval 900 ms, readout ticks
`K_TICKS = (2, 3, 5)`. `MEM_CFG` (`:58`) turns development and STDP off and decouples
delays, so the stage tests memory rather than rewiring.

**Run it.**

```bash
python 02_working_memory.py --smoke                     # 5 s, mechanism sanity only
python 02_working_memory.py --calib                     # per-slot spike counts, 100 ms bins
python 02_working_memory.py --trace-h                   # h_A convergence vs readout tick
python 02_working_memory.py --seeds 51,61 --arms two_pool,snap_off,sham_B --trials 40
```

Arms: `two_pool` (both pools), `snap_off` (no snapshot), `sham_B` (pool B present but
not wired to the readout) — the last two are the controls. `assert arm in ARMS` guards
the constructor.

Overrides worth knowing: `--w-in`, `--w-sub`, `--w-weak`, `--w-rec`, `--w-lat` (slot
self-excitation and lateral inhibition), `--tau-hold`, `--alpha`, `--h-up`, `--iti`,
`--k-ticks`, `--max-retry`.

**Output.** A per-arm table with balanced accuracy at the current readout tick (`acc_cur`)
and at the previous trial's code (`acc_prev`), the shuffled-label null bound, gate-0
statistics (test samples per class), and a per-arm mean. `--diag` prints per-trial slot
spike counts; `--trace-h` prints the convergence of `h_A` by readout tick, which is the
fastest way to tell "the slot never fired" from "the wrong slot fired".

---

## 03_memory_driven_action.py

**What it computes.** Adds one action group per channel and asks which one wins, given
the memory state. The pathway from memory to action is a frozen connection (it does not
see STDP, normalisation or pruning), so the stage can separate "memory drives the
decision" from "plasticity explains the decision".

**Structure.** `class ActNet(m1.MemNet)` (`:45`). Action groups sit on station 2, four
groups of 8 cells; default pathway weight `W_ACT = 10.0`.

**Run it.**

```bash
python 03_memory_driven_action.py --smoke
python 03_memory_driven_action.py --calib-wact          # sweep W_ACT: can the group be read at all?
python 03_memory_driven_action.py --seeds 51 --arms memory,no_slot,freeze_off --trials 40 --freeze-w 1
```

Arms: `memory`, `no_slot` (cannot use the memory), `freeze_off` (cannot use the frozen
pathway). `--freeze-w 1` (default) turns STDP off on the pathway; `--freeze-w 0` leaves
it on so you can measure how much of the effect is plasticity.

**Output.** A summary table per arm × seed with action accuracy and the shuffled-label
baseline, plus two mechanism self-checks printed in the smoke and calibration modes:
action-group mean rate (should be low relative to bare cells) and single-hot hit rate.
★ The self-check thresholds are calibrated under one condition; if you change
`--freeze-w`, recalibrate them before quoting them.

---

## 04_task_environment.py

**What it computes.** A closed-loop task in which a cue is presented, the choice is read
out several rounds later, and a scalar reward is written into the energy field of the
chosen group. Five arms differ in where that reward is allowed to act, which is how the
locality of the modulatory signal is tested.

**Structure.** `class TaskNet(m2.ActNet)` (`:66`). Task constants at the top: round
200 ms, stimulus at t=20 ms for 30 ms, scoring window 60–160 ms, 4 learning rounds and 4
probe rounds per trial, 40 trials, marker→choice mapping `{2: 1, 3: 0}`. Arms:
`ARMS = ('task_off', 'local', 'global_scalar', 'global_center', 'reward_zero')` (`:51`).

**The real entry point is `build()`** (`:647`), not the CLI:

```python
build(seed=51, arm='local', w_stim=2.0, w_p8=0.05, r_star=0.5, p_safe=0.5,
      use_marker=True, n_trial=40, round_ms=200, trace=False,
      choice_mode='hact', win_t0=60.0, win_t1=160.0,
      eng_scale_mode='legacy', eng_scale_scope='global',
      newpath_w=0.0, marker_kill=False, direct_w=1.0,
      credit_mode='none', readout_mode='count', ro_drive=False, mark_gain=1.0,
      dump_x=False, dms=0, g_mem=1.0, h_decay=0.0, thr_margin=0.0)
```

Those keywords are the whole experimental surface of this stage: carrier weight (`w_p8`),
reward scale (`r_star`), safe-side probability (`p_safe`), scoring window, readout mode,
credit mode, and the switches that disable individual pathways. Anything you want to vary
should be varied here.

**What the CLI gives you.**

```bash
python 04_task_environment.py --smoke        # 12 interface assertions, then it stops
python 04_task_environment.py --p8-probe     # is there a bypass when no carrier is supplied?
python 04_task_environment.py --calib-task   # is the task learnable at this setting?
python 04_task_environment.py --calib-p8     # scan w_p8: is there a window that is neither solved nor unsolvable?
python 04_task_environment.py --rstar 0.5 --p-safe 0.5 --round-ms 200 --seed 51
```

★ **Every CLI call site passes `arm='task_off'`** (`:932`, `:1034`). If you want a
different arm, call `build()` yourself and drive it — see
[04_extend.md](04_extend.md) §3 for the three calls such a driver needs.

**Output.** `--smoke` prints a numbered list of assertions with ✅/❌ and a final tally,
then states explicitly that it makes no scientific claim. The calibration modes print a
sweep table with the chosen working point. A driver you write around `build()` gets
whatever you decide to read: `net.acc_probe()` returns `(accuracy, n)`.

---

## 05_prototype.py

**What it computes.** A prototype layer on top of the task: a modulatory drive, a
feedback projection, and a target sequence, with the readout driven by a separate
framework base class.

**Status.** It loads `tools/_dms_run.py` at `:11` and subclasses `M.TaskNet` from it.
That module is part of the author's private working tree and is **not published**. The
script detects this and exits with an explanation rather than a traceback.

**Structure, if you want to rebuild the base.** `class ProtoNet(Base)` (`:39`), with
`p_init()` taking the prototype's own knobs: `n_mod=25` modules, `amp=10`, `n_hot=8`,
`stim_ms=70`, `norm_scale=90`, `rho=0.85`, `sigma=0.15`, `alpha=0.5`, `beta=0.05`, plus
switches for feedback projection, modulation dimension, feedback mode, injection mode
and probe routing.

★ Build your driver on `build_proto(...)` rather than on `ProtoNet` directly: the
constructor signature is the stable surface, and the base class is what you would have
to reimplement. See [03_traps.md](03_traps.md) §5 for a parameter that silently never
reached the venue.
