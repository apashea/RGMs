#!/usr/bin/env python3
"""OPTIM1 Iteration 1 — fidelity Entry 8 / 8+9 timing baseline (isolated runners).

Fair A/B baseline for OPTIM1 scale gates: same ``pre_entry9.pkl`` boundary and
``n_outer=128`` as ``optim1_run_entry8_scale.py`` / ``optim1_run_entry89_scale.py``,
but fidelity ``run_entry8_from_boundary`` / ``run_entry9_from_boundary``.

Does **not** write DEMO1 fixtures; tees timings to stderr and optional log file.

Usage (repo root)::

    python tests/demo1/optim1/optim1_baseline_fidelity_entry89.py
    python tests/demo1/optim1/optim1_baseline_fidelity_entry89.py --entry8-only
    python tests/demo1/optim1/optim1_baseline_fidelity_entry89.py --log logs/optim1_fidelity_entry89_baseline.log
"""
from __future__ import annotations

import argparse
import copy
import pickle
import sys
import time
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _load_boundary(pre9: Path) -> dict[str, Any]:
    if not pre9.is_file():
        raise FileNotFoundError(f"missing pre_entry9 PKL: {pre9}")
    with pre9.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {pre9}")
    return blob


def _run_entry8(boundary: dict[str, Any]) -> dict[str, float]:
    from python_src.toolbox.DEM.fsl_backward_entry8 import run_entry8_from_boundary

    t0 = time.perf_counter()
    out = run_entry8_from_boundary(copy.deepcopy(boundary))
    wall_s = time.perf_counter() - t0
    return {
        "entry8_merge_loop_s": float(out["entry8_merge_loop_s"]),
        "entry8_wall_s": wall_s,
        "n_outer": float(out.get("n_outer", 128)),
    }


def _run_entry89(boundary: dict[str, Any]) -> dict[str, float]:
    from python_src.toolbox.DEM.fsl_backward_entry9 import run_entry9_from_boundary

    t0 = time.perf_counter()
    out = run_entry9_from_boundary(copy.deepcopy(boundary))
    wall_s = time.perf_counter() - t0
    return {
        "entry8_loop_s": float(out["entry8_loop_s"]),
        "entry9_loop_s": float(out["entry9_loop_s"]),
        "entry89_wall_s": wall_s,
        "n_outer": float(out.get("n_outer", 128)),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 fidelity Entry 8/8+9 timing baseline")
    p.add_argument(
        "--pre-entry9",
        type=Path,
        default=None,
        help="DEMO1 pre_entry9 PKL (default: tests/demo1/fixtures/...)",
    )
    p.add_argument("--entry8-only", action="store_true", help="Skip Entry 8+9 combined run")
    p.add_argument("--entry89-only", action="store_true", help="Skip Entry 8 merge-only run")
    p.add_argument("--log", type=Path, default=None, help="Append human-readable summary")
    args = p.parse_args(argv)

    pre9 = args.pre_entry9 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
    )
    boundary = _load_boundary(pre9)
    lines: list[str] = [
        f"[OPTIM1 fidelity baseline] pre_entry9={pre9}",
        f"[OPTIM1 fidelity baseline] Ne={boundary.get('Ne')} NT={boundary.get('NT')} "
        f"n_outer={boundary.get('n_outer', 128)} C={boundary.get('C')}",
    ]

    if not args.entry89_only:
        print("[OPTIM1 fidelity baseline] Entry 8 merge-only (fidelity)", file=sys.stderr)
        e8 = _run_entry8(boundary)
        lines.append(
            f"[OPTIM1 fidelity baseline] Entry8 merge_loop_s={e8['entry8_merge_loop_s']:.3f} "
            f"wall_s={e8['entry8_wall_s']:.3f} n_outer={int(e8['n_outer'])}"
        )

    if not args.entry8_only:
        print("[OPTIM1 fidelity baseline] Entry 8+9 combined (fidelity)", file=sys.stderr)
        e89 = _run_entry89(boundary)
        lines.append(
            f"[OPTIM1 fidelity baseline] Entry89 entry8_loop_s={e89['entry8_loop_s']:.3f} "
            f"entry9_loop_s={e89['entry9_loop_s']:.3f} wall_s={e89['entry89_wall_s']:.3f} "
            f"n_outer={int(e89['n_outer'])}"
        )

    for line in lines:
        print(line, file=sys.stderr)

    if args.log is not None:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        # Write (overwrite) — do not Tee-Object to the same path (Windows file lock).
        with args.log.open("w", encoding="utf-8") as lf:
            lf.write("\n".join(lines) + "\n")
        print(f"[OPTIM1 fidelity baseline] wrote {args.log}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
