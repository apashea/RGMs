"""
DEMO1 Product B — reset generated parity artifacts for a cold re-run.

Deletes under the DEMO1 fixture root (``tests/demo1/fixtures`` by default):

- all ``.mat``, ``.pkl``, and ``.json`` files (including manifest / trace JSON)
- empty subdirectories (e.g. ``fsl_backward_entry11_entry12_vb/``)

Also deletes registry checkpoint artifacts **outside** the fixture root:

- ``matlab_custom/XXX_12_compare_pdp_pkl_to_mat_output.txt`` (Validation 12 tee)
- ``matlab_custom/entry12_draw_index_audit_results.json`` (draw audit summary)
- ``visualizations/DEMO1_matlab_python_parity_12plot.png`` (Phase D shipped PNG)

Does **not** delete ``tests/demo1/python_native/``, oracle fixtures, timestamped
``AtariIII_12plot_*.png`` dev captures, or OPTIM1 paths.

Usage (from repo root)::

    python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity_reset.py
    python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity_reset.py --dry-run

See ``DEMO1.md`` §0 and §4.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Sequence

_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from tests.demo1.demo1_env import apply_shipped_fixture_env
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root, demo1_shipped_fixtures_dir
from tests.demo1.fixture_registry import all_artifacts

_FIXTURE_GLOBS = ("*.mat", "*.pkl", "*.json")
_DRAW_AUDIT_JSON = demo1_repo_root() / "matlab_custom" / "entry12_draw_index_audit_results.json"


def _registry_checkpoint_files(fix_root: Path) -> list[Path]:
    """Registry artifact paths outside ``fix_root`` (Phase C/D checkpoints)."""
    out: list[Path] = []
    for art in all_artifacts():
        p = art.path(fix_root)
        if art.relative_path.endswith("/"):
            continue
        try:
            p.resolve().relative_to(fix_root.resolve())
        except ValueError:
            if p.is_file():
                out.append(p)
    if _DRAW_AUDIT_JSON.is_file():
        out.append(_DRAW_AUDIT_JSON)
    return out


def _fixture_file_targets(fix_root: Path) -> list[Path]:
    if not fix_root.is_dir():
        return []
    out: list[Path] = []
    for pattern in _FIXTURE_GLOBS:
        out.extend(fix_root.rglob(pattern))
    return out


def _collect_targets(fix_root: Path) -> list[Path]:
    files = _fixture_file_targets(fix_root) + _registry_checkpoint_files(fix_root)
    return sorted({p.resolve() for p in files})


def _prune_empty_fixture_dirs(fix_root: Path) -> list[Path]:
    """Remove empty directories under the fixture root (bottom-up)."""
    if not fix_root.is_dir():
        return []
    removed: list[Path] = []
    for p in sorted(fix_root.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if not p.is_dir() or p == fix_root:
            continue
        try:
            next(p.iterdir())
        except StopIteration:
            p.rmdir()
            removed.append(p)
    return sorted(removed)


def reset_fixtures(*, dry_run: bool = False) -> int:
    import os

    had_override = bool(
        str(os.getenv("RGMS_DEMO1_FIXTURES_DIR", "")).strip()
        or str(os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", "")).strip()
    )
    if not had_override:
        apply_shipped_fixture_env()
    fix_root = demo1_fixtures_dir()
    fix_root.mkdir(parents=True, exist_ok=True)
    shipped = demo1_shipped_fixtures_dir()
    if fix_root != shipped.resolve():
        print(
            f"[DEMO1 reset] fixture root (env override): {fix_root}",
            file=sys.stderr,
        )
    else:
        print(f"[DEMO1 reset] fixture root: {fix_root}", file=sys.stderr)

    paths = _collect_targets(fix_root)
    if not paths:
        print("[DEMO1 reset] no parity artifact files to delete", file=sys.stderr)
    else:
        print(
            f"[DEMO1 reset] {'would delete' if dry_run else 'deleting'} {len(paths)} file(s)",
            file=sys.stderr,
        )
        for p in paths:
            try:
                rel = p.relative_to(fix_root)
            except ValueError:
                rel = p.relative_to(demo1_repo_root()) if p.is_relative_to(demo1_repo_root()) else p.name
            print(f"  {rel}", file=sys.stderr)
            if not dry_run:
                p.unlink()

    if not dry_run:
        removed_dirs = _prune_empty_fixture_dirs(fix_root)
        for d in removed_dirs:
            try:
                rel = d.relative_to(fix_root)
            except ValueError:
                rel = d
            print(f"[DEMO1 reset] removed empty dir {rel}", file=sys.stderr)
    elif fix_root.is_dir():
        empty = [
            p
            for p in sorted(fix_root.rglob("*"), key=lambda x: len(x.parts), reverse=True)
            if p.is_dir() and p != fix_root and not any(p.iterdir())
        ]
        for d in empty:
            print(f"[DEMO1 reset] would remove empty dir {d.relative_to(fix_root)}", file=sys.stderr)

    print("[DEMO1 reset] done", file=sys.stderr)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="DEMO1 — cold reset parity artifacts (see DEMO1.md).")
    p.add_argument("--dry-run", action="store_true", help="List targets only; do not delete.")
    args = p.parse_args(argv)
    return reset_fixtures(dry_run=bool(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
