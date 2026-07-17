#!/usr/bin/env python3
"""Entry 4 E3c-b-b4 — ``866ab1a9…`` multi-row ``DHSEQR`` dust-tier ladder (``eig.md`` §4.2 K86).

Post-**K83**/**K85**. Greedy **33** rows (K78 drift ladder) + rank-2 ``ORDER_ROWS``: per-row
``snap_hsevr`` capture vs ref/final ``absv``; greedy-prefix final ``absv`` replay oracles.
No Fortran changes.
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
from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from python_src.utils.eig_nobalance import resolve_backend
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "866ab1a9b2265fd6"
ANCHOR_ROW_0 = 28
ORDER_ROWS = (1, 7, 28, 52, 58)
GREEDY_PREFIX_MILESTONES = (1, 5, 10, 17, 33)


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def _greedy_snap_order(abs_py: np.ndarray, abs_ref: np.ndarray) -> list[int]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    return list(np.argsort(-d).astype(int))


def _greedy_close_count(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> int:
    order_idx = _greedy_snap_order(abs_py, abs_ref)
    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    for k, i in enumerate(order_idx):
        hyb[i] = float(abs_ref[i])
        if _mismatch_count(order_ref, _sort_abs_descend_matlab_like(hyb)) == 0:
            return k + 1
    return len(order_idx)


def _capture_dhseqr_abs(sub: np.ndarray, *, fortran_col: int, row_0: int) -> float:
    anchor = ANCHOR_ROW_0 if row_0 != ANCHOR_ROW_0 else 1
    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    if row_0 < anchor:
        dtrevc3_debug_set_row_pair(row_0 + 1, anchor + 1)
        slot = "post_dhseqr_schur_vr_col_abs_13"
    else:
        dtrevc3_debug_set_row_pair(anchor + 1, row_0 + 1)
        slot = "post_dhseqr_schur_vr_col_abs_44"
    eig_real_nobalance(sub)
    dbg = dtrevc3_debug_get()
    return float(dbg[slot])


def _replay_oracles(
    abs_py: np.ndarray,
    abs_ref: np.ndarray,
    order_ref: np.ndarray,
    greedy_rows: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(name: str, vec: np.ndarray, **extra: Any) -> None:
        order_got = _sort_abs_descend_matlab_like(vec)
        rows.append(
            {
                "replay": name,
                "mismatch_count": _mismatch_count(order_ref, order_got),
                "rank1_got": int(order_got[1]),
                "rank1_ref": int(order_ref[1]),
                "rank2_got": int(order_got[2]) if order_got.size > 2 else None,
                "rank2_ref": int(order_ref[2]) if order_ref.size > 2 else None,
                **extra,
            }
        )

    add("live_py", abs_py)
    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    for i in ORDER_ROWS:
        hyb[i] = float(abs_ref[i])
    add("snap_order_rows_5", hyb, rows_snapped=list(ORDER_ROWS))

    for k in GREEDY_PREFIX_MILESTONES:
        if k > len(greedy_rows):
            continue
        hyb = np.asarray(abs_py, dtype=np.float64).copy()
        for i in greedy_rows[:k]:
            hyb[i] = float(abs_ref[i])
        add(
            f"snap_greedy_prefix_{k}",
            hyb,
            rows_snapped=[int(i) for i in greedy_rows[:k]],
        )

    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    for i in greedy_rows:
        hyb[i] = float(abs_ref[i])
    add("snap_greedy_all", hyb, rows_snapped=[int(i) for i in greedy_rows])

    hyb = np.asarray(abs_ref, dtype=np.float64).copy()
    add("full_ref_absv_hybrid", hyb)
    return rows


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c 866 dhseqr multrow] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c 866 dhseqr multrow] missing oracle blocks", file=sys.stderr)
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
    order_ref = dr["order"]

    w_probe, _ = eig_real_nobalance(sub)
    w_probe = np.asarray(w_probe, dtype=np.complex128).ravel(order="F")
    perm = np.argsort(np.abs(w_probe), kind="mergesort")
    raw_col = int(perm[j_ref])
    fortran_col = raw_col + 1

    dtrevc3_debug_reset()
    dtrevc3_debug_set_col(fortran_col)
    w_v, v_v = eig_real_nobalance(sub)
    w_pp, v_pp = apply_matlab_spectral_postprocess(w_v, v_v)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_py = dp["absv"]

    greedy_rows = _greedy_snap_order(abs_py, abs_ref)
    greedy_close = _greedy_close_count(abs_py, abs_ref, order_ref)
    greedy_33 = greedy_rows[:33]

    probe_rows = sorted(set(greedy_33) | set(ORDER_ROWS))
    dhseqr_table: list[dict[str, Any]] = []
    for row_0 in probe_rows:
        hse = _capture_dhseqr_abs(sub, fortran_col=fortran_col, row_0=row_0)
        final_py = float(abs_py[row_0])
        final_ref = float(abs_ref[row_0])
        dhseqr_table.append(
            {
                "row_0based": int(row_0),
                "dhseqr_abs_py": hse,
                "final_abs_py": final_py,
                "final_abs_ref": final_ref,
                "dhseqr_minus_ref_final": float(hse - final_ref),
                "final_py_minus_ref": float(final_py - final_ref),
                "dhseqr_to_final_py_ratio": (
                    float(hse / final_py) if final_py != 0.0 else None
                ),
                "in_greedy_33": bool(row_0 in greedy_33),
            }
        )

    n_dhseqr_gt_1e15 = sum(
        1 for r in dhseqr_table if abs(r["dhseqr_minus_ref_final"]) > 1e-15
    )
    n_final_gt_1e15 = sum(1 for r in dhseqr_table if abs(r["final_py_minus_ref"]) > 1e-15)

    replays = _replay_oracles(abs_py, abs_ref, order_ref, greedy_rows)
    mm = _mismatch_count(order_ref, dp["order"])
    fm = first_order_mismatch(order_ref, dp["order"], abs_ref, abs_py)

    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.2 E3c-b-b4",
        "sub_hash": HASH,
        "backend": resolve_backend(),
        "fortran_dbg_col": fortran_col,
        "anchor_row_0based": ANCHOR_ROW_0,
        "n": int(sub.shape[0]),
        "order_mismatch_count": mm,
        "greedy_close_snap_count": int(greedy_close),
        "greedy_snap_order_33": [int(i) for i in greedy_33],
        "first_mismatch_default": fm,
        "rank1_ref": int(order_ref[1]),
        "rank1_py": int(dp["order"][1]),
        "rank1_match": bool(order_ref[1] == dp["order"][1]),
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_got": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "dhseqr_row_table": dhseqr_table,
        "dhseqr_drift_summary": {
            "probe_row_count": len(probe_rows),
            "n_dhseqr_minus_ref_gt_1e-15": n_dhseqr_gt_1e15,
            "n_final_py_minus_ref_gt_1e-15": n_final_gt_1e15,
        },
        "replay_oracles": replays,
        "oracle_kind": "wide_column_absv_drift_dhseqr_multrow",
        "compute_patch_hint": (
            "K86: per-row snap_hsevr drift vs ref final for greedy 33 + ORDER_ROWS; "
            "greedy-prefix final snap does not close order at 33; fork needs "
            "multi-row DHSEQR column fidelity not post-DSCAL demote."
        ),
    }

    out = (
        path.parent
        / "DEMAtariIII_fsl_backward_entry4_eig_e3c_866_dhseqr_multrow_ladder.json"
    )
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    ro = {r["replay"]: r for r in replays}
    print(
        f"[e3c 866 dhseqr multrow] mm={mm}/{payload['n']} "
        f"greedy_close={greedy_close} rank1={payload['rank1_match']} "
        f"dhseqr_drift_rows={n_dhseqr_gt_1e15}/{len(probe_rows)} "
        f"snap5={ro['snap_order_rows_5']['mismatch_count']} "
        f"snap33={ro.get('snap_greedy_prefix_33', ro['snap_greedy_all'])['mismatch_count']}"
    )
    print(f"[e3c 866 dhseqr multrow] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
