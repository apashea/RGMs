"""Diag nested child Y{o,t} vs MATLAB at 12F out_t1 (first red causal step)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.spm_dot import spm_dot
from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from python_src.toolbox.DEM.spm_parents import spm_parents
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
    _entry12_run_tag,
    _entry12_workspace_payload,
    _load_subentry_pkl,
    _mat_blob_to_py,
    _subentry_pkl_path,
)


def _max_idx(arr) -> int:
    a = np.asarray(arr, dtype=float).ravel()
    return int(np.argmax(a))


def main() -> int:
    tag = _entry12_run_tag()
    py_ws = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_ws = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    py_child = py_ws["out_t1"]["MDP"]["MDP"]
    mat_child = mat_ws["out_t1"]["MDP"]["MDP"]
    py_Y = py_child["Y"]
    mat_Y = mat_child["Y"]
    print("py Y shape", len(py_Y), "x", len(py_Y[0]) if py_Y else 0)
    print("mat Y flat len", len(mat_Y) if isinstance(mat_Y, list) else type(mat_Y))

    def flat_y(mat_y, o_1b: int, t_1b: int, n_o: int = 9) -> np.ndarray:
        idx = (t_1b - 1) * n_o + (o_1b - 1)
        return np.asarray(mat_y[idx], dtype=float).ravel()

    for o_1b, t_1b in ((1, 1), (2, 1), (1, 2)):
        pv = np.asarray(py_Y[o_1b - 1][t_1b - 1], dtype=float).ravel()
        mv = flat_y(mat_Y, o_1b, t_1b)
        d = np.max(np.abs(pv - mv)) if pv.size == mv.size else None
        print(f"Y{{{o_1b},{t_1b}}} maxdiff={d} py_peak={_max_idx(pv)} mat_peak={_max_idx(mv)}")

    # Rebuild Q row from child returned Q (list of factor matrices) if present
    py_Q = py_child.get("Q")
    if isinstance(py_Q, list) and py_Q and isinstance(py_Q[0], np.ndarray):
        t_idx = 0
        qrow = [np.asarray(py_Q[f], dtype=float)[:, t_idx : t_idx + 1] for f in range(len(py_Q))]
        print("child Q from returned list, n_factors", len(qrow))
    else:
        qrow = None
        print("child Q type", type(py_Q))

    id_py = py_child.get("id", {})
    A_py = py_child.get("A", id_py.get("A"))
    ng = len(A_py) if isinstance(A_py, list) else 0
    print("Ng", ng, "ff", id_py.get("ff"), "max_o", len(py_Y))

    if qrow is not None and ng > 0:
        for g_1b in range(1, min(ng + 1, 6)):
            j, i_ch = spm_parents(id_py, g_1b, qrow)
            j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
            q_list = [qrow[int(jj) - 1] for jj in j_arr.tolist()]
            Ag = np.asarray(A_py[g_1b - 1], dtype=float)
            pred = np.asarray(spm_dot(Ag, q_list), dtype=float).ravel()
            i_flat = np.atleast_1d(np.asarray(i_ch, dtype=float).ravel()).astype(int)
            print(
                f"g={g_1b} j={j_arr.tolist()} i={i_flat.tolist()} "
                f"pred_peak={_max_idx(pred)} pred[:5]={pred[:5]}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
