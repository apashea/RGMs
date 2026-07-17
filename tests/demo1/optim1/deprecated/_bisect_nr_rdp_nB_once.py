#!/usr/bin/env python3
"""One-shot bisect: where nB diverges (not a sign-off instrument)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import matlab.engine
import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from python_src.toolbox.DEM import spm_mdp2rdp_a as m2a
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim
from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
from tests.demo1.demo1_paths import demo1_repo_root
from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat
from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
from tests.demo1.optim1full.optim1full_replay import atari_c_value


def _level_nb(mdp: list, i: int) -> int:
    return len(mdp[i].get("b", []))


def main() -> int:
    repo = demo1_repo_root()
    pre = optim1full_mdp_pre_active_inference_mat()
    c = atari_c_value()
    ns = 256.0
    nt = 256
    mdp0 = load_mdp_from_mat(pre, "MDP_pre_active_inference")
    ne = load_ne_from_mat(pre, "Ne")

    out: dict = {}

    for name, goals_fn in (("fidelity", spm_set_goals), ("optim", spm_set_goals_optim)):
        m = copy.deepcopy(mdp0)
        m = goals_fn(m, [2, 3], [c, -c])
        m = spm_set_costs(m, [2, 3], [c, -c])
        rdp = spm_mdp2rdp(m, 0, 1.0 / ns)
        rdp["T"] = float(int(nt / ne))
        out[name] = {
            "level0_nb": _level_nb(m, 0),
            "level1_nb": _level_nb(m, 1),
            "assembled_nB": len(rdp.get("B", [])),
            "assembled_nA": len(rdp.get("A", [])),
        }

    m = copy.deepcopy(mdp0)
    m = spm_set_goals(m, [2, 3], [c, -c])
    m = spm_set_costs(m, [2, 3], [c, -c])
    nm = len(m)
    idx = nm - 1
    b_shapes = []
    for f in range(_level_nb(m, idx)):
        arr = np.asarray(m2a._unwrap_cell(m[idx]["b"][f]), dtype=np.float64)
        b_shapes.append({"f": f, "shape": list(arr.shape), "size": int(arr.size)})

    m_trim = copy.deepcopy(m)
    n_last = nm - 1
    if len(m_trim[n_last]["b"]) > 1:
        m_trim[n_last]["b"] = [m_trim[n_last]["b"][0]]
    nb = len(m_trim[idx]["b"])
    d_ub = np.ones(nb, dtype=bool)
    for f in range(nb):
        bf = m2a._unwrap_cell(m_trim[idx]["b"][f])
        if np.asarray(bf, dtype=np.float64).size == 1:
            d_ub[f] = False
    kept = int(np.sum(d_ub))

    out["bisect_fidelity"] = {
        "level1_b_shapes_before_mdp2rdp": b_shapes,
        "after_trailing_trim_nb": len(m_trim[idx]["b"]),
        "unitary_d_ub": d_ub.tolist(),
        "unitary_kept": kept,
        "after_unitary_merge_nb": kept,
        "full_mdp2rdp_a_nB": len(
            m2a.spm_mdp2rdp_a(copy.deepcopy(m), 0, 1.0 / ns).get("B", [])
        ),
    }

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        p = str(pre.resolve()).replace("\\", "/")
        eng.eval(
            f"load('{p}','MDP_pre_active_inference','Ne'); "
            f"C={c}; NS={ns}; NT={nt};",
            nargout=0,
        )
        eng.eval(
            "MDP=spm_set_goals(MDP_pre_active_inference,[2,3],[C,-C]); "
            "MDP=spm_set_costs(MDP,[2,3],[C,-C]);",
            nargout=0,
        )
        mat_nb0 = int(eng.eval("numel(MDP{1}.b)"))
        mat_nb1 = int(eng.eval("numel(MDP{2}.b)"))
        mat_b_shapes = []
        for f in range(1, mat_nb1 + 1):
            shp = eng.eval(f"size(MDP{{2}}.b{{{f}}})", nargout=1)
            issc = bool(eng.eval(f"isscalar(MDP{{2}}.b{{{f}}})", nargout=1))
            nel = int(eng.eval(f"numel(MDP{{2}}.b{{{f}}})", nargout=1))
            mat_b_shapes.append(
                {"f": f - 1, "shape": [int(x) for x in np.asarray(shp).ravel()], "isscalar": issc, "numel": nel}
            )
        eng.eval("RDP=spm_mdp2rdp(MDP,0,1/NS); RDP.T=fix(NT/Ne);", nargout=0)
        mat_nB = int(eng.eval("numel(RDP.B)"))
        out["matlab"] = {
            "level0_nb": mat_nb0,
            "level1_nb": mat_nb1,
            "level1_b_shapes": mat_b_shapes,
            "assembled_nB": mat_nB,
        }
        tmp = repo / "matlab_custom" / "_bisect_rdp.mat"
        tmp_posix = str(tmp.resolve()).replace("\\", "/")
        eng.eval(f"save('{tmp_posix}','RDP','-v7');", nargout=0)
        shp_b1 = eng.eval("size(RDP.B{1})", nargout=1)
        out["matlab"]["B1_shape_engine"] = [int(x) for x in np.asarray(shp_b1).ravel()]
    finally:
        eng.quit()

    from scipy.io import loadmat
    from tests.demo1.optim1full.optim1full_audit_nr_segment_draws import assemble_nr_rdp_parity
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    rdp_mat = mat_nested_to_py(loadmat(str(tmp))["RDP"])
    rdp_py = assemble_nr_rdp_parity(mdp0, c, ne)

    def _b0(rdp: dict, key: str) -> dict:
        b = rdp.get("B", [])
        if isinstance(b, np.ndarray):
            len_b = int(b.size) if b.dtype == object else 1
            b0 = b.ravel(order="F")[0] if b.size else None
        else:
            len_b = len(b)
            b0 = b[0] if b else None
        while isinstance(b0, list) and len(b0) == 1:
            b0 = b0[0]
        if b0 is None:
            return {key: {"lenB": 0}}
        arr = np.asarray(b0, dtype=np.float64)
        return {key: {"lenB": len_b, "b0_shape": list(arr.shape), "b0_size": int(arr.size)}}

    out["loadmat_vs_engine"] = {
        **_b0(rdp_mat, "mat_after_loadmat"),
        **_b0(rdp_py, "py_assembled"),
        "mat_len_B_compare_script_metric": int(len(rdp_mat.get("B", []))),
        "py_len_B": len(rdp_py.get("B", [])),
    }

    def _assemble(goals_fn):
        m = copy.deepcopy(mdp0)
        m = goals_fn(m, [2, 3], [c, -c])
        m = spm_set_costs(m, [2, 3], [c, -c])
        r = spm_mdp2rdp(m, 0, 1.0 / ns)
        r["T"] = float(int(nt / ne))
        return r

    rf = _assemble(spm_set_goals)
    ro = _assemble(spm_set_goals_optim)
    bf = np.asarray(rf["B"][0], dtype=np.float64)
    bo = np.asarray(ro["B"][0], dtype=np.float64)
    out["goals_fidelity_vs_optim"] = {
        "B0_shape_match": list(bf.shape) == list(bo.shape),
        "B0_max_abs_delta": float(np.max(np.abs(bf - bo))) if bf.shape == bo.shape else None,
    }

    eng2 = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng2, repo)
        p = str(pre.resolve()).replace("\\", "/")
        eng2.eval(
            f"load('{p}','MDP_pre_active_inference','Ne'); C={c}; NS={ns}; NT={nt};",
            nargout=0,
        )
        eng2.eval(
            "RDP=spm_set_goals(MDP_pre_active_inference,[2,3],[C,-C]); "
            "RDP=spm_set_costs(RDP,[2,3],[C,-C]); "
            "RDP=spm_mdp2rdp(RDP,0,1/NS); RDP.T=fix(NT/Ne);",
            nargout=0,
        )
        bm = np.asarray(eng2.eval("RDP.B{1}", nargout=1), dtype=np.float64)
        out["matlab_vs_py_fidelity_B0"] = {
            "shape_match": list(bm.shape) == list(bf.shape),
            "max_abs_delta": float(np.max(np.abs(bm - bf))) if bm.shape == bf.shape else None,
            "mat_shape": list(bm.shape),
            "py_shape": list(bf.shape),
        }
    finally:
        eng2.quit()

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
