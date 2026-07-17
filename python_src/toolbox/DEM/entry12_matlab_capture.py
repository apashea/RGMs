"""Load Entry 12 MATLAB subentry checkpoint ``.mat`` files (``DEMAtariIII_entry12_<tag>_12X.mat``).

Built by ``matlab_custom/entry12/DEMAtariIII_entry12_dump_all_subentries.m`` (writes **12A**–**12I** in one run).
Uses ``scipy.io.loadmat`` for **MAT v7** and **v7.3** (HDF5) boundary bands **12D–12F**.

Does **not** import any ``tests/oracle`` Entry 1–11 modules.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

_MATLAB_META_KEYS = frozenset({"__header__", "__version__", "__globals__"})


class Entry12CompareLaneError(ValueError):
    """Compare-lane layout conversion failed; do not substitute MATLAB template values."""


def _entry12_compare_lane_fail(where: str, detail: str) -> None:
    raise Entry12CompareLaneError(f"{where}: {detail}")

# Pinned capture tag for documentation / CI (override via ``RGMS_ENTRY12_CANONICAL_RUN_TAG``).
# Generate mats in MATLAB with:
#   ``setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', ENTRY12_CANONICAL_RUN_TAG);``
#   ``DEMAtariIII_entry12_dump_all_subentries();``
ENTRY12_CANONICAL_RUN_TAG = (
    os.getenv("RGMS_ENTRY12_CANONICAL_RUN_TAG", "rgms_canonical").strip() or "rgms_canonical"
)

# Lean 12D/12E/12F boundary keys (``spm_MDP_VB_XXX_entry12_dump.m`` / Python dump mirror).
ENTRY12_LEAN_BOUNDARY_KEYS = ("in", "out_t1", "out_t2", "out_t3", "out_tT")

# OPTIM1FULL call4 — same causal lane as ``ENTRY12_LEAN_BOUNDARY_KEYS`` plus mid-horizon boundaries.
ENTRY12_OPTIM1FULL_CALL4_TAG = "rgms_atari_optim1full_call4"
ENTRY12_CALL4_LEAN_BOUNDARY_KEYS: tuple[str, ...] = (
    "in",
    "out_t1",
    "out_t2",
    "out_t3",
    "out_t10",
    "out_t20",
    "out_t30",
    "out_tT",
)

# Probe rollups on lean snaps (``entry12_Yfill`` / ``entry12_VBX`` diagnostics); not causal compute gates.
ENTRY12_INSPECTION_ONLY_SNAP_KEYS = frozenset({
    "nested_y_summary",
    "entry12_prechild",
    "entry12_phase_log",
    "entry12_forwards",
    "entry12_generation",
})

ENTRY12_PHASE_LOG_ORDER: tuple[str, ...] = (
    "post_generation",
    "post_share",
    "post_hierarchical",
    "pre_forwards",
    "pre_vbx",
    "post_vbx",
    "post_forwards",
    "post_mdp_F",
)

# VB loop order at each ``t``: **12D** (early within-``t``) → **12E** (outcomes) → **12F** (belief).
# Validation 12 evaluates all 15 steps in one run; fix compute in this order (first red wins).
ENTRY12_CAUSAL_BOUNDARY_STEPS: tuple[tuple[str, str], ...] = tuple(
    (band, sub)
    for sub in ENTRY12_LEAN_BOUNDARY_KEYS
    for band in ("12D", "12E", "12F")
)


def entry12_lean_boundary_keys_for_tag(tag: str | None = None) -> tuple[str, ...]:
    """Lean boundary keys for Validation **12** causal gate (call4 includes ``out_t10/20/30``)."""
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_resolve_run_tag

    t = (tag or entry12_resolve_run_tag()).strip()
    if t == ENTRY12_OPTIM1FULL_CALL4_TAG:
        return ENTRY12_CALL4_LEAN_BOUNDARY_KEYS
    return ENTRY12_LEAN_BOUNDARY_KEYS


def entry12_causal_boundary_steps_for_tag(tag: str | None = None) -> tuple[tuple[str, str], ...]:
    """Causal **12D→12E→12F** steps for ``tag`` (call4: **24** steps; default tags: **15**)."""
    return tuple(
        (band, sub)
        for sub in entry12_lean_boundary_keys_for_tag(tag)
        for band in ("12D", "12E", "12F")
    )


# ``spm_MDP_checkX`` / structure-learning ``ss`` blocks: MATLAB ``cell(4,4)`` per field.
_ENTRY12_SS_BLOCK_KEYS = ("D", "E", "ID", "IE")


def rgms_repo_root() -> Path:
    """``RGMs`` repo root (parent of ``python_src``)."""
    return Path(__file__).resolve().parents[3]


def default_entry12_mat_output_dir() -> Path:
    """Default Entry 12 capture dir (``demo1_fixtures_dir``; override with env)."""
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def entry12_capture_run_tag() -> str:
    """Active Entry 12 capture ``tag`` (env ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` or canonical)."""
    raw = str(os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "")).strip()
    return raw or ENTRY12_CANONICAL_RUN_TAG


def default_entry12_vb_matlab_rand_buf_mat_path(tag: str | None = None) -> Path:
    """MATLAB-captured ``rand(K,1)`` for ``spm_MDP_VB_XXX(..., reuse_matlab_draws=True)``."""
    raw = os.getenv("RGMS_ENTRY12_VB_MATLAB_RAND_MAT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    tag = tag or entry12_capture_run_tag()
    fix = default_entry12_mat_output_dir()
    if tag == ENTRY12_CANONICAL_RUN_TAG:
        return fix / "DEMAtariIII_entry12_vb_matlab_rand_buf.mat"
    return fix / f"DEMAtariIII_entry12_vb_matlab_rand_buf_{tag}.mat"


def default_entry12_vb_rand_k_mat_path(tag: str | None = None) -> Path:
    """Preflight ``K`` written for MATLAB dump (``entry12_preflight_vb_rand_k.py``)."""
    tag = tag or entry12_capture_run_tag()
    fix = default_entry12_mat_output_dir()
    if tag == ENTRY12_CANONICAL_RUN_TAG:
        return fix / "entry12_vb_rand_K.mat"
    return fix / f"entry12_vb_rand_K_{tag}.mat"


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


def _align_index_vectors_to_vb_template(py_val: Any, ref_val: Any, *, path: str) -> Any:
    """``sA``/``sC``/``sB`` list → ``ndarray`` when MATLAB VB template uses vectors."""
    import numpy as np

    if isinstance(py_val, list) and isinstance(ref_val, np.ndarray):
        flat = np.asarray(
            [int(x) for x in py_val],
            dtype=ref_val.dtype if ref_val.dtype != object else np.int64,
        )
        if flat.shape != ref_val.shape:
            flat = flat.reshape(ref_val.shape)
        if not np.array_equal(flat, ref_val):
            raise ValueError(f"{path} values differ from MATLAB VB template")
        return np.asarray(flat, dtype=ref_val.dtype)
    return py_val


def _align_mdp_subtree_to_vb_template(py_m: dict[str, Any], ref_m: dict[str, Any], *, path: str) -> None:
    import numpy as np

    from python_src.toolbox.DEM.spm_MDP_checkX import spm_mdp_g_dict_to_matlab_list

    g_py, g_ref = py_m.get("G"), ref_m.get("G")
    if isinstance(g_py, dict) and isinstance(g_ref, list):
        py_m["G"] = spm_mdp_g_dict_to_matlab_list(g_py)
    elif isinstance(g_py, dict) and isinstance(g_ref, np.ndarray):
        vec = spm_mdp_g_dict_to_matlab_list(g_py)
        flat = np.concatenate(
            [np.asarray(x, dtype=np.float64).ravel(order="F") for x in vec],
            axis=0,
        )
        if not np.allclose(flat, np.asarray(g_ref, dtype=np.float64).ravel(order="F"), rtol=0.0, atol=1e-12):
            raise ValueError(f"{path}.G values differ from MATLAB VB template")
        py_m["G"] = np.asarray(g_ref, dtype=g_ref.dtype).copy()
    for key in ("sA", "sB", "sC"):
        if key in py_m and key in ref_m:
            py_m[key] = _align_index_vectors_to_vb_template(
                py_m[key], ref_m[key], path=f"{path}.{key}"
            )
    u_py, u_ref = py_m.get("U"), ref_m.get("U")
    if isinstance(u_py, np.ndarray) and isinstance(u_ref, np.ndarray) and u_py.shape != u_ref.shape:
        flat = np.asarray(u_py, dtype=u_ref.dtype).ravel(order="F")
        if flat.size != u_ref.size:
            raise ValueError(f"{path}.U size {flat.size} != template {u_ref.size}")
        if not np.array_equal(flat, u_ref.ravel(order="F")):
            raise ValueError(f"{path}.U values differ from MATLAB VB template")
        py_m["U"] = flat.reshape(u_ref.shape).copy()


def align_rdp_containers_to_vb_template(py: dict[str, Any], template: dict[str, Any]) -> None:
    """
    Align checkX'd Python ``RDP`` containers to the MATLAB-derived VB template.

    ``template`` is ``entry12_rdp_for_vb_from_mat_nested(loadmat ...['RDP'])`` — same lane as
    script **3**, not a Python FSL assembly object.
    """
    import numpy as np
    import scipy.sparse as sp

    for key in ("sA", "sC"):
        if key in py and key in template:
            py[key] = _align_index_vectors_to_vb_template(py[key], template[key], path=f"RDP.{key}")
    id_py, id_ref = py.get("id"), template.get("id")
    if isinstance(id_py, dict) and isinstance(id_ref, dict):
        for key in ("cid", "hid"):
            if key in id_py and key in id_ref:
                id_py[key] = _align_index_vectors_to_vb_template(
                    id_py[key], id_ref[key], path=f"RDP.id.{key}"
                )

    h_py, h_ref = py.get("H"), template.get("H")
    if isinstance(h_py, list) and sp.issparse(h_ref):
        stacked = np.concatenate(
            [np.asarray(cell, dtype=np.float64).ravel(order="F") for cell in h_py],
            axis=0,
        )
        ref_dense = np.asarray(h_ref.todense(), dtype=np.float64).ravel(order="F")
        if stacked.size != ref_dense.size:
            raise ValueError(
                f"RDP.H list ravel len {stacked.size} != MATLAB template len {ref_dense.size}"
            )
        if not np.allclose(stacked, ref_dense, rtol=0.0, atol=1e-12, equal_nan=True):
            raise ValueError("RDP.H values differ from MATLAB VB template after ravel")
        ref_arr = np.asarray(h_ref.todense(), dtype=np.float64)
        py["H"] = sp.csc_array(stacked.reshape(ref_arr.shape))

    mdp_py, mdp_ref = py.get("MDP"), template.get("MDP")
    if isinstance(mdp_py, dict) and isinstance(mdp_ref, dict):
        _align_mdp_subtree_to_vb_template(mdp_py, mdp_ref, path="RDP.MDP")
    if not isinstance(mdp_py, dict) or not isinstance(mdp_ref, dict):
        return
    a_py, a_ref = mdp_py.get("A"), mdp_ref.get("A")
    if not isinstance(a_py, dict) or not isinstance(a_ref, dict):
        return
    for key in a_py:
        if key not in a_ref:
            continue
        va = np.asarray(a_py[key], dtype=np.float64)
        vb = np.asarray(a_ref[key], dtype=np.float64)
        if va.ndim == 2 and va.shape[1] == 1 and vb.ndim == 1 and va.shape[0] == vb.shape[0]:
            flat = va.reshape(-1)
            if not np.allclose(flat, vb, rtol=0.0, atol=1e-12, equal_nan=True):
                raise ValueError(f"RDP.MDP.A[{key!r}] values differ from MATLAB VB template")
            a_py[key] = flat.copy()


def rdp_for_vb_from_python_assembly(
    rdp_assembly: dict[str, Any],
    *,
    tag: str = "rgms_canonical",
    align_to_mat_template: bool | None = None,
) -> dict[str, Any]:
    """
    ``DEM_AtariIII`` / FSL Entry **11**: ``entry12_rdp_for_vb_from_mat_nested`` on Python-built ``RDP``.

    Default (``align_to_mat_template=False``): checkX + ``spm_mdp_normalize_rdp_matlab_containers``
    from ``spm_mdp2rdp`` must match script **3** ``load_entry12_rdp_for_tag`` on ``rgms_canonical``.

    Set ``align_to_mat_template=True`` (or env ``RGMS_RDP_ALIGN_TO_MAT_VB_TEMPLATE=1``) to run
    ``align_rdp_containers_to_vb_template`` against ``XXX_12_rdp.mat`` — diagnostic / legacy only.
    """
    import copy
    import os

    from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call_rdp_mat_path
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import load_entry12_rdp_mat_nested_for_tag

    py = entry12_rdp_for_vb_from_mat_nested(copy.deepcopy(rdp_assembly))
    if align_to_mat_template is None:
        raw = str(os.getenv("RGMS_RDP_ALIGN_TO_MAT_VB_TEMPLATE", "")).strip().lower()
        align_to_mat_template = raw in ("1", "true", "yes")
    if not align_to_mat_template:
        return py

    mat_p = entry12_atari_call_rdp_mat_path(tag)
    if not mat_p.is_file():
        raise FileNotFoundError(f"missing RDP mat for tag {tag!r}: {mat_p}")
    mat_nested = load_entry12_rdp_mat_nested_for_tag(tag, mat_p)
    template = entry12_rdp_for_vb_from_mat_nested(copy.deepcopy(mat_nested))
    align_rdp_containers_to_vb_template(py, template)
    return py


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


def _entry12_peel_nm_one_model_shell(py_cell: Any, mat_ref: Any) -> Any:
    """Drop leading ``Nm=1`` model axis on Python 12C shells (MATLAB ``.mat`` has no model row)."""
    if not isinstance(py_cell, list) or not isinstance(mat_ref, list) or len(py_cell) != 1:
        return py_cell
    inner = py_cell[0]
    if not isinstance(inner, list):
        return py_cell
    py_sh = _entry12_nested_list_shape(py_cell)
    mat_sh = _entry12_nested_list_shape(mat_ref)
    if len(py_sh) >= 2 and py_sh[0] == 1:
        if py_sh[1:] == mat_sh:
            return inner
        if len(mat_ref) == py_sh[1]:
            return inner
    return py_cell


def _entry12_align_12c_O_preloop(py_o: Any, mat_o: Any) -> Any:
    """``O{m,g,t}`` at **12C**: empty pre-loop cells (MATLAB ``[]``) vs Python ``None`` placeholders."""
    import numpy as np

    py_use = _entry12_peel_nm_one_model_shell(py_o, mat_o)
    if not isinstance(py_use, list) or not isinstance(mat_o, list):
        return _entry12_cast_leaf_for_compare(py_use, mat_o)
    rows: list[Any] = []
    for g_idx, mat_row in enumerate(mat_o):
        py_row = py_use[g_idx] if g_idx < len(py_use) else []
        if not isinstance(mat_row, list):
            rows.append(_entry12_cast_leaf_for_compare(py_row, mat_row))
            continue
        cells: list[Any] = []
        for t_idx, mat_leaf in enumerate(mat_row):
            py_leaf = py_row[t_idx] if isinstance(py_row, list) and t_idx < len(py_row) else None
            mat_arr = np.asarray(mat_leaf, dtype=np.float64)
            if py_leaf is None or (isinstance(py_leaf, list) and len(py_leaf) == 0):
                cells.append(
                    np.zeros((0,), dtype=np.float64)
                    if mat_arr.size == 0
                    else _entry12_cast_leaf_for_compare(py_leaf, mat_leaf)
                )
            else:
                cells.append(_entry12_cast_leaf_for_compare(py_leaf, mat_leaf))
        rows.append(cells)
    return rows


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
    if isinstance(ref, (int, np.integer)) and isinstance(val, (float, np.floating)):
        fv = float(val)
        if fv == round(fv):
            return int(round(fv))
    if isinstance(ref, np.ndarray) and not isinstance(val, (dict, list)):
        arr = np.asarray(val, dtype=np.float64)
        if ref.size == 1 and arr.size >= 1:
            return np.asarray(float(arr.reshape(-1)[0]), dtype=np.float64).reshape(
                ref.shape, order="F"
            )
        if ref.size == 0 and arr.size == 0:
            return np.asarray([], dtype=ref.dtype)
    # ``mdp.Y{o,t}`` / ``Q.Y`` cells: MATLAB dumps one-hot ``uint8``; Python keeps float64 (~1.0).
    if isinstance(ref, np.ndarray) and isinstance(val, np.ndarray):
        if ref.dtype.kind in "iu" and val.dtype.kind in "f":
            ref = np.asarray(ref, dtype=np.float64)
    return _cast_leaf_like_reference(val, ref)


def _entry12_align_nested_lists_for_compare(py_val: Any, mat_val: Any) -> Any:
    """Recursively align nested list cells (e.g. ``j{g,t}``) before transform-align."""
    if isinstance(mat_val, list) and isinstance(py_val, list):
        n = len(mat_val)
        return [
            _entry12_align_nested_lists_for_compare(
                py_val[i] if i < len(py_val) else py_val[-1],
                mat_val[i],
            )
            for i in range(n)
        ]
    return _entry12_cast_leaf_for_compare(py_val, mat_val)


def _entry12_drop_pdp_mdp_trace_keys_for_value_assert(mdp: dict[str, Any]) -> None:
    """Reserved hook; parity requires ``MDP.G`` and ``Q.E`` stay in compare trees (no drops)."""
    del mdp  # no-op


def _entry12_flatten_Q_E_nested_for_compare(val: Any) -> Any:
    """``mdp.Q.E{L}``: nested list cells with ``(2,1)`` blocks → one MATLAB flat vector."""
    import numpy as np

    scalars: list[float] = []

    def walk(v: Any) -> None:
        if isinstance(v, list):
            for item in v:
                walk(item)
        elif isinstance(v, np.ndarray):
            scalars.extend(np.asarray(v, dtype=np.float64).ravel().tolist())
        elif isinstance(v, (int, float, np.integer, np.floating)):
            scalars.append(float(v))

    walk(val)
    return np.asarray(scalars, dtype=np.float64)


def entry12_mat_mdp_for_subentry_value_assert(
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
) -> dict[str, Any]:
    """Drop MATLAB-only ``MDP`` keys when Python checkpoint omits them (e.g. **12A** ``G``)."""
    import copy

    if not isinstance(mat_mdp, dict):
        return mat_mdp
    out = copy.deepcopy(mat_mdp)
    if isinstance(py_mdp, dict) and "G" not in py_mdp:
        out.pop("G", None)
    py_inner = py_mdp.get("MDP") if isinstance(py_mdp, dict) else None
    mat_inner = out.get("MDP") if isinstance(out, dict) else None
    if isinstance(py_inner, dict) and isinstance(mat_inner, dict):
        out["MDP"] = entry12_mat_mdp_for_subentry_value_assert(py_inner, mat_inner)
    return out


def entry12_mat_pdp_for_value_assert(mat_pdp: dict[str, Any]) -> dict[str, Any]:
    """MATLAB **12H** / final **PDP** snapshot for value assert (drop non-paired probes)."""
    import copy

    out = copy.deepcopy(mat_pdp)
    for key in ("entry12_Yfill", "entry12_VBX", "entry12_forwards", "entry12_generation"):
        out.pop(key, None)
    mdp = out.get("MDP")
    if isinstance(mdp, dict):
        for key in ("entry12_Yfill", "entry12_VBX", "entry12_forwards", "entry12_generation"):
            mdp.pop(key, None)
        _entry12_drop_pdp_mdp_trace_keys_for_value_assert(mdp)
        pa = mdp.get("Pa")
        if pa == [] or pa is None:
            mdp.pop("Pa", None)
    return out


def _entry12_strip_pdp_inspection_probes(py_pdp: dict[str, Any]) -> None:
    """Remove Python-only capture probes before **12H** / **PDP** value assert."""
    _entry12_strip_inspection_only_snap_keys(py_pdp)
    for key in ("entry12_VBX", "entry12_Yfill", "entry12_forwards", "entry12_generation"):
        py_pdp.pop(key, None)
    mdp = py_pdp.get("MDP")
    if isinstance(mdp, dict):
        _entry12_strip_inspection_only_snap_keys(mdp)
        for key in ("entry12_VBX", "entry12_Yfill", "entry12_forwards", "entry12_generation"):
            mdp.pop(key, None)
        _entry12_drop_pdp_mdp_trace_keys_for_value_assert(mdp)
        if mdp.get("Pa") == {}:
            mdp.pop("Pa", None)


def _entry12_flatten_nested_lists_to_ravel(val: Any) -> list[Any]:
    """Depth-first flatten of nested lists (``mdp.Q.E`` script-3 vs ``.mat`` vector)."""
    out: list[Any] = []
    if isinstance(val, list):
        for item in val:
            out.extend(_entry12_flatten_nested_lists_to_ravel(item))
    else:
        out.append(val)
    return out


def _entry12_align_mdp_Q_for_12h(py_q: dict[str, Any], mat_q: dict[str, Any]) -> None:
    """Align assembled ``mdp.Q`` blocks (flat vectors vs nested list cells)."""
    import numpy as np

    for qk, mq in mat_q.items():
        if qk not in py_q:
            continue
        # Trajectory / flat-row blocks: ``_entry12_align_Q_record_to_mat`` only.
        if qk in ("O", "P", "X", "Y", "j", "i", "o"):
            continue
        pq = py_q[qk]
        if isinstance(mq, np.ndarray) and isinstance(pq, list):
            if qk == "E":
                flat = _entry12_flatten_Q_E_nested_for_compare(pq)
            else:
                flat = _entry12_flatten_nested_lists_to_ravel(pq)
            arr = np.asarray(flat, dtype=np.float64).ravel(order="F")
            if arr.size == int(np.asarray(mq).size):
                py_q[qk] = arr.reshape(np.asarray(mq).shape, order="F")
        elif isinstance(mq, list) and isinstance(pq, list):
            py_q[qk] = _entry12_align_nested_lists_for_compare(pq, mq)


def _entry12_align_id_record_for_compare(py_id: dict[str, Any], mat_id: dict[str, Any]) -> dict[str, Any]:
    """Align ``id.*`` (including ``id.A[f]`` scalars) to MATLAB ``loadmat`` template types."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    out = copy.deepcopy(py_id)
    _spm_MDP_checkX_transform_align(out, mat_id)
    return out


def _entry12_align_pdp_assemble_shell(py_pdp: dict[str, Any], mat_pdp: dict[str, Any]) -> None:
    """
    **12H** / final **PDP** compare lane: MATLAB ``loadmat`` vs Python assemble layout.

    Examples: top-level ``B`` as ``(Ns,Ns,Nu)`` ndarray vs ``[B{1}]`` list; ``MDP.B{f}`` scalar
    ``int`` vs ``(1,1)`` array; ``j{g,t}`` as ``int`` vs Python ``float`` one-hot indices.
    """
    import numpy as np

    mat_b = mat_pdp.get("B")
    py_b = py_pdp.get("B")
    if isinstance(mat_b, np.ndarray) and isinstance(py_b, list) and len(py_b) == 1:
        arr = np.asarray(py_b[0], dtype=np.float64)
        if arr.shape == mat_b.shape:
            py_pdp["B"] = arr
    for key in ("O", "Y", "j", "i", "n", "o"):
        py_v, mat_v = py_pdp.get(key), mat_pdp.get(key)
        if not isinstance(py_v, list) or not isinstance(mat_v, list):
            continue
        if key == "O":
            py_pdp[key] = _entry12_align_mdp_O_ng_t_cells(py_v, mat_v)
        elif len(py_v) > len(mat_v):
            py_pdp[key] = [
                _entry12_cast_leaf_for_compare(py_v[i], mat_v[i]) for i in range(len(mat_v))
            ]
        elif len(py_v) == len(mat_v):
            if (
                key in ("Y", "j", "i")
                and py_v
                and isinstance(py_v[0], list)
                and isinstance(mat_v[0], list)
            ):
                py_pdp[key] = [
                    _entry12_align_nested_lists_for_compare(py_v[i], mat_v[i])
                    for i in range(len(mat_v))
                ]
            else:
                py_pdp[key] = _entry12_align_scalar_list_to_mat(py_v, mat_v)
    py_pa, mat_pa = py_pdp.get("Pa"), mat_pdp.get("Pa")
    if isinstance(py_pa, dict) and isinstance(mat_pa, list):
        keys = sorted(py_pa.keys(), key=lambda k: int(k) if str(k).isdigit() else k)
        py_pdp["Pa"] = [
            _entry12_cast_leaf_for_compare(
                py_pa[keys[i]] if i < len(keys) else {},
                mat_pa[i] if i < len(mat_pa) else mat_pa[-1],
            )
            for i in range(len(mat_pa))
        ]
    py_id, mat_id = py_pdp.get("id"), mat_pdp.get("id")
    if isinstance(py_id, dict) and isinstance(mat_id, dict):
        py_pdp["id"] = _entry12_align_id_record_for_compare(py_id, mat_id)
    for sk in ("T", "U"):
        if sk in py_pdp and sk in mat_pdp:
            py_pdp[sk] = _entry12_cast_leaf_for_compare(py_pdp[sk], mat_pdp[sk])
    py_q, mat_q = py_pdp.get("Q"), mat_pdp.get("Q")
    if isinstance(py_q, dict) and isinstance(mat_q, dict):
        py_pdp["Q"] = _entry12_align_Q_record_to_mat(py_q, mat_q)
    py_mdp = py_pdp.get("MDP")
    mat_mdp = mat_pdp.get("MDP")
    if isinstance(py_mdp, dict) and isinstance(mat_mdp, dict):
        for cell_key in ("B", "D", "E", "H"):
            pb, mb = py_mdp.get(cell_key), mat_mdp.get(cell_key)
            if isinstance(pb, list) and isinstance(mb, list):
                py_mdp[cell_key] = [
                    _entry12_cast_leaf_for_compare(pb[i] if i < len(pb) else pb[-1], mb[i])
                    for i in range(len(mb))
                ]
        for key in ("j", "i", "n", "o", "sA", "sB", "sC"):
            if key in py_mdp and key in mat_mdp:
                py_mdp[key] = _entry12_align_nested_lists_for_compare(
                    py_mdp[key], mat_mdp[key]
                )
        py_o, mat_o = py_mdp.get("O"), mat_mdp.get("O")
        if isinstance(py_o, list) and isinstance(mat_o, list):
            py_mdp["O"] = _entry12_align_mdp_O_ng_t_cells(py_o, mat_o)
        py_q, mat_q = py_mdp.get("Q"), mat_mdp.get("Q")
        if isinstance(py_q, dict) and isinstance(mat_q, dict):
            _entry12_align_mdp_Q_for_12h(py_q, mat_q)
        py_id_n, mat_id_n = py_mdp.get("id"), mat_mdp.get("id")
        if isinstance(py_id_n, dict) and isinstance(mat_id_n, dict):
            py_mdp["id"] = _entry12_align_id_record_for_compare(py_id_n, mat_id_n)
        for sk in ("T", "U", "u"):
            if sk in py_mdp and sk in mat_mdp:
                py_mdp[sk] = _entry12_cast_leaf_for_compare(py_mdp[sk], mat_mdp[sk])


def _entry12_align_scalar_list_to_mat(py_list: list[Any], mat_list: list[Any]) -> list[Any]:
    n = len(mat_list)
    return [_entry12_cast_leaf_for_compare(py_list[i] if i < len(py_list) else py_list[-1], mat_list[i]) for i in range(n)]


def _entry12_collect_nested_leaves(val: Any, out: list[Any]) -> None:
    if isinstance(val, list):
        for item in val:
            _entry12_collect_nested_leaves(item, out)
    else:
        out.append(val)


def _entry12_align_mdp_O_ng_t_cells(py_o: list[Any], mat_o: list[Any]) -> list[Any]:
    """
    Assembled **12H** ``MDP.O``: Python ``O[t][g]`` (time-outer) vs MATLAB ``O{g,t}`` cells.

    After ``shiftdim``, script **3** may leave ``[T][Ng]`` while ``loadmat`` exposes ``Ng`` cells
    each holding a length-``T`` row.
    """
    if not isinstance(py_o, list) or not isinstance(mat_o, list) or not mat_o:
        return py_o
    if len(py_o) == len(mat_o):
        if mat_o and isinstance(mat_o[0], list):
            ng = len(mat_o)
            return [
                [
                    _entry12_cast_leaf_for_compare(
                        py_o[g][t] if isinstance(py_o[g], list) and t < len(py_o[g]) else py_o[g],
                        mat_o[g][t] if t < len(mat_o[g]) else mat_o[g][-1],
                    )
                    for t in range(len(mat_o[g]))
                ]
                for g in range(ng)
            ]
        return _entry12_align_scalar_list_to_mat(py_o, mat_o)
    if (
        py_o
        and isinstance(py_o[0], list)
        and len(py_o) != len(mat_o)
        and isinstance(mat_o[0], list)
    ):
        nt = len(py_o)
        ng = len(py_o[0])
        if ng == len(mat_o) and mat_o and len(mat_o[0]) == nt:
            return [
                [
                    _entry12_cast_leaf_for_compare(
                        py_o[t][g] if t < len(py_o) and g < len(py_o[t]) else py_o[-1][g],
                        mat_o[g][t] if t < len(mat_o[g]) else mat_o[g][-1],
                    )
                    for t in range(nt)
                ]
                for g in range(ng)
            ]
    return _entry12_flatten_O_ng_t_mat(py_o, mat_o)


def _entry12_flatten_O_ng_t_mat(py_o: list[Any], mat_o: list[Any]) -> list[Any]:
    """Flatten nested ``O{g,t}`` (Python ``O[g][t]``) to MATLAB column-major ``Ng×T`` cell vector."""
    if not isinstance(py_o, list) or not isinstance(mat_o, list):
        return py_o
    if len(py_o) == len(mat_o):
        return _entry12_align_scalar_list_to_mat(py_o, mat_o)
    if not py_o or not isinstance(py_o[0], list):
        return _entry12_flatten_nested_list_to_mat(py_o, mat_o)
    ng = len(py_o)
    nt = len(py_o[0])
    if ng * nt != len(mat_o):
        return _entry12_flatten_nested_list_to_mat(py_o, mat_o)
    flat: list[Any] = []
    for t_idx in range(nt):
        for g in range(ng):
            leaf = py_o[g][t_idx] if t_idx < len(py_o[g]) else py_o[g][-1]
            flat.append(leaf)
    return [_entry12_cast_leaf_for_compare(flat[i], mat_o[i]) for i in range(len(mat_o))]


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


def _entry12_q_o_flat_index_t_shiftdim(t: int, g: int, *, ncol: int) -> int:
    """Linear index for post-``shiftdim`` ``T×Ng`` cell row (MATLAB ``(:)`` column-major): ``t + g*ncol``."""
    return int(t) + int(g) * int(ncol)


def _entry12_q_o_flat_index_g_preshiftdim(g: int, t: int, *, ng: int) -> int:
    """Linear index for pre-``shiftdim`` ``Ng×T`` cell row (MATLAB ``(:)`` column-major): ``g + t*ng``."""
    return int(g) + int(t) * int(ng)


def _entry12_is_flat_q_o_cell_row(mat_o_level: list[Any], ncol: int) -> bool:
    """True when ``mat_o_level`` is MATLAB ``shiftdim`` flat ``T×Ng`` cell row (not one dense matrix)."""
    import numpy as np

    n_leaf = len(mat_o_level)
    if ncol < 1 or n_leaf <= ncol or n_leaf % ncol != 0:
        return False
    if n_leaf == 1:
        first = np.asarray(mat_o_level[0])
        return bool(first.ndim == 2 and int(first.shape[1]) == ncol)
    ng = n_leaf // ncol
    if ng <= 1:
        return False
    for item in mat_o_level[: min(16, n_leaf)]:
        a = np.asarray(item)
        if a.ndim == 2 and int(a.shape[1]) > 1:
            return False
    return True


def _entry12_q_o_cells_row_to_matrix(mat_cells: list[Any], ncol: int) -> Any:
    """
    Rebuild MATLAB ``Q.O{L}`` from a flat post-``shiftdim`` ``T×Ng`` cell row (``(:)`` order).

    Flat index ``t + g*ncol``; columns are time ``t``; rows stack modalities ``g`` (variable ``No(g)``).
    """
    import numpy as np

    n_leaf = len(mat_cells)
    if ncol < 1 or n_leaf % ncol != 0:
        _entry12_compare_lane_fail(
            "_entry12_q_o_cells_row_to_matrix",
            f"ncol={ncol} n_leaf={n_leaf} (not divisible)",
        )
    ng = n_leaf // ncol
    cols: list[np.ndarray] = []
    for t in range(ncol):
        parts = [
            np.asarray(mat_cells[_entry12_q_o_flat_index_t_shiftdim(t, g, ncol=ncol)], dtype=np.float64).reshape(
                -1, 1
            )
            for g in range(ng)
        ]
        cols.append(np.vstack(parts))
    max_h = max(int(c.shape[0]) for c in cols)
    out = np.zeros((max_h, ncol), dtype=np.float64, order="F")
    for t, col in enumerate(cols):
        out[: col.shape[0], t : t + 1] = col
    return np.asfortranarray(out)


def _entry12_is_q_o_mat_nested_grid(mat_o_level: list[Any]) -> bool:
    """MATLAB ``loadmat`` ``Q.O{L}`` as ``Ng`` rows × ``T`` nested cells (``O{g,t}``)."""
    import numpy as np

    if not isinstance(mat_o_level, list) or not mat_o_level:
        return False
    first = mat_o_level[0]
    return isinstance(first, list) and not isinstance(first, np.ndarray)


def _entry12_q_ot_mat_row_len(row: Any) -> int | None:
    """Length of one MATLAB ``Q.{Y,j,i,o}`` outcome row (``Ng×T`` history)."""
    import numpy as np

    if isinstance(row, list):
        return len(row)
    if isinstance(row, np.ndarray) and row.dtype == object:
        return int(row.size)
    return None


def _entry12_q_ot_mat_row_cell(row: Any, t: int) -> Any:
    import numpy as np

    if isinstance(row, list):
        return row[t]
    if isinstance(row, np.ndarray) and row.dtype == object:
        return row[t]
    return row


def _entry12_is_q_ot_mat_outcome_rows(mat_level: list[Any]) -> bool:
    """``Q.{Y,j,i,o}{L}`` as ``Ng`` outcome rows × ``T`` history cells (``(:)`` index ``o + t*Ng``)."""
    if not isinstance(mat_level, list) or len(mat_level) < 2:
        return False
    t_len = _entry12_q_ot_mat_row_len(mat_level[0])
    if t_len is None or t_len < 1:
        return False
    for row in mat_level[1 : min(16, len(mat_level))]:
        if _entry12_q_ot_mat_row_len(row) != t_len:
            return False
    return True


def _entry12_pair_q_ot_flat_py_to_mat_outcome_rows(
    flat: list[Any],
    mat_rows: list[Any],
) -> list[Any]:
    """Pair flat Python ``Q.{Y,j,i,o}`` (``o + t*Ng``) to MATLAB ``Ng×T`` outcome rows — no substitution."""
    ng = len(mat_rows)
    t_len = _entry12_q_ot_mat_row_len(mat_rows[0])
    if t_len is None:
        _entry12_compare_lane_fail(
            "_entry12_pair_q_ot_flat_py_to_mat_outcome_rows",
            "mat_rows[0] is not a length-T cell row",
        )
    n_expect = ng * t_len
    if len(flat) != n_expect:
        _entry12_compare_lane_fail(
            "_entry12_pair_q_ot_flat_py_to_mat_outcome_rows",
            f"flat len {len(flat)} != Ng*T {n_expect} (Ng={ng} T={t_len})",
        )
    out: list[Any] = []
    for o in range(ng):
        mat_row = mat_rows[o]
        if _entry12_q_ot_mat_row_len(mat_row) != t_len:
            _entry12_compare_lane_fail(
                "_entry12_pair_q_ot_flat_py_to_mat_outcome_rows",
                f"row {o} len != T {t_len}",
            )
        row: list[Any] = []
        for t in range(t_len):
            idx = _entry12_q_o_flat_index_g_preshiftdim(o, t, ng=ng)
            row.append(
                _entry12_cast_leaf_for_compare(flat[idx], _entry12_q_ot_mat_row_cell(mat_row, t))
            )
        out.append(row)
    return out


def _entry12_q_o_py_flat_cell_row(py_o_level: Any) -> list[Any] | None:
    """Script **3** flat post-``shiftdim`` ``Q.O{L}`` row (``t + g*T`` leaf list)."""
    import numpy as np

    if not isinstance(py_o_level, list) or not py_o_level:
        return None
    first = py_o_level[0]
    if isinstance(first, (list, tuple)) and not isinstance(first, np.ndarray):
        return None
    if isinstance(first, np.ndarray) and first.ndim > 1 and int(first.size) > 64:
        return None
    return py_o_level


def _entry12_pair_q_o_flat_py_to_mat_grid(
    flat: list[Any],
    mat_grid: list[Any],
) -> list[Any]:
    """Pair flat Python ``Q.O{L}`` (``t + g*ncol``) to MATLAB ``Ng×T`` grid — no MATLAB substitution."""
    ng = len(mat_grid)
    if ng < 1 or not isinstance(mat_grid[0], list):
        _entry12_compare_lane_fail(
            "_entry12_pair_q_o_flat_py_to_mat_grid",
            "mat_grid is not Ng×T nested lists",
        )
    ncol = len(mat_grid[0])
    n_expect = ng * ncol
    if len(flat) != n_expect:
        _entry12_compare_lane_fail(
            "_entry12_pair_q_o_flat_py_to_mat_grid",
            f"flat len {len(flat)} != Ng*T {n_expect} (Ng={ng} T={ncol})",
        )
    out: list[Any] = []
    for g in range(ng):
        mat_row = mat_grid[g]
        if len(mat_row) != ncol:
            _entry12_compare_lane_fail(
                "_entry12_pair_q_o_flat_py_to_mat_grid",
                f"row {g} len {len(mat_row)} != T {ncol}",
            )
        row: list[Any] = []
        for t in range(ncol):
            idx = _entry12_q_o_flat_index_t_shiftdim(t, g, ncol=ncol)
            row.append(_entry12_cast_leaf_for_compare(flat[idx], mat_row[t]))
        out.append(row)
    return out


def _entry12_is_q_o_ng_t_rows(level: Any) -> bool:
    """``mdp.Q.O{L}`` as ``Ng`` rows of ragged time vectors (paired ``.mat`` / script **3**)."""
    if not isinstance(level, list) or not level:
        return False
    return isinstance(level[0], (list, tuple))


def _entry12_align_q_o_ng_t_rows(py_rows: list[Any], mat_rows: list[Any]) -> list[Any]:
    """Element-wise align one ``Q.O{L}`` level stored as ``cell(Ng,T)`` rows."""
    ng = max(len(py_rows), len(mat_rows))
    out: list[Any] = []
    for g in range(ng):
        py_r = py_rows[g] if g < len(py_rows) else []
        mat_r = mat_rows[g] if g < len(mat_rows) else []
        if not isinstance(py_r, (list, tuple)):
            py_r = [py_r]
        if not isinstance(mat_r, (list, tuple)):
            mat_r = [mat_r]
        ncol = max(len(py_r), len(mat_r))
        row: list[Any] = []
        for t in range(ncol):
            py_c = py_r[t] if t < len(py_r) else (py_r[-1] if py_r else None)
            mat_c = mat_r[t] if t < len(mat_r) else (mat_r[-1] if mat_r else None)
            row.append(_entry12_cast_leaf_for_compare(py_c, mat_c))
        out.append(row)
    return out


def _entry12_Q_O_level_to_mat_cells(
    py_o_level: Any,
    mat_o_level: Any,
    *,
    kind: str = "O",
) -> Any:
    """
    Compare lane: one ``Q.*{L}`` level.

    ``O`` uses post-``shiftdim`` flat index ``t + g*ncol``; ``Y``/``j``/``i``/``o`` use ``o + t*Ng``.
    """
    import copy

    import numpy as np

    if not isinstance(mat_o_level, list) or not mat_o_level:
        return _entry12_cast_leaf_for_compare(py_o_level, mat_o_level)
    if (
        kind == "O"
        and isinstance(py_o_level, list)
        and _entry12_is_q_o_ng_t_rows(mat_o_level)
        and _entry12_is_q_o_ng_t_rows(py_o_level)
    ):
        return _entry12_align_q_o_ng_t_rows(py_o_level, mat_o_level)
    if (
        kind in ("Y", "j", "i", "o")
        and isinstance(py_o_level, list)
        and _entry12_is_q_ot_mat_outcome_rows(mat_o_level)
        and _entry12_is_q_ot_mat_outcome_rows(py_o_level)
    ):
        return _entry12_align_q_o_ng_t_rows(py_o_level, mat_o_level)
    flat_py = _entry12_q_o_py_flat_cell_row(py_o_level)
    if flat_py is not None and kind in ("Y", "j", "i", "o") and _entry12_is_q_ot_mat_outcome_rows(
        mat_o_level
    ):
        return _entry12_pair_q_ot_flat_py_to_mat_outcome_rows(flat_py, mat_o_level)
    if flat_py is not None and _entry12_is_q_o_mat_nested_grid(mat_o_level):
        if kind in ("Y", "j", "i", "o"):
            return _entry12_pair_q_ot_flat_py_to_mat_outcome_rows(flat_py, mat_o_level)
        return _entry12_pair_q_o_flat_py_to_mat_grid(flat_py, mat_o_level)
    if isinstance(py_o_level, list) and len(py_o_level) == len(mat_o_level):
        return _entry12_align_scalar_list_to_mat(py_o_level, mat_o_level)
    py_arr: np.ndarray | None = None
    if isinstance(py_o_level, np.ndarray):
        py_arr = np.asarray(py_o_level, dtype=np.float64)
    elif isinstance(py_o_level, list) and len(py_o_level) == 1:
        try:
            py_arr = np.asarray(py_o_level[0], dtype=np.float64)
        except (TypeError, ValueError):
            py_arr = None
    if py_arr is None or py_arr.size == 0:
        py_list = py_o_level if isinstance(py_o_level, list) else [py_o_level]
        flat_py = _entry12_q_o_py_flat_cell_row(py_list)
        if flat_py is not None and _entry12_is_q_o_mat_nested_grid(mat_o_level):
            if kind in ("Y", "j", "i", "o"):
                return _entry12_pair_q_ot_flat_py_to_mat_outcome_rows(flat_py, mat_o_level)
            return _entry12_pair_q_o_flat_py_to_mat_grid(flat_py, mat_o_level)
        return _entry12_align_scalar_list_to_mat(py_list, mat_o_level)
    if py_arr.ndim == 1:
        py_arr = py_arr.reshape(-1, 1)
    if py_arr.ndim != 2:
        return _entry12_align_scalar_list_to_mat(
            py_o_level if isinstance(py_o_level, list) else [py_o_level],
            mat_o_level,
        )
    ncol = int(py_arr.shape[1])
    n_leaf = len(mat_o_level)
    if ncol < 1 or n_leaf % ncol != 0:
        _entry12_compare_lane_fail(
            "_entry12_Q_O_level_to_mat_cells",
            f"ncol={ncol} n_leaf={n_leaf} (not divisible)",
        )
    ng = n_leaf // ncol
    flat: list[Any] = []
    row = 0
    for g in range(ng):
        for t in range(ncol):
            idx = _entry12_q_o_flat_index_t_shiftdim(t, g, ncol=ncol)
            ref = np.asarray(mat_o_level[idx]).reshape(-1, 1)
            n = int(ref.shape[0])
            if row + n > py_arr.shape[0]:
                mat_m = _entry12_q_o_cells_row_to_matrix(mat_o_level, ncol)
                _entry12_compare_lane_fail(
                    "_entry12_Q_O_level_to_mat_cells",
                    f"row overflow at g={g} t={t} (py rows={py_arr.shape[0]} "
                    f"mat rows={mat_m.shape[0]})",
                )
            chunk = py_arr[row : row + n, t : t + 1]
            flat.append(_entry12_cast_leaf_for_compare(chunk.reshape(-1, 1), mat_o_level[idx]))
            row += n
    if len(flat) == len(mat_o_level):
        return flat
    _entry12_compare_lane_fail(
        "_entry12_Q_O_level_to_mat_cells",
        f"flattened len {len(flat)} != mat_o_level len {len(mat_o_level)}",
    )


def _entry12_cast_q_trajectory_ndarray_for_compare(val: Any, ref: Any) -> Any:
    """``Q.s`` / ``Q.u`` / ``Q.o`` / ``Q.E``: Python column blocks vs MATLAB ``Ng×T`` ``ndarray``."""
    import numpy as np

    arr = np.asarray(val, dtype=np.float64)
    ref_a = np.asarray(ref, dtype=np.float64)
    if ref_a.dtype.kind in "iu":
        ref_a = ref_a.astype(np.float64)
    if arr.size == ref_a.size and arr.shape != ref_a.shape:
        # Appended trajectory columns are MATLAB ``[old new]`` hstack; serialized as a tall column.
        if np.allclose(arr.reshape(ref_a.shape, order="C"), ref_a, rtol=0.0, atol=1e-10):
            arr = arr.reshape(ref_a.shape, order="C")
        elif np.allclose(arr.reshape(ref_a.shape, order="F"), ref_a, rtol=0.0, atol=1e-10):
            arr = arr.reshape(ref_a.shape, order="F")
    return _entry12_cast_leaf_for_compare(arr, ref_a)


def _entry12_unwrap_q_py_level_for_ndarray_compare(py_levels: Any) -> Any:
    """Python ``mdp.Q.*{L}`` may be ``[matrix]`` or ``[[col…]]``; MATLAB dump may be a bare ``ndarray``."""
    import numpy as np

    cur: Any = py_levels[0] if isinstance(py_levels, list) and len(py_levels) == 1 else py_levels
    if isinstance(cur, list) and len(cur) == 1:
        cur = cur[0]
    if isinstance(cur, list) and cur and isinstance(cur[0], np.ndarray):
        cols: list[np.ndarray] = []
        for item in cur:
            arr = np.asarray(item, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1, order="F")
            elif arr.ndim == 2 and int(arr.shape[1]) > 1:
                arr = arr[:, :1].copy()
            cols.append(np.asfortranarray(arr))
        if cols:
            return np.asfortranarray(np.hstack(cols))
    return cur


def _entry12_align_Q_record_to_mat(py_q: Any, mat_q: Any) -> Any:
    """Compare lane: trajectory ``mdp.Q`` on hierarchical models (``O,P,X,s,u,…``)."""
    import copy

    import numpy as np

    if not isinstance(mat_q, dict):
        return _entry12_cast_leaf_for_compare(py_q, mat_q)
    if not isinstance(py_q, dict):
        _entry12_compare_lane_fail("_entry12_align_Q_record_to_mat", "py_q is not a dict")
    out = copy.deepcopy(py_q)
    for key in list(out.keys()):
        if key not in mat_q:
            del out[key]
    def _align_Q_PX_level(py_li: Any, mat_li: Any) -> Any:
        import numpy as np

        if isinstance(mat_li, list) and mat_li and isinstance(py_li, list) and py_li:
            if len(py_li) == len(mat_li) and isinstance(py_li[0], np.ndarray) and py_li[0].ndim == 2:
                return [
                    _entry12_cast_leaf_for_compare(py_li[f], mat_li[f])
                    for f in range(len(mat_li))
                ]
            if len(py_li) > len(mat_li) and isinstance(py_li[0], np.ndarray) and py_li[0].ndim <= 2:
                ng = len(mat_li) // max(1, int(np.asarray(mat_li[0]).shape[1]) if mat_li else 1)
                ncol = int(np.asarray(mat_li[0]).shape[1]) if mat_li else 1
                if ng * ncol == len(py_li):
                    flat = [
                        _entry12_cast_leaf_for_compare(
                            py_li[_entry12_q_o_flat_index_t_shiftdim(t, g, ncol=ncol)],
                            mat_li[_entry12_q_o_flat_index_t_shiftdim(t, g, ncol=ncol)],
                        )
                        for g in range(ng)
                        for t in range(ncol)
                    ]
                    return flat
        return _entry12_Q_O_level_to_mat_cells(py_li, mat_li, kind="O")

    if "O" in mat_q and "O" in out:
        py_o = out["O"]
        mat_o = mat_q["O"]
        if isinstance(mat_o, list) and mat_o:
            if isinstance(py_o, list) and py_o and isinstance(py_o[0], (list, np.ndarray)) and not (
                len(py_o) == len(mat_o) and not isinstance(py_o[0], np.ndarray)
            ):
                # ``Q.O{L}`` list-of-levels (Python) vs flat cell row (MATLAB) when ``L==1``.
                if len(py_o) == 1 and len(mat_o) > 1:
                    inner = py_o[0]
                    if isinstance(inner, list) and _entry12_is_q_o_ng_t_rows(inner):
                        out["O"] = _entry12_align_q_o_ng_t_rows(inner, mat_o)
                    else:
                        out["O"] = _entry12_Q_O_level_to_mat_cells(py_o[0], mat_o)
                else:
                    out["O"] = [
                        _entry12_Q_O_level_to_mat_cells(
                            py_o[li] if li < len(py_o) else py_o[-1],
                            mat_o[li] if li < len(mat_o) else mat_o[-1],
                        )
                        for li in range(len(mat_o))
                    ]
            else:
                out["O"] = _entry12_Q_O_level_to_mat_cells(py_o, mat_o)
    for key in ("P", "X", "Y", "s", "u", "o", "j", "E"):
        if key not in mat_q or key not in out:
            continue
        py_levels = out[key] if isinstance(out[key], list) else [out[key]]
        mat_ref = mat_q[key]
        if isinstance(mat_ref, np.ndarray):
            if key == "E":
                flat = _entry12_flatten_Q_E_nested_for_compare(py_levels)
                ref_a = np.asarray(mat_ref, dtype=np.float64)
                if int(flat.size) != int(ref_a.size):
                    _entry12_compare_lane_fail(
                        "_entry12_align_Q_record_to_mat E",
                        f"flattened len {flat.size} != mat len {ref_a.size}",
                    )
                out[key] = _entry12_cast_leaf_for_compare(
                    flat.reshape(ref_a.shape, order="F"),
                    mat_ref,
                )
            else:
                out[key] = _entry12_cast_q_trajectory_ndarray_for_compare(
                    _entry12_unwrap_q_py_level_for_ndarray_compare(py_levels),
                    mat_ref,
                )
            continue
        if not isinstance(mat_ref, list):
            continue
        mat_levels = mat_ref
        if key in ("P", "X") and len(py_levels) == 1 and len(mat_levels) > 1:
            out[key] = _align_Q_PX_level(py_levels[0], mat_levels)
            continue
        if len(py_levels) == 1 and len(mat_levels) > 1:
            if key in ("Y", "j", "i", "o") and _entry12_is_q_ot_mat_outcome_rows(mat_levels):
                out[key] = _entry12_align_q_o_ng_t_rows(py_levels[0], mat_levels)
                continue
            if not isinstance(mat_levels[0], list) or key in ("Y", "j", "i", "o"):
                out[key] = _entry12_Q_O_level_to_mat_cells(py_levels[0], mat_levels, kind=key)
                continue
        if len(py_levels) == len(mat_levels):
            out[key] = [
                _entry12_Q_O_level_to_mat_cells(
                    py_levels[li] if li < len(py_levels) else py_levels[-1],
                    mat_levels[li],
                    kind=key,
                )
                if isinstance(mat_levels[li], list)
                and len(mat_levels[li]) > 1
                and not isinstance(py_levels[li], list)
                else (
                    _entry12_flatten_nested_list_to_mat(py_levels[li], mat_levels[li])
                    if isinstance(mat_levels[li], list) and isinstance(py_levels[li], list)
                    else _entry12_cast_leaf_for_compare(py_levels[li], mat_levels[li])
                )
                for li in range(len(mat_levels))
            ]
    if "F" in mat_q:
        out["F"] = _entry12_cast_leaf_for_compare(out.get("F", mat_q["F"]), mat_q["F"])
    return out


_ENTRY12_MATLAB_ONLY_MDP_SNAP_KEYS: frozenset[str] = frozenset(
    {"GA", "GB", "GU", "GD", "GE", "GV", "ID", "chi"}
)


def _entry12_prune_mat_mdp_snap_keys_for_py(mat_node: Any, py_node: Any) -> Any:
    """Drop MATLAB-only generative-process snap keys on ``mat`` when absent on paired ``py``."""
    import copy

    if not isinstance(mat_node, dict) or not isinstance(py_node, dict):
        return mat_node
    out = copy.deepcopy(mat_node)
    for key in list(out.keys()):
        if key not in py_node and key in _ENTRY12_MATLAB_ONLY_MDP_SNAP_KEYS:
            del out[key]
        elif key in py_node and isinstance(out[key], dict) and isinstance(py_node[key], dict):
            out[key] = _entry12_prune_mat_mdp_snap_keys_for_py(out[key], py_node[key])
    return out


def _entry12_align_12D_mdp_branch(
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
    *,
    skip_template_keys: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Align hierarchical **12D** ``MDP`` containers (``U``, ``id``, inner ``MDP``, scalar cells)."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    skip = skip_template_keys or frozenset()
    out = copy.deepcopy(py_mdp)
    for key in list(out.keys()):
        if key not in mat_mdp:
            del out[key]
    for key in mat_mdp:
        if key not in out and key not in skip:
            if key in _ENTRY12_MATLAB_ONLY_MDP_SNAP_KEYS:
                # MATLAB dump fork may list ``GP``/``ID``/``chi`` on saved ``MDP``; Python
                # keeps likelihood ``A``/``B`` on the struct and workspace bundles elsewhere.
                continue
            _entry12_compare_lane_fail(
                "_entry12_align_12D_mdp_branch",
                f"missing Python key {key!r}",
            )
    if "U" in mat_mdp and "U" in out:
        out["U"] = _entry12_cast_leaf_for_compare(out["U"], mat_mdp["U"])
    if "u" in mat_mdp and "u" in out:
        out["u"] = _entry12_cast_leaf_for_compare(out["u"], mat_mdp["u"])
    if "id" in mat_mdp and "id" in out and isinstance(mat_mdp["id"], dict):
        sub = copy.deepcopy(out["id"])
        _spm_MDP_checkX_transform_align(sub, mat_mdp["id"])
        out["id"] = sub
    if "Q" in mat_mdp and "Q" in out and isinstance(mat_mdp["Q"], dict):
        out["Q"] = _entry12_align_Q_record_to_mat(out["Q"], mat_mdp["Q"])
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
        out["O"] = _entry12_flatten_O_ng_t_mat(out["O"], mat_mdp["O"])
    if "Y" in mat_mdp and "Y" in out and isinstance(mat_mdp["Y"], list) and isinstance(out["Y"], list):
        py_y, mat_y = out["Y"], mat_mdp["Y"]
        if (
            py_y
            and mat_y
            and isinstance(py_y[0], (list, tuple))
            and isinstance(mat_y[0], (list, tuple))
            and len(py_y) == len(mat_y)
        ):
            out["Y"] = [
                [
                    _entry12_cast_leaf_for_compare(
                        py_y[o][t] if t < len(py_y[o]) else py_y[o][-1],
                        mat_y[o][t] if t < len(mat_y[o]) else mat_y[o][-1],
                    )
                    for t in range(len(mat_y[o]))
                ]
                for o in range(len(mat_y))
            ]
        else:
            flat_y = _entry12_flatten_O_ng_t_mat(py_y, mat_y)
            if len(flat_y) != len(mat_y):
                _entry12_compare_lane_fail(
                    "_entry12_align_12D_mdp_branch Y",
                    f"flatten len {len(flat_y)} != mat len {len(mat_y)}",
                )
            out["Y"] = flat_y
    for key in ("i", "j"):
        if key in mat_mdp and key in out and isinstance(mat_mdp[key], list) and isinstance(out[key], list):
            out[key] = _entry12_flatten_pair_index_list(out[key], mat_mdp[key])
    if "T" in mat_mdp and "T" in out:
        out["T"] = _entry12_cast_leaf_for_compare(out["T"], mat_mdp["T"])
    if "Pa" in mat_mdp and "Pa" in out:
        out["Pa"] = _entry12_cast_leaf_for_compare(out["Pa"], mat_mdp["Pa"])
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
        t_idx = _entry12_snap_t_idx(mat_snap if "t" in mat_snap else py_snap)
        py_mdp = out["MDP"]
        mat_mdp = mat_snap["MDP"]
        out["MDP"] = _entry12_align_boundary_mdp_fgz(
            _entry12_align_12D_mdp_branch(py_mdp, mat_mdp),
            py_mdp,
            mat_mdp,
            t_idx=t_idx,
            trace_slot=_entry12_12D_trace_slot(t_idx),
        )
    _entry12_strip_inspection_only_snap_keys(out)
    _entry12_strip_nested_mdp_policy_traces(out)
    return out


def entry12_align_12D_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12D**: align lean boundary snapshots to MATLAB template."""
    import copy

    out = copy.deepcopy(py_ws)
    for key in ENTRY12_LEAN_BOUNDARY_KEYS:
        if key in out and key in mat_ws:
            out[key] = entry12_align_12D_snap_to_mat(out[key], mat_ws[key])
    return out


def _entry12_normalize_12E_O_layout(py_o: Any, mat_o: Any) -> tuple[Any, Any]:
    """
    MATLAB **12E** dumps ``O`` as a flat ``Ng`` cell row; Python keeps ``[[O_g,…]]`` per model.

    Normalize both to ``list[list[leaf]]`` (one parent row) before per-modality compare.
    """
    import copy

    if not isinstance(py_o, list) or not isinstance(mat_o, list):
        return py_o, mat_o
    py_use: Any = py_o
    mat_use: Any = mat_o
    if py_o and isinstance(py_o[0], list):
        py_use = py_o
    elif py_o:
        py_use = [py_o]
    if mat_o and not isinstance(mat_o[0], list):
        mat_use = [mat_o]
    elif mat_o:
        mat_use = mat_o
    return copy.deepcopy(py_use), copy.deepcopy(mat_use)


def _entry12_align_12E_O_at_t(py_o: Any, mat_o: Any) -> Any:
    """Align lean ``O{m,g}`` slice at one ``t`` (nested model × modality lists)."""
    import copy

    py_o, mat_o = _entry12_normalize_12E_O_layout(py_o, mat_o)
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
                _entry12_compare_lane_fail(
                    "_entry12_align_12E_O_at_t",
                    f"missing O leaf model={mi} modality={g_idx}",
                )
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
    _entry12_strip_inspection_only_snap_keys(out)
    return out


def entry12_align_12E_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12E**: align lean boundary snapshots to MATLAB template."""
    import copy

    out = copy.deepcopy(py_ws)
    for key in ENTRY12_LEAN_BOUNDARY_KEYS:
        if key in out and key in mat_ws:
            out[key] = entry12_align_12E_snap_to_mat(out[key], mat_ws[key])
    return out


def _entry12_strip_inspection_only_snap_keys(snap: dict[str, Any]) -> None:
    """Remove py/mat probe rollups before causal boundary value assert (compare lane)."""
    for key in ENTRY12_INSPECTION_ONLY_SNAP_KEYS:
        snap.pop(key, None)


def _entry12_snap_t_idx(snap: dict[str, Any]) -> int:
    """Lean boundary ``t`` label → 0-based column index (``12F.in`` uses ``t=0`` pre-loop)."""
    import numpy as np

    t_lab = int(np.asarray(snap.get("t", 1), dtype=np.float64).item())
    if t_lab <= 0:
        return 0
    return t_lab - 1


def _entry12_strip_nested_mdp_policy_traces(root: dict[str, Any]) -> None:
    """12F snap stores ``R``/``v``/``w`` at boundary root; drop duplicate nested ``MDP.MDP`` copies."""
    if not isinstance(root, dict):
        return
    if "t" in root or "Q" in root or "P" in root:
        parent = root.get("MDP")
    else:
        parent = root
    if not isinstance(parent, dict):
        return
    child_raw = parent.get("MDP")
    if isinstance(child_raw, list) and child_raw:
        child = child_raw[0]
    elif isinstance(child_raw, dict):
        child = child_raw
    else:
        return
    if isinstance(child, dict):
        for key in (
            "R",
            "U",
            "v",
            "w",
            "F",
            "GE",
            "GD",
            "entry12_Yfill",
            "entry12_VBX",
            "entry12_forwards",
            "entry12_generation",
        ):
            child.pop(key, None)


def _entry12_align_boundary_mdp_fgz(
    out: dict[str, Any],
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
    *,
    t_idx: int,
    trace_slot: int | None = None,
) -> dict[str, Any]:
    """Slice Python length-``T`` ``F``/``G``/``Z`` to MATLAB per-boundary scalars/vectors."""
    import numpy as np

    slot = t_idx if trace_slot is None else trace_slot
    if "G" in mat_mdp and "G" in out:
        py_g = py_mdp.get("G")
        mat_g = mat_mdp["G"]
        if isinstance(mat_g, list) and isinstance(py_g, list):
            n = len(mat_g)
            out["G"] = [
                _entry12_cast_leaf_for_compare(
                    np.asarray(py_g[i] if i < len(py_g) else py_g[-1], dtype=np.float64).ravel(),
                    mat_g[i],
                )
                for i in range(n)
            ]
        elif not isinstance(mat_g, list):
            if isinstance(py_g, list) and 0 <= slot < len(py_g) and py_g[slot] is not None:
                g_slice = np.asarray(py_g[slot], dtype=np.float64).ravel()
                out["G"] = _entry12_cast_leaf_for_compare(g_slice, mat_g)
            elif py_g is not None:
                out["G"] = _entry12_cast_leaf_for_compare(
                    np.asarray(py_g, dtype=np.float64).ravel(), mat_g
                )
    if "F" in mat_mdp and "F" in out:
        pf = np.asarray(py_mdp.get("F"), dtype=np.float64).ravel()
        mf = np.asarray(mat_mdp["F"], dtype=np.float64).ravel()
        if pf.size == 1 and mf.size == 1:
            out["F"] = _entry12_cast_leaf_for_compare(float(pf[0]), float(mf[0]))
        elif mf.ndim == 0 and pf.size > slot:
            out["F"] = _entry12_cast_leaf_for_compare(float(pf[slot]), mat_mdp["F"])
        elif mf.size == pf.size:
            out["F"] = _entry12_cast_leaf_for_compare(py_mdp["F"], mat_mdp["F"])
    if "Z" in mat_mdp and "Z" in out:
        pz = np.asarray(py_mdp.get("Z"), dtype=np.float64).ravel()
        mz = np.asarray(mat_mdp["Z"], dtype=np.float64).ravel()
        if mz.size == 0:
            pass
        elif mz.size == pz.size:
            out["Z"] = _entry12_cast_leaf_for_compare(py_mdp["Z"], mat_mdp["Z"])
        elif mz.size == 1:
            idx = min(max(slot, 0), pz.size - 1) if pz.size else 0
            out["Z"] = _entry12_cast_leaf_for_compare(float(pz[idx]), float(mz[0]))
        elif pz.size > mz.size:
            end = min(pz.size, max(slot, 0) + 1)
            start = max(0, end - mz.size)
            out["Z"] = _entry12_cast_leaf_for_compare(pz[start:end], mz)
        else:
            out["Z"] = _entry12_cast_leaf_for_compare(py_mdp["Z"], mat_mdp["Z"])
    return out


def _entry12_12D_trace_slot(t_idx: int) -> int:
    """**12D** early within-``t`` snap: MATLAB ``F``/``G``/``Z`` reflect prior completed column."""
    return max(0, t_idx - 1)


def _entry12_align_12F_mdp_branch(
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
    *,
    t_idx: int,
) -> dict[str, Any]:
    """``MDP`` subtree for **12F** when MATLAB saves per-``t`` ``G`` / scalar ``F`` at boundaries."""
    out = _entry12_align_12D_mdp_branch(
        py_mdp,
        mat_mdp,
        skip_template_keys=frozenset({"R", "U", "v", "w", "F"}),
    )
    _entry12_strip_nested_mdp_policy_traces(out)
    return _entry12_align_boundary_mdp_fgz(out, py_mdp, mat_mdp, t_idx=t_idx, trace_slot=t_idx)


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
        if arr.ndim == 1 and arr.size >= marr.size:
            return _entry12_cast_leaf_for_compare(arr.ravel()[: marr.size], mat_val)
        if arr.ndim == 1 and arr.size > t_idx:
            return _entry12_cast_leaf_for_compare(arr[t_idx], mat_val)
    if marr.ndim == 2 and arr.ndim == 2:
        if arr.shape == marr.shape:
            return _entry12_cast_leaf_for_compare(arr, mat_val)
        if arr.shape[0] == marr.shape[0] and arr.shape[1] >= marr.shape[1]:
            return _entry12_cast_leaf_for_compare(arr[:, : marr.shape[1]], mat_val)
    return _entry12_cast_leaf_for_compare(py_val, mat_val)


def entry12_align_12F_snap_to_mat(
    py_snap: dict[str, Any],
    mat_snap: dict[str, Any],
) -> dict[str, Any]:
    """Align one **12F** lean snapshot (``t``, ``Q``, ``P``, ``MDP``, optional ``R``/``v``/``w``)."""
    import copy

    import numpy as np

    mat_ref = copy.deepcopy(mat_snap)
    _entry12_strip_nested_mdp_policy_traces(mat_ref)
    out = copy.deepcopy(py_snap)
    _entry12_strip_nested_mdp_policy_traces(out)
    t_idx = _entry12_snap_t_idx(mat_ref if "t" in mat_ref else py_snap)
    if "t" in out and "t" in mat_ref:
        out["t"] = _entry12_cast_leaf_for_compare(out["t"], mat_ref["t"])
    for key in ("Q", "P"):
        if key in out and key in mat_ref:
            out[key] = _entry12_flatten_matlab_cell_like(out[key], mat_ref[key])
    if "MDP" in out and "MDP" in mat_ref and isinstance(out["MDP"], dict) and isinstance(mat_ref["MDP"], dict):
        out["MDP"] = _entry12_align_12F_mdp_branch(out["MDP"], mat_ref["MDP"], t_idx=t_idx)
    for key in ("R", "v", "w"):
        if key in out and key in mat_ref:
            out[key] = _entry12_align_12F_Rvw_at_t(out[key], mat_ref[key], t_idx=t_idx)
    _entry12_strip_inspection_only_snap_keys(out)
    return out


def entry12_align_12F_workspace_to_mat(
    py_ws: dict[str, Any],
    mat_ws: dict[str, Any],
) -> dict[str, Any]:
    """Validation 12 **12F**: align lean boundary snapshots to MATLAB template."""
    import copy

    out = copy.deepcopy(py_ws)
    for key in ENTRY12_LEAN_BOUNDARY_KEYS:
        if key in out and key in mat_ws:
            out[key] = entry12_align_12F_snap_to_mat(out[key], mat_ws[key])
    return out


def entry12_12F_mat_snap_for_value_assert(mat_snap: dict[str, Any]) -> dict[str, Any]:
    """MATLAB **12F** snapshot with nested ``MDP.MDP`` policy traces removed (compare lane)."""
    import copy

    out = copy.deepcopy(mat_snap)
    _entry12_strip_nested_mdp_policy_traces(out)
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
            if key == "O":
                out[key] = _entry12_align_12c_O_preloop(out[key], mat_ws[key])
            else:
                py_peeled = _entry12_peel_nm_one_model_shell(out[key], mat_ws[key])
                out[key] = _entry12_flatten_matlab_cell_like(py_peeled, mat_ws[key])
    _spm_MDP_checkX_transform_align(out, mat_ws)
    return out


def entry12_align_mdp_to_mat_workspace(
    py_mdp: dict[str, Any],
    mat_mdp: dict[str, Any],
) -> dict[str, Any]:
    """Align Python ``MDP`` / **12H** ``PDP`` to MATLAB workspace (compare lane only)."""
    import copy

    from python_src.toolbox.DEM.spm_MDP_checkX import _spm_MDP_checkX_transform_align

    out = copy.deepcopy(py_mdp)
    orig_inner_q = None
    if isinstance(py_mdp.get("MDP"), dict) and isinstance(py_mdp["MDP"].get("Q"), dict):
        orig_inner_q = copy.deepcopy(py_mdp["MDP"]["Q"])
    _entry12_align_pdp_assemble_shell(out, mat_mdp)
    # **12H** assembled ``PDP``: hierarchical shell; align nested ``MDP.G`` (checkX ``1×4`` row).
    if "L" in mat_mdp and isinstance(mat_mdp.get("MDP"), dict):
        py_inner = out.get("MDP")
        mat_inner = mat_mdp["MDP"]
        if isinstance(py_inner, dict) and isinstance(mat_inner, dict):
            mat_q = mat_inner.get("Q")
            if isinstance(orig_inner_q, dict) and isinstance(mat_q, dict):
                py_inner["Q"] = _entry12_align_Q_record_to_mat(orig_inner_q, mat_q)
            pg, mg = py_inner.get("G"), mat_inner.get("G")
            if isinstance(pg, list) and isinstance(mg, list) and mg:
                py_inner["G"] = [
                    _entry12_cast_leaf_for_compare(pg[i] if i < len(pg) else pg[-1], mg[i])
                    for i in range(len(mg))
                ]
        _entry12_strip_pdp_inspection_probes(out)
        return out
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


def _load_mat_via_engine_export_v7(path: Path) -> dict[str, Any]:
    """Load MAT v7.3 (or any Engine-readable ``.mat``) via round-trip ``save(...,'-v7')``."""
    import matlab.engine
    from scipy.io import loadmat

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root

    repo = demo1_repo_root()
    tmp = repo / "matlab_custom" / "_entry12_v73_export.mat"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        posix = str(path.resolve()).replace("\\", "/")
        tmp_posix = str(tmp.resolve()).replace("\\", "/")
        eng.eval(f"S = load('{posix}'); fn = fieldnames(S);", nargout=0)
        eng.eval(
            f"save('{tmp_posix}', fn{{:}}, '-struct', 'S', '-v7');",
            nargout=0,
        )
        raw = loadmat(str(tmp), simplify_cells=True)
        return {k: v for k, v in raw.items() if k not in _MATLAB_META_KEYS}
    finally:
        eng.quit()


def load_entry12_subentry_mat(path: Path | str) -> dict[str, Any]:
    """Load a MATLAB ``.mat`` file and return user variables (no ``__header__`` / ``__version__``).

    Nested MATLAB structs arrive as ``numpy`` structured arrays / objects depending on
    ``scipy`` version; callers performing oracle compares should normalize further as needed.

    Supports MAT **v7.3** boundary sidecars (``*_12F_in.mat``) and Engine round-trip when
    ``h5py`` is unavailable.
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
    except NotImplementedError:
        mat = _load_mat_via_engine_export_v7(p)

    out = {k: v for k, v in mat.items() if k not in _MATLAB_META_KEYS}
    in_sidecar = p.parent / f"{p.stem}_in.mat"
    if "in" not in out and in_sidecar.is_file():
        side = load_entry12_subentry_mat(in_sidecar)
        if "in" in side:
            out["in"] = side["in"]
    return out


def load_entry12_subentry_mat_from_env(code: str) -> dict[str, Any]:
    """Load using ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` and optional ``RGMS_ENTRY12_CAPTURE_OUT_DIR``."""
    tag = os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", "default").strip() or "default"
    out = os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    od: Path | None = Path(out) if out else None
    return load_entry12_subentry_mat(entry12_subentry_mat_path(tag, code, out_dir=od))


# Nested ``mdp.O`` / ``MDP.MDP.O``: post-``shiftdim`` script **3** dump uses ``O[t][g]`` (T×Ng);
# paired ``.mat`` loads ``cell(Ng,T)`` as ``O[g][t]`` (Ng×T). Canonical compare form: Ng outer, T inner.
_ENTRY12_O_TIME_OUTER_MAX_T = 16


def _entry12_O_nested_is_time_outer(n_outer: int, n_inner: int) -> bool:
    return n_inner > n_outer and n_outer > 0 and n_outer <= _ENTRY12_O_TIME_OUTER_MAX_T


def _entry12_transpose_O_tg_to_gt(O_tg: list[Any]) -> list[Any]:
    """``O[t][g]`` (post-``shiftdim``) → ``O[g][t]`` for paired compare with MATLAB ``.mat``."""
    if not O_tg or not isinstance(O_tg[0], (list, tuple)):
        return O_tg
    t_count = len(O_tg)
    ng = len(O_tg[0])
    out: list[list[Any]] = []
    for g in range(ng):
        row: list[Any] = []
        for t in range(t_count):
            src = O_tg[t]
            row.append(src[g] if g < len(src) else src[-1])
        out.append(row)
    return out


def _entry12_unflatten_ng_t_flat_row(flat: list[Any]) -> list[list[Any]] | None:
    """Rebuild ``Ng×T`` nested ``[o][t]`` from flat row (MATLAB ``(:)`` index ``o + t*Ng``)."""
    n = len(flat)
    if n < 2:
        return None
    for t_count in range(2, _ENTRY12_O_TIME_OUTER_MAX_T + 1):
        if n % t_count != 0:
            continue
        ng = n // t_count
        if ng > t_count:
            return [[flat[int(o) + int(t) * ng] for t in range(t_count)] for o in range(ng)]
    return None


def _entry12_canonicalize_Q_ot_grid_levels(val: Any) -> Any:
    """
    ``mdp.Q.{Y,j,i,o}{L}`` levels: script **3** flat ``Ng×T`` append row; ``.mat`` nested ``[o][t]``.
    Flat index ``o + t*Ng`` (MATLAB ``(:)`` on ``cell(Ng,T)``).
    """
    if not isinstance(val, list):
        return val
    # ``mat_nested_to_py`` may expose ``Q.*{L}`` as ``Ng`` outcome rows (not one list-of-levels).
    if _entry12_is_q_ot_mat_outcome_rows(val):
        return val
    if len(val) == 1 and _entry12_is_q_ot_mat_outcome_rows(val[0]):
        return val
    out: list[Any] = []
    for level in val:
        if isinstance(level, list) and level and isinstance(level[0], (list, tuple)):
            out.append(level)
        elif isinstance(level, list):
            nested = _entry12_unflatten_ng_t_flat_row(level)
            out.append(nested if nested is not None else level)
        else:
            out.append(level)
    return out


def _entry12_canonicalize_O_nested_block(val: Any) -> Any:
    """
    One nested ``O`` block: symmetric Ng×T ``O[g][t]`` before causal assert.

    Python VB after ``shiftdim`` stores ``O[t][g]``; MATLAB ``loadmat`` exposes ``cell(Ng,T)``
    as length-Ng list of length-T rows (or ``ndarray`` shape ``(Ng,T)``). Same cells as
    ``_entry12_q_o_flat_index_t_shiftdim`` pairing ``py[t][g]`` vs ``mat[g,t]``.
    """
    import numpy as np

    if val is None:
        return val
    if isinstance(val, np.ndarray) and val.dtype == object and val.ndim == 2:
        n0, n1 = int(val.shape[0]), int(val.shape[1])
        if _entry12_O_nested_is_time_outer(n0, n1):
            val = val.T
        elif _entry12_O_nested_is_time_outer(n1, n0):
            pass
        return [
            [val[g, t] for t in range(int(val.shape[1]))] for g in range(int(val.shape[0]))
        ]
    if not isinstance(val, list) or not val:
        return val
    if not isinstance(val[0], (list, tuple)):
        return val
    n_outer, n_inner = len(val), len(val[0])
    if _entry12_O_nested_is_time_outer(n_outer, n_inner):
        return _entry12_transpose_O_tg_to_gt(val)
    return val


def _entry12_canonicalize_ss_cell_block(val: Any) -> Any:
    """
    One ``ss.{D,E,ID,IE}`` block: script **3** pickle uses flat length-16 in **row-major**
    ``[i][j]`` order (``k = i*4 + j`` on ``4×4``). ``mat_nested_to_py`` may leave ``4×4`` as nested lists;
    flatten **row-major** on both sides so causal compare matches paired artifacts. Applied symmetrically.
    """
    import numpy as np

    if val is None:
        return val
    if isinstance(val, np.ndarray) and val.dtype == object:
        if val.ndim == 2:
            flat: list[Any] = []
            for i in range(val.shape[0]):
                for j in range(val.shape[1]):
                    flat.append(val[i, j])
            return flat
        flat = [val.flat[i] for i in range(val.size)]
        return flat[0] if len(flat) == 1 else flat
    if isinstance(val, list):
        if val and not isinstance(val[0], (list, tuple)):
            return val
        if val and isinstance(val[0], list):
            nrows = len(val)
            ncols = len(val[0]) if val[0] else 0
            flat = []
            for i in range(nrows):
                row = val[i]
                for j in range(ncols):
                    flat.append(row[j] if j < len(row) else row[-1])
            return flat
        if len(val) == 1:
            return _entry12_canonicalize_ss_cell_block(val[0])
    return val


def entry12_canonicalize_saved_structures_for_compare(obj: Any) -> Any:
    """Symmetric pre-assert canonicalization (py and mat) for saved-structure contract."""
    import numpy as np

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k == "ss" and isinstance(v, dict):
                ss_out = dict(v)
                for sk in _ENTRY12_SS_BLOCK_KEYS:
                    if sk in ss_out:
                        ss_out[sk] = _entry12_canonicalize_ss_cell_block(ss_out[sk])
                out[k] = ss_out
            elif k == "O":
                out[k] = _entry12_canonicalize_O_nested_block(v)
            elif k == "Q" and isinstance(v, dict):
                q_out: dict[str, Any] = {}
                for qk, qv in v.items():
                    if qk in ("Y", "j", "i", "o"):
                        q_out[qk] = _entry12_canonicalize_Q_ot_grid_levels(qv)
                    else:
                        q_out[qk] = entry12_canonicalize_saved_structures_for_compare(qv)
                out[k] = q_out
            else:
                out[k] = entry12_canonicalize_saved_structures_for_compare(v)
        return out
    if isinstance(obj, list):
        return [entry12_canonicalize_saved_structures_for_compare(x) for x in obj]
    if isinstance(obj, np.ndarray) and obj.dtype.names:
        return {
            str(n): entry12_canonicalize_saved_structures_for_compare(obj[n][()])
            for n in obj.dtype.names
        }
    return obj


def entry12_mat_snap_for_value_assert(code: str, mat_snap: dict[str, Any]) -> dict[str, Any]:
    """MATLAB snapshot prep for value assert (**12F** strips nested policy duplicates)."""
    if code == "12F":
        out = entry12_12F_mat_snap_for_value_assert(mat_snap)
    else:
        out = copy.deepcopy(mat_snap)
    if code == "12E" and isinstance(out.get("O"), list):
        o_field = out["O"]
        if o_field and not isinstance(o_field[0], list):
            out["O"] = [o_field]
    if code in ("12D", "12E", "12F"):
        _entry12_strip_inspection_only_snap_keys(out)
        _entry12_strip_nested_mdp_policy_traces(out)
    return out


# Keys on parent ``MDP`` excluded from causal value assert (wrong instant or wrong storage).
# ``F``/``G``/``Z`` are aligned per-boundary in ``_entry12_align_boundary_mdp_fgz`` before payload build.
_ENTRY12_CAUSAL_12D_MDP_DROP: tuple[str, ...] = ("A", "B", "O", "o")
_ENTRY12_CAUSAL_12F_MDP_DROP: tuple[str, ...] = ("A",)
# Nested generative-process copies (``MDP.MDP``) — not causal witnesses; see ``12DEF.md``.
_ENTRY12_CAUSAL_NESTED_MDP_DROP: tuple[str, ...] = ("Y", "j", "i")


def _entry12_mdp_drop_top_level_keys(
    md: Any,
    drop_keys: tuple[str, ...],
    *,
    nested_extra_drop: tuple[str, ...] = _ENTRY12_CAUSAL_NESTED_MDP_DROP,
) -> Any:
    """
    Drop keys on each model dict and on nested ``MDP.MDP`` children.

    Struct ``MDP.A`` / ``MDP.Y`` (parent or child) are not causal witnesses; workspace
    ``A{m,g}`` is asserted via ``A_peaks_*`` on **12F**; outcomes at ``t`` via **12E** ``O``.
    """
    import copy

    if isinstance(md, list):
        return [
            _entry12_mdp_drop_top_level_keys(x, drop_keys, nested_extra_drop=nested_extra_drop)
            for x in md
        ]
    if not isinstance(md, dict):
        return copy.deepcopy(md)
    out = copy.deepcopy(md)
    for key in drop_keys:
        out.pop(key, None)
    nested = out.get("MDP")
    child_drop = tuple(dict.fromkeys(drop_keys + nested_extra_drop))
    if isinstance(nested, list):
        out["MDP"] = [
            _entry12_mdp_drop_top_level_keys(x, child_drop, nested_extra_drop=())
            if isinstance(x, dict)
            else copy.deepcopy(x)
            for x in nested
        ]
    elif isinstance(nested, dict):
        out["MDP"] = _entry12_mdp_drop_top_level_keys(nested, child_drop, nested_extra_drop=())
    return out


def _entry12_causal_mdp_strip_nested_Q(md: Any) -> Any:
    """Drop all ``Q`` on parent and child (legacy); prefer ``_entry12_causal_mdp_strip_child_Q_only``."""
    import copy

    if isinstance(md, list):
        return [_entry12_causal_mdp_strip_nested_Q(x) for x in md]
    if not isinstance(md, dict):
        return copy.deepcopy(md)
    out = copy.deepcopy(md)
    out.pop("Q", None)
    nested = out.get("MDP")
    if isinstance(nested, list):
        out["MDP"] = [
            (copy.deepcopy(c) if isinstance(c, dict) else c)
            for c in nested
        ]
        for i, child in enumerate(out["MDP"]):
            if isinstance(child, dict):
                child.pop("Q", None)
                out["MDP"][i] = child
    elif isinstance(nested, dict):
        child = copy.deepcopy(nested)
        child.pop("Q", None)
        out["MDP"] = child
    return out


def _entry12_causal_mdp_strip_child_Q_only(md: Any) -> Any:
    """
    Keep parent ``mdp.Q`` (aligned in compare lane) for causal assert; drop child ``MDP.MDP.Q`` only.

    Child ``Q`` layout differs between script **3** and ``loadmat``; parent ``Q`` is the hierarchical
    update witness at **12D** / **12F** boundaries.
    """
    import copy

    if isinstance(md, list):
        return [_entry12_causal_mdp_strip_child_Q_only(x) for x in md]
    if not isinstance(md, dict):
        return copy.deepcopy(md)
    out = copy.deepcopy(md)
    nested = out.get("MDP")
    if isinstance(nested, list):
        out["MDP"] = [
            (copy.deepcopy(c) if isinstance(c, dict) else c)
            for c in nested
        ]
        for i, child in enumerate(out["MDP"]):
            if isinstance(child, dict):
                child.pop("Q", None)
                out["MDP"][i] = child
    elif isinstance(nested, dict):
        child = copy.deepcopy(nested)
        child.pop("Q", None)
        out["MDP"] = child
    return out


def _entry12_is_scalar_peak_index(item: Any) -> bool:
    """True when ``item`` is already a 1-based peak index (not a likelihood vector)."""
    import numpy as np

    if item is None:
        return True
    if isinstance(item, (bool, np.bool_)):
        return False
    if isinstance(item, (int, np.integer)):
        return True
    if isinstance(item, float) and np.isfinite(item) and item == round(item):
        return True
    arr = np.asarray(item)
    return arr.ndim == 0 and np.isfinite(arr) and float(arr) == round(float(arr))


def _entry12_normalize_a_peaks_list(val: Any) -> list[int | None]:
    """
    Per-modality workspace ``A{m,g}`` peaks (1-based), as stored by dump forks.

    ``entry12_a_peaks_at_m_`` / ``_entry12_a_peaks_for_model`` already save peak indices.
    Python dumps store that row as a list of ints; MATLAB often saves a numeric vector.
    Do not ``argmax`` scalar list elements (that maps every index ``k`` to ``1``).
    """
    import numpy as np

    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        if not val:
            return []
        if all(_entry12_is_scalar_peak_index(x) for x in val):
            return [None if x is None else int(x) for x in val]
        out: list[int | None] = []
        for item in val:
            if item is None:
                out.append(None)
            elif _entry12_is_scalar_peak_index(item):
                out.append(int(item))
            else:
                arr = np.asarray(item, dtype=np.float64).ravel(order="F")
                out.append(int(np.argmax(arr) + 1) if arr.size else None)
        return out
    arr = np.asarray(val)
    if arr.ndim == 0:
        return [int(arr.item())]
    flat = arr.ravel()
    if flat.size == 0:
        return []
    if np.issubdtype(arr.dtype, np.integer) or (
        flat.size > 1 and np.all(flat == np.round(flat))
    ):
        return [int(x) for x in flat.tolist()]
    arrf = np.asarray(val, dtype=np.float64).ravel(order="F")
    return [int(np.argmax(arrf) + 1)]


def _entry12_a_peaks_from_snap_at_phase(
    snap: dict[str, Any],
    phase: str,
    *,
    m_1b: int = 1,
) -> list[int | None] | None:
    """``A_peaks`` from ``entry12_phase_log`` on a lean **12E/12F** snap (parent model)."""
    entries = _entry12_phase_log_model_entries(snap.get("entry12_phase_log"), m_1b=m_1b)
    if not entries:
        return None
    parent_map = _entry12_phase_log_parent_phase_map(entries)
    ent = parent_map.get(phase)
    if ent is None:
        for item in reversed(entries):
            if str(item.get("phase") or "") == phase and "A_peaks" in item:
                ent = item
                break
    if not ent:
        return None
    return _entry12_normalize_a_peaks_list(ent.get("A_peaks"))


def entry12_causal_payload_12d(snap: dict[str, Any]) -> dict[str, Any]:
    """
    Causal value payload for **12D** (early within-``t``).

    ``MDP.O`` / ``MDP.o`` / ``MDP.A`` are excluded — outcomes at ``t`` are **12E** ``O``;
    workspace ``A{m,g}`` for ``spm_VBX`` is **12F** ``A_peaks_*``, not struct ``MDP.A``.
    Parent ``MDP.Q`` and trace-aligned ``MDP.F``/``G``/``Z`` are included (compare-aligned snap).
    """
    import copy

    out: dict[str, Any] = {}
    if "t" in snap:
        out["t"] = copy.deepcopy(snap["t"])
    if "Mrow" in snap:
        out["Mrow"] = copy.deepcopy(snap["Mrow"])
    if "MDP" in snap:
        out["MDP"] = _entry12_causal_mdp_strip_child_Q_only(
            _entry12_mdp_drop_top_level_keys(snap["MDP"], _ENTRY12_CAUSAL_12D_MDP_DROP)
        )
    return out


def entry12_causal_payload_12e(snap: dict[str, Any]) -> dict[str, Any]:
    """Causal value payload for **12E**: workspace ``O{m,g,t}`` at boundary ``t``."""
    import copy

    return {k: copy.deepcopy(snap[k]) for k in ("t", "O") if k in snap}


def entry12_causal_payload_12f(
    aligned_snap: dict[str, Any],
    raw_snap: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Causal value payload for **12F** (end of ``t``).

    Workspace ``Q``/``P``/``R``/``v``/``w`` plus filtered ``MDP`` (no parent ``MDP.A``; ``F``/``G``/``Z`` kept).
    Parent ``MDP.Q`` included; child ``MDP.MDP.Q`` stripped. Workspace ``A{m,g}`` at ``spm_VBX`` via
    ``A_peaks_pre_vbx`` / ``A_peaks_pre_forwards`` from ``entry12_phase_log`` on ``raw_snap``.
    """
    import copy

    out: dict[str, Any] = {}
    if "t" in aligned_snap:
        out["t"] = copy.deepcopy(aligned_snap["t"])
    for key in ("Q", "P", "R", "v", "w"):
        if key in aligned_snap:
            out[key] = copy.deepcopy(aligned_snap[key])
    if "MDP" in aligned_snap:
        out["MDP"] = _entry12_causal_mdp_strip_child_Q_only(
            _entry12_mdp_drop_top_level_keys(aligned_snap["MDP"], _ENTRY12_CAUSAL_12F_MDP_DROP)
        )
    missing: list[str] = []
    import numpy as np

    try:
        t_lab = int(np.asarray(aligned_snap.get("t", 0), dtype=np.float64).item())
    except (TypeError, ValueError):
        t_lab = 0
    if t_lab > 0:
        for phase, label in (
            ("pre_vbx", "A_peaks_pre_vbx"),
            ("pre_forwards", "A_peaks_pre_forwards"),
        ):
            peaks = _entry12_a_peaks_from_snap_at_phase(raw_snap, phase)
            if peaks is None:
                missing.append(label)
            else:
                out[label] = peaks
    return out, missing


def entry12_assert_causal_def_boundaries(
    py_by_code: dict[str, dict[str, Any]],
    mat_by_code: dict[str, dict[str, Any]],
    *,
    densify: Any | None = None,
    steps: tuple[tuple[str, str], ...] | None = None,
) -> list[str]:
    """
    Value-assert **12D → 12E → 12F** at each boundary in ``steps`` (default: ``ENTRY12_CAUSAL_BOUNDARY_STEPS``).

    Compares **causal payloads** (correct witnesses per band), not whole lean snaps.
    Evaluates all steps in one call. Returns failure messages (empty if all pass).
    Fix compute using the **first** list entry (causal order).
    """
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    _align_snap = {
        "12D": entry12_align_12D_snap_to_mat,
        "12E": entry12_align_12E_snap_to_mat,
        "12F": entry12_align_12F_snap_to_mat,
    }
    steps_use = ENTRY12_CAUSAL_BOUNDARY_STEPS if steps is None else steps
    failures: list[str] = []
    for code, sub in steps_use:
        label = f"{code}.{sub}"
        mat_ws = mat_by_code[code]
        py_ws = py_by_code[code]
        if sub not in py_ws or sub not in mat_ws:
            failures.append(f"{label} (missing key)")
            continue
        raw_py = py_ws[sub]
        raw_mat = mat_ws[sub]
        try:
            py_cmp = _align_snap[code](raw_py, raw_mat)
        except Entry12CompareLaneError as exc:
            failures.append(f"{label}: compare-lane {exc}")
            continue
        mat_cmp = entry12_mat_snap_for_value_assert(code, raw_mat)
        if densify is not None:
            py_cmp = densify(py_cmp)
            mat_cmp = densify(mat_cmp)
        py_cmp = entry12_canonicalize_saved_structures_for_compare(py_cmp)
        mat_cmp = entry12_canonicalize_saved_structures_for_compare(mat_cmp)
        if isinstance(py_cmp.get("MDP"), dict) and isinstance(mat_cmp.get("MDP"), dict):
            mat_cmp["MDP"] = _entry12_prune_mat_mdp_snap_keys_for_py(mat_cmp["MDP"], py_cmp["MDP"])
        if code == "12D":
            py_payload = entry12_causal_payload_12d(py_cmp)
            mat_payload = entry12_causal_payload_12d(mat_cmp)
        elif code == "12E":
            py_payload = entry12_causal_payload_12e(py_cmp)
            mat_payload = entry12_causal_payload_12e(mat_cmp)
        else:
            py_payload, py_missing = entry12_causal_payload_12f(py_cmp, raw_py)
            mat_payload, mat_missing = entry12_causal_payload_12f(mat_cmp, raw_mat)
            miss = sorted(set(py_missing) | set(mat_missing))
            if miss:
                failures.append(
                    f"{label}: missing {', '.join(miss)} on entry12_phase_log (rerun 1b→3)"
                )
                continue
        try:
            _assert_nested_rdp_equal(py_payload, mat_payload, label)
        except (AssertionError, TypeError, ValueError, Entry12CompareLaneError) as exc:
            failures.append(f"{label}: {exc}")
    return failures


# --- Accumulated inspection blocks (called only from Validation 12 / script 4) ---
# Add new Entry 12 debug sections here — not in new ``matlab_custom/_diag_*`` scripts.

_ENTRY12_QO_AB_FLAT_INDICES: tuple[int, ...] = (0, 1, 2, 3)  # (0,0), (0,1), (1,0), (1,1) at T=2
_ENTRY12_QO_AB_SITES: tuple[tuple[int, int], ...] = ((1, 0), (0, 1))  # (g zero-based, t_idx)


def _entry12_qo_one_hot_peak(col: Any) -> int | None:
    import numpy as np

    a = np.asarray(col, dtype=np.float64).reshape(-1)
    if a.size == 0:
        return None
    return int(np.argmax(a) + 1)


def entry12_print_qo_ab_diagnostics(
    py_by_code: dict[str, dict[str, Any]],
    mat_by_code: dict[str, dict[str, Any]],
    *,
    stream: Any = None,
) -> None:
    """
    Inspection block: nested-child ``Q.O`` 2×2 table + per-site replay on **12F.out_t1**.

    Invoked from **Validation 12** (script **4**) when the causal gate fails on a ``Q.O`` path.
    New Entry 12 inspections belong in this module and are wired from script **4** only.
    """
    import numpy as np

    from python_src.toolbox.DEM import spm_parents as spm_parents_mod
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
        _unwrap_gp_elem,
        _vb_gp_A_outcome_column,
    )

    def _out(msg: str = "") -> None:
        print(msg, file=stream)

    py_snap = py_by_code.get("12F", {}).get("out_t1")
    mat_snap = mat_by_code.get("12F", {}).get("out_t1")
    if not isinstance(py_snap, dict) or not isinstance(mat_snap, dict):
        _out("\n[XXX 12 inspection][qo-ab] skip: missing 12F.out_t1 lean snap")
        return

    def _parent_mdp(snap: dict[str, Any]) -> dict[str, Any]:
        mdp = snap.get("MDP")
        if isinstance(mdp, dict):
            return mdp
        if isinstance(mdp, list) and mdp and isinstance(mdp[0], dict):
            return mdp[0]
        raise TypeError(f"unexpected MDP container: {type(mdp).__name__}")

    def _nested_child(parent: dict[str, Any]) -> dict[str, Any]:
        ch = parent.get("MDP")
        if isinstance(ch, dict):
            return ch
        if isinstance(ch, list) and ch and isinstance(ch[0], dict):
            return ch[0]
        raise TypeError(f"unexpected nested MDP: {type(ch).__name__}")

    def _flat_cells(child: dict[str, Any]) -> tuple[list[Any], int, int]:
        qo = child.get("Q", {}).get("O") if isinstance(child.get("Q"), dict) else None
        if not isinstance(qo, list) or not qo:
            return [], 111, 2
        ng = len(child.get("A", [])) if isinstance(child.get("A"), list) else 111
        t_child = int(np.asarray(child.get("T", 2)).reshape(-1)[0])
        n_block = ng * t_child
        L = int(np.asarray(child.get("L", 1)).reshape(-1)[0])
        if len(qo) == 1 and isinstance(qo[0], list):
            level: Any = qo[0]
        elif len(qo) >= n_block and len(qo) != L:
            level = qo
        elif len(qo) >= L:
            level = qo[L - 1]
        else:
            level = qo
        if isinstance(level, list) and len(level) >= n_block:
            return list(level[:n_block]), ng, t_child
        return [], ng, t_child

    _out(
        "\n[XXX 12 inspection][qo-ab] --- nested child Q.O on 12F.out_t1 (first-red context) ---\n"
        "[XXX 12 inspection][qo-ab] Living compare path: 12F.out_t1.MDP.MDP.Q.O[k] "
        "(post-shiftdim flat k = t + g*T; e.g. g=1,t=0 → k=2 when T=2).\n"
        "[XXX 12 inspection][qo-ab] Replay uses exported snap s/id (may differ from state at "
        "OPTIONS.O if belief updated s later in the same t)."
    )

    side_reports: dict[str, dict[int, dict[str, Any]]] = {}
    for side, snap in (("py", py_snap), ("mat", mat_snap)):
        try:
            child = _nested_child(_parent_mdp(snap))
        except TypeError as exc:
            _out(f"[XXX 12 inspection][qo-ab] {side}: {exc}")
            continue
        cells, ng, t_child = _flat_cells(child)
        if not cells:
            _out(f"[XXX 12 inspection][qo-ab] {side}: could not read Q.O flat block")
            continue
        _out(f"[XXX 12 inspection][qo-ab] {side}: Ng={ng} T={t_child} len={len(cells)}")
        for fi in _ENTRY12_QO_AB_FLAT_INDICES:
            if fi < len(cells):
                _out(f"  flat[{fi}] Q.O peak={_entry12_qo_one_hot_peak(cells[fi])}")
        reps: dict[int, dict[str, Any]] = {}
        for g_zero, t_idx in _ENTRY12_QO_AB_SITES:
            g_1based = g_zero + 1
            flat_i = _entry12_q_o_flat_index_t_shiftdim(t_idx, g_zero, ncol=t_child)
            s = np.asarray(child.get("s"), dtype=np.float64)
            o = np.asarray(child.get("o"), dtype=np.float64)
            n = np.asarray(child.get("n"), dtype=np.float64)
            cid = child.get("id", {})
            s_col = s[:, t_idx] if s.ndim == 2 and s.shape[1] > t_idx else s.ravel()
            j_p, i_ch = spm_parents_mod.spm_parents(cid, g_1based, s_col)
            j_arr = np.atleast_1d(np.asarray(j_p, dtype=float)).ravel()
            i_arr = np.atleast_1d(np.asarray(i_ch, dtype=float)).ravel()
            ind_parts: list[int] = []
            s_vals: list[float] = []
            for jx in j_arr:
                jxi = int(round(float(jx)))
                if jxi < 1 or s.ndim < 2:
                    continue
                s_vals.append(float(s[jxi - 1, t_idx]))
                ind_parts.append(int(round(float(s[jxi - 1, t_idx]))) - 1)
            o_idx = int(round(float(i_arr[0]))) - 1 if len(i_arr) else g_zero
            gp_peak, gp_err = None, ""
            try:
                src = child.get("GA") or child.get("A")
                ag = np.asarray(_unwrap_gp_elem(src[g_zero]), dtype=np.float64)
                gp_peak = _entry12_qo_one_hot_peak(
                    _vb_gp_A_outcome_column(ag, ind_parts)
                )
            except Exception as exc:
                gp_err = str(exc)
            q_peak = _entry12_qo_one_hot_peak(cells[flat_i]) if flat_i < len(cells) else None
            reps[flat_i] = {
                "j": j_arr.tolist(),
                "i_codomain": i_arr.tolist(),
                "s_jt": s_vals,
                "ind_0based": ind_parts,
                "Q_O_peak": q_peak,
                "GP_col_peak": gp_peak,
                "o_o_t": float(o[o_idx, t_idx]) if o.ndim == 2 and 0 <= o_idx < o.shape[0] else None,
                "gp_err": gp_err,
            }
            _out(
                f"  site g={g_zero} t={t_idx} flat={flat_i}: "
                f"j={reps[flat_i]['j']} i={reps[flat_i]['i_codomain']} "
                f"s(j,t)={reps[flat_i]['s_jt']} ind0={reps[flat_i]['ind_0based']} "
                f"o(o,t)={reps[flat_i]['o_o_t']} Q.O={q_peak} GP.A peak={gp_peak} {gp_err}"
            )
        side_reports[side] = reps

    if "py" not in side_reports or "mat" not in side_reports:
        return
    _out("\n[XXX 12 inspection][qo-ab] cross-side (flat 1 and 111):")
    for fi in (1, 111):
        p, m = side_reports["py"].get(fi, {}), side_reports["mat"].get(fi, {})
        _out(f"  flat[{fi}]:")
        for k in ("j", "i_codomain", "s_jt", "ind_0based", "Q_O_peak", "GP_col_peak", "o_o_t"):
            pv, mv = p.get(k), m.get(k)
            _out(f"    {k}: py={pv} mat={mv}" + (" ***" if pv != mv else ""))


