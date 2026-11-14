# -*- coding: utf-8 -*-
"""Compatibility layer for the prototype stage.

`05_prototype.py` loads this file and subclasses `M.TaskNet` from it. In the original
(private) working tree this file was a ~2700-line batch driver: sharding, per-round cell
dumps, collectors and statistics, with output paths tied to that tree.

**None of that touches the model.** The original did exactly three things that
`05_prototype.py` depends on:

    M = load("011_v2 任务环境.py", "_dms_011")   # the task module itself
    md5_of(weights)                              # weight-vector fingerprint
    ...plus batch orchestration, which the stage never calls

So the model-facing surface is a `load()` of the task module and one hash function. This
file reproduces that surface against `04_task_environment.py`. It is a rename, not a
reimplementation: every class and function the prototype uses comes from stage 04, so
behaviour is identical to the original driver's, minus the batch tooling.

If you want to run batches of your own, write your own driver on top of `M.build()` —
see `operations/04_extend.md`. Do not add batch code here; this file exists so that
`05_prototype.py` can be read and run, and it should stay small enough to audit.
"""
import hashlib
import importlib.util
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(fn, name):
    """Load a stage by filename, the way every stage in this repository chains."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, fn))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# The task module. Same object the original loaded; only the filename differs.
M = load("04_task_environment.py", "_dms_011")


def md5_of(a):
    """Short fingerprint of a weight vector, used to prove two arms differ."""
    return hashlib.md5(np.ascontiguousarray(np.asarray(a, float)).tobytes()).hexdigest()[:16]


# Convenience aliases, so a driver can do `from _dms_run import build, TaskNet`.
build = M.build
TaskNet = M.TaskNet
