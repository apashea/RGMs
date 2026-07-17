#!/usr/bin/env python3
"""Entry 4 — multi-solver T0 matrix + fail/pass structure (``eig.md`` §29).

Read-only. Scores each backend against MATLAB dump references; records tie
structure on principal ``absv``. No production wiring.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import scipy.linalg as spla

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

EigFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


def _scipy_eig(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    w, v = spla.eig(a, check_finite=False, overwrite_a=False)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    return w, v


def _numpy_eig(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    w, v = np.linalg.eig(a)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    return w, v


def _vendored_eig(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from python_src.utils.eig_lapack_nobalance import eig_real_nobalance

    return eig_real_nobalance(a)


def _geevx_nobalance_raw(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """LAPACK ``geevx`` ``balanc='N'`` — raw pair; post-process applied in ``_score_backend``."""
    from scipy.linalg import lapack

    from python_src.utils.eig_nobalance import _real_geev_evecs_to_complex

    a_f = np.asarray(a, dtype=np.float64, order="F")
    geevx = lapack.get_lapack_funcs("geevx", (a_f,))
    out = geevx(a_f, balanc="N", jobvl="N", jobvr="V", sense="N")
    wr, wi, _vl, vr = out[0], out[1], out[2], out[3]
    info = int(out[-1])
    if info != 0:
        raise RuntimeError(f"LAPACK geevx failed with info={info}")
    w = np.asarray(wr, dtype=np.float64) + 1j * np.asarray(wi, dtype=np.float64)
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v = _real_geev_evecs_to_complex(np.asarray(vr, dtype=np.float64), wi)
    return w, v


def _dgeev_balanced(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from scipy.linalg import lapack

    wr, wi, _, vr, info = lapack.dgeev(a, compute_vl=0, compute_vr=1)
    if int(info) != 0:
        raise RuntimeError(f"dgeev info={info}")
    n = int(a.shape[0])
    wi = np.asarray(wi, dtype=np.float64).ravel(order="F")
    w = np.asarray(wr, dtype=np.float64) + 1j * wi
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    vr = np.asarray(vr, dtype=np.float64)
    vc = np.zeros((n, n), dtype=np.complex128, order="F")
    k = 0
    while k < n:
        if abs(float(wi[k])) < 1e-300:
            vc[:, k] = vr[:, k]
            k += 1
        else:
            vc[:, k] = vr[:, k] + 1j * vr[:, k + 1]
            vc[:, k + 1] = vr[:, k] - 1j * vr[:, k + 1]
            k += 2
    return w, vc


def _principal_absv_tie_count(absv: np.ndarray) -> int:
    a = np.asarray(absv, dtype=np.float64).ravel()
    if a.size < 2:
        return 0
    s = np.sort(a)[::-1]
    tol = max(1e-15, 1e-14 * float(s[0]))
    return int(np.sum(np.abs(s[:-1] - s[1:]) < tol))


def _score_backend(blocks: list[dict], eig_fn: EigFn, label: str) -> dict[str, Any]:
    order_ok = jmax_ok = 0
    fail_only_order = 0
    tie_fail: list[int] = []
    tie_pass: list[int] = []
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w, v = eig_fn(sub)
        w, v = apply_matlab_spectral_postprocess(w, v)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w, v)
        jmax_ok += int(dr["jmax"] == dp["jmax"])
        ok = bool(np.array_equal(dr["order"], dp["order"]))
        order_ok += int(ok)
        h = str(blk.get("sub_hash", ""))
        ties = _principal_absv_tie_count(dp["absv"])
        if h in KNOWN_FAIL_HASHES:
            tie_fail.append(ties)
            if ok:
                fail_only_order += 1
        else:
            tie_pass.append(ties)
    return {
        "label": label,
        "order_ok": order_ok,
        "jmax_ok": jmax_ok,
        "n": len(blocks),
        "fail_group_absv_tie_mean": float(np.mean(tie_fail)) if tie_fail else None,
        "pass_group_absv_tie_mean": float(np.mean(tie_pass)) if tie_pass else None,
    }


def main() -> int:
    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[entry4 solver matrix] missing oracle blocks", file=sys.stderr)
        return 2

    with path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    backends: list[tuple[str, EigFn]] = [
        ("scipy_eig", _scipy_eig),
        ("numpy_eig", _numpy_eig),
    ]
    try:
        from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available

        if lapack_nobalance_available():
            backends.append(("vendored_dgeevx_nobalance", _vendored_eig))
    except ImportError:
        pass
    backends.append(("lapack_dgeev_balanced", _dgeev_balanced))

    allow_geevx = str(os.getenv("RGMS_EIG_NOBALANCE_ALLOW_GEEVX", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if allow_geevx:
        from python_src.utils.eig_nobalance import geevx_available

        if geevx_available():
            backends.append(("scipy_geevx_nobalance", _geevx_nobalance_raw))

    rows = [_score_backend(blocks, fn, label) for label, fn in backends]
    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "mkl_probe": allow_geevx,
        "n_blocks": len(blocks),
        "known_fail_hashes": sorted(KNOWN_FAIL_HASHES),
        "backends": rows,
        "structure_note": (
            "Seven fail blocks show higher principal-column |abs| tie counts than passing blocks; "
            "all tested OpenBLAS-family solvers score 51/58 order."
        ),
        "toolchain_leads": [
            "MATLAB-linked BLAS/LAPACK (e.g. MKL) build of geevx/nobalance — not in rgms SciPy",
            "Compare live MATLAB eig vectors (Engine probe §28) — post-process OK at 58/58",
        ],
    }
    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_solver_matrix.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[entry4 solver matrix] wrote {out}")
    for r in rows:
        print(
            f"  {r['label']}: order={r['order_ok']}/{r['n']} "
            f"fail_tie_mean={r['fail_group_absv_tie_mean']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