_ENTRY12_Y_AB_FIRST_RED_FLAT = 1  # compare path MDP.MDP.Y[1] (0-based flat; t*Ng+g at site o=2,t=1)
_ENTRY12_Y_AB_SITES: tuple[tuple[int, int], ...] = (
    (1, 0),
    (0, 0),
    (1, 1),
)  # (outcome o zero-based, t_idx) — include (1,1) for O{2,2} context at first-red site


def _entry12_y_ab_y_flat_index(t_idx: int, o_zero: int, *, ng: int) -> int:
    """``_entry12_flatten_O_ng_t_mat`` order (loop ``t`` then ``o``): ``k = t*Ng + o``."""
    return int(t_idx) * int(ng) + int(o_zero)


def _entry12_y_ab_ji_flat_index(o_zero: int, t_idx: int, *, t_child: int) -> int:
    """``_entry12_flatten_pair_index_list`` for nested ``j{o,t}`` / ``i{o,t}``: ``2*o+t`` when ``T=2``."""
    return int(o_zero) * int(t_child) + int(t_idx)


def _entry12_y_ab_peak(col: Any) -> tuple[int | None, float | None]:
    import numpy as np

    a = np.asarray(col, dtype=np.float64).reshape(-1)
    if a.size == 0:
        return None, None
    return int(np.argmax(a) + 1), float(np.max(a))


