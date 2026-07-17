#!/usr/bin/env python3
"""Entry 4 — sweep general ``eig_spectral_policy`` options (inspection; ``eig.md`` §27)."""
from __future__ import annotations

import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy.linalg as spla

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir

from python_src.utils.eig_spectral_policy import apply_matlab_spectral_postprocess
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl


def _score(blocks: list[dict], *, label: str, post_kwargs: dict) -> dict:
    order_ok = jmax_ok = 0
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w, v = spla.eig(sub, check_finite=False, overwrite_a=False)
        w = np.asarray(w, dtype=np.complex128).ravel(order="F")
        v = np.asarray(v, dtype=np.complex128, order="F")
        w, v = apply_matlab_spectral_postprocess(w, v, **post_kwargs)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w, v)
        jmax_ok += int(dr["jmax"] == dp["jmax"])
        order_ok += int(np.array_equal(dr["order"], dp["order"]))
    return {"label": label, "n": len(blocks), "order_ok": order_ok, "jmax_ok": jmax_ok, **post_kwargs}


def main() -> int:
    path = entry4_eig_oracle_blocks_pkl()
    if not path.is_file():
        print("[entry4 policy sweep] missing oracle blocks", file=sys.stderr)
        return 2
    with path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]

    policies = [
        _score(blocks, label="baseline_asc_l2", post_kwargs={"ascending_w": True, "canonicalize_columns": False, "l2_principal": True, "principal_refine": False}),
        _score(blocks, label="canonicalize_all_cols", post_kwargs={"ascending_w": True, "canonicalize_columns": True, "l2_principal": True, "principal_refine": False}),
        _score(blocks, label="degenerate_span_refine", post_kwargs={"ascending_w": True, "canonicalize_columns": True, "l2_principal": True, "principal_refine": True}),
    ]
    out = demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry4_eig_policy_sweep.json"
    payload = {"utc": datetime.now(timezone.utc).isoformat(), "policies": policies}
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[entry4 policy sweep] wrote {out}")
    for p in policies:
        print(f"  {p['label']}: order={p['order_ok']}/{p['n']} jmax={p['jmax_ok']}/{p['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
