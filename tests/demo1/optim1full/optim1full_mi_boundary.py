"""OPTIM1FULL MI boundary helpers — load MATLAB authority, count ``np`` (line 429)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np


def _merge_level1_generative_process_fields(
    mdp: list[dict[str, Any]], m1: dict[str, Any]
) -> None:
    """Attach ``GA``/``GB``/``GU``/``GD``/``ID``/``chi`` from MATLAB ``MDP{1}`` save."""
    if not mdp:
        return
    for key in ("GA", "GB", "GU", "GD", "ID", "chi"):
        if key in m1:
            mdp[0][key] = copy.deepcopy(m1[key])


def load_mdp_from_mat(mat_path: Path, var_name: str) -> list[dict[str, Any]]:
    """Load nested MDP cell from a MATLAB ``.mat`` via Engine pull.

    Scalar Engine pull omits generative-process attach on level 1; merge via v7
    ``save`` of ``{var_name}{1}`` (same pattern as DEMO2 post-NR assembly oracle).
    """
    import matlab.engine
    from scipy.io import loadmat

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _pull_mdp_from_matlab

    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        mdp = _pull_mdp_from_matlab(eng, var_name)
        tmp = repo / "matlab_custom" / "_optim1full_mdp1_gp.mat"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp_posix = str(tmp.resolve()).replace("\\", "/")
        eng.eval(f"MDP1 = {var_name}{{1}}; save('{tmp_posix}','MDP1');", nargout=0)
        m1 = mat_nested_to_py(loadmat(str(tmp))["MDP1"])
        _merge_level1_generative_process_fields(mdp, m1)
        return mdp
    finally:
        eng.quit()


def load_ne_from_mat(mat_path: Path, var_name: str = "Ne") -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root

    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        val = eng.workspace[var_name]
        return int(np.asarray(val, dtype=np.int64).reshape(-1)[0])
    finally:
        eng.quit()


def load_np_mi429_from_mat(mat_path: Path) -> int:
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root

    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        val = eng.workspace["np_mi429"]
        return int(np.asarray(val, dtype=np.int64).reshape(-1)[0])
    finally:
        eng.quit()


def count_mdp_parameters_np(mdp: list[dict[str, Any]], nm: int) -> int:
    """``DEM_AtariIII.m`` lines 429--439 — ``nnz`` over ``a`` and ``b`` after ``spm_RDP_MI``."""
    total = 0
    for n in range(int(nm)):
        mdp_n = mdp[n]
        for g in range(len(mdp_n.get("a", []))):
            arr = mdp_n["a"][g]
            if isinstance(arr, list):
                arr = arr[0]
            total += int(np.count_nonzero(np.asarray(arr, dtype=np.float64)))
        for f in range(len(mdp_n.get("b", []))):
            arr = mdp_n["b"][f]
            if isinstance(arr, list):
                arr = arr[0]
            total += int(np.count_nonzero(np.asarray(arr, dtype=np.float64)))
    return total


def _flatten_id_tokens(x: Any) -> list[Any]:
    if isinstance(x, list):
        out: list[Any] = []
        for item in x:
            out.extend(_flatten_id_tokens(item))
        return out
    return [x]


def _id_labels_equal(py_val: Any, mat_val: Any) -> bool:
    return _flatten_id_tokens(py_val) == _flatten_id_tokens(mat_val)


def _is_empty_ss_cell(x: Any) -> bool:
    if x is None:
        return True
    if isinstance(x, dict):
        return False
    arr = np.asarray(x, dtype=np.float64)
    return int(arr.size) == 0


def _assert_ss_cell_pairing_equal(p_cell: Any, m_cell: Any, label: str, k: int) -> None:
    """Pair empty/``None`` ss cells; dict sparse maps vs dense mat; tensor-exact otherwise."""
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_array_equal_exact,
        _to_tensor,
    )

    if _is_empty_ss_cell(p_cell) and _is_empty_ss_cell(m_cell):
        return
    if isinstance(p_cell, dict):
        arr = None if _is_empty_ss_cell(m_cell) else np.asarray(m_cell, dtype=np.float64)
        for (fi, fj), val in p_cell.items():
            if arr is None or arr.size == 0:
                raise AssertionError(f"call={k} {label}: py dict {p_cell!r} mat empty")
            got = float(arr[int(fi) - 1, int(fj) - 1])
            if not np.isclose(float(val), got, rtol=0.0, atol=1e-12):
                raise AssertionError(
                    f"call={k} {label}: ss ({fi},{fj}) py={float(val)} mat={got}"
                )
        return
    if isinstance(m_cell, dict):
        raise AssertionError(
            f"call={k} {label}: type py={type(p_cell).__name__} mat=dict"
        )
    ps = _to_tensor(p_cell)
    ms = _to_tensor(m_cell)
    _assert_array_equal_exact(ps, ms, label, k)


def assert_optim1full_mdp_pre_pairing_equal(py_mdp: list[dict], mat_mdp: list[dict], k: int) -> None:
    """Pairing audit — tensor-exact MDP; ``id.*`` label cells reported separately."""
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_array_equal_exact,
        _to_tensor,
    )

    if len(py_mdp) != len(mat_mdp):
        raise AssertionError(f"call={k} level-count py={len(py_mdp)} mat={len(mat_mdp)}")
    id_mismatches: list[str] = []
    for n in range(len(py_mdp)):
        p = py_mdp[n]
        m = mat_mdp[n]
        if not np.isclose(float(p["T"]), float(m["T"]), rtol=0.0, atol=1e-12):
            raise AssertionError(f"call={k} lev={n+1} field=T py={float(p['T'])} mat={float(m['T'])}")
        for field in ("sA", "sB", "sC"):
            if list(p[field]) != list(m[field]):
                raise AssertionError(f"call={k} lev={n+1} field={field} mismatch")
        for field in ("A", "D", "E"):
            if not _id_labels_equal(p["id"][field], m["id"][field]):
                id_mismatches.append(f"lev={n+1} id.{field}")
        if p["G"].keys() != m["G"].keys():
            raise AssertionError(f"call={k} lev={n+1} G key mismatch")
        for sk in p["G"].keys():
            pg = p["G"][sk]
            mg = m["G"][sk]
            if len(pg) != len(mg):
                raise AssertionError(f"call={k} lev={n+1} G[{sk}] group-count mismatch")
            for gi in range(len(pg)):
                pg_arr = np.asarray(pg[gi], dtype=np.int64).ravel()
                mg_arr = np.asarray(mg[gi], dtype=np.int64).ravel()
                if not np.array_equal(pg_arr, mg_arr):
                    raise AssertionError(f"call={k} lev={n+1} G[{sk}]{{{gi+1}}} mismatch")
        if len(p["a"]) != len(m["a"]):
            raise AssertionError(f"call={k} lev={n+1} a-count py={len(p['a'])} mat={len(m['a'])}")
        if len(p["b"]) != len(m["b"]):
            raise AssertionError(f"call={k} lev={n+1} b-count py={len(p['b'])} mat={len(m['b'])}")
        for g in range(len(p["a"])):
            pa = _to_tensor(p["a"][g])
            ma = _to_tensor(m["a"][g])
            _assert_array_equal_exact(pa, ma, f"lev={n+1} a[{g+1}]", k)
        for f in range(len(p["b"])):
            pb = _to_tensor(p["b"][f])
            mb = _to_tensor(m["b"][f])
            _assert_array_equal_exact(pb, mb, f"lev={n+1} b[{f+1}]", k)
        for ss_field in ("D", "E", "ID", "IE"):
            p_ss = p["ss"][ss_field]
            m_ss = m["ss"][ss_field]
            if len(p_ss) != len(m_ss):
                raise AssertionError(f"call={k} lev={n+1} ss.{ss_field} row-count mismatch")
            for i in range(len(p_ss)):
                if len(p_ss[i]) != len(m_ss[i]):
                    raise AssertionError(
                        f"call={k} lev={n+1} ss.{ss_field} col-count mismatch at row={i+1}"
                    )
                for j in range(len(p_ss[i])):
                    _assert_ss_cell_pairing_equal(
                        p_ss[i][j],
                        m_ss[i][j],
                        f"lev={n+1} ss.{ss_field}[{i+1},{j+1}]",
                        k,
                    )
    if id_mismatches:
        print(
            f"[OPTIM1FULL MDP_pre compare] NOTE id label drift (non-gating): {', '.join(id_mismatches)}",
            file=__import__('sys').stderr,
        )


def assert_optim1full_mdp_pre_equal(py_mdp: list[dict], mat_mdp: list[dict], k: int) -> None:
    """Strict MDP_pre compare including ``id.*`` labels."""
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_array_equal_exact,
        _to_tensor,
    )

    if len(py_mdp) != len(mat_mdp):
        raise AssertionError(f"call={k} level-count py={len(py_mdp)} mat={len(mat_mdp)}")
    for n in range(len(py_mdp)):
        p = py_mdp[n]
        m = mat_mdp[n]
        if not np.isclose(float(p["T"]), float(m["T"]), rtol=0.0, atol=1e-12):
            raise AssertionError(f"call={k} lev={n+1} field=T py={float(p['T'])} mat={float(m['T'])}")
        for field in ("sA", "sB", "sC"):
            if list(p[field]) != list(m[field]):
                raise AssertionError(f"call={k} lev={n+1} field={field} mismatch")
        for field in ("A", "D", "E"):
            if not _id_labels_equal(p["id"][field], m["id"][field]):
                raise AssertionError(f"call={k} lev={n+1} id.{field} mismatch")
        if p["G"].keys() != m["G"].keys():
            raise AssertionError(f"call={k} lev={n+1} G key mismatch")
        for sk in p["G"].keys():
            pg = p["G"][sk]
            mg = m["G"][sk]
            if len(pg) != len(mg):
                raise AssertionError(f"call={k} lev={n+1} G[{sk}] group-count mismatch")
            for gi in range(len(pg)):
                if not np.array_equal(np.asarray(pg[gi], dtype=np.int64), np.asarray(mg[gi], dtype=np.int64)):
                    raise AssertionError(f"call={k} lev={n+1} G[{sk}]{{{gi+1}}} mismatch")
        if len(p["a"]) != len(m["a"]):
            raise AssertionError(f"call={k} lev={n+1} a-count py={len(p['a'])} mat={len(m['a'])}")
        if len(p["b"]) != len(m["b"]):
            raise AssertionError(f"call={k} lev={n+1} b-count py={len(p['b'])} mat={len(m['b'])}")
        for g in range(len(p["a"])):
            pa = _to_tensor(p["a"][g])
            ma = _to_tensor(m["a"][g])
            _assert_array_equal_exact(pa, ma, f"lev={n+1} a[{g+1}]", k)
        for f in range(len(p["b"])):
            pb = _to_tensor(p["b"][f])
            mb = _to_tensor(m["b"][f])
            _assert_array_equal_exact(pb, mb, f"lev={n+1} b[{f+1}]", k)
        for ss_field in ("D", "E", "ID", "IE"):
            p_ss = p["ss"][ss_field]
            m_ss = m["ss"][ss_field]
            if len(p_ss) != len(m_ss):
                raise AssertionError(f"call={k} lev={n+1} ss.{ss_field} row-count mismatch")
            for i in range(len(p_ss)):
                if len(p_ss[i]) != len(m_ss[i]):
                    raise AssertionError(
                        f"call={k} lev={n+1} ss.{ss_field} col-count mismatch at row={i+1}"
                    )
                for j in range(len(p_ss[i])):
                    ps = _to_tensor(p_ss[i][j])
                    ms = _to_tensor(m_ss[i][j])
                    _assert_array_equal_exact(ps, ms, f"lev={n+1} ss.{ss_field}[{i+1},{j+1}]", k)