def _entry12_y_ab_qrow_from_X(child: dict[str, Any], t_idx: int) -> list[Any] | None:
    """``Q(m,:,t)`` replay from exported ``X{f}(:,t)`` (post ``X <- Q`` reorganise)."""
    import numpy as np

    X = child.get("X")
    if not isinstance(X, list) or not X:
        return None
    qrow: list[Any] = []
    for xf in X:
        a = np.asarray(xf, dtype=np.float64)
        if a.ndim == 1:
            qrow.append(a.reshape(-1, 1))
        else:
            qrow.append(a[:, t_idx : t_idx + 1].copy())
    return qrow


def _entry12_y_ab_read_Y_cell(
    child: dict[str, Any],
    *,
    o_zero: int,
    t_idx: int,
    ng: int,
) -> Any:
    """Read live ``Y{o,t}`` (outcome row ``o``, time ``t``) from nested py grid or flat cell row."""
    Y = child.get("Y")
    if not isinstance(Y, list) or not Y:
        return None
    if Y and isinstance(Y[0], list):
        row = Y[o_zero] if o_zero < len(Y) else []
        if not isinstance(row, list) or t_idx >= len(row):
            return None
        return row[t_idx]
    flat_i = _entry12_y_ab_y_flat_index(t_idx, o_zero, ng=ng)
    if flat_i < len(Y):
        return Y[flat_i]
    return None


