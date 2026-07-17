#!/usr/bin/env python3
"""Entry 4 E3b-b — ``866ab1a9…`` causal row-pair ladder 7 vs 58 (``eig.md`` §4.1).

Parametrized Fortran debug rows (``set_row_pair(8,59)``) on principal column
``jmax+1``; locates first pipeline stage where row **7** overtakes **58** in
``abs`` leader vs MATLAB ref expectation (**58** wins ``kmax``).
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
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "866ab1a9b2265fd6"
ROW_LO_0 = 7
ROW_HI_0 = 58
ROW_LO_1 = ROW_LO_0 + 1
ROW_HI_1 = ROW_HI_0 + 1


def _leader(abs_lo: float, abs_hi: float) -> int | None:
    if abs_lo == 0.0 and abs_hi == 0.0:
        return None
    tol = 1e-15 * max(abs_lo, abs_hi, 1.0)
    if abs(abs_lo - abs_hi) <= tol:
        return ROW_LO_0
    if abs_lo > abs_hi:
        return ROW_LO_0
    return ROW_HI_0


def _stage(abs_lo: float, abs_hi: float) -> dict[str, Any]:
    return {
        "abs_lo": float(abs_lo),
        "abs_hi": float(abs_hi),
        "row_lo_0based": ROW_LO_0,
        "row_hi_0based": ROW_HI_0,
        "leader_0based": _leader(abs_lo, abs_hi),
        "diff_lo_minus_hi": float(abs_lo) - float(abs_hi),
    }


def _first_causal_flip(
    ladder: list[tuple[str, dict[str, Any]]],
    *,
    ref_pair_leader: int,
) -> dict[str, Any]:
    """First informative stage where vendored pair leader is row_lo (7) vs ref row_hi (58)."""
    if ref_pair_leader != ROW_HI_0:
        return {
            "site": None,
            "note": "ref pair leader is not row_hi; ladder semantics differ",
            "ref_pair_leader_0based": ref_pair_leader,
        }
    prev_leader: int | None = None
    for name, st in ladder:
        leader = st["leader_0based"]
        if leader is None:
            continue
        leader_i = int(leader)
        if prev_leader is None:
            prev_leader = leader_i
            continue
        if leader_i == ROW_LO_0 and prev_leader == ROW_HI_0:
            return {
                "site": name,
                "from_leader_0based": prev_leader,
                "to_leader_0based": leader_i,
                "stage": st,
            }
        if leader_i != prev_leader:
            prev_leader = leader_i
    return {
        "site": None,
        "from_leader_0based": ref_pair_leader,
        "to_leader_0based": prev_leader,
        "stage": None,
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3b-b 866 ladder] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3b-b 866 ladder] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blk = [b for b in pickle.load(f)["blocks"] if b["sub_hash"] == HASH][0]

    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    j_ref = int(dr["jmax"])
    abs_ref = dr["absv"]
    ref_leader = int(np.argmax(abs_ref))
    ref_pair = _stage(float(abs_ref[ROW_LO_0]), float(abs_ref[ROW_HI_0]))

    w_probe, v_probe = eig_real_nobalance(sub)
    w_probe = np.asarray(w_probe, dtype=np.complex128).ravel(order="F")
    perm = np.argsort(np.abs(w_probe), kind="mergesort")
    raw_j = int(np.argmax(np.abs(w_probe)))
    raw_col_for_jref = int(perm[j_ref])
    fortran_col = raw_col_for_jref + 1

    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    dtrevc3_debug_set_row_pair(ROW_LO_1, ROW_HI_1)
    w_v, v_v = eig_real_nobalance(sub)
    dbg = dtrevc3_debug_get()

    w_pp, v_pp = apply_matlab_spectral_postprocess(w_v, v_v)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_py = dp["absv"]
    py_leader = int(np.argmax(abs_py))
    py_pair_final = _stage(float(abs_py[ROW_LO_0]), float(abs_py[ROW_HI_0]))

    ladder_ordered: list[tuple[str, dict[str, Any]]] = [
        (
            "1_post_DGEHRD_hessenberg_H_col",
            _stage(dbg["post_dgehrd_hess_col_abs_13"], dbg["post_dgehrd_hess_col_abs_44"]),
        ),
        (
            "2_post_DORGHR_orthogonal_Q_col",
            _stage(dbg["post_dorghr_q_col_abs_13"], dbg["post_dorghr_q_col_abs_44"]),
        ),
        (
            "2a_post_DLAQR0_in_VR_col",
            _stage(dbg["dlaqr0_in_vr_col_abs_13"], dbg["dlaqr0_in_vr_col_abs_44"]),
        ),
        (
            "2b_post_DLAQR0_out_schur_VR_col",
            _stage(dbg["dlaqr0_out_vr_col_abs_13"], dbg["dlaqr0_out_vr_col_abs_44"]),
        ),
        (
            "3_post_DHSEQR_schur_VR_col",
            _stage(
                dbg["post_dhseqr_schur_vr_col_abs_13"],
                dbg["post_dhseqr_schur_vr_col_abs_44"],
            ),
        ),
        (
            "4_DTREVC3_at_KI_vr_col",
            _stage(dbg["vr_col_k_abs_13"], dbg["vr_col_k_abs_44"]),
        ),
        (
            "5_DTREVC3_post_DGEMM_pre_IDAMAX",
            _stage(dbg["post_bt_pre_idamax_abs_13"], dbg["post_bt_pre_idamax_abs_44"]),
        ),
        (
            "6_DTREVC3_post_IDAMAX_normalize",
            _stage(dbg["post_abs_13"], dbg["post_abs_44"]),
        ),
        (
            "7_final_raw_lapack_col",
            _stage(
                float(np.abs(v_v[ROW_LO_0, raw_col_for_jref])),
                float(np.abs(v_v[ROW_HI_0, raw_col_for_jref])),
            ),
        ),
        (
            "8_final_pp_eig_col",
            py_pair_final,
        ),
    ]

    transitions: list[dict[str, Any]] = []
    for i in range(1, len(ladder_ordered)):
        prev_n, prev_s = ladder_ordered[i - 1]
        cur_n, cur_s = ladder_ordered[i]
        transitions.append(
            {
                "from": prev_n,
                "to": cur_n,
                "delta_lo": float(cur_s["abs_lo"] - prev_s["abs_lo"]),
                "delta_hi": float(cur_s["abs_hi"] - prev_s["abs_hi"]),
                "leader_changed": (
                    prev_s["leader_0based"] is not None
                    and cur_s["leader_0based"] is not None
                    and prev_s["leader_0based"] != cur_s["leader_0based"]
                ),
            }
        )

    causal = _first_causal_flip(
        ladder_ordered, ref_pair_leader=int(ref_pair["leader_0based"])
    )

    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3b-b (column index corrected E3b-b3)",
        "sub_hash": HASH,
        "row_pair_0based": [ROW_LO_0, ROW_HI_0],
        "row_pair_1based": [ROW_LO_1, ROW_HI_1],
        "fortran_dbg_col": fortran_col,
        "fortran_dbg_col_note": "LAPACK KI=raw_col_for_jref+1 (idx[j_ref] before ascending-|w| pp)",
        "ref_jmax_0based": j_ref,
        "raw_jmax_0based": raw_j,
        "raw_col_for_jref_0based": raw_col_for_jref,
        "ki_jref_eq_raw_jmax": bool(raw_col_for_jref == raw_j),
        "wrong_index_j_ref_on_raw_v": bool(
            float(np.abs(v_v[ROW_LO_0, j_ref])) == 0.0
            and float(np.abs(v_v[ROW_HI_0, j_ref])) == 0.0
            and float(np.abs(v_v[ROW_LO_0, raw_col_for_jref])) > 0.0
        ),
        "kmax_ref": ref_leader,
        "kmax_py": py_leader,
        "kmax_match": ref_leader == py_leader,
        "ref_pair_at_jmax": ref_pair,
        "py_pair_at_jmax": py_pair_final,
        "ref_leader_on_pair": ref_pair["leader_0based"],
        "py_leader_on_pair": py_pair_final["leader_0based"],
        "dbg_hit": int(dbg.get("hit", 0)),
        "dbg_path_code": int(dbg.get("path_code", 0)),
        "dbg_path": dbg.get("path", "unknown"),
        "dbg_idamax_ii_1based": int(dbg.get("idamax_ii", 0)),
        "ladder_ordered": {name: st for name, st in ladder_ordered},
        "transitions": transitions,
        "first_causal_flip_vs_ref_kmax": causal,
        "oracle_kind": "spurious_plateau_inflation",
        "compute_patch_hint": (
            "E3b-c: owned-fork patch at first_causal_flip site to demote row 7 "
            "spurious max-tier inflation (not tie-band env)."
        ),
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3b_866_row_ladder.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    site = causal.get("site")
    print(
        f"[e3b-b 866 ladder] kmax ref={ref_leader} py={py_leader} "
        f"pair_leader ref={ref_pair['leader_0based']} py={py_pair_final['leader_0based']} "
        f"first_flip={site}"
    )
    print(f"[e3b-b 866 ladder] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
