#!/usr/bin/env python3
"""XXX_matlab-6/7 — optim PDP export, MATLAB compare, and post-record F/Q.E rows.

Authority: XXX_optim.md § XXX_matlab. No fidelity lane. No deepcopy restore.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pickle
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

TAG = "rgms_atari_optim1full_call4"
OUT_DIR = _REPO / "logs"
OPTIM_PKL = OUT_DIR / f"xxx_matlab_6_{TAG}_optim_pdp.pkl"
MATLAB_MAT = OUT_DIR / f"xxx_matlab_6_{TAG}_matlab_pdp.mat"
MATLAB_MAT_V7 = OUT_DIR / f"xxx_matlab_6_{TAG}_matlab_pdp_v7.mat"
COMPARE_LOG = OUT_DIR / "optim1full_w2_XXX_matlab_6_compare.log"
XM7_OPTIM_JSON = OUT_DIR / f"xxx_matlab_7_{TAG}_optim_rows.json"


def _configure_env(tag: str) -> None:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fix = str(optim1full_fixtures_dir().resolve())
    os.environ["RGMS_OPTIM1FULL_FIXTURES_DIR"] = fix
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = fix
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = str(tag).strip()
    os.environ.setdefault("RGMS_ATARI_RUN_DEADLINE_MINUTES", "240")
    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")


def export_optim(tag: str) -> dict:
    from tests.demo1.optim1full.optim1full_vb_optim_equivalence import (
        _load_tag_rdp_and_buf,
        _run_vb_tag_lane,
    )
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready

    _configure_env(tag)
    assert_entry12_vb_tag_ready(tag)
    rdp, _buf, k = _load_tag_rdp_and_buf(tag)
    print(f"[XM6-optim] tag={tag!r} vb_rand_buf.k={k}", flush=True)
    t0 = time.perf_counter()
    pdp = _run_vb_tag_lane(rdp, lane="optim")
    wall = time.perf_counter() - t0
    payload = {"PDP": pdp, "tag": tag, "k": k, "optim_vb_s": wall}
    with open(OPTIM_PKL, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[XM6-optim] wall_s={wall:.6f} wrote {OPTIM_PKL}", flush=True)
    return payload


def export_xm7_optim(tag: str) -> dict:
    """XXX_matlab-7: optim VB with post-merge F/Q.E row dump (RGMS_XXX_MATLAB_7=1)."""
    from python_src.optimized.toolbox.DEM import vb_hierarchical_optim as _hier
    from tests.demo1.optim1full.optim1full_vb_optim_equivalence import (
        _load_tag_rdp_and_buf,
        _run_vb_tag_lane,
    )
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready

    _configure_env(tag)
    assert_entry12_vb_tag_ready(tag)
    os.environ["RGMS_XXX_MATLAB_7"] = "1"
    _hier.xm7_rows_clear()
    rdp, _buf, k = _load_tag_rdp_and_buf(tag)
    print(f"[XM7-optim] tag={tag!r} vb_rand_buf.k={k}", flush=True)
    t0 = time.perf_counter()
    _run_vb_tag_lane(rdp, lane="optim")
    wall = time.perf_counter() - t0
    rows = _hier.xm7_rows_get()
    os.environ.pop("RGMS_XXX_MATLAB_7", None)
    payload = {"tag": tag, "k": k, "optim_vb_s": wall, "n_rows": len(rows), "rows": rows}
    with open(XM7_OPTIM_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[XM7-optim] wall_s={wall:.6f} n_rows={len(rows)} wrote {XM7_OPTIM_JSON}", flush=True)
    if rows:
        r0 = rows[0]
        print(
            f"[XM7-optim] SUMMARY first: n={r0['n']} path={r0['path']} "
            f"F_numel={r0['F_numel']} QE_L_numel={r0['QE_L_numel']} "
            f"F_sum={r0['F_sum']:.6g} Q_F={r0['Q_F']:.6g}",
            flush=True,
        )
        if len(rows) > 1:
            r1 = rows[1]
            print(
                f"[XM7-optim] SUMMARY second: n={r1['n']} path={r1['path']} "
                f"F_numel={r1['F_numel']} QE_L_numel={r1['QE_L_numel']} "
                f"F_sum={r1['F_sum']:.6g} Q_F={r1['Q_F']:.6g}",
                flush=True,
            )
        last = rows[-1]
        print(
            f"[XM7-optim] SUMMARY last: n={last['n']} path={last['path']} "
            f"F_numel={last['F_numel']} QE_L_numel={last['QE_L_numel']} "
            f"F_sum={last['F_sum']:.6g} Q_F={last['Q_F']:.6g}",
            flush=True,
        )
    return payload


def _load_matlab_pdp(mat_path: Path):
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp

    return _load_matlab_pdp(mat_path)


def compare_optim_vs_matlab() -> int:
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
        _compare_pair,
        _densify_sparse_leaves,
    )

    if not OPTIM_PKL.is_file():
        raise FileNotFoundError(OPTIM_PKL)
    mat_use = MATLAB_MAT_V7 if MATLAB_MAT_V7.is_file() else MATLAB_MAT
    if not mat_use.is_file():
        raise FileNotFoundError(mat_use)

    with open(OPTIM_PKL, "rb") as f:
        optim_payload = pickle.load(f)
    pdp_optim = optim_payload["PDP"]
    pdp_matlab = _load_matlab_pdp(mat_use)

    print(
        f"[XM6-compare] optim_k={optim_payload.get('k')} "
        f"optim_vb_s={optim_payload.get('optim_vb_s')} "
        f"matlab={mat_use.name}",
        flush=True,
    )
    label = f"XXX_matlab-6 optim vs MATLAB ({TAG})"
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
        print(f"[XM6-compare] FAIL: {e}", flush=True)
        return 1
    print("[XM6-compare] PASS: optim PDP == MATLAB PDP (aligned)", flush=True)
    return 0


def compare_xm7_rows() -> int:
    """Compare MATLAB vs optim post-record size series (XXX_matlab-7)."""
    from scipy.io import loadmat

    mat_path = OUT_DIR / f"xxx_matlab_7_{TAG}_matlab_rows.mat"
    if not mat_path.is_file():
        raise FileNotFoundError(mat_path)
    if not XM7_OPTIM_JSON.is_file():
        raise FileNotFoundError(XM7_OPTIM_JSON)

    raw = loadmat(str(mat_path), simplify_cells=True)
    m_rows = raw.get("rows")
    if m_rows is None:
        raise KeyError("rows missing in MATLAB mat")
    if isinstance(m_rows, dict):
        m_list = [m_rows]
    else:
        m_list = list(m_rows) if not isinstance(m_rows, list) else m_rows

    with open(XM7_OPTIM_JSON, encoding="utf-8") as f:
        o_payload = json.load(f)
    o_list = o_payload["rows"]

    print(f"[XM7-compare] matlab_n={len(m_list)} optim_n={len(o_list)}", flush=True)

    def _g(r, k, default=None):
        if isinstance(r, dict):
            return r.get(k, default)
        return getattr(r, k, default)

    n = min(len(m_list), len(o_list))
    first_bad = None
    for i in range(n):
        mr = m_list[i]
        orow = o_list[i]
        mf = int(_g(mr, "F_numel", -1))
        of = int(orow["F_numel"])
        me = int(_g(mr, "QE_L_numel", -1))
        oe = int(orow["QE_L_numel"])
        mpath = str(_g(mr, "path", "?"))
        opath = str(orow["path"])
        if mf != of or me != oe or mpath != opath:
            first_bad = {
                "i": i + 1,
                "matlab": {
                    "F_numel": mf,
                    "QE_L_numel": me,
                    "path": mpath,
                    "F_sum": float(_g(mr, "F_sum", float("nan"))),
                    "Q_F": float(_g(mr, "Q_F", float("nan"))),
                },
                "optim": {
                    "F_numel": of,
                    "QE_L_numel": oe,
                    "path": opath,
                    "F_sum": orow["F_sum"],
                    "Q_F": orow["Q_F"],
                },
            }
            break
    if len(m_list) != len(o_list):
        print(
            f"[XM7-compare] WARN n_rows mismatch matlab={len(m_list)} optim={len(o_list)}",
            flush=True,
        )
    if first_bad is None and len(m_list) == len(o_list):
        print("[XM7-compare] PASS: F_numel/QE_L_numel/path match all rows", flush=True)
        return 0
    print(f"[XM7-compare] FAIL first diverge: {json.dumps(first_bad, indent=2)}", flush=True)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--mode",
        choices=("export-optim", "compare", "all", "xm7-optim", "xm7-compare"),
        default="all",
    )
    args = p.parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rc = 0
    if args.mode in ("export-optim", "all"):
        export_optim(TAG)
    if args.mode in ("compare", "all"):

        class _Tee:
            def __init__(self, *streams):
                self.streams = streams

            def write(self, data):
                for s in self.streams:
                    s.write(data)
                    s.flush()

            def flush(self):
                for s in self.streams:
                    s.flush()

        with open(COMPARE_LOG, "w", encoding="utf-8") as logf:
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = _Tee(old_out, logf)
            try:
                rc = compare_optim_vs_matlab()
            finally:
                sys.stdout, sys.stderr = old_out, old_err
        print(f"[XM6-compare] log={COMPARE_LOG}", flush=True)
    if args.mode == "xm7-optim":
        export_xm7_optim(TAG)
    if args.mode == "xm7-compare":
        rc = compare_xm7_rows()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