def _entry12_y_ab_read_ji_cell(
    child: dict[str, Any],
    key: str,
    *,
    o_zero: int,
    t_idx: int,
    t_child: int,
) -> Any:
    """Read stored ``j{o,t}`` / ``i{o,t}`` (likelihood index ``o`` = MATLAB ``g`` at fill)."""
    field = child.get(key)
    if not isinstance(field, list) or not field:
        return None
    if field and isinstance(field[0], list):
        row = field[o_zero] if o_zero < len(field) else []
        if not isinstance(row, list) or t_idx >= len(row):
            return None
        return row[t_idx]
    flat_i = _entry12_y_ab_ji_flat_index(o_zero, t_idx, t_child=t_child)
    if flat_i < len(field):
        return field[flat_i]
    return None


def _entry12_y_ab_unwrap_id_a(val: Any) -> Any:
    if isinstance(val, (list, tuple)) and len(val) == 1:
        return val[0]
    return val


def _entry12_y_ab_spm_parents_branch(cid: dict[str, Any]) -> str:
    if "ff" in cid:
        if "fg" in cid:
            return "state-dependent: id.fg"
        return "state-dependent: id.A"
    return "state-independent: j=id.A{g}, i=g"


def _entry12_y_ab_likelihood_writers(
    child: dict[str, Any],
    *,
    o_target_1b: int,
    t_idx: int,
) -> list[tuple[int, int | None]]:
    """Likelihood indices ``g`` (1-based) with ``spm_parents`` codomain ``i`` containing ``o_target``."""
    import numpy as np

    from python_src.toolbox.DEM import spm_parents as spm_parents_mod

    cid = child.get("id", {})
    if not isinstance(cid, dict):
        return []
    ng = len(child.get("A", [])) if isinstance(child.get("A"), list) else 0
    qrow = _entry12_y_ab_qrow_from_X(child, t_idx)
    if qrow is None:
        return []
    writers: list[tuple[int, int | None]] = []
    for g_1b in range(1, ng + 1):
        _j, i_ch = spm_parents_mod.spm_parents(cid, g_1b, qrow)
        i_flat = np.atleast_1d(np.asarray(i_ch, dtype=np.int64).ravel()).astype(int).tolist()
        if o_target_1b not in i_flat:
            continue
        pred_peak: int | None = None
        try:
            from python_src.spm_dot import spm_dot

            j_arr = np.atleast_1d(np.asarray(_j, dtype=np.int64).ravel())
            q_list = [qrow[int(jj) - 1] for jj in j_arr.tolist() if int(jj) > 0]
            Ag = child.get("A", [None] * ng)[g_1b - 1]
            if Ag is not None and q_list:
                pred = np.asarray(spm_dot(np.asarray(Ag, dtype=np.float64), q_list), dtype=np.float64).ravel()
                if pred.size:
                    pred_peak = int(np.argmax(pred) + 1)
        except Exception:
            pred_peak = None
        writers.append((g_1b, pred_peak))
    return writers


