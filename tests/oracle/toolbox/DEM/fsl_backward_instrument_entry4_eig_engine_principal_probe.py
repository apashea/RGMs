#!/usr/bin/env python3
"""Entry 4 — Engine vs Python principal-column research (``eig.md`` §28).

Read-only. Compares live MATLAB ``eig(...,'nobalance')`` to captured dumps and
``eig_nobalance``; tests whether any **reference-free** post-``eig`` rule closes T0.
Does not modify production ``spm_rgm_group`` / ``eig_nobalance`` defaults.
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_eig_engine_principal_probe_json,
    entry4_eig_oracle_blocks_pkl,
)
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES


def _engine_probe(eng: Any, sub: np.ndarray) -> dict[str, Any]:
    import matlab

    eng.workspace["rgms_sub"] = matlab.double(np.asarray(sub, dtype=np.float64).tolist())
    eng.eval("rgms_out = entry4_eig_principal_column_probe(rgms_sub);", nargout=0)
    n = int(sub.shape[0])
    w = np.asarray(eng.eval("rgms_out.w"), dtype=np.complex128).ravel(order="F")
    v = np.asarray(eng.eval("rgms_out.e"), dtype=np.complex128, order="F")
    if v.size != n * n:
        raise RuntimeError(f"MATLAB e size {v.size} != {n*n}")
    v = v.reshape((n, n), order="F")
    absv = np.asarray(eng.eval("rgms_out.absv"), dtype=np.float64).ravel()
    order = np.asarray(eng.eval("rgms_out.order"), dtype=np.float64).ravel().astype(np.int64) - 1
    jmax = int(np.asarray(eng.eval("rgms_out.jmax"), dtype=np.float64).ravel()[0]) - 1
    return {
        "w": w,
        "v": v,
        "jmax": jmax,
        "absv": absv,
        "order": order,
        "kmax_abs_entry": int(np.asarray(eng.eval("rgms_out.kmax_abs_entry"), dtype=np.float64).ravel()[0]) - 1,
        "col_l2_norm": float(np.asarray(eng.eval("rgms_out.col_l2_norm"), dtype=np.float64).ravel()[0]),
        "w_ascending": bool(np.asarray(eng.eval("rgms_out.w_ascending"), dtype=np.float64).ravel()[0]),
    }


def _order_ok(sub: np.ndarray, w_ref: np.ndarray, v_ref: np.ndarray, w: np.ndarray, v: np.ndarray) -> bool:
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dp = rgm_spectral_decisions(sub, w, v)
    return bool(np.array_equal(dr["order"], dp["order"]))


def _max_principal_diff(v_a: np.ndarray, w_a: np.ndarray, v_b: np.ndarray, w_b: np.ndarray) -> float:
    ja = int(np.argmax(np.abs(w_a)))
    jb = int(np.argmax(np.abs(w_b)))
    ca = v_a[:, ja]
    cb = v_b[:, jb]
    if np.vdot(ca, cb).real < 0:
        cb = -cb
    return float(np.max(np.abs(ca - cb)))


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[entry4 engine principal probe] missing oracle blocks pkl", file=sys.stderr)
        return 2

    try:
        import matlab.engine
    except ImportError:
        print("[entry4 engine principal probe] matlab.engine not available", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    eng = matlab.engine.start_matlab()
    rows: list[dict[str, Any]] = []
    try:
        eng.addpath(str(_REPO / "matlab_custom"), nargout=0)
        n = len(blocks)
        cnt = {
            "dump_matches_live_engine_order": 0,
            "py_eig_nobalance_order": 0,
            "live_engine_then_py_postprocess_order": 0,
            "live_engine_raw_layout_order": 0,
        }
        for blk in blocks:
            sub = np.asarray(blk["sub_mi"], dtype=np.float64)
            w_dump = np.asarray(blk["vals_mat"], dtype=np.complex128)
            v_dump = np.asarray(blk["vecs_mat"], dtype=np.complex128)
            live = _engine_probe(eng, sub)
            w_live, v_live = live["w"], live["v"]
            w_py, v_py = eig_nobalance(sub)

            ok_dump_live = _order_ok(sub, w_dump, v_dump, w_live, v_live)
            ok_py = _order_ok(sub, w_dump, v_dump, w_py, v_py)
            w_pp, v_pp = apply_matlab_spectral_postprocess(w_live, v_live)
            ok_live_pp = _order_ok(sub, w_dump, v_dump, w_pp, v_pp)
            ok_live_raw = _order_ok(sub, w_dump, v_dump, w_live, v_live)

            cnt["dump_matches_live_engine_order"] += int(ok_dump_live)
            cnt["py_eig_nobalance_order"] += int(ok_py)
            cnt["live_engine_then_py_postprocess_order"] += int(ok_live_pp)
            cnt["live_engine_raw_layout_order"] += int(ok_live_raw)

            rows.append(
                {
                    "sub_hash": blk.get("sub_hash", ""),
                    "known_fail": blk.get("sub_hash") in KNOWN_FAIL_HASHES,
                    "n": int(sub.shape[0]),
                    "dump_matches_live_engine_order": ok_dump_live,
                    "py_eig_nobalance_order": ok_py,
                    "live_engine_then_py_postprocess_order": ok_live_pp,
                    "live_engine_raw_layout_order": ok_live_raw,
                    "max_abs_w_diff_dump_vs_live": float(
                        np.max(np.abs(np.sort(np.abs(w_dump)) - np.sort(np.abs(w_live))))
                    ),
                    "max_principal_diff_dump_vs_live": _max_principal_diff(v_dump, w_dump, v_live, w_live),
                    "max_principal_diff_py_vs_live": _max_principal_diff(v_py, w_py, v_live, w_live),
                    "max_principal_diff_py_vs_dump": _max_principal_diff(v_py, w_py, v_dump, w_dump),
                    "live_w_ascending": live["w_ascending"],
                    "live_jmax": live["jmax"],
                    "dump_jmax": int(np.argmax(np.abs(w_dump))),
                    "py_jmax": int(np.argmax(np.abs(w_py))),
                }
            )
    finally:
        eng.quit()

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "n_blocks": n,
        "counts": cnt,
        "reference_free_conclusion": (
            "solver_gap_matlab_eig_required"
            if cnt["live_engine_then_py_postprocess_order"] == n
            and cnt["py_eig_nobalance_order"] < n
            else (
                "postprocess_only_closes_t0"
                if cnt["live_engine_then_py_postprocess_order"] == n
                else "solver_or_layout_gap"
            )
        ),
        "rows": rows,
    }
    out_path = entry4_eig_engine_principal_probe_json()
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[entry4 engine principal probe] wrote {out_path}")
    for k, v in cnt.items():
        print(f"  {k}: {v}/{n}")
    print(f"  reference_free_conclusion: {payload['reference_free_conclusion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
