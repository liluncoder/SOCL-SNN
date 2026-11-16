"""Instrument diagnostic: when does the third factor reach the events it multiplies?

The rule in `_stdp_step` reads the reward *at the event*: `R = _reward_of(postsynaptic
cell)`. The decision that scores a trial runs at `win_t1` (70 ms by default), after the
stimulus window. So:

  * every stimulus-driven event before 70 ms is scaled by the reward written at the end of
    the *previous* round;
  * every event after 70 ms is scaled by this round's reward but happened after the readout,
    so it did not contribute to the outcome it is credited with.

This script measures both halves and the signed reward the events actually see, under the
two available energy frames. It is a diagnostic, not a gate: it decides nothing about a
mechanism, it says whether the arm delivers a reward at all.

Usage:  python instrument_reward_delivery.py [--arm local] [--w-p8 0.05] [--seed 411]
"""
import argparse
import importlib.util
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
PIPE = os.path.join(ROOT, "legacy", "pipeline_v1", "04_task_environment.py")
spec = importlib.util.spec_from_file_location("t", PIPE)
t = importlib.util.module_from_spec(spec)
sys.modules["t"] = t
spec.loader.exec_module(t)


def measure(arm, w_p8, seed, n_trial, scope):
    net = t.build(seed=seed, arm=arm, w_p8=w_p8, n_trial=n_trial, round_ms=200.0,
                  p_safe=0.5, win_t0=20.0, win_t1=70.0, eng_scale_scope=scope)
    act = np.concatenate([net.ACT[0], net.ACT[1]])
    marker = np.concatenate([net.INJ[2], net.INJ[3]])
    trace = {}
    spikes = {}
    # an edge-event is one edge touched by one spike: a marker spike touches 8 carrier
    # edges, an ACT spike touches 8 carrier in-edges (p8_pairs tiles 8x8 per channel)
    edge_events = {"pre_before": 0, "pre_after": 0, "post_before": 0, "post_after": 0}
    while net.t < 200.0 * n_trial * 8 + 50.0:
        before = net.n_spkE.copy()
        net.step(1)
        k = net._r_idx
        if k < 0:
            continue
        rel = net.t - 1.0 - net._r_t0
        if 0.0 <= rel < 200.0:
            trace.setdefault(k, []).append(
                (rel, float(np.mean(net._reward_of(net.ACT[0]))),
                 float(np.mean(net._reward_of(net.ACT[1])))))
            d = net.n_spkE - before
            if d[act].any():
                spikes.setdefault(k, []).append((rel, int(d[act].sum())))
            early = rel <= 70.0
            edge_events["pre_before" if early else "pre_after"] += 8 * int(d[marker].sum())
            edge_events["post_before" if early else "post_after"] += 8 * int(d[act].sum())
    return net, trace, spikes, edge_events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="local")
    ap.add_argument("--w-p8", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=411)
    ap.add_argument("--trials", type=int, default=3)
    a = ap.parse_args()

    for scope in ("global", "act"):
        net, trace, spikes, ev = measure(a.arm, a.w_p8, a.seed, a.trials, scope)
        rounds = net._rounds
        pre = sum(n for k in spikes for (tr, n) in spikes[k] if tr <= 70.0)
        post = sum(n for k in spikes for (tr, n) in spikes[k] if tr > 70.0)
        tot_ev = sum(ev.values())
        pre_ev = ev["pre_before"] + ev["post_before"]
        print("=" * 100)
        print("scope=%-6s arm=%-9s w_p8=%-5g seed=%d   acc=%s" %
              (scope, a.arm, a.w_p8, a.seed, net.acc_probe()))
        print("  ACT spikes: %d before the write (%.1f%%), %d after it (%.1f%%)"
              % (pre, 100.0 * pre / max(1, pre + post),
                 post, 100.0 * post / max(1, pre + post)))
        print("  carrier edge-events: %d before the write (%.1f%% of %d); "
              "pre-side %d, post-side %d"
              % (pre_ev, 100.0 * pre_ev / max(1, tot_ev), tot_ev,
                 ev["pre_before"], ev["post_before"]))
        print("  For each round: mean R of each group over the stimulus window, and the")
        print("  outcome of the round that wrote it (the value the events actually see).")
        print("  %3s %5s %4s | %7s %7s | %7s %7s | %7s | %s" %
              ("r", "phase", "s", "R_a0", "R_a1", "win", "lose", "win-lose", "writer"))
        diffs = []
        for r in rounds:
            i = r["i"]
            seg = [x for x in trace.get(i, []) if 20.0 <= x[0] <= 70.0]
            if not seg:
                continue
            ra0 = float(np.mean([x[1] for x in seg]))
            ra1 = float(np.mean([x[2] for x in seg]))
            prev = [q for q in rounds if q["i"] == i - 1]
            if not prev:
                print("  %3d %5s %4d | %7.3f %7.3f | %7s %7s | %7s | (none)" %
                      (i, r["phase"], r["correct"], ra0, ra1, "-", "-", "-"))
                continue
            pw, pc = prev[0]["winner"], prev[0]["correct"]
            rw, rl = (ra0, ra1) if pw == 0 else (ra1, ra0)
            diffs.append(rw - rl)
            print("  %3d %5s %4d | %7.3f %7.3f | %7.3f %7.3f | %+7.3f | r%d s=%+d" %
                  (i, r["phase"], r["correct"], ra0, ra1, rw, rl, rw - rl,
                   i - 1, 1 if pc else -1))
        d = np.asarray(diffs, float)
        print("  mean(win - lose) over the window = %+.4f   |d|>0.05 in %d/%d rounds"
              % (d.mean() if d.size else float("nan"),
                 int(np.sum(np.abs(d) > 0.05)), d.size))
        ok = tot = 0
        for r in rounds:
            i = r["i"]
            seg = [x for x in trace.get(i, []) if 20.0 <= x[0] <= 70.0]
            prev = [q for q in rounds if q["i"] == i - 1]
            if not seg or not prev:
                continue
            ra0 = float(np.mean([x[1] for x in seg]))
            ra1 = float(np.mean([x[2] for x in seg]))
            pw, pc = prev[0]["winner"], prev[0]["correct"]
            rw, rl = (ra0, ra1) if pw == 0 else (ra1, ra0)
            want = +1 if pc else -1
            tot += 1
            ok += int(np.sign(rw - rl) == want)
        print("  the winner group has the larger reward in the intended direction: %d/%d"
              % (ok, tot))
        if pre + post:
            print("  VERDICT: %.1f%% of answer-path events precede the write, so they are"
                  " scaled by the previous round's outcome."
                  % (100.0 * pre / (pre + post)))


if __name__ == "__main__":
    main()
