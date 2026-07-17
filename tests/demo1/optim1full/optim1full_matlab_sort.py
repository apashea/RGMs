"""OPTIM1FULL Product B — Engine ``spm_RDP_sort`` (spectral bottleneck lane).

Default sign-off: ``RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1`` runs MATLAB
``spm_RDP_sort`` on the Engine (same policy tier as FSL Entry **4**
``run_entry4_matlab_structure_learning``). Hook-only ``eig=`` inject is diagnostic only.

Native / future Product A uses Python ``spm_RDP_sort_optim`` (not wired here).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[3]


def optim1full_matlab_sort_enabled() -> bool:
    """``RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB`` — default **on** for Product B parity."""
    raw = str(os.getenv("RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def _unwrap_cell1(x: Any) -> Any:
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _as_f64(arr: Any) -> np.ndarray:
    return np.asarray(_unwrap_cell1(arr), dtype=np.float64)


def _strip_level1_gp_fields(eng: Any, var_name: str) -> None:
    for key in ("GA", "GB", "GU", "GD", "ID", "chi"):
        eng.eval(
            f"if isfield({var_name}{{1}},'{key}'), "
            f"{var_name}{{1}} = rmfield({var_name}{{1}},'{key}'); end",
            nargout=0,
        )


def _overlay_py_mdp_tensors_to_engine(eng: Any, mdp: list[dict[str, Any]], var_name: str) -> None:
    """Overwrite numeric/tensor fields on an existing Engine cell ``mdp``."""
    import matlab

    nm = len(mdp)
    eng_nm = int(np.asarray(eng.eval(f"numel({var_name})"), dtype=np.int64).reshape(-1)[0])
    if eng_nm != nm:
        raise RuntimeError(f"Engine {var_name} numel={eng_nm} != python Nm={nm}")
    for ni, level in enumerate(mdp, start=1):
        expr = f"{var_name}{{{ni}}}"
        eng.eval(f"{expr}.T = {float(level['T'])};", nargout=0)
        for key in ("sA", "sB", "sC"):
            vals = [int(x) for x in np.asarray(level[key], dtype=np.int64).ravel(order="F").tolist()]
            eng.workspace["rgms_svec"] = matlab.double(vals)
            eng.eval(f"{expr}.{key} = rgms_svec;", nargout=0)
        na = len(level["a"])
        nb = len(level["b"])
        for gi in range(na):
            arr = _as_f64(level["a"][gi])
            eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
            eng.eval(f"{expr}.a{{{gi + 1}}} = rgms_arr;", nargout=0)
        for fi in range(nb):
            arr = _as_f64(level["b"][fi])
            eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
            eng.eval(f"{expr}.b{{{fi + 1}}} = rgms_arr;", nargout=0)
        if ni == 1:
            from tests.demo1.optim1full.optim1full_mdp_engine_io import (
                _push_level1_generative_process,
            )

            _push_level1_generative_process(eng, expr, level)
        if "U" in level:
            arr = _as_f64(level["U"])
            eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
            eng.eval(f"{expr}.U = rgms_arr;", nargout=0)
        if "C" in level:
            nc = len(level["C"])
            for ci in range(nc):
                arr = _as_f64(level["C"][ci])
                eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
                eng.eval(f"{expr}.C{{{ci + 1}}} = rgms_arr;", nargout=0)


def _pull_sorted_mdp_from_engine(eng: Any, sorted_var: str) -> list[dict[str, Any]]:
    from scipy.io import loadmat

    from tests.demo1.optim1full.optim1full_mi_boundary import _merge_level1_generative_process_fields
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    mdp = _pull_mdp_from_matlab(eng, sorted_var)
    tmp = _REPO / "matlab_custom" / "_optim1full_sort_mdp1_gp.mat"
    tmp_posix = str(tmp.resolve()).replace("\\", "/")
    eng.eval(f"MDP1 = {sorted_var}{{1}}; save('{tmp_posix}','MDP1');", nargout=0)
    m1 = mat_nested_to_py(loadmat(str(tmp))["MDP1"])
    _merge_level1_generative_process_fields(mdp, m1)
    return mdp


def run_spm_RDP_sort_matlab(
    eng: Any,
    mdp: list[dict[str, Any]],
    *,
    mat_path: Path | None = None,
    mat_var: str = "MDP_post_nr",
    template_mat: Path | None = None,
    workspace_out_var: str = "rgms_mdp_sorted",
    strip_level1_gp: bool = False,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Run Engine ``spm_RDP_sort``; return sorted ``MDP`` cell + ``j`` (1-based column)."""
    if mat_path is not None:
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        in_var = mat_var
    else:
        if template_mat is None:
            raise ValueError("template_mat required when mat_path is None")
        p = str(template_mat.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        in_var = mat_var
        if strip_level1_gp:
            _strip_level1_gp_fields(eng, in_var)
        _overlay_py_mdp_tensors_to_engine(eng, mdp, in_var)
    eng.eval(f"[{workspace_out_var}, rgms_j_sort] = spm_RDP_sort({in_var});", nargout=0)
    sorted_mdp = _pull_sorted_mdp_from_engine(eng, workspace_out_var)
    j_raw = eng.eval("rgms_j_sort")
    j_out = np.asarray(j_raw, dtype=np.int64).ravel(order="F")
    eng.eval("clear rgms_j_sort rgms_arr rgms_svec", nargout=0)
    return sorted_mdp, j_out


def assemble_rdp_call3_post_nr_optim1full_parity(
    eng: Any,
    mdp: list[dict[str, Any]],
    c_val: float,
    ns: float,
    *,
    mat_path: Path | None = None,
    mat_var: str = "MDP_post_nr",
    template_mat: Path | None = None,
) -> dict[str, Any]:
    """Product B call-3: Engine ``spm_RDP_sort`` then Python goals / costs / ``spm_mdp2rdp``."""
    from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_set_costs import spm_set_costs

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1 "
            "(Engine spm_RDP_sort); hook-only eig inject is not sign-off"
        )
    sorted_mdp, _j = run_spm_RDP_sort_matlab(
        eng,
        mdp,
        mat_path=mat_path,
        mat_var=mat_var,
        template_mat=template_mat,
    )
    rdp = spm_set_goals_optim(sorted_mdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_mdp2rdp(rdp, 0, 1.0 / float(ns))
    rdp["T"] = 128
    return rdp


def assemble_rdp_call4_post_nr_optim1full_parity(
    eng: Any,
    mdp: list[dict[str, Any]],
    c_val: float,
    ns: float,
    *,
    mat_path: Path | None = None,
    mat_var: str = "MDP_post_nr",
    template_mat: Path | None = None,
) -> dict[str, Any]:
    """Product B call-4: Engine sort → ``spm_RDP_MI`` → goals / costs / ``spm_mdp2rdp``."""
    from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_RDP_MI import spm_RDP_MI
    from python_src.toolbox.DEM.spm_set_costs import spm_set_costs

    if not optim1full_matlab_sort_enabled():
        raise RuntimeError(
            "OPTIM1FULL Product B requires RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1"
        )
    sorted_mdp, _j = run_spm_RDP_sort_matlab(
        eng,
        mdp,
        mat_path=mat_path,
        mat_var=mat_var,
        template_mat=template_mat,
    )
    rdp = spm_RDP_MI(sorted_mdp)
    rdp = spm_set_goals_optim(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_set_costs(rdp, [2, 3], [float(c_val), -float(c_val)])
    rdp = spm_mdp2rdp(rdp, 0, 1.0 / float(ns))
    rdp["T"] = 128
    return rdp


def validation_sort_metadata() -> dict[str, Any]:
    return {
        "sort_source": "matlab_engine" if optim1full_matlab_sort_enabled() else "native",
        "RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB": optim1full_matlab_sort_enabled(),
    }
