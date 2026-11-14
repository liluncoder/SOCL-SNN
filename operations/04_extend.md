# 04 — Extending the code

How to add a stage, an arm, a knob, or a driver without breaking the pipeline. Every
structural claim here is verifiable in the source; line numbers refer to this repository.

---

## 1. The shape you are extending

```
01  Network        cells, synapses, energy, development, pruning
02  MemNet         + slot pools A/B, injection, hold/decay, WTA
03  ActNet         + action groups, frozen readout pathway
04  TaskNet        + stimulus rounds, reward write, probe scoring
05  ProtoNet       + modulatory drive, feedback   (needs an unpublished base)
```

Confirm with:

```bash
grep -n "^class " 0*.py
# 01_substrate.py:156:class Network:
# 02_working_memory.py:69:class MemNet(dev6.Network):
# 03_memory_driven_action.py:45:class ActNet(m1.MemNet):
# 04_task_environment.py:66:class TaskNet(m2.ActNet):
# 05_prototype.py:39:class ProtoNet(Base):
```

Each stage is one file that subclasses the previous one and adds *one* mechanism. The
discipline that makes the chain useful: a stage does not re-implement what it inherits,
and it does not edit the file it inherits from. If you need to change inherited behaviour,
add a config key with a default that reproduces the old behaviour exactly, and register
the change.

---

## 2. Adding a stage

1. **Create the file** with the next number and a snake_case name:
   `06_your_stage.py`.
2. **Load the predecessor by filename**, following the existing pattern exactly:

   ```python
   import importlib.util, os, sys
   _HERE = os.path.dirname(os.path.abspath(__file__))

   def _load(fn, name):
       p = os.path.join(_HERE, fn)
       spec = importlib.util.spec_from_file_location(name, p)
       m = importlib.util.module_from_spec(spec)
       sys.modules[name] = m
       spec.loader.exec_module(m)
       return m

   prev = _load("04_task_environment.py", "task4")
   ```

3. **Subclass and add the mechanism.** Keep the addition to one mechanism. Override the
   smallest method that has to change; do not copy a method to edit two lines in it —
   that is how a chain forks into two model definitions that silently disagree.
4. **Add `cfg` keys, not new globals.** The base merges config dicts (`_merge` in stage
   01); a new parameter should be a key with a default. Underscore-prefixed keys
   (`cfg['_p8_w']`, `cfg['_dms']`) are how stage 04 passes switches that are read deep in
   the run loop — follow that pattern if your parameter has to reach the inner loop.
5. **Add a CLI path and a smoke mode.** `--help` should list your knobs, and a smoke
   mode should assert that fields exist and the mechanism does not collapse, then print
   that it makes no claim. Every stage in this repository does this; it is what makes the
   chain usable by someone who did not write it.

**Invariant:** after adding a stage, `python <file> --help` must load the *whole chain*
without error. Because importing executes the upstream files, `--help` is a real
integration test.

---

## 3. Adding an arm, and driving it

An arm is a string plus the branches where behaviour must differ. In stage 04:

- the list: `ARMS` at `:51`;
- the constructor takes it: `build(..., arm=...)` at `:647`, stored as `self.arm011` at `:98`;
- the branches read it at `:239`–`:301` (reward routing) and `:456`–`:468` (write checks).

To add an arm: append the string to `ARMS`, add the branch where the intervention differs,
and add a **control arm that should null it**. An arm without a null is not an arm — it
is a different experiment.

To *run* an arm you have to drive `build()` yourself, because the CLI hard-codes
`task_off`. The three calls the CLI itself makes are:

```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("t", "04_task_environment.py")
t = importlib.util.module_from_spec(spec); sys.modules["t"] = t; spec.loader.exec_module(t)

net = t.build(seed=51, arm="local", n_trial=40, round_ms=200, p_safe=0.5)
t._run(net, 200 * 320 + 50)          # horizon is in ms
acc, n = net.acc_probe()             # returns (accuracy, scored rounds)
```

★ `_run` and `acc_probe` are internal names; a driver built on them is pinned to this
file's shape. That is acceptable for an experiment driver — but pin the commit, and put
the commit hash in your run record.

★ For stages 02 and 03 the cheapest template for a driver is the `mode_*` functions in
the same file. They show, in working code, how to instantiate the class, run the trials,
and pull the summary statistic. Copy one and change what you read.

---

## 4. Adding a knob without breaking the old runs

1. **Default off / default old value.** A new switch must reproduce the previous
   behaviour bit-for-bit when untouched.
2. **Verify that.** Same seed, same flags, new code ⇒ identical weight digest. If the
   digest moves, your "inert" switch is not inert.
3. **Add a manipulation check.** Before trusting any result from the knob, turn it to an
   extreme and confirm a quantity you can compute independently moves. A knob that is not
   connected to anything produces a beautiful, meaningless null.
4. **Record the condition in the run.** `--freeze-w`, `p_safe`, `eng_scale_mode` and
   friends change what the same accuracy means.

---

## 5. Invariants

1. **Filenames are the interface.** The chain resolves literal names. Grep before renaming.
2. **Do not edit the criteria functions to make a run pass.** `dev_criteria()` and
   `print_criteria()` (`01_substrate.py:1709`, `:1742`) are the instrument. If the
   instrument is wrong, add a second one beside it and report both.
3. **Keep the frozen pathway frozen.** The stimulus→choice path goes through `extra_I`,
   which STDP, normalisation and pruning never touch. Making it plastic changes what the
   baseline means; if you do it, register it.
4. **Keep `infra` edges protected if you want to measure their share.** 128 carrier pairs
   are excluded from pruning (`04_task_environment.py:218`, generated at `:55`). Any
   statement about their weight share depends on that protection.
5. **Determinism at fixed seed.** Same seed + same flags ⇒ same digest. Diagnostics must
   not consume randomness.
6. **Gate 0 before any readout.** ≥5 samples per class, with the count printed.
7. **One mechanism per stage, one change per round.** The chain is only readable because
   each step adds one thing.

---

## 6. What this tree is missing, and what to do

**a) A multi-seed replication harness.** Nothing here loops seeds per arm and emits a
paired Δ. Every stage prints per-arm summaries for the seeds you hand it, so the loop is
short — but it does not exist, and each round of work needs it:

```text
for arm in arms:
    for seed in seeds:
        run stage --arms $arm --seeds $seed --log logs/$arm-$seed.log
        parse the summary line
report: per-seed Δ, sign count, mean, SD of Δ, mean/SD, MDES
```

Parsing the printed summary is fine; do not re-derive statistics from screenshots.

**b) `tools/_dms_run.py`.** Required by stage 05, not published (2687 lines in the
private tree). Two honest routes: ask the author for the file and drop it in `tools/`
with that exact name, or reimplement the `TaskNet` surface that `ProtoNet` overrides —
which means rebuilding the venue, and the numbers will not match anything.

**c) A per-subset weight report.** Net change over the whole weight vector and net change
over the subset a mechanism can actually reach are different numbers with different
denominators, and the difference between them is large. If your question is about
plasticity, report both, labelled by denominator. Computing them is a few lines over the
weight vector and a boolean mask.

---

## 7. Before you call a stage finished

- `python <stage>.py --help` loads the whole chain.
- A smoke mode exists and prints its own no-claim disclaimer.
- The new behaviour is reachable from the config, not only from the code path you
  happened to write.
- Every new assertion has been made to fail once, on purpose.
- The run record names the command, the seed set, the condition, and the commit.
