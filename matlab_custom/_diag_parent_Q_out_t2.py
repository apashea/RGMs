"""Parent workspace Q at 12F out_t2 (mat vs py)."""
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


def main() -> None:
    tag = _entry12_run_tag()
    py = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    key = "out_t2"
    for label, snap in ("mat", mat[key]), ("py", py[key]):
        Q = snap["Q"]
        print(f"\n{label} Q factors={len(Q)}")
        for fi, qf in enumerate(Q):
            a = np.asarray(qf, dtype=np.float64)
            col = a[:, -1] if a.ndim >= 2 else a.ravel()
            print(f"  f={fi+1} shape={a.shape} last_col peak={int(np.argmax(col)+1)} maxdiff n/a")


if __name__ == "__main__":
    main()
