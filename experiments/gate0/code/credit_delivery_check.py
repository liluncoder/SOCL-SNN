"""Instrument check for `credit.at` — the switch that moves the third factor to the
decision.

Five checks, each of which can fail:

  C1  inert when off       same fixed configuration, `credit.at='event'`: the ee weight
                           fingerprint must equal the recorded 830136398b09fbed
  C2  no write between decisions   with 'decision', weights may only change at the
                           decision; the eligibility step must not touch them
  C3  arrival              on a learned round with arm='local', some weight must move
  C4  confinement          on that round, the change on every edge whose postsynaptic
                           cell is outside the chosen group must be exactly zero
  C5  null arms            probe rounds and arm='task_off' must move nothing at all

C4 is the one that makes the switch trustworthy: it says the credit went to the group the
outcome named, not to the network at large. C3 alone would pass for any perturbation.

Usage:  python credit_delivery_check.py [--seed 411] [--w-p8 0.05]
"""
import argparse
import hashlib
import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PIPE = os.path.join(ROOT, "legacy", "pipeline_v1")
RECORDED_FP = "830136398b09fbed"


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(PIPE, fn))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


s1 = load("s1_check", "01_substrate.py")
t = load("t_check", "04_task_environment.py")

fails = []


def chk(name, ok, detail=""):
    print("  %s %s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        fails.append(name)


def fingerprint():
    cfg = s1._merge(s1.copy.deepcopy(s1.DEFAULT_CFG), {"n_units": 6, "seed": 7})
    net = s1.Network(cfg)
    net.run_until(4000.0)
    w = net.S["ee"]["w"]
    return hashlib.md5(w.tobytes()).hexdigest()[:16]


def run_rounds(net, n_round):
    """Step ms by ms, recording the weight change at each decision."""
    prev_dec = -1
    stats = []
    act_all = np.concatenate([net.ACT[0], net.ACT[1]])
    post = net.S["ee"]["post"]
    while net._r_idx < n_round:
        w0 = np.asarray(net.S["ee"]["w"], float).copy()
        net.step(1)
        if net._decided and net._r_idx != prev_dec:
            prev_dec = net._r_idx
            rec = [r for r in net._rounds if r["i"] == net._r_idx][0]
            w1 = np.asarray(net.S["ee"]["w"], float).copy()
            d = w1 - w0
            grp = net.ACT[rec["winner"]].tolist()
            inside = np.isin(post, grp)
            outside = np.isin(post, [c for c in act_all.tolist() if c not in set(grp)])
            stats.append(dict(i=rec["i"], phase=rec["phase"], correct=rec["correct"],
                              credit=float(rec["round_credit"]),
                              inside=float(np.abs(d[inside]).sum()) if inside.any() else 0.0,
                              outside=float(np.abs(d[outside]).sum()) if outside.any() else 0.0,
                              total=float(np.abs(d).sum())))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=411)
    ap.add_argument("--w-p8", type=float, default=0.05)
    ap.add_argument("--rounds", type=int, default=8)
    a = ap.parse_args()

    print("C1 inertness")
    fp = fingerprint()
    chk("C1 weight fingerprint with credit.at=event", fp == RECORDED_FP,
        "got %s, recorded %s" % (fp, RECORDED_FP))

    for arm in ("local", "task_off"):
        print("C2-C5 arm=%s" % arm)
        net = t.build(seed=a.seed, arm=arm, w_p8=a.w_p8, n_trial=2, round_ms=200.0,
                      p_safe=0.5, win_t0=20.0, win_t1=70.0, credit_at="decision")
        stats = run_rounds(net, a.rounds)
        # C2: after the last decision, weights must not move until the next decision
        moves = []
        prev = np.asarray(net.S["ee"]["w"], float).copy()
        for _ in range(3):
            net.step(1)
            cur = np.asarray(net.S["ee"]["w"], float).copy()
            moves.append(float(np.abs(cur - prev).sum()))
            prev = cur
        nondec = [s for s in stats if s["phase"] == "probe"]
        learn = [s for s in stats if s["phase"] == "learn"]
        print("    %3s %6s %7s %6s | %9s %9s %9s" %
              ("r", "phase", "correct", "credit", "|dw| in", "|dw| out", "|dw| all"))
        for s in stats:
            print("    %3d %6s %7s %6.3f | %9.3e %9.3e %9.3e" %
                  (s["i"], s["phase"], str(s["correct"]), s["credit"],
                   s["inside"], s["outside"], s["total"]))
        chk("C2 no write between decisions", max(moves) == 0.0,
            "3 ms after the decision: %s" % ["%.1e" % m for m in moves])
        if arm == "local":
            nz = [s for s in learn if s["credit"] > 0.0]
            chk("C3 arrival on a learned round", len(nz) > 0 and max(s["total"] for s in nz) > 0.0,
                "%d/%d learned rounds moved weight" % (len(nz), len(learn)))
            chk("C4 credit confined to the chosen group",
                all(s["outside"] == 0.0 for s in learn),
                "max |dw| outside = %.3e" % (max([s["outside"] for s in learn] or [0.0])))
            chk("C5 probe rounds write nothing",
                all(s["total"] == 0.0 for s in nondec),
                "max |dw| on a probe round = %.3e" % (max([s["total"] for s in nondec] or [0.0])))
        else:
            chk("C3 null arm writes nothing", all(s["total"] == 0.0 for s in stats),
                "max |dw| = %.3e" % max([s["total"] for s in stats] or [0.0]))

    print("")
    print("RESULT: %s" % ("all checks passed" if not fails else "FAILED: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
