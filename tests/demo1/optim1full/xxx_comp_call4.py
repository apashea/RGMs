#!/usr/bin/env python3
"""XXX_comp — call4 full-VB wall time + MATLAB PDP parity (no fidelity lane).

Authority: XXX_optim.md § XXX_comp (Snapshot vs run; Workflow Steps 1–4).

Re-run any snapshot: restore → reverify → optim-wall → compare-matlab.
See XXX_optim.md for full PowerShell restore block and $snapName table.

Frozen tag: rgms_atari_optim1full_call4 (vb_rand_buf.k=32256).

Sign-off driver ONLY:
  tests/demo1/optim1full/xxx_comp_call4.py --mode optim-wall
  tests/demo1/optim1full/xxx_comp_call4.py --mode compare-matlab  (after optim-wall)

Host-correlated wall (PRE/POST RAM/commit; does not touch perf_counter):
  tests/demo1/optim1full/optim1full_w2_optim_wall_logged.ps1 -Label <label>

Verify live = snapshot:
  tests/demo1/optim1full/optim1full_w2_c4ab_reverify.py --snapshot notes/w2_backup/<name>

Do NOT use: 3f gate, fidelity lane, compare-matlab optim_wall_s as fresh wall.
"""
from __future__ import annotations

import argparse
import copy
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

TAG = "rgms_atari_optim1full_call4"
OUT_DIR = _REPO / "logs"
OPTIM_PKL = OUT_DIR / f"xxx_comp_{TAG}_optim_pdp.pkl"
MATLAB_MAT_V7 = OUT_DIR / f"xxx_matlab_6_{TAG}_matlab_pdp_v7.mat"
MATLAB_MAT = OUT_DIR / f"xxx_matlab_6_{TAG}_matlab_pdp.mat"


def _configure_env(tag: str) -> None:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fix = str(optim1full_fixtures_dir().resolve())
    os.environ["RGMS_OPTIM1FULL_FIXTURES_DIR"] = fix
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = fix
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = str(tag).strip()
    os.environ.setdefault("RGMS_ATARI_RUN_DEADLINE_MINUTES", "240")
    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")


def run_optim_wall(tag: str) -> dict[str, Any]:
    """One full ``spm_MDP_VB_XXX_optim`` on frozen call4 fixtures; return wall + PDP."""
    from tests.demo1.optim1full.optim1full_vb_optim_equivalence import (
        _configure_entry12_fixture_env,
        _load_tag_rdp_and_buf,
        _run_vb_tag_lane,
    )
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready

    _configure_entry12_fixture_env(tag)
    _configure_env(tag)
    assert_entry12_vb_tag_ready(tag)
    rdp, _buf, k = _load_tag_rdp_and_buf(tag)
    print(f"[XXX_comp] tag={tag!r} vb_rand_buf.k={k} mode=optim-wall", flush=True)
    t0 = time.perf_counter()
    pdp = _run_vb_tag_lane(rdp, lane="optim")
    wall = time.perf_counter() - t0
    payload = {
        "tag": tag,
        "k": k,
        "optim_wall_s": wall,
        "PDP": pdp,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OPTIM_PKL, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(
        f"[XXX_comp] optim_wall_s={wall:.6f} wrote {OPTIM_PKL}",
        flush=True,
    )
    return payload


def compare_optim_vs_matlab(tag: str = TAG) -> int:
    """Optim PDP vs cached MATLAB PDP (XXX_matlab-6 mat artifacts). No fidelity."""
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _densify_sparse_leaves,
        _load_matlab_pdp,
    )

    if not OPTIM_PKL.is_file():
        raise FileNotFoundError(OPTIM_PKL)
    mat_use = MATLAB_MAT_V7 if MATLAB_MAT_V7.is_file() else MATLAB_MAT
    if not mat_use.is_file():
        raise FileNotFoundError(
            f"MATLAB PDP missing: {MATLAB_MAT_V7} / {MATLAB_MAT} "
            "(run matlab_custom/xxx_matlab_6_run.m first)"
        )

    with open(OPTIM_PKL, "rb") as f:
        optim_payload = pickle.load(f)
    pdp_optim = optim_payload["PDP"]
    pdp_matlab = _load_matlab_pdp(mat_use)

    print(
        f"[XXX_comp] mode=compare-matlab tag={tag!r} "
        f"optim_wall_s={optim_payload.get('optim_wall_s')} "
        f"matlab={mat_use.name}",
        flush=True,
    )
    label = f"XXX_comp optim vs MATLAB ({tag})"
    try:
        if isinstance(pdp_optim, dict) and isinstance(pdp_matlab, dict):
            py_cmp = entry12_align_mdp_to_mat_workspace(copy.deepcopy(pdp_optim), pdp_matlab)
            mat_cmp = entry12_mat_pdp_for_value_assert(pdp_matlab)
        else:
            py_cmp, mat_cmp = pdp_optim, pdp_matlab
        _compare_pair(
            label,
            _densify_sparse_leaves(copy.deepcopy(py_cmp)),
            _densify_sparse_leaves(copy.deepcopy(mat_cmp)),
            "PDP",
            report_only=False,
            coerce_sparse=False,
        )
    except AssertionError as e:
        print(f"[XXX_comp] FAIL compare-matlab: {e}", flush=True)
        return 1
    print("[XXX_comp] PASS: optim PDP == MATLAB PDP (aligned)", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--mode",
        choices=("optim-wall", "compare-matlab"),
        required=True,
    )
    p.add_argument("--tag", default=TAG)
    args = p.parse_args(argv)
    tag = str(args.tag).strip()
    if args.mode == "optim-wall":
        run_optim_wall(tag)
        return 0
    return compare_optim_vs_matlab(tag)


if __name__ == "__main__":
    raise SystemExit(main())
