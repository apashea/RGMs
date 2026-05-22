"""MAT child P{2} across 12F boundaries."""
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
    _mat_blob_to_py,
)


def _child(snap):
    m0 = snap["MDP"][0] if isinstance(snap["MDP"], list) else snap["MDP"]
    c = m0["MDP"]
    return c[0] if isinstance(c, list) else c


def main() -> None:
    tag = _entry12_run_tag()
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    for key in ("out_t1", "out_t2"):
        Pf = np.asarray(_child(mat_f[key])["P"][1], dtype=np.float64)
        print(key, "P2 cols", Pf.shape[1])
        for c in range(Pf.shape[1]):
            print(f"  col{c+1}", Pf[:, c].ravel()[:4])


if __name__ == "__main__":
    main()
