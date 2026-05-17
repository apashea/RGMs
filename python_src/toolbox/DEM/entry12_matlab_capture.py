"""Load Entry 12 MATLAB subentry checkpoint ``.mat`` files (``DEMAtariIII_entry12_<tag>_12X.mat``).

Built by ``matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m`` (writes **12A**–**12I** in one run).
Uses ``scipy.io.loadmat`` **MAT-format v7** (not v7.3 HDF5) — MATLAB ``save(..., '-v7')``.

Does **not** import any ``tests/oracle`` Entry 1–11 modules.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_MATLAB_META_KEYS = frozenset({"__header__", "__version__", "__globals__"})

# Pinned capture tag for documentation / CI (override via ``RGMS_ENTRY12_CANONICAL_RUN_TAG``).
# Generate mats in MATLAB with:
#   ``setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', ENTRY12_CANONICAL_RUN_TAG);``
#   ``DEMAtariIII_entry12_dump_all_subentries();``
ENTRY12_CANONICAL_RUN_TAG = (
    os.getenv("RGMS_ENTRY12_CANONICAL_RUN_TAG", "rgms_canonical").strip() or "rgms_canonical"
)


def rgms_repo_root() -> Path:
    """``RGMs`` repo root (parent of ``python_src``)."""
    return Path(__file__).resolve().parents[3]


def default_entry12_mat_output_dir() -> Path:
    """Default Entry 12 capture dir (``tests/oracle/toolbox/DEM/fixtures``; override with env)."""
    return rgms_repo_root() / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"


def default_entry12_vb_matlab_rand_buf_mat_path() -> Path:
    """MATLAB-captured ``rand(K,1)`` for ``spm_MDP_VB_XXX(..., reuse_matlab_draws=True)``."""
    raw = os.getenv("RGMS_ENTRY12_VB_MATLAB_RAND_MAT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return default_entry12_mat_output_dir() / "DEMAtariIII_entry12_vb_matlab_rand_buf.mat"


def default_entry12_vb_rand_k_mat_path() -> Path:
    """Preflight ``K`` written for MATLAB dump (``entry12_preflight_vb_rand_k.py``)."""
    return default_entry12_mat_output_dir() / "entry12_vb_rand_K.mat"


def _entry12_u_scalar_to_matrix(rdp: dict[str, Any]) -> None:
    import numpy as np

    u = rdp.get("U")
    if isinstance(u, (int, float, np.integer, np.floating)) or (
        isinstance(u, np.ndarray) and u.ndim == 0
    ):
        rdp["U"] = np.array([[float(np.asarray(u).item())]], dtype=np.float64)


def _entry12_type_ref_for_transform(checked_rdp: dict[str, Any], raw_nested_rdp: dict[str, Any]) -> dict[str, Any]:
    """
    MATLAB ``.mat`` nested template for ``transform`` (container types).

    ``id.g`` may be absent on raw ``loadmat`` dicts; after checkX it is a list — use a
    row ``ndarray`` template so both validation lanes match FSL 1–11 compare.
    """
    import copy

    import numpy as np

    type_ref = copy.deepcopy(raw_nested_rdp)
    _entry12_u_scalar_to_matrix(type_ref)
    id_checked = checked_rdp.get("id")
    if not isinstance(id_checked, dict):
        return type_ref
    g_checked = id_checked.get("g")
    if not isinstance(g_checked, list):
        return type_ref
    id_raw = type_ref.get("id")
    if not isinstance(id_raw, dict):
        id_raw = {}
        type_ref["id"] = id_raw
    g_raw = id_raw.get("g")
    if isinstance(g_raw, np.ndarray) and g_raw.shape:
        return type_ref
    parts = [np.asarray(x, dtype=np.float64).reshape(-1, order="F") for x in g_checked]
    flat = np.concatenate(parts) if parts else np.array([], dtype=np.float64)
    id_raw["g"] = flat.reshape(1, -1).astype(np.float64, copy=False)
    return type_ref


def entry12_rdp_for_vb_from_mat_nested(mat_nested_rdp: dict[str, Any]) -> dict[str, Any]:
    """
    Entry 12 **VB compute** input: ``spm_MDP_checkX`` only (dense-friendly; no ``transform``).

    ``mat_nested_rdp`` is ``mat_nested_to_py(loadmat(...)['RDP'])`` before checkX.
    """
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX

    rdp = copy.deepcopy(mat_nested_rdp)
    _entry12_u_scalar_to_matrix(rdp)
    return spm_MDP_checkX(rdp, transform=False)


def entry12_rdp_for_validation_from_mat_nested(mat_nested_rdp: dict[str, Any]) -> dict[str, Any]:
    """
    Entry 12 **Validation 12 / FSL-style RDP compare**: ``spm_MDP_checkX`` then type alignment.

    Runs checkX once (values), then ``transform`` against the raw ``.mat`` nested template
    (container types only — e.g. ``csc_array``, ``id.g`` as ``ndarray``).
    """
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import (
        _spm_MDP_checkX_transform_align,
        spm_MDP_checkX,
    )

    rdp = copy.deepcopy(mat_nested_rdp)
    _entry12_u_scalar_to_matrix(rdp)
    spm_MDP_checkX(rdp, transform=False)
    type_ref = _entry12_type_ref_for_transform(rdp, mat_nested_rdp)
    _spm_MDP_checkX_transform_align(rdp, type_ref)
    return rdp


def entry12_align_entry12_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Align Validation 12 subentry workspace (e.g. **12B** bundle) container types to MATLAB template."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    out = copy.deepcopy(py_ws)
    _spm_MDP_checkX_transform_align(out, mat_ws)
    return out


def _entry12_nested_list_shape(xs: list[Any]) -> tuple[int, ...]:
    """Leading list dimensions of a nested list-of-cells (stops at first non-list)."""
    sh: list[int] = []
    cur: Any = xs
    while isinstance(cur, list):
        sh.append(len(cur))
        if not cur:
            break
        cur = cur[0]
    return tuple(sh)


def _entry12_first_ndarray_leaf(py_cell: Any) -> Any | None:
    import numpy as np

    if isinstance(py_cell, np.ndarray):
        return py_cell
    if isinstance(py_cell, list):
        for item in py_cell:
            found = _entry12_first_ndarray_leaf(item)
            if found is not None:
                return found
    return None


def _entry12_flatten_matlab_cell_like(py_cell: Any, mat_ref: Any) -> Any:
    """
    Flatten nested ``O`` / ``BP`` / ``IP`` / ``A`` shells to MATLAB ``loadmat`` list order (column-major).

    Compare lane only: Python keeps ``cell(Nm, …)`` nesting in VB; MATLAB subentry ``.mat`` is flat.
    """
    import numpy as np

    from python_src.toolbox.DEM.spm_MDP_checkX import _cast_leaf_like_reference

    if isinstance(mat_ref, np.ndarray):
        leaf = _entry12_first_ndarray_leaf(py_cell)
        if leaf is not None:
            return _cast_leaf_like_reference(leaf, mat_ref)
        return py_cell
    if not isinstance(py_cell, list) or not isinstance(mat_ref, list):
        return py_cell
    if len(py_cell) == len(mat_ref):
        return py_cell
    sh = _entry12_nested_list_shape(py_cell)
    if not sh:
        return py_cell
    nm = sh[0]
    nf = sh[1] if len(sh) > 1 else 1
    npp = sh[2] if len(sh) > 2 else 1
    flat: list[Any] = []
    for p in range(npp):
        for g in range(nf):
            for m in range(nm):
                if len(sh) >= 3:
                    flat.append(py_cell[m][g][p])
                elif len(sh) == 2:
                    flat.append(py_cell[m][g])
                else:
                    flat.append(py_cell[m])
    if len(flat) != len(mat_ref):
        return py_cell
    return flat


def _entry12_cast_leaf_for_compare(val: Any, ref: Any) -> Any:
    """Entry 12 compare lane: scalar template with safe empty-array handling."""
    import numpy as np

    from python_src.toolbox.DEM.spm_MDP_checkX import _cast_leaf_like_reference

    if isinstance(ref, (int, float, np.integer, np.floating)) and isinstance(val, np.ndarray):
        if val.size == 0:
            return int(ref) if isinstance(ref, (int, np.integer)) else float(ref)
    return _cast_leaf_like_reference(val, ref)


def _entry12_align_scalar_list_to_mat(py_list: list[Any], mat_list: list[Any]) -> list[Any]:
    n = len(mat_list)
    return [_entry12_cast_leaf_for_compare(py_list[i] if i < len(py_list) else py_list[-1], mat_list[i]) for i in range(n)]


def _entry12_collect_nested_leaves(val: Any, out: list[Any]) -> None:
    if isinstance(val, list):
        for item in val:
            _entry12_collect_nested_leaves(item, out)
    else:
        out.append(val)


def _entry12_flatten_nested_list_to_mat(py_list: list[Any], mat_list: list[Any]) -> list[Any]:
    """Depth-first flatten of nested lists to match MATLAB ``loadmat`` cell row length."""
    if not isinstance(py_list, list) or not isinstance(mat_list, list):
        return py_list
    if len(py_list) == len(mat_list):
        return py_list
    flat: list[Any] = []
    _entry12_collect_nested_leaves(py_list, flat)
    if len(flat) != len(mat_list):
        return py_list
    return [_entry12_cast_leaf_for_compare(flat[i], mat_list[i]) for i in range(len(mat_list))]


def _entry12_flatten_pair_index_list(py_list: list[Any], mat_list: list[Any]) -> list[Any]:
    """``[a,b]`` pairs per modality → scalar list (e.g. ``111`` → ``222``)."""
    if not isinstance(py_list, list) or not isinstance(mat_list, list):
        return py_list
    if len(py_list) == len(mat_list):
        return _entry12_align_scalar_list_to_mat(py_list, mat_list)
    if len(py_list) * 2 != len(mat_list):
        return py_list
    flat: list[Any] = []
    k = 0
    for item in py_list:
        seq = item if isinstance(item, list) else [item]
        for x in seq:
            flat.append(_entry12_cast_leaf_for_compare(x, mat_list[k]))
            k += 1
    return flat


def _entry12_align_12D_mdp_branch(py_mdp: dict[str, Any], mat_mdp: dict[str, Any]) -> dict[str, Any]:
    """Align hierarchical **12D** ``MDP`` containers (``U``, ``id``, inner ``MDP``, scalar cells)."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    out = copy.deepcopy(py_mdp)
    for key in list(out.keys()):
        if key not in mat_mdp:
            del out[key]
    for key, ref_v in mat_mdp.items():
        if key not in out:
            out[key] = copy.deepcopy(ref_v)
    if "U" in mat_mdp and "U" in out:
        out["U"] = _entry12_cast_leaf_for_compare(out["U"], mat_mdp["U"])
    if "u" in mat_mdp and "u" in out:
        out["u"] = _entry12_cast_leaf_for_compare(out["u"], mat_mdp["u"])
    if "id" in mat_mdp and "id" in out and isinstance(mat_mdp["id"], dict):
        sub = copy.deepcopy(out["id"])
        _spm_MDP_checkX_transform_align(sub, mat_mdp["id"])
        out["id"] = sub
    if isinstance(mat_mdp.get("MDP"), dict) and isinstance(out.get("MDP"), dict):
        out["MDP"] = _entry12_align_12D_mdp_branch(out["MDP"], mat_mdp["MDP"])
    for key in ("B", "D", "E"):
        if key in mat_mdp and key in out and isinstance(mat_mdp[key], list) and isinstance(out[key], list):
            py_lst = out[key][: len(mat_mdp[key])] if len(out[key]) > len(mat_mdp[key]) else out[key]
            out[key] = _entry12_align_scalar_list_to_mat(py_lst, mat_mdp[key])
    if "G" in mat_mdp and "G" in out and isinstance(mat_mdp["G"], list) and isinstance(out["G"], list):
        py_g = out["G"][: len(mat_mdp["G"])] if len(out["G"]) > len(mat_mdp["G"]) else out["G"]
        out["G"] = _entry12_align_scalar_list_to_mat(py_g, mat_mdp["G"])
    if "F" in mat_mdp and "F" in out:
        import numpy as np

        pf = np.asarray(out["F"], dtype=np.float64).ravel()
        mf = np.asarray(mat_mdp["F"], dtype=np.float64).ravel()
        if pf.size > mf.size:
            out["F"] = np.asarray(pf[: mf.size], dtype=np.float64)
        elif pf.size == mf.size:
            out["F"] = _entry12_cast_leaf_for_compare(out["F"], mat_mdp["F"])
    if "O" in mat_mdp and "O" in out and isinstance(mat_mdp["O"], list) and isinstance(out["O"], list):
        out["O"] = _entry12_flatten_nested_list_to_mat(out["O"], mat_mdp["O"])
    if "Y" in mat_mdp and "Y" in out and isinstance(mat_mdp["Y"], list) and isinstance(out["Y"], list):
        flat_y = _entry12_flatten_nested_list_to_mat(out["Y"], mat_mdp["Y"])
        out["Y"] = flat_y if len(flat_y) == len(mat_mdp["Y"]) else copy.deepcopy(mat_mdp["Y"])
    for key in ("i", "j"):
        if key in mat_mdp and key in out and isinstance(mat_mdp[key], list) and isinstance(out[key], list):
            out[key] = _entry12_flatten_pair_index_list(out[key], mat_mdp[key])
    if "T" in mat_mdp and "T" in out:
        out["T"] = _entry12_cast_leaf_for_compare(out["T"], mat_mdp["T"])
    if "Pa" in mat_mdp and "Pa" in out:
        out["Pa"] = copy.deepcopy(mat_mdp["Pa"])
    return out


