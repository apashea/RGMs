#!/usr/bin/env python3
"""Entry 4 B5.3 prep — ``absv`` component diff vs live Engine (``eig.md`` §4.1 O2)."""
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

from python_src.utils.eig_nobalance import eig_nobalance
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import KNOWN_FAIL_HASHES


def _absv_near_count(absv: np.ndarray, value: float, rtol: float = 1e-14) -> int:
    a = np.asarray(absv, dtype=np.float64).ravel()
    tol = max(1e-300, rtol * max(float(np.max(a)), float(value), 1.0))
    return int(np.sum(np.abs(a - float(value)) <= tol))


def _engine_absv(sub: np.ndarray, eng: Any) -> np.ndarray:
    import matlab

    eng.workspace["rgms_sub"] = matlab.double(np.asarray(sub, dtype=np.float64).tolist())
    eng.eval("rgms_out = entry4_eig_principal_column_probe(rgms_sub);", nargout=0)
    return np.asarray(eng.eval("rgms_out.absv"), dtype=np.float64).ravel()


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print("[absv component diff] missing oracle blocks", file=sys.stderr)
        return 2
    try:
        import matlab.engine
    except ImportError:
        print("[absv component diff] matlab.engine required", file=sys.stderr)
        return 2

    with blocks_path.open("rb") as f:
        by_hash = {str(b.get("sub_hash", "")): b for b in pickle.load(f)["blocks"]}

    eng = matlab.engine.start_matlab()
    rows: list[dict[str, Any]] = []
    try:
        eng.addpath(str(_REPO / "matlab_custom"), nargout=0)
        for h in sorted(KNOWN_FAIL_HASHES):
            blk = by_hash[h]
            sub = np.asarray(blk["sub_mi"], dtype=np.float64, order="F")
            w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
            v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
            absv_live = _engine_absv(sub, eng)
            w_py, v_py = eig_nobalance(sub)
            py = rgm_spectral_decisions(sub, w_py, v_py)
            absv_py = py["absv"]
            n = int(absv_py.size)
            d = np.abs(absv_py - absv_live)
            plateau = float(np.max(absv_live))
            tol = max(1e-300, 1e-14 * plateau)
            on_plateau = np.abs(absv_live - plateau) <= tol
            diff_mask = d > tol
            diff_on_plateau = diff_mask & on_plateau
            rows.append(
                {
                    "sub_hash": h,
                    "n": n,
                    "absv_max_live": plateau,
                    "n_on_plateau": int(np.sum(on_plateau)),
                    "n_diff_above_ulp": int(np.sum(diff_mask)),
                    "n_diff_on_plateau": int(np.sum(diff_on_plateau)),
                    "max_absv_diff": float(np.max(d)),
                    "frac_diff_on_plateau": float(np.sum(diff_on_plateau) / max(1, np.sum(on_plateau))),
                    "first_diff_index": int(np.argmax(diff_mask)) if np.any(diff_mask) else None,
                }
            )
    finally:
        eng.quit()

    payload = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "eig_md_section": "4.1",
        "rows": rows,
        "use": "High n_diff_on_plateau → B5.3 must fix principal column on tie set, not sort.",
    }
    out = blocks_path.parent / "DEMAtariIII_fsl_backward_entry4_eig_absv_component_diff.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[absv component diff] wrote {out}")
    for r in rows:
        print(
            f"  {r['sub_hash']}: plateau={r['n_on_plateau']} "
            f"diff_on_plateau={r['n_diff_on_plateau']} max_diff={r['max_absv_diff']:.3e}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
