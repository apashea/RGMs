"""Diff all nested child numeric fields at 12F out_t2."""
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


def _diff_val(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a) | set(b))
        for k in keys:
            _diff_val(a.get(k), b.get(k), f"{path}.{k}" if path else k)
        return
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        n = max(len(a), len(b))
        for i in range(n):
            _diff_val(a[i] if i < len(a) else None, b[i] if i < len(b) else None, f"{path}[{i}]")
        return
    try:
        aa = np.asarray(a, dtype=np.float64)
        bb = np.asarray(b, dtype=np.float64)
        if aa.shape != bb.shape:
            print(f"{path} shape {aa.shape} vs {bb.shape}")
            return
        d = float(np.max(np.abs(aa.ravel() - bb.ravel()))) if aa.size and bb.size else 0.0
        if d > 1e-12:
            print(f"{path} maxdiff={d}")
    except Exception:
        if a != b:
            print(f"{path} type/value mismatch")


def main() -> None:
    tag = _entry12_run_tag()
    py_f = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    _diff_val(_child(py_f["out_t2"]), _child(mat_f["out_t2"]))


if __name__ == "__main__":
    main()
