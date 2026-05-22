"""Print first 12F value-assert failure (in / out_t1 / out_t2 / out_t3 / out_tT)."""
from __future__ import annotations

import copy
import pickle
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_12F_mat_snap_for_value_assert,
    entry12_align_12F_workspace_to_mat,
)
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
    _ENTRY12_SUBENTRY_CODES,
    _densify_sparse_leaves,
    _entry12_run_tag,
    _entry12_workspace_payload,
    _load_subentry_pkl,
    _mat_blob_to_py,
    _subentry_pkl_path,
)
from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

code = "12F"
tag = _entry12_run_tag()
mat_p = entry12_subentry_mat_path(tag, code)
pkl_p = _subentry_pkl_path(code)
py_blob = _load_subentry_pkl(pkl_p)
mat_blob = _mat_blob_to_py(load_entry12_subentry_mat(mat_p))
py_ws = _entry12_workspace_payload(py_blob, code)
mat_ws = _entry12_workspace_payload(mat_blob, code)
py_ws = entry12_align_12F_workspace_to_mat(py_ws, mat_ws)
for sub in ("in", "out_t1", "out_t2", "out_t3", "out_tT"):
    print(f"=== assert {code}.{sub} ===")
    try:
        py_cmp = _densify_sparse_leaves(copy.deepcopy(py_ws[sub]))
        mat_cmp = _densify_sparse_leaves(
            entry12_12F_mat_snap_for_value_assert(mat_ws[sub])
        )
        _assert_nested_rdp_equal(py_cmp, mat_cmp, f"{code}.{sub}")
        print("OK")
    except AssertionError:
        traceback.print_exc()
