#!/usr/bin/env python3
"""cProfile hot paths on the *OPTIM1* merge+basin compute path (Entry 8+9).

This is the “real lane” counterpart of ``optim1_profile_entry89.py``:
it calls the OPTIM1 functions under ``python_src/optimized/`` rather than the
fidelity counterparts under ``python_src/toolbox/``.

Usage (repo root)::

    conda activate rgms
    python tests/demo1/optim1/optim1_profile_entry89_optimpath.py
"""

from __future__ import annotations

import argparse
import cProfile
import copy
import io
import pickle
import pstats
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _load_boundary(pre9: Path) -> dict[str, Any]:
    with pre9.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {pre9}")
    return blob


def _first_o_seg(boundary: dict[str, Any]) -> tuple[list, list[dict[str, Any]]]:
    """First inner merge window (outer i=1, inner s=1) like the baseline profile."""

    pdp_o = boundary["pdp_o"]
    ne = int(boundary["Ne"])
    nt = int(boundary.get("NT", 100))
    ng = len(pdp_o)

    offset = int(np.remainder(1, 100 - 1)) * nt
    t = np.arange(0, nt + ne + 1, dtype=np.int64) + int(offset)
    cols = (t + 1).astype(np.int64)
    cols_list = cols.tolist()
    o_seg = [[pdp_o[g][int(c) - 1] for c in cols_list] for g in range(ng)]

    mdp = copy.deepcopy(boundary["mdp"])
    return o_seg, mdp


def _profile_merge_once(boundary: dict[str, Any]) -> None:
    from python_src.optimized.toolbox.DEM.spm_merge_structure_learning_optim import (
        spm_merge_structure_learning_optim,
    )

    o_seg, mdp = _first_o_seg(boundary)
    spm_merge_structure_learning_optim(o_seg, mdp)


def _mdp_after_first_merge(boundary: dict[str, Any]) -> list:
    from python_src.optimized.toolbox.DEM.spm_merge_structure_learning_optim import (
        spm_merge_structure_learning_optim,
    )

    o_seg, mdp = _first_o_seg(boundary)
    return spm_merge_structure_learning_optim(o_seg, mdp)


def _profile_basin_once(boundary: dict[str, Any]) -> None:
    from python_src.optimized.toolbox.DEM.spm_RDP_basin_optim import spm_RDP_basin_optim

    mdp = _mdp_after_first_merge(boundary)
    c_val = float(boundary["C"])
    # S=[2,3] exactly as in the entry 9 optim ledger.
    spm_RDP_basin_optim(mdp, [2, 3], [c_val, -c_val])


def _profile_one_outer_combined(boundary: dict[str, Any]) -> None:
    from python_src.optimized.toolbox.DEM.dem_atariiii_entry9_optim import (
        basin_training_loop,
    )

    pdp_o = boundary["pdp_o"]
    mdp = copy.deepcopy(boundary["mdp"])
    ne = int(boundary["Ne"])
    c_val = float(boundary["C"])
    nt = int(boundary.get("NT", 100))
    # Only one outer iteration: we want representative “inner cost shape”,
    # not to burn through the full n_outer=128.
    basin_training_loop(pdp_o, mdp, ne, c_val, nt=nt, n_outer=1)


def _run_profile(label: str, fn, *, sort: str, top: int) -> tuple[str, float]:
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    fn()
    pr.disable()
    elapsed = time.perf_counter() - t0
    buf = io.StringIO()
    ps = pstats.Stats(pr, stream=buf).sort_stats(sort)
    ps.print_stats(top)
    header = f"=== {label} wall_s={elapsed:.6f} (top {top} by {sort}) ===\n"
    return header + buf.getvalue(), elapsed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 8+9 optimpath cProfile")
    p.add_argument("--pre-entry9", type=Path, default=None)
    p.add_argument("--sort", default="cumtime", choices=("cumtime", "tottime"))
    p.add_argument("--top", type=int, default=40)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Report path (default: logs/optim1_entry89_optimpath_profile.txt)",
    )
    p.add_argument("--skip-outer", action="store_true", help="Skip one-outer combined profile")
    args = p.parse_args(argv)

    pre9 = args.pre_entry9 or (demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl")
    if not pre9.is_file():
        print(f"[OPTIM1 profile] missing {pre9}", file=sys.stderr)
        return 2

    boundary = _load_boundary(pre9)

    out_path = args.out or (_REPO / "logs" / "optim1_entry89_optimpath_profile.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sections: list[str] = [
        "OPTIM1 Entry 8+9 optimpath profile report",
        f"pre_entry9={pre9}",
        f"Ne={boundary.get('Ne')} NT={boundary.get('NT', 100)} n_outer={boundary.get('n_outer', 128)}",
        "",
    ]

    timings: dict[str, float] = {}
    profile_specs = [
        (
            "merge_once_s",
            "spm_merge_structure_learning_optim (single call, first window)",
            lambda: _profile_merge_once(boundary),
        ),
        (
            "basin_once_s",
            "spm_RDP_basin_optim (single call, after first merge window)",
            lambda: _profile_basin_once(boundary),
        ),
    ]

    for key, label, fn in profile_specs:
        print(f"[OPTIM1 profile] {label}", file=sys.stderr)
        text, elapsed = _run_profile(label, fn, sort=args.sort, top=args.top)
        sections.append(text)
        sections.append("")
        timings[key] = elapsed

    if not args.skip_outer:
        print("[OPTIM1 profile] basin_training_loop optim n_outer=1", file=sys.stderr)
        text, elapsed = _run_profile(
            "basin_training_loop (optim, n_outer=1)",
            lambda: _profile_one_outer_combined(boundary),
            sort=args.sort,
            top=args.top,
        )
        sections.append(text)
        timings["one_outer_s"] = elapsed

    summary = (
        "=== summary ===\n"
        f"merge_once_s={timings.get('merge_once_s', 0):.6f}\n"
        f"basin_once_s={timings.get('basin_once_s', 0):.6f}\n"
    )
    if "one_outer_s" in timings:
        summary += f"one_outer_s={timings['one_outer_s']:.6f}\n"
    sections.append(summary)

    report = "\n".join(sections)
    out_path.write_text(report, encoding="utf-8")
    print(f"[OPTIM1 profile] wrote {out_path}", file=sys.stderr)
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