def entry12_print_y_ab_diagnostics(
    py_by_code: dict[str, dict[str, Any]],
    mat_by_code: dict[str, dict[str, Any]],
    *,
    stream: Any = None,
) -> None:
    """
    Inspection block: nested-child live ``mdp.Y{g,t}`` on **12F.out_t1** (first-red context).

    Invoked from **Validation 12** (script **4**) when the causal gate fails on ``MDP.MDP.Y``.
    """
    import numpy as np

    from python_src.spm_dot import spm_dot
    from python_src.toolbox.DEM import spm_parents as spm_parents_mod

    def _out(msg: str = "") -> None:
        print(msg, file=stream)

    py_snap = py_by_code.get("12F", {}).get("out_t1")
    mat_snap = mat_by_code.get("12F", {}).get("out_t1")
    if not isinstance(py_snap, dict) or not isinstance(mat_snap, dict):
        _out("\n[XXX 12 inspection][y-ab] skip: missing 12F.out_t1 lean snap")
        return

    def _parent_mdp(snap: dict[str, Any]) -> dict[str, Any]:
        mdp = snap.get("MDP")
        if isinstance(mdp, dict):
            return mdp
        if isinstance(mdp, list) and mdp and isinstance(mdp[0], dict):
            return mdp[0]
        raise TypeError(f"unexpected MDP container: {type(mdp).__name__}")

    def _nested_child(parent: dict[str, Any]) -> dict[str, Any]:
        ch = parent.get("MDP")
        if isinstance(ch, dict):
            return ch
        if isinstance(ch, list) and ch and isinstance(ch[0], dict):
            return ch[0]
        raise TypeError(f"unexpected nested MDP: {type(ch).__name__}")

    _out(
        "\n[XXX 12 inspection][y-ab] --- nested child mdp.Y on 12F.out_t1 (first-red context) ---\n"
        "[XXX 12 inspection][y-ab] Living compare path: 12F.out_t1.MDP.MDP.Y[k] "
        "(flatten ``_entry12_flatten_O_ng_t_mat``: k = t*Ng + o; first red k=1 → outcome o=2, t=1).\n"
        "[XXX 12 inspection][y-ab] Stored j/i use ``_entry12_flatten_pair_index_list`` "
        "(k_ji = o*T + t on flat row length Ng*T). Replay: spm_parents(id,g,Q(m,:,t)) from X(:,t); "
        "spm_dot(A{g},Q(m,j,t)) at likelihood g (not outcome o)."
    )

    side_reports: dict[str, dict[int, dict[str, Any]]] = {}
    for side, snap in (("py", py_snap), ("mat", mat_snap)):
        try:
            child = _nested_child(_parent_mdp(snap))
        except TypeError as exc:
            _out(f"[XXX 12 inspection][y-ab] {side}: {exc}")
            continue
        ng = len(child.get("A", [])) if isinstance(child.get("A"), list) else 0
        t_child = int(np.asarray(child.get("T", 2)).reshape(-1)[0])
        if ng <= 0:
            _out(f"[XXX 12 inspection][y-ab] {side}: could not read Ng from child.A")
            continue
        _out(f"[XXX 12 inspection][y-ab] {side}: Ng={ng} T={t_child}")
        cid = child.get("id", {})
        if isinstance(cid, dict):
            id_a_g2 = (
                _entry12_y_ab_unwrap_id_a(cid.get("A", [None, None])[1])
                if isinstance(cid.get("A"), list) and len(cid.get("A", [])) > 1
                else None
            )
            _out(
                f"[XXX 12 inspection][y-ab] {side}: spm_parents branch: "
                f"{_entry12_y_ab_spm_parents_branch(cid)}; "
                f"id ff={'ff' in cid} fg={'fg' in cid} gg={'gg' in cid}; "
                f"id.A{{g=2}}={id_a_g2}"
            )
        reps: dict[int, dict[str, Any]] = {}
        for o_zero, t_idx in _ENTRY12_Y_AB_SITES:
            o_1b = o_zero + 1
            flat_y = _entry12_y_ab_y_flat_index(t_idx, o_zero, ng=ng)
            flat_ji = _entry12_y_ab_ji_flat_index(o_zero, t_idx, t_child=t_child)
            y_leaf = _entry12_y_ab_read_Y_cell(child, o_zero=o_zero, t_idx=t_idx, ng=ng)
            y_peak, y_max = _entry12_y_ab_peak(y_leaf)
            j_store = _entry12_y_ab_read_ji_cell(
                child, "j", o_zero=o_zero, t_idx=t_idx, t_child=t_child
            )
            i_store = _entry12_y_ab_read_ji_cell(
                child, "i", o_zero=o_zero, t_idx=t_idx, t_child=t_child
            )
            qrow_x = _entry12_y_ab_qrow_from_X(child, t_idx)
            g_like = o_1b  # state-independent branch: likelihood g matches codomain o
            j_sp, i_sp = (None, None)
            if qrow_x is not None:
                j_sp, i_sp = spm_parents_mod.spm_parents(cid, g_like, qrow_x)
            pred_peak, pred_err = None, ""
            Ag = child.get("A", [None] * ng)[o_zero]
            ag_shape = tuple(np.asarray(Ag).shape) if Ag is not None else ()
            if qrow_x is not None and j_sp is not None and Ag is not None:
                try:
                    j_arr = np.atleast_1d(np.asarray(j_sp, dtype=np.int64).ravel())
                    q_list = [qrow_x[int(jj) - 1] for jj in j_arr.tolist() if int(jj) > 0]
                    if int(np.asarray(Ag).size) > 1 and q_list:
                        pred = np.asarray(
                            spm_dot(np.asarray(Ag, dtype=np.float64), q_list),
                            dtype=np.float64,
                        ).ravel()
                        pred_peak, _ = _entry12_y_ab_peak(pred)
                except Exception as exc:
                    pred_err = str(exc)
            i_codomain = int(
                np.round(float(np.atleast_1d(np.asarray(i_store if i_store is not None else i_sp).ravel())[0]))
            )
            writers = _entry12_y_ab_likelihood_writers(child, o_target_1b=o_1b, t_idx=t_idx)
            o_peak = None
            O_field = child.get("O")
            if isinstance(O_field, list) and O_field:
                if isinstance(O_field[0], list) and o_zero < len(O_field) and t_idx < len(O_field[o_zero]):
                    o_peak, _ = _entry12_y_ab_peak(O_field[o_zero][t_idx])
                else:
                    flat_o = _entry12_y_ab_y_flat_index(t_idx, o_zero, ng=ng)
                    if flat_o < len(O_field):
                        o_peak, _ = _entry12_y_ab_peak(O_field[flat_o])
            reps[flat_y] = {
                "O_peak": o_peak,
                "Y_peak": y_peak,
                "Y_max": y_max,
                "j_store": j_store,
                "i_store": i_store,
                "j_sp": np.atleast_1d(np.asarray(j_sp, dtype=float)).ravel().tolist() if j_sp is not None else None,
                "i_sp": np.atleast_1d(np.asarray(i_sp, dtype=float)).ravel().tolist() if i_sp is not None else None,
                "pred_peak": pred_peak,
                "pred_err": pred_err,
                "i_codomain": i_codomain,
                "A_shape": ag_shape,
                "writers": writers,
                "flat_ji": flat_ji,
            }
            _out(
                f"  site outcome o={o_1b} t={t_idx+1} flat_Y={flat_y} flat_ji={flat_ji}: "
                f"Y_peak={y_peak} j_store={j_store} i_store={i_store} "
                f"j(spm_parents,g={g_like})={reps[flat_y]['j_sp']} "
                f"A{{g}}_shape={ag_shape} pred_peak={pred_peak} writers={writers} {pred_err}"
            )
        if _ENTRY12_Y_AB_FIRST_RED_FLAT < ng * t_child:
            fr = reps.get(_ENTRY12_Y_AB_FIRST_RED_FLAT, {})
            _out(
                f"[XXX 12 inspection][y-ab] {side}: first-red flat[{_ENTRY12_Y_AB_FIRST_RED_FLAT}] "
                f"Y_peak={fr.get('Y_peak')} j_store={fr.get('j_store')} pred_peak={fr.get('pred_peak')}"
            )
        side_reports[side] = reps

    if "py" not in side_reports or "mat" not in side_reports:
        return
    _out(f"\n[XXX 12 inspection][y-ab] cross-side first-red flat[{_ENTRY12_Y_AB_FIRST_RED_FLAT}]:")
    p = side_reports["py"].get(_ENTRY12_Y_AB_FIRST_RED_FLAT, {})
    m = side_reports["mat"].get(_ENTRY12_Y_AB_FIRST_RED_FLAT, {})
    for k in (
        "Y_peak",
        "j_store",
        "j_sp",
        "pred_peak",
        "i_store",
        "A_shape",
        "writers",
    ):
        pv, mv = p.get(k), m.get(k)
        _out(f"  {k}: py={pv} mat={mv}" + (" ***" if pv != mv else ""))

    def _site_o_peak(reps_side: dict[int, dict[str, Any]], o1b: int, t1b: int) -> int | None:
        flat_y = _entry12_y_ab_y_flat_index(t1b - 1, o1b - 1, ng=ng)
        return reps_side.get(flat_y, {}).get("O_peak")

    py_rep = side_reports.get("py", {})
    mat_rep = side_reports.get("mat", {})
    _out(
        "[XXX 12 inspection][y-ab] O peaks (modality 2): "
        f"O{{2,1}} py={_site_o_peak(py_rep, 2, 1)} mat={_site_o_peak(mat_rep, 2, 1)}; "
        f"O{{2,2}} py={_site_o_peak(py_rep, 2, 2)} mat={_site_o_peak(mat_rep, 2, 2)}"
    )
    _out(
        "[XXX 12 inspection][y-ab] Note: nested child has no field `a` on either side — "
        "in-loop active learning (`.m` ~1403) is skipped; `OPTIONS.Y` uses workspace `A{m,g}` from init only."
    )
    _entry12_print_yfill_probe_block(py_snap, mat_snap, stream=stream)