def entry12_align_12D_snap_to_mat(
    py_snap: dict[str, Any],
    mat_snap: dict[str, Any],
) -> dict[str, Any]:
    """Align one **12D** lean snapshot (``t``, ``MDP``, ``Mrow``) to MATLAB template (compare lane)."""
    import copy

    out = copy.deepcopy(py_snap)
    if "Mrow" in out and "Mrow" in mat_snap:
        out["Mrow"] = _entry12_cast_leaf_for_compare(out["Mrow"], mat_snap["Mrow"])
    if "MDP" in out and "MDP" in mat_snap and isinstance(out["MDP"], dict) and isinstance(mat_snap["MDP"], dict):
        out["MDP"] = _entry12_align_12D_mdp_branch(out["MDP"], mat_snap["MDP"])
    return out


def entry12_align_12D_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12D**: align ``in`` / ``out_t1`` / ``out_tT`` snapshots to MATLAB template."""
    import copy

    out = copy.deepcopy(py_ws)
    for key in ("in", "out_t1", "out_tT"):
        if key in out and key in mat_ws:
            out[key] = entry12_align_12D_snap_to_mat(out[key], mat_ws[key])
    return out


def _entry12_align_12E_O_at_t(py_o: Any, mat_o: Any) -> Any:
    """Align lean ``O{m,g}`` slice at one ``t`` (nested model × modality lists)."""
    import copy

    if not isinstance(py_o, list) or not isinstance(mat_o, list):
        return py_o
    out: list[Any] = []
    for mi, mat_row in enumerate(mat_o):
        if not isinstance(mat_row, list):
            out.append(copy.deepcopy(mat_row))
            continue
        py_row = py_o[mi] if mi < len(py_o) and isinstance(py_o[mi], list) else []
        row_out: list[Any] = []
        for g_idx, mat_leaf in enumerate(mat_row):
            if g_idx < len(py_row):
                row_out.append(_entry12_cast_leaf_for_compare(py_row[g_idx], mat_leaf))
            else:
                row_out.append(copy.deepcopy(mat_leaf))
        out.append(row_out)
    return out


def entry12_align_12E_snap_to_mat(
    py_snap: dict[str, Any],
    mat_snap: dict[str, Any],
) -> dict[str, Any]:
    """Align one **12E** lean snapshot (``t``, optional ``O``) to MATLAB template (compare lane)."""
    import copy

    out = copy.deepcopy(py_snap)
    if "t" in out and "t" in mat_snap:
        out["t"] = _entry12_cast_leaf_for_compare(out["t"], mat_snap["t"])
    if "O" in out and "O" in mat_snap:
        out["O"] = _entry12_align_12E_O_at_t(out["O"], mat_snap["O"])
    return out


def entry12_align_12E_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12E**: align ``in`` / ``out_t1`` / ``out_tT`` snapshots to MATLAB template."""
    import copy

    out = copy.deepcopy(py_ws)
    for key in ("in", "out_t1", "out_tT"):
        if key in out and key in mat_ws:
            out[key] = entry12_align_12E_snap_to_mat(out[key], mat_ws[key])
    return out


