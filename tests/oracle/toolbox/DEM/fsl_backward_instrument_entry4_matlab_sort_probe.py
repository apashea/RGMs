#!/usr/bin/env python3
"""Entry 4 — MATLAB ``sort(abs(...),'descend')`` probe on failure replay (``eig.md`` §22)."""
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
from python_src.utils.eig_nobalance import eig_nobalance
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import (
    entry4_dump_report_txt,
    entry4_eig_failure_replay_pkl,
)


def _matlab_sort_indices(eng: Any, absv: np.ndarray) -> np.ndarray:
    import matlab

    col = np.asarray(absv, dtype=np.float64).ravel().reshape(-1, 1)
    eng.workspace["rgms_absv"] = matlab.double(col.tolist())
    eng.eval("rgms_out = entry4_sort_abs_descend_probe(rgms_absv);", nargout=0)
    ix = np.asarray(eng.eval("rgms_out.ix"), dtype=np.float64).ravel()
    return (ix - 1).astype(np.int64)


def main() -> int:
    replay_path = entry4_eig_failure_replay_pkl()
    if not replay_path.is_file():
        print("[entry4 matlab sort probe] missing failure_replay.pkl", file=sys.stderr)
        return 2

    try:
        import matlab.engine
    except ImportError:
        print("[entry4 matlab sort probe] matlab.engine not available", file=sys.stderr)
        return 2

    with replay_path.open("rb") as f:
        replay = pickle.load(f)

    eng = matlab.engine.start_matlab()
    try:
        eng.addpath(str(_REPO / "matlab_custom"), nargout=0)
        rows: list[dict[str, Any]] = []
        for ent in replay["entries"]:
            sub = np.asarray(ent["sub_mi"], dtype=np.float64)
            w_ref = np.asarray(ent["vals_mat"], dtype=np.complex128)
            v_ref = np.asarray(ent["vecs_mat"], dtype=np.complex128)
            dr = rgm_spectral_decisions(sub, w_ref, v_ref)
            w_py, v_py = eig_nobalance(sub)
            j = int(dr["jmax"])
            absv_mat = dr["absv"]
            absv_py = np.abs(v_py[:, j])
            ix_mat = _matlab_sort_indices(eng, absv_mat)
            ix_py = _sort_abs_descend_matlab_like(absv_py)
            ix_mat_on_py = _matlab_sort_indices(eng, absv_py)
            rows.append(
                {
                    "sub_hash": ent["sub_hash"],
                    "n": int(sub.shape[0]),
                    "order_matlab_eig": dr["order"].tolist(),
                    "ix_numpy_sort_on_py_absv": ix_py.tolist(),
                    "ix_matlab_sort_on_mat_absv": ix_mat.tolist(),
                    "ix_matlab_sort_on_py_absv": ix_mat_on_py.tolist(),
                    "numpy_vs_matlab_sort_on_py_absv": bool(np.array_equal(ix_py, ix_mat_on_py)),
                    "mat_absv_sort_recovers_matlab_order": bool(
                        np.array_equal(dr["order"], ix_mat_on_py)
                    ),
                }
            )
    finally:
        eng.quit()

    utc = datetime.now(timezone.utc).isoformat()
    out_path = replay_path.parent / "DEMAtariIII_fsl_backward_entry4_rgm_spectral_matlab_sort_probe.json"
    payload = {"utc": utc, "rows": rows}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    lines = [
        f"=== Entry 4 MATLAB sort probe {utc} ===",
        f"wrote={out_path}",
    ]
    for r in rows:
        lines.append(
            f"  {r['sub_hash']} n={r['n']} "
            f"mat_sort_on_py={r['numpy_vs_matlab_sort_on_py_absv']} "
            f"mat_sort_recovers_order={r['mat_absv_sort_recovers_matlab_order']}"
        )
    entry4_dump_report_txt().parent.mkdir(parents=True, exist_ok=True)
    with entry4_dump_report_txt().open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for ln in lines:
        print(f"[entry4 matlab sort probe] {ln}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