def _entry12_yfill_site_from_child(
    child: dict[str, Any], g_1b: int, t_1b: int, o_1b: int
) -> dict[str, Any] | None:
    """Return one ``entry12_Yfill`` site struct for ``(g,t,o)`` if captured."""
    import numpy as np

    yfill = child.get("entry12_Yfill")
    if yfill is None:
        return None
    g_idx, t_idx = g_1b - 1, t_1b - 1
    sites = None
    try:
        if isinstance(yfill, list):
            ylen = len(yfill)
            ng_candidates: list[int] = []
            y_n = len(child.get("Y", []))
            if y_n > 0 and ylen % y_n == 0:
                ng_candidates.append(y_n)
            if ylen % 111 == 0:
                ng_candidates.append(111)
            sites = None
            for ng in ng_candidates:
                nt = ylen // ng
                if nt >= t_1b and ylen == ng * nt:
                    sites = yfill[t_idx * ng + g_idx]
                    break
            if sites is None:
                row = yfill[g_idx]
                sites = row[t_idx] if isinstance(row, list) else row
        elif isinstance(yfill, np.ndarray) and yfill.dtype == object:
            if yfill.ndim == 2:
                sites = yfill[g_idx, t_idx]
            elif yfill.ndim == 1 and len(child.get("Y", [])) > 0:
                ng = len(child["Y"])
                sites = yfill[t_idx * ng + g_idx]
    except (IndexError, TypeError):
        return None
    if sites is None:
        return None
    if type(sites).__name__ == "mat_struct":
        from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

        sites = mat_nested_to_py(sites)
    if isinstance(sites, dict):
        return sites if int(sites.get("o", -1)) == o_1b else None
    if isinstance(sites, list):
        for item in sites:
            if isinstance(item, dict) and int(item.get("o", -1)) == o_1b:
                return item
    return None


