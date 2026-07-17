#!/usr/bin/env python3
"""Entry 4 — read-only spectral / ``eig_nobalance`` diagnosis (``eig.md`` §19).

Reads canonical dump PKLs. Writes:

- ``..._eig_diagnosis.json`` — summary + probe rows
- ``..._eig_diagnosis_granular.json`` — per-block stage ladder (W → jmax → sort → chosen)

Appends human summary to ``matlab_custom/fsl_backward_entry4_rgm_spectral_eig_dump_output.txt``.
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance, geevx_available, resolve_backend
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import (
    STAGE_OK,
    STAGE_SORT_ABS,
    STAGE_W_SPECTRUM,
    compare_eig_to_matlab_ref,
    granular_spectral_report,
    probe_record_decisions,
    scipy_eig_fn,
    stage_counts,
    sub_hash,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_dump_report_txt,
    entry4_eig_diagnosis_granular_json,
    entry4_eig_diagnosis_json,
    entry4_eig_oracle_blocks_pkl,
    entry4_matlab_eig_records_mat,
    entry4_python_engine_probe_pkl,
)


def _append_report(lines: list[str]) -> None:
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def _load_matlab_records_v7() -> list[dict[str, Any]] | None:
    mat_path = entry4_matlab_eig_records_mat()
    if not mat_path.is_file():
        return None
    try:
        from scipy.io import loadmat
    except ImportError:
        return None
    try:
        raw = loadmat(str(mat_path), simplify_cells=True)
    except NotImplementedError:
        return None
    recs = raw.get("rgms_entry4_spectral_records")
    if recs is None:
        return None
    return [r for r in recs if isinstance(r, dict)]


def _index_probe_by_hash(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rec in records:
        h = sub_hash(np.asarray(rec["sub_mi"], dtype=np.float64))
        out[h] = rec
    return out


def main() -> int:
    probe_path = entry4_python_engine_probe_pkl()
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not probe_path.is_file() or not blocks_path.is_file():
        print(
            "[entry4 eig diagnosis] missing dump PKLs — run fsl_backward_dump_entry4_spectral_eig.py first",
            file=sys.stderr,
        )
        return 2

    with probe_path.open("rb") as f:
        probe = pickle.load(f)
    with blocks_path.open("rb") as f:
        blocks_payload = pickle.load(f)
    records: list[dict] = probe["records"]
    blocks: list[dict] = blocks_payload["blocks"]
    probe_by_hash = _index_probe_by_hash(records)

    probe_rows = [probe_record_decisions(r) for r in records]
    n_probe = len(probe_rows)
    n_mat_probe_ok = sum(1 for x in probe_rows if x["mat_recompute_matches_probe"])
    n_scipy_vs_mat = sum(1 for x in probe_rows if x["scipy_vs_matlab_order"])

    granular_nb: list[dict[str, Any]] = []
    granular_sp: list[dict[str, Any]] = []
    nobalance_rows: list[dict[str, Any]] = []
    scipy_rows: list[dict[str, Any]] = []

    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        h = blk.get("sub_hash") or sub_hash(sub)
        prec = probe_by_hash.get(h)
        granular_nb.append(
            granular_spectral_report(
                sub, w_ref, v_ref, eig_fn=eig_nobalance, label="eig_nobalance", probe_rec=prec
            )
        )
        granular_sp.append(
            granular_spectral_report(
                sub, w_ref, v_ref, eig_fn=scipy_eig_fn, label="scipy.linalg.eig", probe_rec=prec
            )
        )
        nobalance_rows.append(
            compare_eig_to_matlab_ref(
                sub, w_ref, v_ref, eig_fn=eig_nobalance, label="eig_nobalance", probe_rec=prec
            )
        )
        scipy_rows.append(
            compare_eig_to_matlab_ref(
                sub, w_ref, v_ref, eig_fn=scipy_eig_fn, label="scipy.linalg.eig", probe_rec=prec
            )
        )

    n_blocks = len(blocks)
    nb_stages = stage_counts(granular_nb)
    fail_nb = [g for g in granular_nb if g["stage"] != STAGE_OK]
    sort_only = [g for g in fail_nb if g["stage"] == STAGE_SORT_ABS and g.get("jmax_ok")]
    w_only = [g for g in fail_nb if g["stage"] == STAGE_W_SPECTRUM]

    n_nb_order = sum(1 for x in nobalance_rows if x["order_ok"])
    n_nb_jmax = sum(1 for x in nobalance_rows if x["jmax_ok"])
    n_sp_order = sum(1 for x in scipy_rows if x["order_ok"])
    first_fail = fail_nb[0] if fail_nb else None

    mat_recs = _load_matlab_records_v7()
    mat_v7_note = "loaded" if mat_recs else "unavailable"

    utc = datetime.now(timezone.utc).isoformat()
    summary = {
        "utc": utc,
        "backend": resolve_backend(),
        "geevx_available": geevx_available(),
        "n_probe_records": n_probe,
        "n_oracle_blocks": n_blocks,
        "probe_mat_order_matches_capture": n_mat_probe_ok,
        "probe_scipy_order_matches_matlab_eig": n_scipy_vs_mat,
        "eig_nobalance_order_ok": n_nb_order,
        "eig_nobalance_jmax_ok": n_nb_jmax,
        "scipy_order_ok": n_sp_order,
        "eig_nobalance_stage_counts": nb_stages,
        "n_eig_nobalance_fail": len(fail_nb),
        "n_fail_w_spectrum": len(w_only),
        "n_fail_sort_abs_jmax_ok": len(sort_only),
        "matlab_mat_file": mat_v7_note,
        "first_fail": first_fail,
    }

    granular_path = entry4_eig_diagnosis_granular_json()
    with granular_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "meta": {
                    "purpose": "Per-block spectral stage ladder vs MATLAB Engine eig reference",
                    "stages": [
                        "W_SPECTRUM",
                        "PRINCIPAL_COL",
                        "SORT_ABS",
                        "CHOSEN_THRESH",
                        "PROBE_CAPTURE",
                        "OK",
                    ],
                },
                "summary": summary,
                "granular_eig_nobalance": granular_nb,
                "granular_scipy": granular_sp,
            },
            f,
            indent=2,
            default=str,
        )
        f.write("\n")

    diag_path = entry4_eig_diagnosis_json()
    with diag_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "probe_rows": probe_rows,
                "eig_nobalance": nobalance_rows,
                "scipy": scipy_rows,
            },
            f,
            indent=2,
            default=str,
        )
        f.write("\n")

    lines = [
        f"=== Entry 4 eig diagnosis (granular) {utc} ===",
        f"backend={summary['backend']} geevx={summary['geevx_available']}",
        f"blocks={n_blocks} probe_records={n_probe}",
        f"stages_eig_nobalance={nb_stages}",
        f"fail_w_spectrum={len(w_only)} fail_sort_abs_with_jmax_ok={len(sort_only)}",
        f"order_ok={n_nb_order}/{n_blocks} jmax_ok={n_nb_jmax}/{n_blocks}",
        f"wrote_granular={granular_path}",
        f"wrote_summary={diag_path}",
    ]
    if first_fail:
        ctx = first_fail.get("context") or {}
        wm = first_fail.get("order_first_mismatch") or {}
        lines.append(
            "first_fail: "
            f"stage={first_fail['stage']} hash={first_fail['sub_hash']} n={first_fail['n']} "
            f"lev={ctx.get('lev_call')} stream={ctx.get('stream_idx')} iter={ctx.get('iter_idx')} "
            f"jmax {first_fail['jmax_ref']}->{first_fail['jmax_got']} "
            f"sort_rank0 mismatch={wm}"
        )
    _append_report(lines)
    for ln in lines:
        print(f"[entry4 eig diagnosis] {ln}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
