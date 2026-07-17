#!/usr/bin/env python3
"""Entry 4 E3c-b-b1 — ``866ab1a9…`` column ``absv`` snap ladder (``eig.md`` §4.1).

Post-**K77** (``kmax`` **58/58**). Quantifies how many per-row ``absv`` snaps close default-path
``order``, greedy drift-priority ladder, plateau-head replay, and ref-``absv`` hybrid oracle.
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

from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available
from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "866ab1a9b2265fd6"
PLATEAU_RTOL = 1e-14
DRIFT_THRESHOLDS = (1e-15, 1e-14, 1e-13)


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def _plateau_indices(absv: np.ndarray) -> list[int]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    m = float(np.max(a))
    tol = max(1e-300, PLATEAU_RTOL * max(m, 1.0))
    return np.flatnonzero(np.abs(a - m) <= tol).astype(int).tolist()


def _greedy_snap_ladder(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> dict[str, Any]:
    d = np.abs(np.asarray(abs_py, dtype=np.float64) - np.asarray(abs_ref, dtype=np.float64))
    order_idx = list(np.argsort(-d))
    hyb = np.asarray(abs_py, dtype=np.float64).copy()
    steps: list[dict[str, Any]] = []
    close_at: int | None = None
    for k, i in enumerate(order_idx):
        hyb[i] = float(abs_ref[i])
        mm = _mismatch_count(order_ref, _sort_abs_descend_matlab_like(hyb))
        if k < 8 or mm in (0, 1, 2, 5, 10, 54, 55, 58, 59):
            steps.append(
                {
                    "snap_count": k + 1,
                    "row": int(i),
                    "drift": float(d[i]),
                    "mismatch_count": mm,
                }
            )
        if mm == 0 and close_at is None:
            close_at = k + 1
    if close_at is None:
        close_at = len(order_idx)
    return {
        "greedy_close_snap_count": int(close_at),
        "greedy_snap_order": [int(i) for i in order_idx[:close_at]],
        "ladder_steps": steps,
    }


def _replay_demote_spurious(
    abs_py: np.ndarray, abs_ref: np.ndarray, order_ref: np.ndarray
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for eps in (5e-15, 1e-14, 1.2e-14, 1.5e-14, 2e-14, 3e-14, 5e-14):
        a = np.asarray(abs_py, dtype=np.float64).copy()
        for i in (7, 52):
            a[i] *= 1.0 - eps
        rows.append(
            {
                "replay": f"demote_rows_7_52_eps_{eps:g}",
                "mismatch_count": _mismatch_count(
                    order_ref, _sort_abs_descend_matlab_like(a)
                ),
                "kmax_got": int(np.argmax(a)),
            }
        )
    a = np.asarray(abs_py, dtype=np.float64).copy()
    a[7] = float(abs_ref[7])
    a[52] = float(abs_ref[52])
    rows.append(
        {
            "replay": "snap_rows_7_52_to_ref",
            "mismatch_count": _mismatch_count(order_ref, _sort_abs_descend_matlab_like(a)),
            "kmax_got": int(np.argmax(a)),
        }
    )
    big = [i for i in range(abs_py.size) if abs(abs_py[i] - abs_ref[i]) > 1e-15]
    a = np.asarray(abs_py, dtype=np.float64).copy()
    for i in big:
        a[i] = float(abs_ref[i])
    rows.append(
        {
            "replay": "snap_all_rows_drift_gt_1e-15",
            "mismatch_count": _mismatch_count(order_ref, _sort_abs_descend_matlab_like(a)),
            "kmax_got": int(np.argmax(a)),
            "rows": big,
        }
    )
    a = np.asarray(abs_ref, dtype=np.float64).copy()
    rows.append(
        {
            "replay": "full_ref_absv_hybrid",
            "mismatch_count": _mismatch_count(order_ref, _sort_abs_descend_matlab_like(a)),
            "kmax_got": int(np.argmax(a)),
        }
    )
    return rows


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c 866 snap] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c 866 snap] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blk = [b for b in pickle.load(f)["blocks"] if b["sub_hash"] == HASH][0]

    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    w_py, v_py = eig_nobalance(sub)
    w_pp, v_pp = apply_matlab_spectral_postprocess(w_py, v_py)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    abs_ref = dr["absv"]
    abs_py = dp["absv"]
    order_ref = dr["order"]
    order_py = dp["order"]

    d = np.abs(abs_py - abs_ref)
    drift_stats: dict[str, Any] = {
        "max_abs_diff": float(np.max(d)),
        "mean_abs_diff": float(np.mean(d)),
    }
    for thr in DRIFT_THRESHOLDS:
        drift_stats[f"n_rows_gt_{thr:g}"] = int(np.sum(d > thr))

    graft_self_consistent = bool(
        np.array_equal(_sort_abs_descend_matlab_like(abs_ref), order_ref)
    )
    hybrid_mm = _mismatch_count(
        order_ref, _sort_abs_descend_matlab_like(np.asarray(abs_ref, dtype=np.float64))
    )

    ladder = _greedy_snap_ladder(abs_py, abs_ref, order_ref)
    replays = _replay_demote_spurious(abs_py, abs_ref, order_ref)

    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3c-b-b1",
        "sub_hash": HASH,
        "backend": resolve_backend(),
        "n": int(sub.shape[0]),
        "jmax": int(dr["jmax"]),
        "order_mismatch_count_default": _mismatch_count(order_ref, order_py),
        "first_mismatch_default": first_order_mismatch(
            order_ref, order_py, abs_ref, abs_py
        ),
        "plateau_ref": _plateau_indices(abs_ref),
        "plateau_py": _plateau_indices(abs_py),
        "spurious_py_plateau": sorted(
            set(_plateau_indices(abs_py)) - set(_plateau_indices(abs_ref))
        ),
        "absv_diff": drift_stats,
        "graft_ref_absv_self_consistent": graft_self_consistent,
        "hybrid_ref_absv_mismatch_count": hybrid_mm,
        "greedy_snap_ladder": ladder,
        "replay_demote": replays,
        "compute_patch_hint": (
            "866 order needs >=33 coupled per-row absv snaps (greedy drift order); "
            "plateau-head demote/snap alone leaves 55–58/63 mismatches; "
            "postprocess does not change drift (LAPACK column fidelity)."
        ),
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3c_866_absv_snap_ladder.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"[e3c 866 snap] mm={payload['order_mismatch_count_default']}/{payload['n']} "
        f"greedy_close={ladder['greedy_close_snap_count']} "
        f"snap8big={replays[-2]['mismatch_count']} "
        f"hybrid_ref_mm={hybrid_mm}"
    )
    print(f"[e3c 866 snap] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
