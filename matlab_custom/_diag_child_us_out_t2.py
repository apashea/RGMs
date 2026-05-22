"""child u,s at 12F out_t2."""
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
    m0 = snap["MDP"][0] if isinstance(snap["MDP"], list) else snap["MDP"]
    c = m0["MDP"]
    return c[0] if isinstance(c, list) else c


def main() -> None:
    tag = _entry12_run_tag()
    py_f = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    pc, mc = _child(py_f["out_t2"]), _child(mat_f["out_t2"])
    for fld in ("u", "s"):
        a = np.asarray(pc[fld], dtype=np.float64)
        b = np.asarray(mc[fld], dtype=np.float64)
        print(fld, "diff", float(np.max(np.abs(a.ravel() - b.ravel()))), "py", a.ravel()[:8], "mat", b.ravel()[:8])


if __name__ == "__main__":
    main()
