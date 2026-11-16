"""Paired arm runner at the gate-0 venue, with a selectable credit mode.

Same protocol as before (seed-paired, learn/probe schedule, window aligned to the marker),
but the third factor can be read either at the event (historical) or at the decision (the
fix validated by `credit_delivery_check.py`).

  python paired_arms.py --seeds first8 --arms task_off,local --credit-at decision \
      --w-p8 0.01 --trials 12 --out ../../../.workbuddy/runs/r81.jsonl

Rows already present in --out are skipped, so a killed run can be resumed.
"""
import argparse
import importlib.util
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PIPE = os.path.join(ROOT, "legacy", "pipeline_v1", "04_task_environment.py")
spec = importlib.util.spec_from_file_location("t", PIPE)
t = importlib.util.module_from_spec(spec)
sys.modules["t"] = t
spec.loader.exec_module(t)


def _seeds(s):
    if s == "first8":
        return [411 + 10 * i for i in range(8)]
    if s == "first15":
        return [411 + 10 * i for i in range(15)]
    return [int(x) for x in s.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w-p8", default="0.01")
    ap.add_argument("--arms", default="task_off,local")
    ap.add_argument("--seeds", default="first8")
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--credit-at", default="event", choices=["event", "decision"])
    ap.add_argument("--win", default="20,70")
    ap.add_argument("--p-safe", type=float, default=0.5)
    ap.add_argument("--out", default=os.path.join(ROOT, ".workbuddy", "runs", "r81.jsonl"))
    a = ap.parse_args()

    ws = [float(x) for x in a.w_p8.split(",") if x.strip()]
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    seeds = _seeds(a.seeds)
    w0, w1 = [float(x) for x in a.win.split(",")]

    done = set()
    if os.path.exists(a.out):
        for line in open(a.out, encoding="utf-8"):
            try:
                r = json.loads(line)
                done.add((r["arm"], r["seed"], r["w_p8"], r["credit_at"]))
            except Exception:
                pass

    t0 = time.time()
    total = len(ws) * len(arms) * len(seeds)
    k = 0
    for w in ws:
        for arm in arms:
            for seed in seeds:
                k += 1
                if (arm, seed, w, a.credit_at) in done:
                    continue
                net = t.build(seed=seed, arm=arm, w_p8=w, n_trial=a.trials,
                              round_ms=200.0, p_safe=a.p_safe, win_t0=w0, win_t1=w1,
                              credit_at=a.credit_at)
                w_before = np.asarray(net.S["ee"]["w"], float).copy()
                t._run(net, 200.0 * a.trials * 8 + 50.0, sweep=False)
                dv = np.abs(np.asarray(net.S["ee"]["w"], float) - w_before)
                mcar = getattr(net, "_p8_mask", None)
                if mcar is not None and mcar.any():
                    dw_car = float(dv[mcar].sum())
                    dw_non = float(dv[~mcar].sum())
                else:
                    dw_car, dw_non = float("nan"), float("nan")
                acc, n = net.acc_probe()
                pr = [x for x in net._rounds if x["phase"] == "probe"]
                kk = max(1, len(pr) // 3)
                head = (sum(1 for x in pr[:kk] if x["correct"]) / float(kk)) if kk else float("nan")
                tail = (sum(1 for x in pr[-kk:] if x["correct"]) / float(kk)) if kk else float("nan")
                row = dict(arm=arm, seed=seed, w_p8=w, credit_at=a.credit_at,
                           acc=round(float(acc), 4), n=int(n), trials=a.trials,
                           head=round(float(head), 4), tail=round(float(tail), 4),
                           dw=float(net.dw_abs_cum), dw_car=dw_car, dw_non=dw_non,
                           credit_applied=float(getattr(net, "credit_applied", 0.0)))
                with open(a.out, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
                print("[%2d/%d %5.0fs] %-9s %-8s w=%-6g seed=%d acc=%.3f "
                      "head=%.3f tail=%.3f dw=%.3g car=%.3g credit=%.3g" %
                      (k, total, time.time() - t0, arm, a.credit_at, w, seed, acc,
                       head, tail, float(net.dw_abs_cum), dw_car,
                       float(getattr(net, "credit_applied", 0.0))), flush=True)


if __name__ == "__main__":
    main()
