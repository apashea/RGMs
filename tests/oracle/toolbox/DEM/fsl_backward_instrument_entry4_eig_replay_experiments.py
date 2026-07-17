#!/usr/bin/env python3
"""Entry 4 — replay-corpus experiments for ``eig_nobalance`` (``eig.md`` §21).

Loads ``..._eig_failure_replay.pkl`` and measures what numpy-only transforms can
recover MATLAB spectral ``order`` (inspection; not production wiring).
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

from python_src.toolbox.DEM.spm_rgm_group import _sort_abs_descend_matlab_like
from python_src.utils.eig_layout_research import (
    align_column_signs_to_reference,
    assign_eigenpairs_greedy_w,
    sort_ulp_failure_report,
)
from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_dump_report_txt,
    entry4_eig_failure_replay_pkl,
    entry4_eig_oracle_blocks_pkl,
)


def _order_matches_matlab(sub, w_ref, v_ref, w, v) -> bool:
    dr = rgm_spectral_decisions(sub, w_ref, v_ref)
    dg = rgm_spectral_decisions(sub, w, v)
    return bool(np.array_equal(dr["order"], dg["order"]))


def _append_report(lines: list[str]) -> None:
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def main() -> int:
    replay_path = entry4_eig_failure_replay_pkl()
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not replay_path.is_file():
        print("[entry4 replay experiments] missing failure_replay.pkl — run deep inspection first", file=sys.stderr)
        return 2

    with replay_path.open("rb") as f:
        replay = pickle.load(f)
    entries = replay["entries"]

    all_blocks = []
    if blocks_path.is_file():
        with blocks_path.open("rb") as f:
            all_blocks = pickle.load(f)["blocks"]

    n_all = len(all_blocks)
    n_fail = len(entries)
    experiments: list[dict[str, Any]] = []

    for ent in entries:
        sub = np.asarray(ent["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(ent["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(ent["vecs_mat"], dtype=np.complex128)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)

        w0, v0 = eig_nobalance(sub)
        ok_raw = _order_matches_matlab(sub, w_ref, v_ref, w0, v0)

        w1, v1 = assign_eigenpairs_greedy_w(w0, v0, w_ref)
        ok_greedy = _order_matches_matlab(sub, w_ref, v_ref, w1, v1)

        v2 = align_column_signs_to_reference(v1, v_ref)
        ok_sign = _order_matches_matlab(sub, w_ref, v_ref, w1, v2)

        dg = rgm_spectral_decisions(sub, w1, v1)
        ulp = sort_ulp_failure_report(dr["absv"], dg["absv"], dr["order"], dg["order"])

        jmax_match_after_greedy = bool(dr["jmax"] == dg["jmax"])
        if ok_raw:
            kind = "pass"
        elif jmax_match_after_greedy:
            kind = "ulp_principal_absv_sort"
        else:
            kind = "layout_w_and_sort"

        experiments.append(
            {
                "sub_hash": ent["sub_hash"],
                "n": int(sub.shape[0]),
                "context": ent.get("context"),
                "order_ok": {"raw_eig_nobalance": ok_raw, "greedy_w_assign": ok_greedy, "greedy_plus_sign": ok_sign},
                "jmax": {
                    "matlab": int(dr["jmax"]),
                    "after_greedy": int(dg["jmax"]),
                    "match_after_greedy": jmax_match_after_greedy,
                },
                "ulp_sort": ulp,
                "classification": kind,
            }
        )

    n_pass_all = 0
    for blk in all_blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w, v = eig_nobalance(sub)
        if _order_matches_matlab(sub, w_ref, v_ref, w, v):
            n_pass_all += 1

    utc = datetime.now(timezone.utc).isoformat()
    out_path = replay_path.parent / "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_experiments.json"
    summary = {
        "utc": utc,
        "backend": resolve_backend(),
        "n_oracle_blocks": n_all,
        "n_pass_raw_eig_nobalance": n_pass_all,
        "n_fail_replay": n_fail,
        "n_fail_greedy_w_recovers_order": sum(1 for e in experiments if e["order_ok"]["greedy_w_assign"]),
        "policy": "numpy-only; geevx/MKL disabled (eig.md §21)",
    }
    payload = {"summary": summary, "failure_experiments": experiments}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
        f.write("\n")

    lines = [
        f"=== Entry 4 replay experiments {utc} ===",
        f"backend={summary['backend']} pass_raw={n_pass_all}/{n_all} fail={n_fail}",
        f"classification: "
        f"ulp_sort={sum(1 for e in experiments if e['classification']=='ulp_principal_absv_sort')} "
        f"layout_w={sum(1 for e in experiments if e['classification']=='layout_w_and_sort')} "
        f"pass={sum(1 for e in experiments if e['classification']=='pass')}",
        f"wrote={out_path}",
    ]
    for e in experiments:
        u = e["ulp_sort"]
        lines.append(
            f"  {e['sub_hash']} n={e['n']} raw={e['order_ok']['raw_eig_nobalance']} "
            f"greedy={e['order_ok']['greedy_w_assign']} "
            f"ulp_max_absv_diff={u['max_absv_vector_diff']:.3e} "
            f"rank_mismatch={u['n_rank_mismatches']}"
        )
    _append_report(lines)
    for ln in lines:
        print(f"[entry4 replay experiments] {ln}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
