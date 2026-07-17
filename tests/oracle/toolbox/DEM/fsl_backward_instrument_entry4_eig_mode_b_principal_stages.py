#!/usr/bin/env python3
"""Entry 4 Mode B — principal column stage ladder (``eig.md`` §4.1 O3, pre-fork)."""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy.linalg as spla

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_lapack_nobalance import eig_real_nobalance, lapack_nobalance_available
from python_src.utils.eig_spectral_policy import (
    apply_matlab_spectral_postprocess,
    canonicalize_all_eigenvector_columns,
    l2_normalize_principal_column,
    reorder_eigenpairs_ascending_abs_w,
)
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

MODE_B_HASHES = ("2d5f8b838be81f21", "866ab1a9b2265fd6")
PLATEAU_RTOL = 1e-14
PLATEAU_INDEX_CAP = 32
PLATEAU_MEMBER_INDEX_CAP = 16


def _plateau_member_abs(
    absv: np.ndarray,
    indices: list[int],
    *,
    rtol: float = PLATEAU_RTOL,
) -> dict[str, Any]:
    """Per-index |V(:,jmax)| at live plateau members (E2d forensic)."""
    a = np.asarray(absv, dtype=np.float64).ravel()
    m = float(np.max(a)) if a.size else 0.0
    tol = max(1e-300, rtol * max(m, 1.0))
    head = indices[:PLATEAU_MEMBER_INDEX_CAP]
    return {
        "absv_max": m,
        "tol": tol,
        "members": [
            {
                "index": int(i),
                "abs": float(a[i]),
                "delta_from_max": float(a[i] - m),
                "on_plateau": bool(abs(a[i] - m) <= tol),
            }
            for i in head
            if 0 <= i < a.size
        ],
    }


def _plateau_at_max(absv: np.ndarray, *, rtol: float = PLATEAU_RTOL) -> dict[str, Any]:
    a = np.asarray(absv, dtype=np.float64).ravel()
    if a.size == 0:
        return {"n_at_plateau": 0, "plateau_indices": [], "absv_max": 0.0}
    m = float(np.max(a))
    tol = max(1e-300, rtol * max(m, 1.0))
    idx = np.flatnonzero(np.abs(a - m) <= tol)
    return {
        "n_at_plateau": int(idx.size),
        "plateau_indices": idx[:PLATEAU_INDEX_CAP].astype(int).tolist(),
        "absv_max": m,
    }