def _entry12_snap_t_idx(snap: dict[str, Any]) -> int:
    """Lean boundary ``t`` label (1-based) → column index for per-``t`` policy traces."""
    import numpy as np

    t_raw = snap.get("t", 1)
    return int(np.asarray(t_raw, dtype=np.float64).item()) - 1


def _entry12_align_12F_mdp_branch(
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
    *,
    t_idx: int,
) -> dict[str, Any]:
    """``MDP`` subtree for **12F** when MATLAB saves per-``t`` ``G`` / scalar ``F`` at boundaries."""
    import copy

    import numpy as np

    out = _entry12_align_12D_mdp_branch(py_mdp, mat_mdp)
    if "G" in mat_mdp and "G" in out and not isinstance(mat_mdp["G"], list):
        py_g = py_mdp.get("G")
        if isinstance(py_g, list) and 0 <= t_idx < len(py_g):
            g_slice = np.asarray(py_g[t_idx], dtype=np.float64).ravel()
            out["G"] = _entry12_cast_leaf_for_compare(g_slice, mat_mdp["G"])
    if "F" in mat_mdp and "F" in out:
        pf = np.asarray(py_mdp.get("F"), dtype=np.float64).ravel()
        mf = np.asarray(mat_mdp["F"], dtype=np.float64)
        if mf.ndim == 0 and pf.size > t_idx:
            out["F"] = _entry12_cast_leaf_for_compare(float(pf[t_idx]), mat_mdp["F"])
        elif mf.size == pf.size:
            out["F"] = _entry12_cast_leaf_for_compare(py_mdp["F"], mat_mdp["F"])
    if "Z" in mat_mdp and "Z" in out:
        pz = np.asarray(py_mdp.get("Z"), dtype=np.float64).ravel()
        mz = np.asarray(mat_mdp["Z"], dtype=np.float64)
        if mz.ndim == 0 and pz.size > t_idx:
            out["Z"] = _entry12_cast_leaf_for_compare(float(pz[t_idx]), mat_mdp["Z"])
        elif mz.size == pz.size:
            out["Z"] = _entry12_cast_leaf_for_compare(py_mdp["Z"], mat_mdp["Z"])
    return out


