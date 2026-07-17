#!/usr/bin/env python3
"""Entry 4 E3d — classify remaining ``kmax`` reds ``4ab4f22d…`` / ``a03d7da5…`` (``eig.md`` §4.1).

Post-**K72** only these two seven-fail hashes still have ``kmax_mismatch``. Plateau /
row oracle replay per hash (no Fortran changes).
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

HASHES = ("4ab4f22de6228a3a", "a03d7da5d5c09bab", "7d978bc6b89bde7b")
PLATEAU_RTOL = 1e-14


def _plateau_indices(absv: np.ndarray) -> list[int]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    m = float(np.max(a))
    tol = max(1e-300, PLATEAU_RTOL * max(m, 1.0))
    return np.flatnonzero(np.abs(a - m) <= tol).astype(int).tolist()


def _replay_kmax_after_demote(
    col: np.ndarray, demote: list[int], *, kmax_ref: int, eps: float = 1.2e-14
) -> int:
    c = np.asarray(col, dtype=np.complex128).copy()
    absv = np.abs(c)
    target = float(absv[kmax_ref]) - eps
    for idx in demote:
        if absv[idx] <= 0:
            continue
        scale = max(0.0, target / float(absv[idx]))
        c[idx] = c[idx] * scale
    return int(np.argmax(np.abs(c)))


def _classify_one(blk: dict[str, Any]) -> dict[str, Any]:
    sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
    w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
    v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
    w_py, v_py = eig_nobalance(sub)
    w_pp, v_pp = apply_matlab_spectral_postprocess(w_py, v_py)
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dp = rgm_spectral_decisions(sub, w_pp, v_pp)
    j = int(dr["jmax"])
    abs_ref = dr["absv"]
    abs_py = dp["absv"]
    kmax_ref = int(np.argmax(abs_ref))
    kmax_py = int(np.argmax(abs_py))
    plateau_ref = _plateau_indices(abs_ref)
    plateau_py = _plateau_indices(abs_py)
    spurious = sorted(set(plateau_py) - set(plateau_ref))
    missing = sorted(set(plateau_ref) - set(plateau_py))

    pair_rows = [kmax_ref, kmax_py]
    if kmax_ref != kmax_py:
        pair_rows = sorted({kmax_ref, kmax_py})
    row_table = []
    for idx in pair_rows:
        r = float(abs_ref[idx])
        p = float(abs_py[idx])
        row_table.append(
            {
                "index": int(idx),
                "abs_ref": r,
                "abs_py": p,
                "delta_py_minus_ref": float(p - r),
                "on_plateau_ref": bool(idx in plateau_ref),
                "on_plateau_py": bool(idx in plateau_py),
            }
        )

    replay_rows = []
    if spurious:
        replay_rows.append(
            {
                "demote_indices": spurious,
                "replay_kmax": _replay_kmax_after_demote(
                    v_pp[:, j], spurious, kmax_ref=kmax_ref
                ),
            }
        )
    replay_rows.append(
        {
            "demote_indices": spurious + missing,
            "replay_kmax": _replay_kmax_after_demote(
                v_pp[:, j], spurious + missing, kmax_ref=kmax_ref
            ),
        }
    )

    if plateau_ref == plateau_py and kmax_ref != kmax_py:
        kind = "plateau_member_pick"
    elif spurious or missing:
        kind = "spurious_plateau_inflation" if spurious else "missing_plateau_member"
    elif kmax_ref != kmax_py:
        kind = "absv_ulp_leader"
    else:
        kind = "kmax_ok"

    return {
        "sub_hash": blk["sub_hash"],
        "n": int(sub.shape[0]),
        "jmax": j,
        "kmax_ref": kmax_ref,
        "kmax_py": kmax_py,
        "kmax_match": kmax_ref == kmax_py,
        "plateau_ref": plateau_ref,
        "plateau_py": plateau_py,
        "spurious_py_plateau": spurious,
        "missing_py_plateau": missing,
        "oracle_kind": kind,
        "row_table": row_table,
        "replay_demote": replay_rows,
    }


def main() -> int:
    if not lapack_nobalance_available():
        print("[e3d kmax classify] lapack_vendored not built", file=sys.stderr)
        return 2

    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[e3d kmax classify] missing oracle blocks", file=sys.stderr)
        return 2

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    with path.open("rb") as f:
        blocks = {b["sub_hash"]: b for b in pickle.load(f)["blocks"]}

    rows = [_classify_one(blocks[h]) for h in HASHES if h in blocks]

    payload: dict[str, Any] = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 E3d",
        "backend": resolve_backend(),
        "hashes": list(HASHES),
        "rows": rows,
    }

    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_e3d_kmax_classify_probe.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for row in rows:
        print(
            f"[e3d kmax classify] {row['sub_hash'][:8]}… "
            f"kind={row['oracle_kind']} kmax {row['kmax_ref']}->{row['kmax_py']} "
            f"plateau_ref={row['plateau_ref']} plateau_py={row['plateau_py']}"
        )
    print(f"[e3d kmax classify] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
