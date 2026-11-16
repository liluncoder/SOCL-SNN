"""Paired summary of the arm runs, one block per credit mode.

Every number that appears in a summary must be produced by this script. It reports the
per-arm mean and SD, the seed-paired difference against the null arm, its t statistic, and
the minimum detectable effect at the sample size actually used (k = 2.8, the same constant
as the earlier rounds). It deliberately prints no verdict: the verdict belongs to a
preregistration, and these runs have none.

Usage:
  python paired_summary.py --in ../../../.workbuddy/runs/r81_credit.jsonl --null task_off
"""
import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--null", default="task_off")
    ap.add_argument("--k", type=float, default=2.8, help="MDES constant, as in earlier rounds")
    a = ap.parse_args()

    rows = load(a.inp)
    by = defaultdict(list)
    for r in rows:
        by[(r.get("credit_at", "event"), r["arm"])].append(r)

    print("file: %s" % os.path.basename(a.inp))
    print("%-9s %-9s %3s %8s %8s %8s %8s" %
          ("credit", "arm", "n", "acc", "sd", "dw_car", "credit_applied"))
    for (mode, arm), rs in sorted(by.items()):
        acc = np.array([r["acc"] for r in rs], float)
        print("%-9s %-9s %3d %8.3f %8.3f %8.1f %8.2f" %
              (mode, arm, acc.size, acc.mean(), acc.std(ddof=1) if acc.size > 1 else 0.0,
               np.mean([r["dw_car"] for r in rs]),
               np.mean([r.get("credit_applied", 0.0) for r in rs])))

    print("")
    print("seed-paired difference against %r" % a.null)
    print("%-9s %-9s %3s %9s %9s %8s %9s %9s" %
          ("credit", "arm", "n", "mean_d", "sd_d", "t", "mdes", "signs +/-/="))
    for mode in sorted({m for (m, _) in by}):
        null = {r["seed"]: r["acc"] for r in by.get((mode, a.null), [])}
        for arm in sorted({x for (m, x) in by if m == mode}):
            if arm == a.null:
                continue
            rs = [r for r in by[(mode, arm)] if r["seed"] in null]
            if not rs:
                continue
            d = np.array([r["acc"] - null[r["seed"]] for r in rs], float)
            n = d.size
            sd = d.std(ddof=1) if n > 1 else 0.0
            se = sd / np.sqrt(n) if n > 1 else float("nan")
            t = d.mean() / se if se and np.isfinite(se) and se > 0 else float("nan")
            mdes = a.k * se if se and np.isfinite(se) else float("nan")
            signs = "%d/%d/%d" % (int(np.sum(d > 0)), int(np.sum(d < 0)), int(np.sum(d == 0)))
            print("%-9s %-9s %3d %9.4f %9.4f %8.2f %9.4f %9s" %
                  (mode, arm, n, d.mean(), sd, t, mdes, signs))

    print("")
    print("mdes = k * se with k = %.1f; an effect smaller than this design could not have" % a.k)
    print("been detected, which is not the same as the effect being absent.")


if __name__ == "__main__":
    main()