def _entry12_print_yfill_probe_block(
    py_snap: dict[str, Any],
    mat_snap: dict[str, Any],
    *,
    stream: Any = None,
) -> None:
    """Cross-side fill-time probes from ``entry12_Yfill`` / ``entry12_VBX`` on nested child."""

    def _out(msg: str = "") -> None:
        print(msg, file=stream)

    def _child_from_snap(snap: dict[str, Any]) -> dict[str, Any] | None:
        mdp = snap.get("MDP")
        if isinstance(mdp, dict):
            parent = mdp
        elif isinstance(mdp, list) and mdp and isinstance(mdp[0], dict):
            parent = mdp[0]
        else:
            return None
        ch = parent.get("MDP")
        if isinstance(ch, dict):
            return ch
        if isinstance(ch, list) and ch and isinstance(ch[0], dict):
            return ch[0]
        return None

    _out(
        "\n[XXX 12 inspection][y-ab] --- entry12_Yfill / entry12_VBX (OPTIONS.Y & post-spm_VBX capture) ---"
    )
    for side, snap in (("py", py_snap), ("mat", mat_snap)):
        ch = _child_from_snap(snap)
        if ch is None:
            _out(f"[XXX 12 inspection][y-ab] {side}: no nested child for fill probe")
            continue
        site = _entry12_yfill_site_from_child(ch, 2, 1, 2)
        if site is None:
            _out(f"[XXX 12 inspection][y-ab] {side}: no entry12_Yfill site g=2 t=1 o=2")
        else:
            _out(
                f"[XXX 12 inspection][y-ab] {side}: Yfill g=2 t=1 o=2: "
                f"A_ws_peak={site.get('A_ws_peak')} Q_ws_peak={site.get('Q_ws_peak')} "
                f"pred_peak={site.get('pred_peak')} Y_peak={site.get('Y_peak')} "
                f"A_export_peak={site.get('A_export_peak')} has_a={site.get('has_a')}"
            )
        vbx = ch.get("entry12_VBX")
        if isinstance(vbx, dict):
            qpk = vbx.get("Q_f_peak")
            opk = vbx.get("O_peaks")
            _out(
                f"[XXX 12 inspection][y-ab] {side}: VBX t={vbx.get('t')} "
                f"Q_f_peak={qpk} O_peaks={opk}"
            )
        else:
            _out(f"[XXX 12 inspection][y-ab] {side}: no entry12_VBX on child")
    nsum_py = py_snap.get("nested_y_summary")
    nsum_mat = mat_snap.get("nested_y_summary")
    if nsum_py is not None or nsum_mat is not None:
        _out("[XXX 12 inspection][y-ab] snap nested_y_summary present on 12F (boundary rollup)")


