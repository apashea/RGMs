"""Run child VB from mat vs py nested MDP at 12F out_t1; compare P(:,end) to 12F out_t2."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
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
    return copy.deepcopy(c[0] if isinstance(c, list) else c)


def _peak(v):
    a = np.asarray(v, dtype=float).ravel()
    return int(np.argmax(a) + 1), a[:6].tolist()


def main() -> None:
    tag = _entry12_run_tag()
    py_f = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    f = 1
    ref_end = np.asarray(_child(mat_f["out_t2"])["P"][f])[:, -1]
    print("mat out_t2 P(:,end) peak", _peak(ref_end))
    for label, snap in ("from_mat_out_t1", _child(mat_f["out_t1"])), ("from_py_out_t1", _child(py_f["out_t1"])):
        ch = spm_MDP_checkX(copy.deepcopy(snap))
        out = vb.spm_MDP_VB_XXX(ch, vb._default_options_vb(), reuse_matlab_draws=False)
        got = np.asarray(out["P"][f])[:, -1]
        d = float(np.max(np.abs(got.ravel() - ref_end.ravel())))
        print(label, "peak", _peak(got), "maxdiff vs mat out_t2", d)


if __name__ == "__main__":
    main()
