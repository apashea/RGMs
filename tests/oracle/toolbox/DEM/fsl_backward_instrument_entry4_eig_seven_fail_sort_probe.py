#!/usr/bin/env python3
"""Entry 4 A1+A2 — seven-fail ``sort(abs(e(:,jmax)),'descend')`` probe (``eig.md`` §13.1).

A1: first-rank ``order`` mismatch vs MATLAB dump + local ``absv`` tie counts.
A2: live Engine ``spm_rgm_group`` spectral step vs ``eig_nobalance`` (same seven hashes).
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from python_src.utils.eig_spectral_policy import sort_abs_descend_matlab_like
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    analyze_w_stage,
    classify_failure_stage,
    first_order_mismatch,
    granular_spectral_report,
    rgm_spectral_decisions,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES

EigFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


def _absv_near_count(absv: np.ndarray, value: float, *, rtol: float = 1e-14) -> int:
    a = np.asarray(absv, dtype=np.float64).ravel()
    if a.size == 0:
        return 0
    tol = max(1e-300, rtol * max(float(np.max(a)), float(value), 1.0))
    return int(np.sum(np.abs(a - float(value)) <= tol))


def _enrich_mismatch(
    mismatch: dict[str, Any] | None, absv_ref: np.ndarray, absv_got: np.ndarray
) -> dict[str, Any] | None:
    if mismatch is None:
        return None
    if mismatch.get("note") == "length_mismatch":
        return mismatch
    ir = int(mismatch["idx_ref"])
    ig = int(mismatch["idx_got"])
    ar = float(mismatch["absv_ref"])
    ag = float(mismatch["absv_got"])
    out = dict(mismatch)
    out["absv_equal_at_ulp"] = bool(abs(ar - ag) <= max(1e-300, 1e-14 * max(ar, ag, 1.0)))
    out["n_ref_within_tol_of_absv_ref"] = _absv_near_count(absv_ref, ar)
    out["n_got_within_tol_of_absv_got"] = _absv_near_count(absv_got, ag)
    out["n_ref_within_tol_of_absv_got"] = _absv_near_count(absv_ref, ag)
    return out


def _report_block(
    sub: np.ndarray,
    w_ref: np.ndarray,
    v_ref: np.ndarray,
    *,
    label: str,
    eig_fn: EigFn,
) -> dict[str, Any]:
    rep = granular_spectral_report(sub, w_ref, v_ref, eig_fn=eig_fn, label=label)
    ref = rgm_spectral_decisions(sub, w_ref, v_ref)
    w_py, v_py = eig_fn(sub)
    got = rgm_spectral_decisions(sub, w_py, v_py)
    ws = rep.get("w_stage") or {}
    absv_max = float(np.max(ref["absv"])) if ref["absv"].size else 0.0
    return {
        "label": label,
        "stage": rep.get("stage"),
        "order_ok": rep.get("order_ok"),
        "jmax_ok": rep.get("jmax_ok"),
        "jmax_ref": rep.get("jmax_ref"),
        "jmax_got": rep.get("jmax_got"),
        "max_abs_principal_col_diff": rep.get("max_abs_principal_col_diff"),
        "w_stage_jmax_match": ws.get("jmax_match"),
        "w_stage_max_abs_w_diff": ws.get("max_abs_w_diff"),
        "order_first_mismatch": _enrich_mismatch(
            rep.get("order_first_mismatch"), ref["absv"], got["absv"]
        ),
        "absv_max": absv_max,
        "n_absv_ties_at_principal_max": _absv_near_count(ref["absv"], absv_max),
    }


def _engine_spectral(sub: np.ndarray, eng: Any) -> dict[str, Any]:
    import matlab

    eng.workspace["rgms_sub"] = matlab.double(np.asarray(sub, dtype=np.float64).tolist())
    eng.eval("rgms_out = entry4_eig_principal_column_probe(rgms_sub);", nargout=0)
    n = int(sub.shape[0])
    w = np.asarray(eng.eval("rgms_out.w"), dtype=np.complex128).ravel(order="F")
    order = np.asarray(eng.eval("rgms_out.order"), dtype=np.float64).ravel().astype(np.int64) - 1
    absv = np.asarray(eng.eval("rgms_out.absv"), dtype=np.float64).ravel()
    jmax = int(np.asarray(eng.eval("rgms_out.jmax"), dtype=np.float64).ravel()[0]) - 1
    sorted_absv = np.asarray(eng.eval("rgms_out.sorted_absv"), dtype=np.float64).ravel()
    return {
        "w": w,
        "jmax": jmax,
        "absv": absv,
        "order": order,
        "sorted_absv_head": sorted_absv[: min(10, sorted_absv.size)].tolist(),
        "n": n,
    }


def _compare_engine_to_py(
    sub: np.ndarray, w_ref: np.ndarray, v_ref: np.ndarray, eng: Any
) -> dict[str, Any]:
    w_py, v_py = eig_nobalance(sub)
    py = rgm_spectral_decisions(sub, w_py, v_py)
    live = _engine_spectral(sub, eng)
    dump = rgm_spectral_decisions(sub, w_ref, v_ref)
    order_live_py = _enrich_mismatch(
        first_order_mismatch(live["order"], py["order"], live["absv"], py["absv"]),
        live["absv"],
        py["absv"],
    )
    order_dump_py = _enrich_mismatch(
        first_order_mismatch(dump["order"], py["order"], dump["absv"], py["absv"]),
        dump["absv"],
        py["absv"],
    )
    order_dump_live = _enrich_mismatch(
        first_order_mismatch(dump["order"], live["order"], dump["absv"], live["absv"]),
        dump["absv"],
        live["absv"],
    )
    return {
        "engine_order_equals_py": bool(np.array_equal(live["order"], py["order"])),
        "dump_order_equals_py": bool(np.array_equal(dump["order"], py["order"])),
        "dump_order_equals_live_engine": bool(np.array_equal(dump["order"], live["order"])),
        "order_first_mismatch_live_vs_py": order_live_py,
        "order_first_mismatch_dump_vs_py": order_dump_py,
        "order_first_mismatch_dump_vs_live": order_dump_live,
        "py_stage_vs_dump_eigpairs": classify_failure_stage(dump, py, w_stage=analyze_w_stage(dump["w"], py["w"])),
        "max_absv_diff_live_py": float(np.max(np.abs(live["absv"] - py["absv"]))),
        "py_sort_from_engine_absv": sort_abs_descend_matlab_like(live["absv"]).tolist()[:10],
        "engine_order_head": live["order"][:10].tolist(),
        "py_order_head": py["order"][:10].tolist(),
    }


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[seven-fail sort probe] missing oracle blocks", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    by_hash = {str(b.get("sub_hash", "")): b for b in blocks}

    a1_rows: list[dict[str, Any]] = []
    for h in sorted(KNOWN_FAIL_HASHES):
        blk = by_hash.get(h)
        if blk is None:
            a1_rows.append({"sub_hash": h, "error": "missing_from_oracle_blocks"})
            continue
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        row: dict[str, Any] = {
            "sub_hash": h,
            "n": int(sub.shape[0]),
            "eig_nobalance_default": _report_block(
                sub, w_ref, v_ref, label="eig_nobalance", eig_fn=eig_nobalance
            ),
        }
        try:
            from python_src.utils.eig_lapack_nobalance import eig_real_nobalance, lapack_nobalance_available
            from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess

            if lapack_nobalance_available():

                def vendored_pp(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
                    w, v = eig_real_nobalance(a)
                    return apply_matlab_spectral_postprocess(w, v)

                row["lapack_vendored"] = _report_block(
                    sub, w_ref, v_ref, label="lapack_vendored", eig_fn=vendored_pp
                )
        except ImportError:
            pass
        a1_rows.append(row)

    a2_rows: list[dict[str, Any]] = []
    a2_note: str | None = None
    try:
        import matlab.engine
    except ImportError:
        a2_note = "matlab.engine not available"
    else:
        eng = matlab.engine.start_matlab()
        try:
            eng.addpath(str(_REPO / "matlab_custom"), nargout=0)
            for h in sorted(KNOWN_FAIL_HASHES):
                blk = by_hash[h]
                sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
                w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
                v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
                a2_rows.append(
                    {
                        "sub_hash": h,
                        **_compare_engine_to_py(sub, w_ref, v_ref, eng),
                    }
                )
        finally:
            eng.quit()

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "13.1",
        "backend_default": resolve_backend(),
        "known_fail_hashes": sorted(KNOWN_FAIL_HASHES),
        "a1_dump_vs_python": a1_rows,
        "a2_engine_vs_python": a2_rows,
        "a2_note": a2_note,
        "interpretation": (
            "If order_first_mismatch.absv_equal_at_ulp and high tie counts → MATLAB tie-break "
            "on sort(abs(e(:,jmax)),'descend'); implement in owned fork (B5.3). "
            "If dump_order_equals_live_engine but not py → Python eig/post-process gap."
        ),
    }
    out = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_eig_seven_fail_sort_probe.json"
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"[seven-fail sort probe] wrote {out}")
    for row in a1_rows:
        rep = row.get("eig_nobalance_default", {})
        mm = (rep.get("order_first_mismatch") or {}) if isinstance(rep, dict) else {}
        print(
            f"  A1 {row.get('sub_hash')}: stage={rep.get('stage')} rank={mm.get('rank')} "
            f"absv_equal_ulp={mm.get('absv_equal_at_ulp')} ties_ref={mm.get('n_ref_within_tol_of_absv_ref')}"
        )
    if a2_rows:
        for row in a2_rows:
            mm = row.get("order_first_mismatch_live_vs_py") or {}
            print(
                f"  A2 {row['sub_hash']}: live==py_order={row.get('engine_order_equals_py')} "
                f"dump==py={row.get('dump_order_equals_py')} rank={mm.get('rank')}"
            )
    elif a2_note:
        print(f"  A2 skipped: {a2_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
