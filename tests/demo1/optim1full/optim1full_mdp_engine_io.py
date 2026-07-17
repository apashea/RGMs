"""OPTIM1FULL — push Python ``MDP`` cell to Engine and save v7 authority ``.mat``."""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B = "capture_optim1full_python_product_b"


def _unwrap_cell1(x: Any) -> Any:
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _as_f64(arr: Any) -> np.ndarray:
    from scipy import sparse

    x = _unwrap_cell1(arr)
    if sparse.issparse(x):
        x = x.toarray()
    return np.asarray(x, dtype=np.float64)


def _flatten_id_tokens(x: Any) -> list[Any]:
    if isinstance(x, list):
        out: list[Any] = []
        for item in x:
            out.extend(_flatten_id_tokens(item))
        return out
    return [x]


def _push_id_scalar_field(eng: Any, expr: str, field: str, tokens: Any) -> None:
    """``id.A`` / ``id.hid`` — one Engine scalar cell per token."""
    import matlab

    flat = _flatten_id_tokens(tokens)
    eng.eval(f"{expr}.id.{field} = cell(1, {len(flat)});", nargout=0)
    for i, tok in enumerate(flat, start=1):
        eng.workspace["rgms_svec"] = matlab.double([float(tok)])
        eng.eval(f"{expr}.id.{field}{{{i}}} = rgms_svec;", nargout=0)


def _push_id_vector_field(eng: Any, expr: str, field: str, cells: list[Any]) -> None:
    """``id.D`` / ``id.E`` — fixed cell count; each cell is a vector (or empty)."""
    import matlab

    eng.eval(f"{expr}.id.{field} = cell(1, {len(cells)});", nargout=0)
    for i, cell in enumerate(cells, start=1):
        if cell is None or (isinstance(cell, list) and len(cell) == 0):
            eng.eval(f"{expr}.id.{field}{{{i}}} = zeros(0,1);", nargout=0)
            continue
        vals = [float(x) for x in _flatten_id_tokens(cell)]
        eng.workspace["rgms_svec"] = matlab.double(vals)
        eng.eval(f"{expr}.id.{field}{{{i}}} = rgms_svec(:);", nargout=0)


def _push_groups(eng: Any, expr: str, groups: dict[int, list[Any]]) -> None:
    import matlab

    for sk in sorted(groups.keys(), key=int):
        glist = groups[sk]
        eng.eval(f"{expr}.G{{{int(sk)}}} = cell(1, {len(glist)});", nargout=0)
        for gi, garr in enumerate(glist, start=1):
            vals = [int(x) for x in np.asarray(garr, dtype=np.int64).ravel(order="F").tolist()]
            eng.workspace["rgms_svec"] = matlab.double(vals)
            eng.eval(f"{expr}.G{{{int(sk)}}}{{{gi}}} = rgms_svec(:);", nargout=0)


def _ss_dict_to_dense(cell: dict) -> np.ndarray:
    """Structure-learning sparse ``ss.*`` cell ``{(fi,fj): val}`` → dense array."""
    if not cell:
        return np.zeros((0, 0), dtype=np.float64)
    max_r = max(int(k[0]) for k in cell)
    max_c = max(int(k[1]) for k in cell)
    arr = np.zeros((max_r, max_c), dtype=np.float64)
    for (fi, fj), val in cell.items():
        arr[int(fi) - 1, int(fj) - 1] = float(val)
    return arr


def _push_ss_field(eng: Any, expr: str, field: str, rows: list[list[Any]]) -> None:
    import matlab

    nr = len(rows)
    nc = len(rows[0]) if rows else 0
    eng.eval(f"{expr}.ss.{field} = cell({nr}, {nc});", nargout=0)
    for ri, row in enumerate(rows, start=1):
        for ci, cell in enumerate(row, start=1):
            if cell is None:
                eng.eval(f"{expr}.ss.{field}{{{ri},{ci}}} = [];", nargout=0)
                continue
            if isinstance(cell, dict):
                arr = _ss_dict_to_dense(cell)
                if arr.size == 0:
                    eng.eval(f"{expr}.ss.{field}{{{ri},{ci}}} = [];", nargout=0)
                else:
                    eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
                    eng.eval(f"{expr}.ss.{field}{{{ri},{ci}}} = rgms_arr;", nargout=0)
                continue
            arr = _as_f64(cell)
            eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
            eng.eval(f"{expr}.ss.{field}{{{ri},{ci}}} = rgms_arr;", nargout=0)


