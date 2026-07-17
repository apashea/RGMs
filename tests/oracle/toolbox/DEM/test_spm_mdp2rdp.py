"""Oracle: ``spm_mdp2rdp`` / ``spm_mdp2rdp_a`` vs MATLAB (Entry 10/11 RDP capture)."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import load_or_build_entry10_sort_artifact


def _unwrap_one(x: Any) -> Any:
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _flatten_list_int_float(x: Any) -> list[float]:
    out: list[float] = []
    if isinstance(x, list):
        for t in x:
            out.extend(_flatten_list_int_float(t))
        return out
    return [float(x)]


def _norm_leaf(x: Any) -> Any:
    """Collapse MATLAB pull ``[[array]]`` wrappers to match bare ndarray Python MDP cells."""
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x


def _unwrap_g_dict_for_compare(g: dict) -> Any:
    """Flatten Python MDP ``G`` dict to a numeric vector (values already match MATLAB)."""
    keys = sorted(g.keys(), key=lambda k: (0, int(k)) if str(k).isdigit() else (1, str(k)))
    parts: list[np.ndarray] = []
    for k in keys:
        v = g[k]
        while isinstance(v, list) and len(v) == 1:
            v = v[0]
        parts.append(np.asarray(v, dtype=np.float64).ravel(order="F"))
    if not parts:
        return np.asarray([], dtype=np.float64)
    if len(parts) == 1:
        return parts[0]
    return np.concatenate(parts)


def _g_dict_to_matlab_list(g: dict) -> list:
    from python_src.toolbox.DEM.spm_MDP_checkX import spm_mdp_g_dict_to_matlab_list

    return spm_mdp_g_dict_to_matlab_list(g)


def _coerce_rdp_compare_pair(py: Any, mat: Any, path: str) -> tuple[Any, Any]:
    """Align common MATLAB pull vs Python MDP container shapes before strict type check."""
    leaf = path.rsplit(".", 1)[-1]
    if leaf == "G":
        if isinstance(py, dict) and isinstance(mat, np.ndarray):
            return _unwrap_g_dict_for_compare(py), mat
        if isinstance(py, np.ndarray) and isinstance(mat, dict):
            return py, _unwrap_g_dict_for_compare(mat)
        if isinstance(py, dict) and isinstance(mat, list):
            return _g_dict_to_matlab_list(py), mat
        if isinstance(py, list) and isinstance(mat, dict):
            return py, _g_dict_to_matlab_list(mat)
    if isinstance(py, list) and isinstance(mat, np.ndarray):
        if not py and mat.size == 0:
            return np.asarray([], dtype=np.float64), mat
        if py and all(isinstance(x, (int, float, np.integer, np.floating)) for x in py):
            return np.asarray(py, dtype=np.float64), mat
    if isinstance(py, list) and isinstance(mat, (int, float, np.integer, np.floating)):
        if len(py) == 1:
            return py[0], mat
    return py, mat


def _assert_nested_rdp_equal(py: Any, mat: Any, path: str) -> None:
    py = _norm_leaf(py)
    mat = _norm_leaf(mat)
    py, mat = _coerce_rdp_compare_pair(py, mat, path)
    if isinstance(py, np.ndarray) and isinstance(mat, list):
        mat = _norm_leaf(mat)
    if isinstance(mat, np.ndarray) and isinstance(py, list):
        py = _norm_leaf(py)
    if isinstance(py, (int, float, np.integer, np.floating)) and isinstance(
        mat, (int, float, np.integer, np.floating)
    ):
        if not np.isclose(float(py), float(mat), rtol=0.0, atol=1e-10):
            raise AssertionError(f"{path}: scalar py={py} mat={mat}")
        return
    if isinstance(py, np.ndarray) and isinstance(mat, (int, float, np.integer, np.floating)):
        if np.asarray(py, dtype=np.float64).size == 1 and np.isclose(
            float(np.asarray(py, dtype=np.float64).ravel()[0]), float(mat), rtol=0.0, atol=1e-10
        ):
            return
    if isinstance(mat, np.ndarray) and isinstance(py, (int, float, np.integer, np.floating)):
        if np.asarray(mat, dtype=np.float64).size == 1 and np.isclose(
            float(np.asarray(mat, dtype=np.float64).ravel()[0]), float(py), rtol=0.0, atol=1e-10
        ):
            return
    if isinstance(py, np.ndarray) and isinstance(mat, list):
        pa = np.asarray(py, dtype=np.float64).ravel()
        try:
            ma = np.asarray([float(x) for x in _flatten_list_int_float(mat)], dtype=np.float64).ravel()
        except (TypeError, ValueError):
            ma = np.asarray([], dtype=np.float64)
        if pa.size == ma.size and (pa.size == 0 or np.allclose(pa, ma, rtol=0.0, atol=1e-10)):
            return
    if isinstance(mat, np.ndarray) and isinstance(py, list):
        ma = np.asarray(mat, dtype=np.float64).ravel()
        pa = np.asarray([float(x) for x in _flatten_list_int_float(py)], dtype=np.float64).ravel()
        if pa.size == ma.size and (pa.size == 0 or np.allclose(pa, ma, rtol=0.0, atol=1e-10)):
            return
    try:
        from scipy import sparse as sp

        if sp.issparse(py) or sp.issparse(mat):
            pa = np.asarray(
                py.toarray() if sp.issparse(py) else py, dtype=np.float64
            ).ravel(order="F")
            ma = np.asarray(
                mat.toarray() if sp.issparse(mat) else mat, dtype=np.float64
            ).ravel(order="F")
            if pa.size != ma.size:
                raise AssertionError(f"{path}: sparse numel py={pa.size} mat={ma.size}")
            if not np.allclose(pa, ma, rtol=0.0, atol=1e-10):
                d = float(np.max(np.abs(pa - ma))) if pa.size else 0.0
                raise AssertionError(f"{path}: sparse max abs diff={d}")
            return
    except ImportError:
        pass
    if type(py) is not type(mat):
        raise AssertionError(f"{path}: type py={type(py)} mat={type(mat)}")
    if isinstance(py, dict):
        if set(py.keys()) != set(mat.keys()):
            raise AssertionError(
                f"{path}: keys py={sorted(py.keys())} mat={sorted(mat.keys())}"
            )
        for k in sorted(py.keys(), key=str):
            _assert_nested_rdp_equal(py[k], mat[k], f"{path}.{k}")
        return
    if isinstance(py, list):
        if len(py) != len(mat):
            raise AssertionError(f"{path}: list len py={len(py)} mat={len(mat)}")
        for i, (a, b) in enumerate(zip(py, mat, strict=True)):
            _assert_nested_rdp_equal(a, b, f"{path}[{i}]")
        return
    if isinstance(py, np.ndarray) and isinstance(mat, np.ndarray):
        pa = np.asarray(py, dtype=np.float64).ravel(order="F")
        ma = np.asarray(mat, dtype=np.float64).ravel(order="F")
        if pa.size != ma.size:
            raise AssertionError(f"{path}: numel py={pa.size} mat={ma.size}")
        if not np.allclose(pa, ma, rtol=0.0, atol=1e-10):
            d = float(np.max(np.abs(pa - ma))) if pa.size else 0.0
            raise AssertionError(f"{path}: max abs diff={d}")
        return
    raise AssertionError(f"{path}: unsupported types py={type(py)} mat={type(mat)}")


@pytest.fixture
def dem_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


@pytest.mark.slow
def test_spm_mdp2rdp_matlab_capture_oracle(dem_eng):
    """Default ``spm_mdp2rdp(MDP)`` then ``RDP.T = 64`` matches MATLAB capture."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = load_or_build_entry10_sort_artifact(dem_eng, training_t, n_outer)
    mdp_in = copy.deepcopy(artifact["mdp11_costs_mat"])
    rdp_py = spm_mdp2rdp(mdp_in)
    rdp_py["T"] = 64.0
    _assert_nested_rdp_equal(rdp_py, artifact["rdp11_nested_mat"], "RDP")
