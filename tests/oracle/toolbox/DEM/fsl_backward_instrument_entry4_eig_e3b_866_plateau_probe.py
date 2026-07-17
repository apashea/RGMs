#!/usr/bin/env python3
"""Entry 4 E3b — ``866ab1a9…`` plateau / ``kmax`` probe (``eig.md`` §4.1 E3b).

Mode B-β: live plateau **{28,58}** (``kmax=58``); vendored inflates **{7,28,52,58}**
to max so ``argmax`` returns **7**. Oracle replay quantifies demotion needed to
restore ``kmax=58``. No Fortran changes — guides owned-fork causal ladder.
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
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

HASH = "866ab1a9b2265fd6"
PLATEAU_RTOL = 1e-14
TRACK_IDX = (7, 28, 52, 58)


def _plateau_indices(absv: np.ndarray, *, rtol: float = PLATEAU_RTOL) -> list[int]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    if a.size == 0:
        return []
    m = float(np.max(a))
    tol = max(1e-300, rtol * max(m, 1.0))
    return np.flatnonzero(np.abs(a - m) <= tol).astype(int).tolist()


def _row_table(absv_ref: np.ndarray, absv_py: np.ndarray) -> list[dict[str, Any]]:
    m_ref = float(np.max(absv_ref))
    m_py = float(np.max(absv_py))
    tol_ref = max(1e-300, PLATEAU_RTOL * max(m_ref, 1.0))
    tol_py = max(1e-300, PLATEAU_RTOL * max(m_py, 1.0))
    rows: list[dict[str, Any]] = []
    for idx in TRACK_IDX:
        r = float(absv_ref[idx])
        p = float(absv_py[idx])
        rows.append(
            {
                "index": int(idx),
                "abs_ref": r,
                "abs_py": p,
                "delta_py_minus_ref": float(p - r),
                "on_plateau_ref": bool(abs(r - m_ref) <= tol_ref),
                "on_plateau_py": bool(abs(p - m_py) <= tol_py),
                "min_demote_delta_for_kmax_58": float(max(0.0, p - m_ref + 1e-15)),
            }
        )
    return rows


def _replay_kmax_after_demote(col: np.ndarray, demote: list[int], *, eps: float = 1.2e-14) -> int:
    c = np.asarray(col, dtype=np.complex128).copy()
    absv = np.abs(c)
    m58 = float(absv[58])
    for idx in demote:
        if absv[idx] <= 0:
            continue
        scale = max(0.0, (m58 - eps) / float(absv[idx]))
        c[idx] = c[idx] * scale
    return int(np.argmax(np.abs(c)))


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3b 866 plateau] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3b 866 plateau] missing oracle blocks", file=sys.stderr)
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
    j = int(dr["jmax"])
    col_pp = v_pp[:, j]
    abs_ref = dr["absv"]
    abs_py = dp["absv"]

    plateau_ref = _plateau_indices(abs_ref)
    plateau_py = _plateau_indices(abs_py)
    spurious_py = sorted(set(plateau_py) - set(plateau_ref))
    missing_py = sorted(set(plateau_ref) - set(plateau_py))

    replay_rows = []
    for demote in ([7], [7, 52], [7, 28, 52]):
        replay_rows.append(
            {
                "demote_indices": demote,
                "replay_kmax": _replay_kmax_after_demote(col_pp, demote),
            }
        )

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3b",
        "sub_hash": HASH,
        "backend": resolve_backend(),
        "n": int(sub.shape[0]),
        "jmax": j,
        "kmax_ref": int(np.argmax(abs_ref)),
        "kmax_py": int(np.argmax(abs_py)),
        "kmax_match": bool(np.argmax(abs_ref) == np.argmax(abs_py)),
        "plateau_ref": plateau_ref,
        "plateau_py": plateau_py,
        "spurious_py_plateau": spurious_py,
        "missing_py_plateau": missing_py,
        "oracle_kind": "spurious_plateau_inflation",
        "row_table": _row_table(abs_ref, abs_py),
        "replay_demote": replay_rows,
        "replay_leader_58_demote_set": [7, 28, 52],
        "compute_patch_hint": (
            "Demote rows 7/28/52 from false max-tier before DTREVC3 IDAMAX; "
            "causal site TBD (E3b-b row-pair ladder 7 vs 58)."
        ),
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3b_866_plateau_probe.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"[e3b 866 plateau] kmax ref={payload['kmax_ref']} py={payload['kmax_py']} "
        f"plateau_ref={plateau_ref} plateau_py={plateau_py} spurious={spurious_py}"
    )
    print(f"[e3b 866 plateau] replay demote [7,28,52] -> kmax={replay_rows[-1]['replay_kmax']}")
    print(f"[e3b 866 plateau] wrote={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