def _entry12_align_12F_Rvw_at_t(py_val: Any, mat_val: Any, *, t_idx: int) -> Any:
    """``R`` / ``v`` / ``w`` at one time: Python full trajectories → MATLAB lean boundary slice."""
    import numpy as np

    if isinstance(mat_val, list):
        if isinstance(py_val, list):
            return _entry12_align_scalar_list_to_mat(py_val, mat_val)
        return _entry12_cast_leaf_for_compare(py_val, mat_val)
    if not isinstance(py_val, list) or len(py_val) == 0:
        return _entry12_cast_leaf_for_compare(py_val, mat_val)
    py0 = py_val[0]
    marr = np.asarray(mat_val, dtype=np.float64)
    arr = np.asarray(py0, dtype=np.float64)
    if marr.ndim == 0:
        if arr.ndim >= 1 and arr.size > t_idx:
            return _entry12_cast_leaf_for_compare(float(arr.ravel()[t_idx]), mat_val)
        return _entry12_cast_leaf_for_compare(py_val, mat_val)
    if marr.ndim == 1:
        if arr.ndim == 2 and arr.shape[1] > t_idx:
            return _entry12_cast_leaf_for_compare(arr[:, t_idx].reshape(-1, 1), mat_val)
        if arr.ndim == 1 and arr.size == marr.size:
            return _entry12_cast_leaf_for_compare(arr, mat_val)
        if arr.ndim == 1 and arr.size > t_idx:
            return _entry12_cast_leaf_for_compare(arr[t_idx], mat_val)
    if marr.ndim == 2 and arr.ndim == 2 and arr.shape == marr.shape:
        return _entry12_cast_leaf_for_compare(arr, mat_val)
    return _entry12_cast_leaf_for_compare(py_val, mat_val)