def _stage_row(
    sub: np.ndarray,
    w_ref: np.ndarray,
    v_ref: np.ndarray,
    w: np.ndarray,
    v: np.ndarray,
    *,
    label: str,
    backend: str,
) -> dict[str, Any]:
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dp = rgm_spectral_decisions(sub, w, v)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    j = int(np.argmax(np.abs(w)))
    col = v[:, j]
    kmax = int(np.argmax(np.abs(col)))
    absv_diff = float(np.max(np.abs(dp["absv"] - dr["absv"])))
    plateau = _plateau_at_max(dp["absv"])
    return {
        "label": label,
        "backend": backend,
        "jmax": j,
        "jmax_match_ref": j == int(dr["jmax"]),
        "kmax_abs_entry": kmax,
        "kmax_match_live": None,
        "order_ok": bool(np.array_equal(dr["order"], dp["order"])),
        "max_absv_diff": absv_diff,
        "col_cosine_vs_dump": float(
            abs(np.vdot(col, dr["v"][:, dr["jmax"]]))
            / (np.linalg.norm(col) * np.linalg.norm(dr["v"][:, dr["jmax"]]) + 1e-300)
        ),
        **plateau,
    }


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[mode B stages] missing oracle blocks", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        by_hash = {str(b.get("sub_hash", "")): b for b in pickle.load(f)["blocks"]}

    live_kmax: dict[str, int] = {}
    live_plateau: dict[str, dict[str, Any]] = {}
    live_absv: dict[str, np.ndarray] = {}
    try:
        import matlab.engine

        eng = matlab.engine.start_matlab()
        eng.addpath(str(_REPO / "matlab_custom"), nargout=0)
        for h in MODE_B_HASHES:
            sub = by_hash[h]["sub_mi"]
            eng.workspace["rgms_sub"] = __import__("matlab").double(
                np.asarray(sub, dtype=np.float64).tolist()
            )
            eng.eval("rgms_out = entry4_eig_principal_column_probe(rgms_sub);", nargout=0)
            # MATLAB probe returns 1-based ``kmax``; Python rows use 0-based.
            live_kmax[h] = int(eng.eval("rgms_out.kmax_abs_entry")) - 1
            absv_live = np.asarray(eng.eval("rgms_out.absv"), dtype=np.float64).ravel()
            live_absv[h] = absv_live
            live_plateau[h] = _plateau_at_max(absv_live)
        eng.quit()
    except Exception as exc:  # pragma: no cover
        print(f"[mode B stages] Engine skipped: {exc}", file=sys.stderr)

    rows: list[dict[str, Any]] = []
    stage_absv_cache: dict[tuple[str, str], np.ndarray] = {}
    for h in MODE_B_HASHES:
        blk = by_hash[h]
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)

        w_s, v_s = spla.eig(sub, check_finite=False)
        w_s = np.asarray(w_s, dtype=np.complex128).ravel(order="F")
        v_s = np.asarray(v_s, dtype=np.complex128, order="F")

        stages: list[tuple[str, str, np.ndarray, np.ndarray]] = [
            ("scipy_raw", "scipy", w_s, v_s),
        ]
        if lapack_nobalance_available():
            w_v, v_v = eig_real_nobalance(sub)
            stages.append(("vendored_raw", "lapack_vendored", w_v, v_v))
            w_vp, v_vp = apply_matlab_spectral_postprocess(w_v, v_v)
            stages.append(("vendored_matlab_pp", "lapack_vendored", w_vp, v_vp))

        w_a, v_a = reorder_eigenpairs_ascending_abs_w(w_s.copy(), v_s.copy())
        stages.append(("scipy_asc_w", "scipy", w_a, v_a))
        v_c = canonicalize_all_eigenvector_columns(v_a.copy())
        stages.append(("scipy_asc_canon", "scipy", w_a, v_c))
        v_l = l2_normalize_principal_column(w_a, v_c.copy())
        stages.append(("scipy_full_pp", "scipy", w_a, v_l))
        w_p, v_p = apply_matlab_spectral_postprocess(w_s, v_s)
        stages.append(("scipy_apply_matlab_pp", "scipy", w_p, v_p))

        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        j_ref = int(dr["jmax"])
        for label, backend, w, v in stages:
            row = _stage_row(sub, w_ref, v_ref, w, v, label=label, backend=backend)
            row["sub_hash"] = h
            if h in live_kmax:
                row["kmax_match_live"] = row["kmax_abs_entry"] == live_kmax[h]
                row["live_kmax_abs_entry"] = live_kmax[h]
                row["live_kmax_matlab_1based"] = live_kmax[h] + 1
            rows.append(row)
            if label in ("vendored_matlab_pp", "scipy_apply_matlab_pp"):
                stage_absv_cache[(h, label)] = np.abs(v[:, j_ref])

    plateau_member_abs: dict[str, dict[str, Any]] = {}
    for h in MODE_B_HASHES:
        if h not in live_plateau:
            continue
        member_idx = live_plateau[h]["plateau_indices"]
        plateau_member_abs[h] = {}
        for label in ("vendored_matlab_pp", "scipy_apply_matlab_pp"):
            key = (h, label)
            if key in stage_absv_cache:
                plateau_member_abs[h][label] = _plateau_member_abs(
                    stage_absv_cache[key], member_idx
                )
        if h in live_absv:
            plateau_member_abs[h]["live_matlab"] = _plateau_member_abs(
                live_absv[h], member_idx
            )

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1 O3 E2d",
        "mode_b_hashes": list(MODE_B_HASHES),
        "plateau_rtol": PLATEAU_RTOL,
        "live_plateau": live_plateau,
        "plateau_member_abs": plateau_member_abs,
        "rows": rows,
    }
    out = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_eig_mode_b_principal_stages.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for h in MODE_B_HASHES:
        sub_rows = [r for r in rows if r["sub_hash"] == h]
        print(f"[mode B stages] {h}")
        if h in live_plateau:
            lp = live_plateau[h]
            print(
                f"  live_matlab              n_plateau={lp['n_at_plateau']} "
                f"kmax={live_kmax.get(h)} indices_head={lp['plateau_indices'][:8]}"
            )
        for r in sub_rows:
            print(
                f"  {r['label']:24s} order_ok={r['order_ok']} kmax={r['kmax_abs_entry']} "
                f"live_match={r['kmax_match_live']} n_plateau={r['n_at_plateau']} "
                f"max_absv_diff={r['max_absv_diff']:.3e}"
            )
    print(f"[mode B stages] wrote={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
