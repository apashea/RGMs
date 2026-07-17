#!/usr/bin/env python3
"""Entry 4 E3c-a — ``866ab1a9…`` default-path ``order`` taxonomy (``eig.md`` §4.1 E3c).

Post-**K72** ``kmax`` is green; ``order`` fails with broad ``absv`` tail drift, not
rank-0 alone. Quantifies mismatch bands, plateau head, and tie-band counterfactual.
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
from python_src.utils.eig_spectral_policy import (
    apply_matlab_spectral_postprocess,
    sort_abs_descend_matlab_like,
    sort_abs_descend_matlab_tie_band,
)
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    first_order_mismatch,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "866ab1a9b2265fd6"
PLATEAU_RTOL = 1e-14
HEAD_RANKS = 16


def _plateau_indices(absv: np.ndarray) -> list[int]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    m = float(np.max(a))
    tol = max(1e-300, PLATEAU_RTOL * max(m, 1.0))
    return np.flatnonzero(np.abs(a - m) <= tol).astype(int).tolist()


def _rank_head(order_ref: np.ndarray, order_got: np.ndarray, *, n: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in range(min(n, len(order_ref), len(order_got))):
        ir = int(order_ref[r])
        ig = int(order_got[r])
        rows.append({"rank": r, "idx_ref": ir, "idx_got": ig, "match": ir == ig})
    return rows


def _mismatch_count(order_ref: np.ndarray, order_got: np.ndarray) -> int:
    n = min(len(order_ref), len(order_got))
    return int(np.sum(order_ref[:n] != order_got[:n]))


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3c 866 order] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3c 866 order] missing oracle blocks", file=sys.stderr)
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
    o_ref = dr["order"]
    o_def = dp["order"]
    o_tb = sort_abs_descend_matlab_tie_band(abs_py)

    mm_def = first_order_mismatch(o_ref, o_def, abs_ref, abs_py)
    mm_tb = first_order_mismatch(o_ref, o_tb, abs_ref, abs_py)

    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3c-a",
        "sub_hash": HASH,
        "backend": resolve_backend(),
        "n": int(sub.shape[0]),
        "jmax": int(dr["jmax"]),
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_got": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "order_ok_default": bool(np.array_equal(o_ref, o_def)),
        "order_ok_tie_band": bool(np.array_equal(o_ref, o_tb)),
        "order_mismatch_count_default": _mismatch_count(o_ref, o_def),
        "order_mismatch_count_tie_band": _mismatch_count(o_ref, o_tb),
        "first_mismatch_default": mm_def,
        "first_mismatch_tie_band": mm_tb,
        "plateau_ref": _plateau_indices(abs_ref),
        "plateau_py": _plateau_indices(abs_py),
        "spurious_py_plateau": sorted(
            set(_plateau_indices(abs_py)) - set(_plateau_indices(abs_ref))
        ),
        "rank_head_default": _rank_head(o_ref, o_def, n=HEAD_RANKS),
        "rank_head_tie_band": _rank_head(o_ref, o_tb, n=HEAD_RANKS),
        "max_absv_diff": float(np.max(np.abs(abs_ref - abs_py))),
        "mean_absv_diff": float(np.mean(np.abs(abs_ref - abs_py))),
        "oracle_kind": "full_column_absv_drift",
        "compute_patch_hint": (
            "866 order needs column-wide absv parity (plateau + tail), not rank-1 "
            "tier demote alone; tie-band does not fix (K73)."
        ),
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3c_866_order_taxonomy.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"[e3c 866 order] kmax_match={payload['kmax_match']} "
        f"order_def={payload['order_ok_default']} order_tb={payload['order_ok_tie_band']} "
        f"mismatch_def={payload['order_mismatch_count_default']} "
        f"first_def_rank={mm_def.get('rank') if mm_def else None}"
    )
    print(f"[e3c 866 order] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
