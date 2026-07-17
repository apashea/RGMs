#!/usr/bin/env python3
"""Entry 4 — principal-column delta vs MATLAB dump (guides owned-fork edits).

Read-only. For each backend, reports ``max|V(:,jmax)_oss - V(:,jmax)_mat|`` on the
seven known-fail blocks and summary on the passing set. See ``eig.md`` §30.8.
"""
from __future__ import annotations

import json
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

from python_src.utils.eig_nobalance import eig_nobalance
from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

EigFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


def _principal_delta(
    w_ref: np.ndarray, v_ref: np.ndarray, w: np.ndarray, v: np.ndarray
) -> dict[str, Any]:
    w_ref = np.asarray(w_ref, dtype=np.complex128).ravel(order="F")
    w = np.asarray(w, dtype=np.complex128).ravel(order="F")
    v_ref = np.asarray(v_ref, dtype=np.complex128, order="F")
    v = np.asarray(v, dtype=np.complex128, order="F")
    j_ref = int(np.argmax(np.abs(w_ref)))
    j = int(np.argmax(np.abs(w)))
    c_ref = v_ref[:, j_ref]
    c = v[:, j]
    if np.vdot(c_ref, c).real < 0:
        c = -c
    d = np.abs(c_ref - c)
    return {
        "jmax_ref": j_ref,
        "jmax_got": j,
        "jmax_match": j_ref == j,
        "max_abs_diff": float(np.max(d)),
        "mean_abs_diff": float(np.mean(d)),
        "l2_ref": float(np.linalg.norm(c_ref)),
        "l2_got": float(np.linalg.norm(c)),
    }


def _score_backend(blocks: list[dict], label: str, eig_fn: EigFn) -> dict[str, Any]:
    fail_rows: list[dict[str, Any]] = []
    pass_max: list[float] = []
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w, v = eig_fn(sub)
        row = {
            "sub_hash": str(blk.get("sub_hash", "")),
            **_principal_delta(w_ref, v_ref, w, v),
        }
        h = row["sub_hash"]
        if h in KNOWN_FAIL_HASHES:
            fail_rows.append(row)
        else:
            pass_max.append(row["max_abs_diff"])
    return {
        "label": label,
        "fail_blocks": fail_rows,
        "fail_max_abs_diff_mean": float(np.mean([r["max_abs_diff"] for r in fail_rows]))
        if fail_rows
        else None,
        "pass_max_abs_diff_max": float(np.max(pass_max)) if pass_max else None,
    }


def main() -> int:
    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[entry4 principal delta] missing oracle blocks", file=sys.stderr)
        return 2

    with path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    def scipy_pp(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w, v = spla.eig(a, check_finite=False, overwrite_a=False)
        w = np.asarray(w, dtype=np.complex128).ravel(order="F")
        v = np.asarray(v, dtype=np.complex128, order="F")
        return apply_matlab_spectral_postprocess(w, v)

    backends: list[tuple[str, EigFn]] = [
        ("scipy_postprocess", scipy_pp),
        ("eig_nobalance_default", lambda a: eig_nobalance(a)),
    ]
    try:
        from python_src.utils.eig_lapack_nobalance import eig_real_nobalance, lapack_nobalance_available

        if lapack_nobalance_available():

            def vendored_pp(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
                w, v = eig_real_nobalance(a)
                return apply_matlab_spectral_postprocess(w, v)

            backends.append(("vendored_dgeevx_postprocess", vendored_pp))
    except ImportError:
        pass

    reports = [_score_backend(blocks, label, fn) for label, fn in backends]
    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "30.8",
        "known_fail_hashes": sorted(KNOWN_FAIL_HASHES),
        "backends": reports,
        "use": "Target edits in tools/eig_lapack_nobalance/src/ or vendor/ to reduce fail_max on seven hashes.",
    }
    out = path.parent / "DEMAtariIII_fsl_backward_entry4_eig_principal_delta.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[entry4 principal delta] wrote {out}")
    for r in reports:
        print(
            f"  {r['label']}: fail_mean_max_abs_diff={r['fail_max_abs_diff_mean']:.6e} "
            f"pass_worst={r['pass_max_abs_diff_max']:.6e}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