def overlay_py_mdp_level_to_engine(
    eng: Any,
    level: dict[str, Any],
    expr: str,
    *,
    push_gp: bool = True,
) -> None:
    """Overwrite one Engine MDP struct (``PDP.MDP`` or ``mdp{ni}``) from Python."""
    import matlab

    eng.eval(f"{expr}.T = {float(np.asarray(level['T']).ravel()[0])};", nargout=0)
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
    for field in ("A",):
        _push_id_scalar_field(eng, expr, field, level["id"][field])
    for field in ("D", "E"):
        _push_id_vector_field(eng, expr, field, level["id"][field])
    if "hid" in level["id"]:
        _push_id_scalar_field(eng, expr, "hid", level["id"]["hid"])
    _push_groups(eng, expr, level["G"])
    for ss_field in ("D", "E", "ID", "IE"):
        _push_ss_field(eng, expr, ss_field, level["ss"][ss_field])
    if push_gp:
        _push_level1_generative_process(eng, expr, level)


def overlay_full_py_mdp_to_engine(eng: Any, mdp: list[dict[str, Any]], var_name: str) -> None:
    """Overwrite Engine ``mdp`` cell from Python (numeric + ``id`` / ``G`` / ``ss`` / GP)."""
    nm = len(mdp)
    eng_nm = int(np.asarray(eng.eval(f"numel({var_name})"), dtype=np.int64).reshape(-1)[0])
    if eng_nm != nm:
        eng.eval(f"{var_name} = cell(1, {nm});", nargout=0)
    for ni, level in enumerate(mdp, start=1):
        overlay_py_mdp_level_to_engine(
            eng,
            level,
            f"{var_name}{{{ni}}}",
            push_gp=(ni == 1),
        )


def _push_level1_generative_process(eng: Any, expr: str, level: dict[str, Any]) -> None:
    import matlab

    for key in ("GA", "GB", "GD"):
        if key not in level:
            continue
        cells = level[key]
        if not isinstance(cells, list):
            cells = [cells]
        eng.eval(f"{expr}.{key} = cell(1, {len(cells)});", nargout=0)
        for ci, cell in enumerate(cells, start=1):
            arr = _as_f64(cell)
            eng.workspace["rgms_arr"] = matlab.double(arr.tolist())
            eng.eval(f"{expr}.{key}{{{ci}}} = rgms_arr;", nargout=0)
    if "GU" in level:
        gu = np.asarray(level["GU"])
        if gu.dtype == np.uint8 or gu.dtype == bool:
            eng.workspace["rgms_arr"] = matlab.logical(gu.astype(bool).tolist())
        else:
            eng.workspace["rgms_arr"] = matlab.double(_as_f64(gu).tolist())
        eng.eval(f"{expr}.GU = rgms_arr;", nargout=0)
    if "chi" in level:
        chi_arr = _as_f64(level["chi"])
        if chi_arr.size == 1:
            eng.eval(f"{expr}.chi = {float(chi_arr.reshape(-1)[0])};", nargout=0)
        else:
            eng.workspace["rgms_arr"] = matlab.double(chi_arr.tolist())
            eng.eval(f"{expr}.chi = rgms_arr;", nargout=0)


def save_mdp_authority_v7_mat(
    eng: Any,
    mdp: list[dict[str, Any]],
    *,
    out_path: Path,
    var_name: str,
    meta_field: str,
    capture_mode: str,
    nm: int,
    ne: int,
    template_mat: Path,
    template_var: str,
) -> None:
    """Save Python-run ``MDP`` as OPTIM1FULL authority ``.mat`` (v7) with capture metadata."""
    import matlab

    p_load = str(template_mat.resolve()).replace("\\", "/")
    eng.eval(f"load('{p_load}','{template_var}');", nargout=0)
    eng.eval(f"{var_name} = {template_var};", nargout=0)
    overlay_full_py_mdp_to_engine(eng, mdp, var_name)
    eng.workspace["Nm"] = matlab.double([float(nm)])
    eng.workspace["Ne"] = matlab.double([float(ne)])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    eng.eval(f"{meta_field} = struct();", nargout=0)
    eng.eval(f"{meta_field}.capture = '{capture_mode}';", nargout=0)
    eng.eval(f"{meta_field}.timestamp = '{ts}';", nargout=0)
    eng.eval(f"{meta_field}.rng_seed = 2;", nargout=0)
    eng.eval(f"{meta_field}.source = 'python_product_b';", nargout=0)
    out_posix = str(out_path.resolve()).replace("\\", "/")
    eng.eval(
        f"save('{out_posix}', '{var_name}', 'Nm', 'Ne', '{meta_field}', '-v7');",
        nargout=0,
    )