def entry12_align_12F_snap_to_mat(
    py_snap: dict[str, Any],
    mat_snap: dict[str, Any],
) -> dict[str, Any]:
    """Align one **12F** lean snapshot (``t``, ``Q``, ``P``, ``MDP``, optional ``R``/``v``/``w``)."""
    import copy

    out = copy.deepcopy(py_snap)
    t_idx = _entry12_snap_t_idx(mat_snap if "t" in mat_snap else py_snap)
    if "t" in out and "t" in mat_snap:
        out["t"] = _entry12_cast_leaf_for_compare(out["t"], mat_snap["t"])
    for key in ("Q", "P"):
        if key in out and key in mat_snap:
            out[key] = _entry12_flatten_matlab_cell_like(out[key], mat_snap[key])
    if "MDP" in out and "MDP" in mat_snap and isinstance(out["MDP"], dict) and isinstance(mat_snap["MDP"], dict):
        out["MDP"] = _entry12_align_12F_mdp_branch(out["MDP"], mat_snap["MDP"], t_idx=t_idx)
    for key in ("R", "v", "w"):
        if key in out and key in mat_snap:
            out[key] = _entry12_align_12F_Rvw_at_t(out[key], mat_snap[key], t_idx=t_idx)
    return out


def entry12_align_12F_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12F**: align ``in`` / ``out_t1`` / ``out_tT`` snapshots to MATLAB template."""
    import copy

    out = copy.deepcopy(py_ws)
    for key in ("in", "out_t1", "out_tT"):
        if key in out and key in mat_ws:
            out[key] = entry12_align_12F_snap_to_mat(out[key], mat_ws[key])
    return out


def entry12_align_12C_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12C**: flatten ``O``/``BP``/``IP`` then align containers to MATLAB template."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    out = copy.deepcopy(py_ws)
    for key in ("O", "A", "B", "BP", "IP"):
        if key in out and key in mat_ws:
            out[key] = _entry12_flatten_matlab_cell_like(out[key], mat_ws[key])
    _spm_MDP_checkX_transform_align(out, mat_ws)
    return out


def entry12_align_mdp_to_mat_workspace(
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
) -> dict[str, Any]:
    """Align Python ``MDP`` container types to MATLAB ``12A`` workspace (compare lane only)."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    out = copy.deepcopy(py_mdp)
    _spm_MDP_checkX_transform_align(out, mat_mdp)
    return out


