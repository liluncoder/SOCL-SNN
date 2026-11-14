"""Regression: every pipeline stage must load, at the root and in the legacy snapshot.

Loading a stage executes the whole upstream chain (the stages import each other by literal
filename), so `--help` is a real integration test: if a filename, a relative path or the
loader's root resolution broke, this fails.

Runs with pytest, or directly:  python tests/regression/test_pipeline_loads.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STAGES = [
    "01_substrate.py",
    "02_working_memory.py",
    "03_memory_driven_action.py",
    "04_task_environment.py",
    "05_prototype.py",
]

TIMEOUT_S = 300


def _loads(script: Path) -> tuple[bool, str]:
    """True if the stage loads and prints its help without error."""
    if not script.exists():
        return False, "missing: %s" % script
    try:
        p = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(script.parent),
            capture_output=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout after %ds: %s" % (TIMEOUT_S, script)
    if p.returncode != 0:
        tail = (p.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-3:]
        return False, "exit %d: %s | %s" % (p.returncode, script, " / ".join(tail))
    return True, ""


def _check_dir(base: Path, label: str) -> list[str]:
    failures = []
    for name in STAGES:
        ok, why = _loads(base / name)
        if not ok:
            failures.append("[%s] %s" % (label, why))
    return failures


def test_stages_load_from_root():
    failures = _check_dir(ROOT, "root")
    assert not failures, "stages failed to load:\n" + "\n".join(failures)


def test_legacy_snapshot_loads():
    """The snapshot must be runnable on its own — its loader resolves relative to the file."""
    legacy = ROOT / "legacy" / "pipeline_v1"
    if not legacy.exists():
        return  # snapshot removed after migration; nothing to check
    failures = _check_dir(legacy, "legacy")
    assert not failures, "legacy stages failed to load:\n" + "\n".join(failures)


def test_loader_module_present():
    """Stage 05 needs tools/_dms_run.py beside the pipeline it loads."""
    for base in (ROOT, ROOT / "legacy" / "pipeline_v1"):
        dms = base / "tools" / "_dms_run.py"
        if base.exists() and (base / "05_prototype.py").exists():
            assert dms.exists(), "missing loader: %s" % dms


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS  %s" % name)
            except AssertionError as e:
                failed += 1
                print("FAIL  %s\n%s" % (name, e))
    print("\n%d failure(s)" % failed)
    sys.exit(1 if failed else 0)
