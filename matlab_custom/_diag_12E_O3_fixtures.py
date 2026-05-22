"""12E.out_t2 O[3] and child P{2}(:,end) from paired fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
    _entry12_run_tag,
    _entry12_workspace_payload,
    _load_subentry_pkl,
    _mat_blob_to_py,
    _subentry_pkl_path,
)


def _peak(v):
    a = np.asarray(v, dtype=float).ravel()
    return a.size, int(np.argmax(a) + 1), float(a[0]), a[:6].tolist()


def _child(snap):
    m0 = snap["MDP"]
    if isinstance(m0, list):
        m0 = m0[0]
    c = m0["MDP"]
    return c[0] if isinstance(c, list) else c


def _child_P_end(snap, f=1):
    return np.asarray(_child(snap)["P"][f], dtype=np.float64)[:, -1]


def _o3(snap):
    O = snap["O"]
    if isinstance(O[0], (list, tuple)):
        return O[0][3]
    return O[3]


def main() -> None:
    tag = _entry12_run_tag()
    py_e = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12E")), "12E")
    mat_e = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12E"))),
        "12E",
    )
    py_f = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    for key in ("out_t1", "out_t2", "out_t3"):
        print(f"\n=== 12E {key} O[3] ===")
        print("mat", _peak(_o3(mat_e[key])))
        print("py ", _peak(_o3(py_e[key])))
        pe, me = _child_P_end(py_f[key]), _child_P_end(mat_f[key])
        print(f"child P{{2}}(:,end) diff max", float(np.max(np.abs(pe.ravel() - me.ravel()))))
        pc = _child(py_f[key])
        mc = _child(mat_f[key])
        Pf_py = np.asarray(pc["P"][1], dtype=np.float64)
        Pf_mat = np.asarray(mc["P"][1], dtype=np.float64)
        print(f"child P{{2}} shape py {Pf_py.shape} mat {Pf_mat.shape}")
        if Pf_py.shape[1] >= 2 and Pf_mat.shape[1] >= 2:
            print("P(:,1) diff", float(np.max(np.abs(Pf_py[:, 0] - Pf_mat[:, 0]))))
            print("P(:,2) diff", float(np.max(np.abs(Pf_py[:, 1] - Pf_mat[:, 1]))))


if __name__ == "__main__":
    main()