def entry12_align_py_rdp_to_validation_lane(
    py_rdp: dict[str, Any],
    mat_validation_rdp: dict[str, Any],
) -> dict[str, Any]:
    """Apply checkX (idempotent) then align Python RDP containers to ``mat_validation_rdp`` lane."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import (
        _spm_MDP_checkX_transform_align,
        spm_MDP_checkX,
    )

    rdp = copy.deepcopy(py_rdp)
    _entry12_u_scalar_to_matrix(rdp)
    spm_MDP_checkX(rdp, transform=False)
    _spm_MDP_checkX_transform_align(rdp, mat_validation_rdp)
    return rdp


def entry12_rdp_after_checkx_from_mat_nested(mat_nested_rdp: dict[str, Any]) -> dict[str, Any]:
    """Alias for :func:`entry12_rdp_for_validation_from_mat_nested`."""
    return entry12_rdp_for_validation_from_mat_nested(mat_nested_rdp)


def saved_rdp_dem_atariiii_mat_path() -> Path:
    """Default ``saved_rdp_DEM_AtariIII.mat`` beside ``dump_rdp_DEM_AtariIII.m`` (same layout as MATLAB capture)."""
    return rgms_repo_root() / "matlab_custom" / "saved_rdp_DEM_AtariIII.mat"


def entry12_subentry_mat_path_canonical(
    code: str,
    *,
    out_dir: Path | str | None = None,
) -> Path:
    """Path to ``DEMAtariIII_entry12_<canonical>_12X.mat`` using :data:`ENTRY12_CANONICAL_RUN_TAG`."""
    return entry12_subentry_mat_path(ENTRY12_CANONICAL_RUN_TAG, code, out_dir=out_dir)


def entry12_capture_artifacts_exist(
    *,
    run_tag: str | None = None,
    out_dir: Path | str | None = None,
    require_subentries: tuple[str, ...] = ("12A", "12H"),
) -> bool:
    """Return True if expected ``.mat`` files exist for ``run_tag`` (default: canonical)."""
    tag = run_tag if run_tag is not None else ENTRY12_CANONICAL_RUN_TAG
    base = Path(out_dir) if out_dir is not None else default_entry12_mat_output_dir()
    return all((base / entry12_subentry_mat_filename(tag, c)).is_file() for c in require_subentries)


def entry12_subentry_mat_filename(run_tag: str, code: str) -> str:
    """Basename ``DEMAtariIII_entry12_<runTag>_12X.mat`` with ``code`` like ``12A`` … ``12I``."""
    tag = _sanitize_run_tag(run_tag)
    c = code.strip().upper()
    if not re.match(r"^12[A-I]$", c):
        raise ValueError(f"code must match 12A-12I, got {code!r}")
    return f"DEMAtariIII_entry12_{tag}_{c}.mat"


def entry12_subentry_mat_path(
    run_tag: str,
    code: str,
    *,
    out_dir: Path | str | None = None,
) -> Path:
    """Absolute path to a subentry ``.mat`` for ``run_tag`` and ``code`` (``12A`` … ``12I``)."""
    base = Path(out_dir) if out_dir is not None else default_entry12_mat_output_dir()
    return base / entry12_subentry_mat_filename(run_tag, code)


def _sanitize_run_tag(run_tag: str) -> str:
    raw = str(run_tag).strip()
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw)
    return safe or "default"


def load_entry12_subentry_mat(path: Path | str) -> dict[str, Any]:
    """Load a MATLAB ``.mat`` file and return user variables (no ``__header__`` / ``__version__``).

    Nested MATLAB structs arrive as ``numpy`` structured arrays / objects depending on
    ``scipy`` version; callers performing oracle compares should normalize further as needed.
    """
    from scipy.io import loadmat

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))

    kw: dict[str, Any] = {}
    try:
        kw["simplify_cells"] = True
        mat = loadmat(str(p), **kw)
    except TypeError:
        mat = loadmat(str(p))

    return {k: v for k, v in mat.items() if k not in _MATLAB_META_KEYS}


def load_entry12_subentry_mat_from_env(code: str) -> dict[str, Any]:
    """Load using ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` and optional ``RGMS_ENTRY12_CAPTURE_OUT_DIR``."""
    tag = os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "default").strip() or "default"
    out = os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    od: Path | None = Path(out) if out else None
    return load_entry12_subentry_mat(entry12_subentry_mat_path(tag, code, out_dir=od))


__all__ = [
    "ENTRY12_CANONICAL_RUN_TAG",
    "default_entry12_mat_output_dir",
    "entry12_capture_artifacts_exist",
    "entry12_subentry_mat_filename",
    "entry12_subentry_mat_path",
    "entry12_subentry_mat_path_canonical",
    "load_entry12_subentry_mat",
    "load_entry12_subentry_mat_from_env",
    "rgms_repo_root",
    "saved_rdp_dem_atariiii_mat_path",
]
