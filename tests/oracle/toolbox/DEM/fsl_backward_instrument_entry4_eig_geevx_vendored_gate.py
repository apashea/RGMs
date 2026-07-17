#!/usr/bin/env python3
"""Option B gate — vendored ``dgeevx`` vs MATLAB on seven fail hashes, then 58 (``eig.md`` §25)."""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.utils.eig_lapack_nobalance import lapack_nobalance_available
from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_dump_report_txt, entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES


def _score_blocks(blocks: list[dict], *, label: str) -> dict:
    order_ok = jmax_ok = 0
    fail_order: list[str] = []
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
        if dr["jmax"] == dp["jmax"]:
            jmax_ok += 1
        if np.array_equal(dr["order"], dp["order"]):
            order_ok += 1
        else:
            fail_order.append(str(blk.get("sub_hash", "")))
    return {
        "label": label,
        "n": len(blocks),
        "order_ok": order_ok,
        "jmax_ok": jmax_ok,
        "order_fail_hashes": fail_order,
    }


def main() -> int:
    if not lapack_nobalance_available():
        print(
            "[entry4 geevx vendored gate] native library not built — "
            "see eig.md §25.4",
            file=sys.stderr,
        )
        return 2

    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[entry4 geevx vendored gate] missing oracle blocks pkl", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        all_blocks = pickle.load(f)["blocks"]
    fail_blocks = [b for b in all_blocks if b.get("sub_hash") in KNOWN_FAIL_HASHES]

    import os

    os.environ["RGMS_EIG_NOBALANCE_BACKEND"] = "lapack_vendored"

    utc = datetime.now(timezone.utc).isoformat()
    seven = _score_blocks(fail_blocks, label="seven_fail_hashes")
    full = _score_blocks(all_blocks, label="all_58")

    payload = {
        "utc": utc,
        "backend": resolve_backend(),
        "lapack_nobalance_available": True,
        "seven_fail_gate": seven,
        "full_corpus": full,
        "pass_criteria": {"seven_fail_order_ok": 7, "full_order_ok": 58},
    }
    out = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_rgm_spectral_geevx_vendored_gate.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    lines = [
        f"=== Entry 4 geevx vendored gate {utc} ===",
        f"seven_fail order={seven['order_ok']}/7 jmax={seven['jmax_ok']}/7",
        f"full order={full['order_ok']}/58",
        f"wrote={out}",
    ]
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for ln in lines:
        print(f"[entry4 geevx vendored gate] {ln}", file=sys.stderr)
    return 0 if seven["order_ok"] == 7 and full["order_ok"] == 58 else 1


if __name__ == "__main__":
    raise SystemExit(main())
