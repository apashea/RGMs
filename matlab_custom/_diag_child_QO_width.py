"""Child mdp.Q.O column width at 12F boundaries (S→O seg driver)."""
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


def _child(snap):
    m0 = snap["MDP"]
    if isinstance(m0, list):
        m0 = m0[0]
    c = m0["MDP"]
    return c[0] if isinstance(c, list) else c


def _q_o_ncols(c):
    q = c.get("Q")
    if not isinstance(q, dict) or "O" not in q:
        return None, None
    L = max(1, int(np.asarray(c.get("L", 1)).ravel()[0]))
    oc = q["O"]
    if not isinstance(oc, (list, tuple)) or len(oc) < L:
        return L, None
    ol = oc[L - 1]
    if isinstance(ol, np.ndarray):
        return L, int(ol.shape[1]) if ol.ndim >= 2 else int(ol.size > 0)
    if isinstance(ol, (list, tuple)):
        return L, len(ol)
    return L, None


def main() -> None:
    tag = _entry12_run_tag()
    py_f = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    for key in ("out_t1", "out_t2"):
        print(f"\n{key}")
        for label, snap in ("mat", mat_f[key]), ("py", py_f[key]):
            c = _child(snap)
            L, w = _q_o_ncols(c)
            S = c.get("S")
            sh = np.asarray(S).shape if S is not None else None
            print(f"  {label} L={L} Q.O width={w} S.shape={sh} T={c.get('T')}")


if __name__ == "__main__":
    main()
