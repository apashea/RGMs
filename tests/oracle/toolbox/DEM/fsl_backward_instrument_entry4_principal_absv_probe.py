#!/usr/bin/env python3
"""Entry 4 — principal ``abs(e(:,jmax))`` probe (``eig.md`` §22–§23)."""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO))

from python_src.utils.eig_nobalance import eig_nobalance
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_dump_report_txt,
    entry4_eig_oracle_blocks_pkl,
)
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        return 2
    with blocks_path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    rows = []
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        h = blk.get("sub_hash", "")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        w_py, v_py = eig_nobalance(sub)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
        j = dr["jmax"]
        absv_m = dr["absv"]
        absv_p = np.abs(v_py[:, j])
        order_m = dr["order"]
        order_p = dp["order"]
        rows.append(
            {
                "sub_hash": h,
                "n": int(sub.shape[0]),
                "known_fail": h in KNOWN_FAIL_HASHES,
                "jmax_match": bool(dr["jmax"] == dp["jmax"]),
                "order_match": bool(np.array_equal(order_m, order_p)),
                "max_absv_diff": float(np.max(np.abs(absv_m - absv_p))),
                "n_sort_rank_mismatch": int(np.sum(order_m != order_p)),
                "l2_norm_py_principal": float(np.linalg.norm(v_py[:, j])),
                "l2_norm_mat_principal": float(np.linalg.norm(v_ref[:, j])),
            }
        )

    utc = datetime.now(timezone.utc).isoformat()
    out_path = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_rgm_spectral_principal_absv_probe.json"
    summary = {
        "utc": utc,
        "n_blocks": len(rows),
        "n_order_match": sum(1 for r in rows if r["order_match"]),
        "n_known_fail": sum(1 for r in rows if r["known_fail"]),
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, indent=2)
        f.write("\n")

    lines = [f"=== Entry 4 principal absv probe {utc} ===", f"order_match={summary['n_order_match']}/{summary['n_blocks']}", f"wrote={out_path}"]
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for ln in lines:
        print(f"[entry4 principal absv probe] {ln}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
