#!/usr/bin/env python3
"""Read-only audit: ``RDP.B`` container shape MATLAB vs Python (tier **3g** blocker context)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _b_summary(rdp: dict, label: str) -> dict:
    b = rdp.get("B", [])
    out: dict = {"label": label, "len_B": len(b) if isinstance(b, list) else None}
    if isinstance(b, list) and b:
        b0 = b[0]
        out["B0_type"] = type(b0).__name__
        if isinstance(b0, list):
            out["B0_len"] = len(b0)
            if b0:
                arr = np.asarray(b0[0], dtype=np.float64)
                out["B0_0_shape"] = tuple(arr.shape)
                out["B0_0_numel"] = int(arr.size)
        elif isinstance(b0, np.ndarray):
            out["B0_shape"] = tuple(np.asarray(b0).shape)
            out["B0_numel"] = int(np.asarray(b0).size)
    # Total numeric leaves under B (recursive)
    total = 0

    def _walk(x: object) -> None:
        nonlocal total
        if isinstance(x, list):
            for y in x:
                _walk(y)
        elif isinstance(x, np.ndarray):
            total += int(np.asarray(x, dtype=np.float64).size)

    _walk(b)
    out["B_leaf_numel"] = total
    return out


def main() -> int:
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
    from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_replay import atari_c_value, optim1full_entry12_fixture_env
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
        load_entry12_rdp_mat_nested_for_tag,
        mat_nested_to_py,
    )
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    pre = optim1full_mdp_pre_active_inference_mat()
    mdp = load_mdp_from_mat(pre, "MDP_pre_active_inference")
    ne = load_ne_from_mat(pre, "Ne")
    c = atari_c_value()
    rdp_py = spm_set_goals(mdp, [2, 3], [c, -c])
    rdp_py = spm_set_costs(rdp_py, [2, 3], [c, -c])
    branch = "spm_mdp2rdp_a" if "a" in mdp[0] else "spm_mdp2rdp"
    rdp_py = spm_mdp2rdp(rdp_py, 0, 1.0 / 256.0)
    rdp_py["T"] = float(int(256 / ne))

    tmp = _REPO / "matlab_custom" / "_optim1full_matlab_rdp_nr1.mat"
    rdp_mat = mat_nested_to_py(loadmat(str(tmp))["RDP"]) if tmp.is_file() else None

    tag = "rgms_atari_optim1full_nr_g01"
    mat_p = pre.parent / f"DEMAtariIII_XXX_12_{tag}_rdp.mat"
    rdp_pc = None
    if mat_p.is_file():
        with optim1full_entry12_fixture_env():
            rdp_pc = load_entry12_rdp_mat_nested_for_tag(tag, mat_p)

    print(f"[audit] spm_mdp2rdp branch: {branch}")
    for rdp, name in ((rdp_py, "python_live"), (rdp_mat, "matlab_engine"), (rdp_pc, "phase_c_tag")):
        if rdp is None:
            print(f"[audit] {name}: missing")
            continue
        s = _b_summary(rdp, name)
        print(f"[audit] {name}: {s}")

    if rdp_mat is not None:
        try:
            _assert_nested_rdp_equal(rdp_py, rdp_mat, "py_vs_mat")
            print("[audit] oracle py_vs_mat: MATCH")
        except AssertionError as exc:
            print(f"[audit] oracle py_vs_mat: MISMATCH — {exc}")

    if rdp_pc is not None:
        try:
            _assert_nested_rdp_equal(rdp_py, rdp_pc, "py_vs_phase_c")
            print("[audit] oracle py_vs_phase_c: MATCH")
        except AssertionError as exc:
            print(f"[audit] oracle py_vs_phase_c: MISMATCH — {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
