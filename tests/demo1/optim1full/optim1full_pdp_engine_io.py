"""OPTIM1FULL — bulk Engine save of spine ``PDP`` authority ``.mat`` (v7)."""
from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from tests.demo1.optim1full.optim1full_export_spine_fence_pdp import (
    CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
)
from tests.demo1.optim1full.optim1full_mdp_engine_io import _as_f64, _ss_dict_to_dense


def _posix(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _is_ss_sparse_dict(x: Any) -> bool:
    return isinstance(x, dict) and bool(x) and all(isinstance(k, tuple) and len(k) == 2 for k in x)


def _to_matlab_array(arr: Any) -> Any:
    import matlab

    a = np.asarray(arr)
    if a.dtype == np.uint8:
        return matlab.uint8(a.tolist())
    if a.dtype == bool or a.dtype == np.bool_:
        return matlab.logical(a.astype(bool).tolist())
    return matlab.double(_as_f64(a).tolist())


def _item_is_simple_leaf(item: Any) -> bool:
    from scipy import sparse

    if item is None:
        return True
    if sparse.issparse(item):
        return True
    if _is_ss_sparse_dict(item):
        return True
    if isinstance(item, (int, float, bool, np.integer, np.floating, np.bool_)):
        return True
    if isinstance(item, np.ndarray):
        return True
    return False


def _grid_all_simple_leaves(grid: list[list[Any]]) -> bool:
    return all(_item_is_simple_leaf(cell) for row in grid for cell in row)


def _matlab_column_vector(arr: np.ndarray) -> np.ndarray:
    """Cell-leaf outcome vectors as ``N×1`` columns (MATLAB ``spm_O2rgb`` authority)."""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 1 and a.size > 1:
        return a.reshape(-1, 1)
    if a.ndim == 2 and a.shape[0] == 1 and a.shape[1] > 1:
        return a.reshape(-1, 1)
    return a


def _cell_item_to_matlab(item: Any) -> Any:
    from scipy import sparse

    if item is None:
        return []
    if sparse.issparse(item):
        item = _as_f64(item)
    if _is_ss_sparse_dict(item):
        item = _ss_dict_to_dense(item)
    if isinstance(item, (dict, list)):
        raise TypeError(f"complex cell item must use per-cell assign, got {type(item).__name__}")
    if isinstance(item, (int, float, bool, np.integer, np.floating, np.bool_)):
        import matlab

        return matlab.double([float(item)])
    if isinstance(item, np.ndarray):
        return _to_matlab_array(_matlab_column_vector(_as_f64(item)))
    return _to_matlab_array(item)


def _assign_cell_row(eng: Any, expr: str, row: list[Any]) -> None:
    if all(_item_is_simple_leaf(x) for x in row):
        flat = [_cell_item_to_matlab(x) for x in row]
        eng.workspace["rgms_flat"] = flat
        eng.eval(f"{expr} = rgms_flat;", nargout=0)
        return
    n = len(row)
    eng.eval(f"{expr} = cell(1, {n});", nargout=0)
    for i, item in enumerate(row):
        _assign_value(eng, f"{expr}{{{i + 1}}}", item)


def _assign_cell_grid(eng: Any, expr: str, grid: list[list[Any]]) -> None:
    import matlab

    nr = len(grid)
    nc = len(grid[0]) if grid else 0
    if not _grid_all_simple_leaves(grid):
        eng.eval(f"{expr} = cell({nr}, {nc});", nargout=0)
        for i, row in enumerate(grid):
            if len(row) != nc:
                raise ValueError(f"{expr}: ragged grid row {i}: {len(row)} vs {nc}")
            for j, cell in enumerate(row):
                _assign_value(eng, f"{expr}{{{i + 1},{j + 1}}}", cell)
        return
    for i, row in enumerate(grid):
        if len(row) != nc:
            raise ValueError(f"{expr}: ragged grid row {i}: {len(row)} vs {nc}")
    flat: list[Any] = []
    for j in range(nc):
        for i in range(nr):
            flat.append(_cell_item_to_matlab(grid[i][j]))
    eng.workspace["rgms_flat"] = flat
    eng.workspace["rgms_nr"] = matlab.double([[float(nr)]])
    eng.workspace["rgms_nc"] = matlab.double([[float(nc)]])
    eng.eval(
        f"optim1full_assign_cell_grid('{expr}', rgms_flat, int32(rgms_nr), int32(rgms_nc));",
        nargout=0,
    )


def _assign_scalar(eng: Any, expr: str, val: Any) -> None:
    if isinstance(val, (bool, np.bool_)):
        eng.eval(f"{expr} = {int(bool(val))};", nargout=0)
        return
    if isinstance(val, (int, np.integer)):
        eng.eval(f"{expr} = {int(val)};", nargout=0)
        return
    arr = np.asarray(val)
    if arr.size == 1:
        eng.eval(f"{expr} = {float(arr.ravel()[0])};", nargout=0)
        return
    eng.workspace["rgms_arr"] = _to_matlab_array(arr)
    eng.eval(f"{expr} = rgms_arr;", nargout=0)


def _assign_dense_or_sparse(eng: Any, expr: str, val: Any) -> None:
    from scipy import sparse

    if sparse.issparse(val):
        dense = _as_f64(val)
        if dense.size == 0:
            eng.eval(f"{expr} = sparse({dense.shape[0]}, {dense.shape[1]});", nargout=0)
            return
        import matlab

        eng.workspace["rgms_arr"] = matlab.double(dense.tolist())
        eng.eval(f"{expr} = sparse(rgms_arr);", nargout=0)
        return
    if _is_ss_sparse_dict(val):
        val = _ss_dict_to_dense(val)
    arr = np.asarray(val)
    if arr.size == 0:
        if arr.ndim == 2:
            eng.eval(f"{expr} = zeros({arr.shape[0]}, {arr.shape[1]});", nargout=0)
        else:
            eng.eval(f"{expr} = zeros(0, 0);", nargout=0)
        return
    eng.workspace["rgms_arr"] = _to_matlab_array(arr)
    eng.eval(f"{expr} = rgms_arr;", nargout=0)


def _assign_pa_dict(eng: Any, expr: str, pa: dict[Any, Any]) -> None:
    n = len(pa)
    eng.eval(f"{expr} = cell(1, {n});", nargout=0)
    for ki in sorted(pa.keys(), key=lambda x: int(x)):
        idx = int(ki)
        item = pa[ki]
        if isinstance(item, dict) and not item:
            eng.eval(f"{expr}{{{idx}}} = struct();", nargout=0)
        else:
            _assign_dense_or_sparse(eng, f"{expr}{{{idx}}}", item)


def _assign_dict_struct(eng: Any, expr: str, val: dict[str, Any]) -> None:
    if not val:
        return
    eng.eval(f"{expr} = struct();", nargout=0)
    for key in val:
        _assign_value(eng, f"{expr}.{key}", val[key])


def _is_list_of_lists(val: list[Any]) -> bool:
    return bool(val) and all(isinstance(x, list) for x in val)


def _is_rectangular_cell_grid(val: list[list[Any]]) -> bool:
    if not _is_list_of_lists(val):
        return False
    ncol = len(val[0])
    return all(len(row) == ncol for row in val)


def _assign_ragged_cell_rows(eng: Any, expr: str, rows: list[Any]) -> None:
    n = len(rows)
    eng.eval(f"{expr} = cell({n}, 1);", nargout=0)
    for i, row in enumerate(rows):
        idx = i + 1
        if isinstance(row, list):
            _assign_cell_row(eng, f"{expr}{{{idx}}}", row)
        else:
            _assign_value(eng, f"{expr}{{{idx}}}", row)


def _assign_list(eng: Any, expr: str, val: list[Any]) -> None:
    if not val:
        eng.eval(f"{expr} = {{}};", nargout=0)
        return
    if _is_list_of_lists(val):
        # MATLAB hierarchical ``{ {Ng×T grid} }``: one outer cell wrapping inner grid.
        if (
            len(val) == 1
            and val[0]
            and _is_rectangular_cell_grid(val[0])
            and len(val[0]) > 1
        ):
            eng.eval(f"{expr} = cell(1, 1);", nargout=0)
            _assign_cell_grid(eng, f"{expr}{{1}}", val[0])
            return
        if (
            len(val) == 1
            and val[0]
            and not isinstance(val[0][0], list)
        ):
            eng.eval(f"{expr} = cell(1, 1);", nargout=0)
            inner = val[0]
            if _is_rectangular_cell_grid(inner):
                _assign_cell_grid(eng, f"{expr}{{1}}", inner)
            else:
                _assign_ragged_cell_rows(eng, f"{expr}{{1}}", inner)
            return
        if _is_rectangular_cell_grid(val):
            _assign_cell_grid(eng, expr, val)
            return
        _assign_ragged_cell_rows(eng, expr, val)
        return
    _assign_cell_row(eng, expr, val)


def _assign_value(eng: Any, expr: str, val: Any) -> None:
    from scipy import sparse

    if val is None:
        eng.eval(f"{expr} = [];", nargout=0)
        return
    if isinstance(val, dict):
        if val and all(isinstance(k, (int, np.integer)) for k in val.keys()):
            _assign_pa_dict(eng, expr, val)
            return
        _assign_dict_struct(eng, expr, val)
        return
    if isinstance(val, list):
        _assign_list(eng, expr, val)
        return
    if sparse.issparse(val) or isinstance(val, np.ndarray) or _is_ss_sparse_dict(val):
        _assign_dense_or_sparse(eng, expr, val)
        return
    _assign_scalar(eng, expr, val)


def _align_spine_pdp_for_engine(py_pdp: dict[str, Any]) -> dict[str, Any]:
    from python_src.toolbox.DEM.entry12_matlab_capture import _entry12_strip_pdp_inspection_probes
    from python_src.toolbox.DEM.entry12_plot import _normalize_pdp_pkl_for_plot

    out = _normalize_pdp_pkl_for_plot(copy.deepcopy(py_pdp))
    # Spine mat authority is for plot pairing — drop Entry 12 inspection probes before
    # Engine overlay (``entry12_Yfill`` alone is ~17M leaves at NR game 32 → hours + GB).
    _entry12_strip_pdp_inspection_probes(out)
    return out


def overlay_py_pdp_to_engine(eng: Any, py_pdp: dict[str, Any], *, expr: str = "PDP") -> None:
    """Bulk-assign Python post-VB ``PDP`` dict to Engine variable ``expr``."""
    eng.eval(f"{expr} = struct();", nargout=0)
    for key in sorted(py_pdp.keys()):
        _assign_value(eng, f"{expr}.{key}", py_pdp[key])


def save_pdp_authority_v7_mat(
    eng: Any,
    py_pdp: dict[str, Any],
    *,
    out_path: Path,
    capture_mode: str = CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
    meta_field: str = "metaPdp",
    py_aligned: dict[str, Any] | None = None,
) -> None:
    """Save spine ``PDP`` authority ``.mat`` (v7.3 HDF5) from Python driver ``PDP`` dict."""
    py_use = py_aligned if py_aligned is not None else _align_spine_pdp_for_engine(py_pdp)
    overlay_py_pdp_to_engine(eng, py_use, expr="PDP")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    eng.eval(f"{meta_field} = struct();", nargout=0)
    eng.eval(f"{meta_field}.capture = '{capture_mode}';", nargout=0)
    eng.eval(f"{meta_field}.timestamp = '{ts}';", nargout=0)
    eng.eval(f"{meta_field}.source = 'python_spine';", nargout=0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    p_out = _posix(out_path)
    eng.eval(f"save('{p_out}', 'PDP', '{meta_field}', '-v7');", nargout=0)
