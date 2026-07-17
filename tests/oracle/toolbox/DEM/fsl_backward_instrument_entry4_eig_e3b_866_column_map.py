#!/usr/bin/env python3
"""Entry 4 E3b-b3 — ``866ab1a9…`` LAPACK ``KI`` ↔ §27 ``j_ref`` column map (``eig.md`` §4.1).

Resolves **K70**: ``j_ref`` is post-ascending-|w| column index; DGEEVX debug
``set_col`` must latch the **raw LAPACK** column ``idx[j_ref]`` (Fortran ``+1``).
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_lapack_nobalance import (
    dtrevc3_debug_get,
    dtrevc3_debug_reset,
    dtrevc3_debug_set_col,
    dtrevc3_debug_set_row_pair,
    eig_real_nobalance,
    lapack_nobalance_available,
)
from python_src.utils.eig_spectral_policy import (
    apply_matlab_spectral_postprocess,
    reorder_eigenpairs_ascending_abs_w,
)
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "866ab1a9b2265fd6"
ROW_LO_0, ROW_HI_0 = 7, 58
ROW_LO_1, ROW_HI_1 = ROW_LO_0 + 1, ROW_HI_0 + 1
TRACK_ROWS = (7, 28, 52, 58)
PLATEAU_RTOL = 1e-14


def _leader_pair(abs_lo: float, abs_hi: float) -> int | None:
    if abs_lo == 0.0 and abs_hi == 0.0:
        return None
    tol = 1e-15 * max(abs_lo, abs_hi, 1.0)
    if abs(abs_lo - abs_hi) <= tol:
        return ROW_LO_0
    return ROW_LO_0 if abs_lo > abs_hi else ROW_HI_0


def _pair_stage(abs_lo: float, abs_hi: float) -> dict[str, Any]:
    return {
        "abs_lo": float(abs_lo),
        "abs_hi": float(abs_hi),
        "leader_0based": _leader_pair(abs_lo, abs_hi),
        "diff_lo_minus_hi": float(abs_lo) - float(abs_hi),
    }


def _row_table(absv: np.ndarray, *, label: str) -> dict[str, Any]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    m = float(np.max(a)) if a.size else 0.0
    tol = max(1e-300, PLATEAU_RTOL * max(m, 1.0))
    rows = []
    for idx in TRACK_ROWS:
        val = float(a[idx])
        rows.append(
            {
                "index": int(idx),
                "abs": val,
                "on_plateau": bool(abs(val - m) <= tol),
                "delta_from_max": float(val - m),
            }
        )
    return {
        "label": label,
        "kmax_0based": int(np.argmax(a)) if a.size else -1,
        "max_abs": m,
        "rows": rows,
    }


def _pipeline_ladder(dbg: dict[str, float | int], *, raw_col: int, v_raw: np.ndarray) -> dict[str, Any]:
    ladder: list[tuple[str, dict[str, Any]]] = [
        ("1_post_DGEHRD", _pair_stage(dbg["post_dgehrd_hess_col_abs_13"], dbg["post_dgehrd_hess_col_abs_44"])),
        ("2_post_DORGHR", _pair_stage(dbg["post_dorghr_q_col_abs_13"], dbg["post_dorghr_q_col_abs_44"])),
        ("2a_DLAQR0_in", _pair_stage(dbg["dlaqr0_in_vr_col_abs_13"], dbg["dlaqr0_in_vr_col_abs_44"])),
        ("2b_DLAQR0_out", _pair_stage(dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"])),
        ("3_post_DHSEQR", _pair_stage(dbg["post_dhseqr_schur_vr_col_abs_13"], dbg["post_dhseqr_schur_vr_col_abs_44"])),
        ("4_DTREVC3_at_KI", _pair_stage(dbg["vr_col_k_abs_13"], dbg["vr_col_k_abs_44"])),
        ("5_DTREVC3_pre_IDAMAX", _pair_stage(dbg["post_bt_pre_idamax_abs_13"], dbg["post_bt_pre_idamax_abs_44"])),
        ("6_DTREVC3_post_IDAMAX", _pair_stage(dbg["post_abs_13"], dbg["post_abs_44"])),
        (
            "7_final_raw_lapack_col",
            _pair_stage(
                float(np.abs(v_raw[ROW_LO_0, raw_col])),
                float(np.abs(v_raw[ROW_HI_0, raw_col])),
            ),
        ),
    ]
    first_tied_max: str | None = None
    for name, st in ladder:
        if st["leader_0based"] == ROW_LO_0 and st["abs_lo"] > 0 and st["abs_hi"] > 0:
            tol = 1e-15 * max(st["abs_lo"], st["abs_hi"], 1.0)
            if abs(st["abs_lo"] - st["abs_hi"]) <= tol and first_tied_max is None:
                first_tied_max = name
    return {
        "ladder": {name: st for name, st in ladder},
        "first_tied_max_leader_7": first_tied_max,
    }


def _run_armed_eig(sub: np.ndarray, fortran_col: int) -> tuple[dict[str, float | int], np.ndarray, np.ndarray]:
    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    dtrevc3_debug_set_row_pair(ROW_LO_1, ROW_HI_1)
    w_v, v_v = eig_real_nobalance(sub)
    return dtrevc3_debug_get(), w_v, v_v


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3b-b3 866 colmap] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3b-b3 866 colmap] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blk = [b for b in pickle.load(f)["blocks"] if b["sub_hash"] == HASH][0]

    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    dr_ref = rgm_spectral_decisions(sub, w_ref, v_ref)
    j_ref = int(dr_ref["jmax"])

    w_raw, v_raw = eig_real_nobalance(sub)
    w_raw = np.asarray(w_raw, dtype=np.complex128).ravel(order="F")
    v_raw = np.asarray(v_raw, dtype=np.complex128, order="F")
    perm = np.argsort(np.abs(w_raw), kind="mergesort")
    raw_jmax = int(np.argmax(np.abs(w_raw)))
    raw_col_for_jref = int(perm[j_ref])
    fortran_ki_jref = raw_col_for_jref + 1
    fortran_ki_raw_jmax = raw_jmax + 1

    w_pp, v_pp = apply_matlab_spectral_postprocess(w_raw, v_raw)
    dr_py = rgm_spectral_decisions(sub, w_pp, v_pp)
    j_py = int(dr_py["jmax"])

    # Sanity: ascending reorder maps raw_col_for_jref -> j_ref
    w_check, v_check = reorder_eigenpairs_ascending_abs_w(w_raw, v_raw)
    col_match = bool(np.allclose(v_check[:, j_ref], v_raw[:, raw_col_for_jref]))

    dbg_jref, w_arm, v_arm = _run_armed_eig(sub, fortran_ki_jref)
    ladder_jref = _pipeline_ladder(dbg_jref, raw_col=raw_col_for_jref, v_raw=v_arm)

    dual_ladder: dict[str, Any] | None = None
    if fortran_ki_jref != fortran_ki_raw_jmax:
        dbg_raw, w2, v2 = _run_armed_eig(sub, fortran_ki_raw_jmax)
        dual_ladder = {
            "fortran_ki_raw_jmax": fortran_ki_raw_jmax,
            "pipeline": _pipeline_ladder(dbg_raw, raw_col=raw_jmax, v_raw=v2),
        }

    ref_rows = _row_table(dr_ref["absv"], label="matlab_ref_pp")
    py_rows = _row_table(dr_py["absv"], label="vendored_pp")
    spurious = sorted(
        {r["index"] for r in py_rows["rows"] if r["on_plateau"]}
        - {r["index"] for r in ref_rows["rows"] if r["on_plateau"]}
    )

    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3b-b3",
        "sub_hash": HASH,
        "n": int(sub.shape[0]),
        "j_ref_0based": j_ref,
        "j_py_0based": j_py,
        "jmax_match": j_ref == j_py,
        "raw_jmax_0based": raw_jmax,
        "raw_col_for_jref_0based": raw_col_for_jref,
        "fortran_ki_for_jref": fortran_ki_jref,
        "fortran_ki_raw_jmax": fortran_ki_raw_jmax,
        "ki_jref_eq_raw_jmax": fortran_ki_jref == fortran_ki_raw_jmax,
        "perm_ascending_abs_w": perm.astype(int).tolist(),
        "v_check_col_match": col_match,
        "column_map_note": (
            "j_ref is index after ascending-|w| reorder; DGEEVX set_col = raw_col_for_jref+1. "
            "Do not index raw v with j_ref."
        ),
        "ref_row_table": ref_rows,
        "py_row_table": py_rows,
        "spurious_py_plateau": spurious,
        "kmax_ref": ref_rows["kmax_0based"],
        "kmax_py": py_rows["kmax_0based"],
        "pipeline_ladder_ki_jref": ladder_jref,
        "pipeline_dual_ladder": dual_ladder,
        "first_informative_site": ladder_jref["first_tied_max_leader_7"],
        "compute_patch_hint": (
            "E3b-c: demote spurious plateau rows at or before first_informative_site "
            f"(rows {spurious}); oracle replay demote {{7,28,52}}."
        ),
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3b_866_column_map.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"[e3b-b3 866 colmap] j_ref={j_ref} raw_col={raw_col_for_jref} "
        f"KI={fortran_ki_jref} ki_eq_raw={payload['ki_jref_eq_raw_jmax']} "
        f"first_tied={ladder_jref['first_tied_max_leader_7']} "
        f"spurious={spurious}"
    )
    print(f"[e3b-b3 866 colmap] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
