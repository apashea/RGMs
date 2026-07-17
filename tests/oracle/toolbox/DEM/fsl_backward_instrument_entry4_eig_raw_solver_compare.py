#!/usr/bin/env python3
"""Entry 4 — raw eigensolver vs MATLAB dump (``eig.md`` §30.7).

Read-only. Scores scipy / vendored ``dgeevx`` **before** ``eig_spectral_policy``,
then after post-process, against captured ``vals_mat``/``vecs_mat``.
"""
from __future__ import annotations

import json
import pickle
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import scipy.linalg as spla

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    STAGE_OK,
    STAGE_PRINCIPAL_COL,
    STAGE_SORT_ABS,
    STAGE_W_SPECTRUM,
    analyze_w_stage,
    classify_failure_stage,
    granular_spectral_report,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

EigFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


def _scipy_raw(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    w, v = spla.eig(a, check_finite=False, overwrite_a=False)
    return (
        np.asarray(w, dtype=np.complex128).ravel(order="F"),
        np.asarray(v, dtype=np.complex128, order="F"),
    )


def _vendored_raw(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from python_src.utils.eig_lapack_nobalance import eig_real_nobalance

    w, v = eig_real_nobalance(a)
    return (
        np.asarray(w, dtype=np.complex128).ravel(order="F"),
        np.asarray(v, dtype=np.complex128, order="F"),
    )


def _with_postprocess(eig_fn: EigFn) -> EigFn:
    def _wrapped(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w, v = eig_fn(a)
        return apply_matlab_spectral_postprocess(w, v)

    return _wrapped


def _summarize_stage(rows: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        c[str(r.get("stage", "?"))] += 1
    return dict(c)


def _score_raw_w_jmax(blocks: list[dict], eig_fn: EigFn) -> dict[str, int]:
    jmax_ok = 0
    w_near_ok = 0
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128).ravel(order="F")
        w_py, _ = eig_fn(sub)
        ws = analyze_w_stage(w_ref, w_py)
        jmax_ok += int(ws.get("jmax_match", False))
        mad = ws.get("max_abs_w_diff")
        if mad is not None and float(mad) <= 1e-10:
            w_near_ok += 1
    n = len(blocks)
    return {"jmax_match": jmax_ok, "w_elementwise_1e10": w_near_ok, "n": n}


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[entry4 raw solver compare] missing oracle blocks pkl", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    backends: list[tuple[str, EigFn, bool]] = [
        ("scipy_eig_raw", _scipy_raw, True),
        ("scipy_eig_postprocess", _with_postprocess(_scipy_raw), True),
    ]
    try:
        from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available

        if lapack_nobalance_available():
            backends.extend(
                [
                    ("vendored_dgeevx_raw", _vendored_raw, True),
                    ("vendored_dgeevx_postprocess", _with_postprocess(_vendored_raw), True),
                ]
            )
    except ImportError:
        pass

    backend_reports: list[dict[str, Any]] = []
    for label, eig_fn, run_granular in backends:
        rows = []
        if run_granular:
            for blk in blocks:
                sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
                w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
                v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
                rows.append(
                    granular_spectral_report(
                        sub,
                        w_ref,
                        v_ref,
                        eig_fn=eig_fn,
                        label=label,
                    )
                )
        order_ok = sum(1 for r in rows if r.get("order_ok"))
        stage_counts = _summarize_stage(rows)
        raw_w = _score_raw_w_jmax(blocks, eig_fn) if label.endswith("_raw") else None
        fail_stage = _summarize_stage([r for r in rows if str(r.get("sub_hash")) in KNOWN_FAIL_HASHES])
        backend_reports.append(
            {
                "label": label,
                "order_ok": order_ok,
                "n": len(blocks),
                "stage_counts_all": stage_counts,
                "stage_counts_seven_fail_hashes": fail_stage,
                "raw_w_scores": raw_w,
            }
        )

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "30.7",
        "n_blocks": len(blocks),
        "known_fail_hashes": sorted(KNOWN_FAIL_HASHES),
        "matlab_reference": "Intel oneMKL 2024.1 / LAPACK 3.11 (captured vals_mat/vecs_mat; §29)",
        "oss_netlib": "LAPACK 3.12 dgeevx subset, gfortran DLL (§25)",
        "backends": backend_reports,
        "interpretation_guide": {
            STAGE_W_SPECTRUM: "raw (w,V) layout / jmax differs before sort",
            STAGE_PRINCIPAL_COL: "jmax matches but |V(:,jmax)| differs (ULP / phase)",
            STAGE_SORT_ABS: "principal absv ties sort differently",
            STAGE_OK: "full order matches MATLAB dump path",
        },
    }
    out = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_eig_raw_solver_compare.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[entry4 raw solver compare] wrote {out}")
    for br in backend_reports:
        sc = br.get("stage_counts_all", {})
        rw = br.get("raw_w_scores")
        extra = f" raw_w={rw}" if rw else ""
        print(f"  {br['label']}: order={br['order_ok']}/{br['n']} stages={sc}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