def _entry12_parent_mdp_from_12f_snap(snap: dict[str, Any]) -> dict[str, Any] | None:
    mdp = snap.get("MDP")
    if isinstance(mdp, dict):
        return mdp
    if isinstance(mdp, list) and mdp and isinstance(mdp[0], dict):
        return mdp[0]
    return None


def _entry12_fwd_scalar_diff(py_v: Any, mat_v: Any) -> str:
    import numpy as np

    try:
        a = float(np.asarray(py_v, dtype=np.float64).item())
        b = float(np.asarray(mat_v, dtype=np.float64).item())
    except (TypeError, ValueError):
        return f"py={py_v!r} mat={mat_v!r}"
    return f"py={a:.12g} mat={b:.12g} diff={a - b:.12g}"


def _entry12_fwd_vec_diff(label: str, py_v: Any, mat_v: Any, *, stream: Any) -> None:
    import numpy as np

    def _out(msg: str) -> None:
        print(msg, file=stream, flush=True)

    if py_v is None and mat_v is None:
        return
    try:
        a = np.asarray(py_v, dtype=np.float64).ravel()
        b = np.asarray(mat_v, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        _out(f"[XXX 12 inspection][fwd] {label}: shape/type mismatch py={type(py_v)} mat={type(mat_v)}")
        return
    if a.shape != b.shape:
        _out(f"[XXX 12 inspection][fwd] {label}: shape py={a.shape} mat={b.shape}")
        return
    if a.size == 0:
        _out(f"[XXX 12 inspection][fwd] {label}: empty")
        return
    d = float(np.max(np.abs(a - b)))
    pk_py = int(np.argmax(a) + 1) if a.size else None
    pk_mat = int(np.argmax(b) + 1) if b.size else None
    _out(
        f"[XXX 12 inspection][fwd] {label}: max|diff|={d:.6g} "
        f"peak_py={pk_py} peak_mat={pk_mat}"
    )


def entry12_print_forwards_diagnostics(
    py_by_code: dict[str, dict[str, Any]],
    mat_by_code: dict[str, dict[str, Any]],
    *,
    stream: Any = None,
) -> None:
    """
    Inspection block: ``entry12_forwards`` / ``entry12_generation`` on **12F** boundaries.

    Wired from script **4** when causal gate fails on ``MDP.F`` (forwards ELBO at parent ``t``).
    """
    import numpy as np

    def _out(msg: str) -> None:
        print(msg, file=stream, flush=True)

    for sub in ("out_t2", "out_t3", "out_tT"):
        if sub not in py_by_code.get("12F", {}) or sub not in mat_by_code.get("12F", {}):
            continue
        py_snap = py_by_code["12F"][sub]
        mat_snap = mat_by_code["12F"][sub]
        t_lab = int(np.asarray(py_snap.get("t", 0), dtype=np.float64).item())
        _out(f"\n[XXX 12 inspection][fwd] --- 12F.{sub} t={t_lab} forwards/generation ---")
        py_fwd_snap = py_snap.get("entry12_forwards")
        mat_fwd_snap = mat_snap.get("entry12_forwards")
        py_gen_snap = py_snap.get("entry12_generation")
        mat_gen_snap = mat_snap.get("entry12_generation")
        py_mdp = _entry12_parent_mdp_from_12f_snap(py_snap)
        mat_mdp = _entry12_parent_mdp_from_12f_snap(mat_snap)
        if py_mdp is None or mat_mdp is None:
            _out("[XXX 12 inspection][fwd] missing parent MDP on snap")
            continue
        F_py = py_mdp.get("F")
        F_mat = mat_mdp.get("F")
        if F_py is not None and F_mat is not None:
            try:
                fi = max(0, t_lab - 1) if t_lab > 0 else 0
                _out(
                    f"[XXX 12 inspection][fwd] MDP.F[{fi}] "
                    f"{_entry12_fwd_scalar_diff(F_py[fi], F_mat[fi])}"
                )
            except (IndexError, TypeError, ValueError) as exc:
                _out(f"[XXX 12 inspection][fwd] MDP.F slot read failed: {exc}")
        for side, mdp, fwd_snap, gen_snap in (
            ("py", py_mdp, py_fwd_snap, py_gen_snap),
            ("mat", mat_mdp, mat_fwd_snap, mat_gen_snap),
        ):
            fwd = fwd_snap if isinstance(fwd_snap, dict) else mdp.get("entry12_forwards")
            gen = gen_snap if isinstance(gen_snap, dict) else mdp.get("entry12_generation")
            if isinstance(fwd, dict):
                _out(
                    f"[XXX 12 inspection][fwd] {side} entry12_forwards: "
                    f"F_after_fwd={fwd.get('F_after_fwd')} "
                    f"F_mdp_slot={fwd.get('F_mdp_slot')} "
                    f"phase={fwd.get('phase')}"
                )
            else:
                _out(f"[XXX 12 inspection][fwd] {side}: no entry12_forwards on parent MDP")
            if isinstance(gen, dict):
                _out(
                    f"[XXX 12 inspection][fwd] {side} entry12_generation: "
                    f"k_policy={gen.get('k_policy')} t={gen.get('t')}"
                )
            else:
                _out(f"[XXX 12 inspection][fwd] {side}: no entry12_generation on parent MDP")
        py_fwd = (
            py_fwd_snap
            if isinstance(py_fwd_snap, dict)
            else (py_mdp.get("entry12_forwards") if isinstance(py_mdp.get("entry12_forwards"), dict) else {})
        )
        mat_fwd = (
            mat_fwd_snap
            if isinstance(mat_fwd_snap, dict)
            else (mat_mdp.get("entry12_forwards") if isinstance(mat_mdp.get("entry12_forwards"), dict) else {})
        )
        for key in ("F_after_fwd", "F_mdp_slot"):
            if key in py_fwd or key in mat_fwd:
                _out(
                    f"[XXX 12 inspection][fwd] {key}: "
                    f"{_entry12_fwd_scalar_diff(py_fwd.get(key), mat_fwd.get(key))}"
                )
        for key in ("Q_pre_fwd_f", "Q_post_fwd_f", "policy_P_at_t", "policy_P_post_fwd"):
            py_cells = py_fwd.get(key)
            mat_cells = mat_fwd.get(key)
            if not isinstance(py_cells, list) or not isinstance(mat_cells, list):
                continue
            nf = max(len(py_cells), len(mat_cells))
            for f_i in range(nf):
                py_f = py_cells[f_i] if f_i < len(py_cells) else None
                mat_f = mat_cells[f_i] if f_i < len(mat_cells) else None
                _entry12_fwd_vec_diff(f"{sub}.{key}{{f={f_i + 1}}}", py_f, mat_f, stream=stream)
        py_gen = py_mdp.get("entry12_generation") if isinstance(py_mdp.get("entry12_generation"), dict) else {}
        mat_gen = mat_mdp.get("entry12_generation") if isinstance(mat_mdp.get("entry12_generation"), dict) else {}
        for key in ("Q_after_gen_f", "policy_P_after_gen"):
            py_cells = py_gen.get(key)
            mat_cells = mat_gen.get(key)
            if not isinstance(py_cells, list) or not isinstance(mat_cells, list):
                continue
            nf = max(len(py_cells), len(mat_cells))
            for f_i in range(nf):
                py_f = py_cells[f_i] if f_i < len(py_cells) else None
                mat_f = mat_cells[f_i] if f_i < len(mat_cells) else None
                _entry12_fwd_vec_diff(f"{sub}.gen.{key}{{f={f_i + 1}}}", py_f, mat_f, stream=stream)


def _entry12_phase_log_qf_factor1(q_f: Any) -> np.ndarray | None:
    """Parent factor-1 belief vector from a phase record (``Q_f`` list or ndarray)."""
    import numpy as np

    if q_f is None:
        return None
    try:
        if isinstance(q_f, list):
            if not q_f:
                return None
            inner = q_f[0]
            if isinstance(inner, list):
                return np.asarray(inner, dtype=np.float64).ravel()
            return np.asarray(inner, dtype=np.float64).ravel()
        return np.asarray(q_f, dtype=np.float64).ravel()
    except (ValueError, TypeError):
        # Nested child rows (e.g. ``post_hierarchical``) may carry short / ragged ``Q_f``.
        return None


def _entry12_phase_log_model_entries(log: Any, *, m_1b: int = 1) -> list[dict[str, Any]]:
    """Normalize ``entry12_phase_log`` from py dict or mat struct to a list of phase records."""
    import copy

    import numpy as np

    if log is None:
        return []
    if isinstance(log, dict):
        ml = log.get("model_logs", [])
    else:
        ml = getattr(log, "model_logs", [])
    # scipy ``simplify_cells`` can flatten a single model_log struct to {m,t,entries}.
    if isinstance(ml, dict) and "entries" in ml:
        ml = [ml]
    if isinstance(ml, np.ndarray) and ml.dtype == object:
        ml = ml.ravel(order="F").tolist()
    for row in ml if isinstance(ml, list) else [ml]:
        if isinstance(row, dict):
            m_val = int(row.get("m", 0))
        else:
            m_val = int(getattr(row, "m", 0))
        if m_val != m_1b:
            continue
        ent = row.get("entries") if isinstance(row, dict) else getattr(row, "entries", [])
        if isinstance(ent, np.ndarray) and ent.dtype == object:
            ent = ent.ravel(order="F").tolist()
        out: list[dict[str, Any]] = []
        for item in ent if isinstance(ent, list) else []:
            if isinstance(item, dict):
                out.append(copy.deepcopy(item))
            else:
                d: dict[str, Any] = {}
                for fn in dir(item):
                    if fn.startswith("_"):
                        continue
                    try:
                        d[fn] = getattr(item, fn)
                    except Exception:
                        pass
                if "phase" in d:
                    out.append(d)
        return out
    return []


def _entry12_phase_log_parent_phase_map(
    entries: list[dict[str, Any]], *, min_q_len: int = 400
) -> dict[str, dict[str, Any]]:
    """
    Map phase name → last parent record (long ``Q_f`` vector).

    Nested child VB appends short ``Q_f`` rows; last-wins on the raw list mis-assigns F_vbx.
    """
    out: dict[str, dict[str, Any]] = {}
    for ent in entries:
        ph = str(ent.get("phase") or "")
        if not ph:
            continue
        qv = _entry12_phase_log_qf_factor1(ent.get("Q_f"))
        if qv is None or int(qv.size) < int(min_q_len):
            continue
        out[ph] = ent
    return out


def entry12_print_phase_log_diagnostics(
    py_by_code: dict[str, dict[str, Any]],
    mat_by_code: dict[str, dict[str, Any]],
    *,
    stream: Any = None,
) -> None:
    """
    Walk ``entry12_phase_log`` on **12F** / **12E** snaps.

    Reports first phase where parent ``Q_f`` or ``F_*`` diverge. Causal **12F** already
    asserts ``A_peaks_pre_vbx`` / ``A_peaks_pre_forwards``; this block is extra context.
    """
    import numpy as np

    def _out(msg: str) -> None:
        print(msg, file=stream, flush=True)

    _out(
        "\n[XXX 12 inspection][phase-log] --- entry12_phase_log (12F/12E; causal first-red still wins) ---"
    )
    bands = (
        ("12F", "out_t2"),
        ("12F", "out_t3"),
        ("12E", "out_t2"),
        ("12F", "out_tT"),
    )
    for code, sub in bands:
        if sub not in py_by_code.get(code, {}) or sub not in mat_by_code.get(code, {}):
            continue
        py_snap = py_by_code[code][sub]
        mat_snap = mat_by_code[code][sub]
        t_lab = int(np.asarray(py_snap.get("t", 0), dtype=np.float64).item())
        py_entries = _entry12_phase_log_model_entries(py_snap.get("entry12_phase_log"))
        mat_entries = _entry12_phase_log_model_entries(mat_snap.get("entry12_phase_log"))
        if not py_entries and not mat_entries:
            _out(f"[XXX 12 inspection][phase-log] {code}.{sub} t={t_lab}: no entry12_phase_log")
            continue
        py_map = _entry12_phase_log_parent_phase_map(py_entries)
        mat_map = _entry12_phase_log_parent_phase_map(mat_entries)
        _out(f"[XXX 12 inspection][phase-log] --- {code}.{sub} t={t_lab} ---")
        py_mdp = _entry12_parent_mdp_from_12f_snap(py_snap) if code == "12F" else None
        mat_mdp = _entry12_parent_mdp_from_12f_snap(mat_snap) if code == "12F" else None
        if py_mdp is not None and mat_mdp is not None:
            try:
                fi = max(0, t_lab - 1) if t_lab > 0 else 0
                _out(
                    f"[XXX 12 inspection][phase-log] MDP.F[{fi}] "
                    f"{_entry12_fwd_scalar_diff(py_mdp.get('F')[fi], mat_mdp.get('F')[fi])}"
                )
            except (IndexError, TypeError, ValueError) as exc:
                _out(f"[XXX 12 inspection][phase-log] MDP.F read failed: {exc}")
        for ph in ENTRY12_PHASE_LOG_ORDER:
            if ph not in py_map and ph not in mat_map:
                continue
            pe = py_map.get(ph, {})
            me = mat_map.get(ph, {})
            _out(f"[XXX 12 inspection][phase-log] phase={ph}")
            for sk in ("F_vbx", "F_after_fwd", "F_mdp_slot", "k_policy"):
                if sk in pe or sk in me:
                    _out(f"  {sk}: {_entry12_fwd_scalar_diff(pe.get(sk), me.get(sk))}")
            if ph in ("pre_forwards", "pre_vbx") and (
                "A_peaks" in pe or "A_peaks" in me
            ):
                py_a = _entry12_normalize_a_peaks_list(pe.get("A_peaks"))
                mat_a = _entry12_normalize_a_peaks_list(me.get("A_peaks"))
                if py_a or mat_a:
                    n = max(len(py_a), len(mat_a))
                    for gi in range(min(n, 8)):
                        pa = py_a[gi] if gi < len(py_a) else None
                        ma = mat_a[gi] if gi < len(mat_a) else None
                        _out(
                            f"  A_peaks[g={gi + 1}]: "
                            f"{_entry12_fwd_scalar_diff(pa, ma)}"
                        )
                    if n > 8:
                        _out(f"  A_peaks: ... ({n} modalities, showing first 8)")
            py_f0 = _entry12_phase_log_qf_factor1(pe.get("Q_f"))
            mat_f0 = _entry12_phase_log_qf_factor1(me.get("Q_f"))
            if py_f0 is not None or mat_f0 is not None:
                _entry12_fwd_vec_diff(
                    f"  {code}.{sub}.{ph}.Q_f{{f=1}}",
                    py_f0,
                    mat_f0,
                    stream=stream,
                )


__all__ = [
    "Entry12CompareLaneError",
    "ENTRY12_CAUSAL_BOUNDARY_STEPS",
    "ENTRY12_CALL4_LEAN_BOUNDARY_KEYS",
    "ENTRY12_CANONICAL_RUN_TAG",
    "ENTRY12_LEAN_BOUNDARY_KEYS",
    "ENTRY12_OPTIM1FULL_CALL4_TAG",
    "entry12_assert_causal_def_boundaries",
    "entry12_causal_boundary_steps_for_tag",
    "entry12_lean_boundary_keys_for_tag",
    "entry12_print_qo_ab_diagnostics",
    "entry12_print_y_ab_diagnostics",
    "entry12_print_forwards_diagnostics",
    "entry12_print_phase_log_diagnostics",
    "ENTRY12_PHASE_LOG_ORDER",
    "entry12_mat_snap_for_value_assert",
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
