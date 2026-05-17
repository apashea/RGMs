"""
MDP structure checking for XXX routines (MATLAB-compatible).

Translated from spm_MDP_checkX.m (Pass 1 faithful transliteration).

Staged MATLAB uses `size(MDP.A{1},2:ndims(MDP.A{1}))` (SPM had `ndims(A)` typo).
"""

from __future__ import annotations

import copy
from typing import Any, List, Optional, Tuple, Union

import numpy as np
from scipy import sparse

from matlab_compat import full as mfull, matlab_ndims
from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_MDP_size import _getfield, _hasfield


def _setfield(mdp: Any, field: str, value: Any) -> None:
    if isinstance(mdp, dict):
        mdp[field] = value
    else:
        setattr(mdp, field, value)


def _iscell_like(x: Any) -> bool:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return True
    return isinstance(x, (list, tuple))


def _normalize_mdp_argument(
    MDP: Union[dict, List[Any]],
) -> Tuple[Optional[dict], Optional[List[List[dict]]]]:
    if isinstance(MDP, dict):
        return MDP, None
    if isinstance(MDP, list) and MDP and isinstance(MDP[0], list):
        return None, MDP
    if isinstance(MDP, list) and MDP and isinstance(MDP[0], dict):
        return None, [[d] for d in MDP]
    raise TypeError(
        "MDP must be a dict, a list of dicts (column struct array), or list-of-lists of dicts"
    )


def _isnumeric_like(x: Any) -> bool:
    if sparse.issparse(x):
        return True
    return isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.number)


def _to_dense_double(x: Any) -> np.ndarray:
    if sparse.issparse(x):
        return np.asarray(mfull(x), dtype=np.float64)
    return np.asarray(x, dtype=np.float64)


def _id_g_cell_partitions(g_cell: Any) -> list[np.ndarray]:
    """
    MATLAB ``id.g`` covert partitions: one cell per partition, each holding modality indices.

    Do not ``ravel`` an object array built from a single ``(1, n)`` row — that splits one
    partition into ``n`` scalar cells and inflates ``numel(id.g)`` in ``spm_forwards``.
    """
    if isinstance(g_cell, np.ndarray) and g_cell.dtype == object:
        items = [g_cell.reshape(-1, order="F")[k] for k in range(g_cell.size)]
    elif isinstance(g_cell, list):
        items = list(g_cell)
    else:
        items = [g_cell]
    row_cells: list[np.ndarray] = []
    for item in items:
        v = np.asarray(item, dtype=np.float64)
        if v.ndim == 0:
            v = v.reshape(1, 1)
        elif v.ndim == 1:
            v = v.reshape(1, -1)
        elif v.ndim >= 2:
            v = np.squeeze(v)
            if v.ndim == 1:
                v = v.reshape(1, -1)
            elif v.ndim == 0:
                v = v.reshape(1, 1)
            else:
                v = v.reshape(1, -1)
        row_cells.append(np.asarray(v, dtype=np.float64))
    return row_cells


def _list_cell_to_ndarray_like_reference(val_list: list[Any], ref: np.ndarray) -> np.ndarray:
    """Pack checkX ``id.g``-style list-of-rows into one MATLAB-shaped ndarray."""
    parts: list[np.ndarray] = []
    for item in val_list:
        parts.append(np.asarray(item, dtype=np.float64).reshape(-1, order="F"))
    flat = np.concatenate(parts) if parts else np.array([], dtype=np.float64)
    arr = np.asarray(flat, dtype=ref.dtype)
    if ref.shape and arr.size == int(np.prod(ref.shape)):
        return arr.reshape(ref.shape, order="F")
    return arr


def _cast_leaf_like_reference(val: Any, ref: Any) -> Any:
    """Entry 12 ``transform``: match MATLAB ``.mat`` container types; keep Python numeric content."""
    if val is None and isinstance(ref, np.ndarray):
        return np.array([], dtype=ref.dtype)
    if sparse.issparse(ref):
        arr = _to_dense_double(val)
        if hasattr(sparse, "csc_array") and type(ref).__name__ == "csc_array":
            return sparse.csc_array(arr)
        if isinstance(ref, sparse.csr_matrix):
            return sparse.csr_matrix(arr)
        return sparse.csc_matrix(arr)
    if isinstance(ref, np.ndarray):
        if isinstance(val, list):
            return _list_cell_to_ndarray_like_reference(val, ref)
        if ref.dtype.kind in "iu":
            arr = np.asarray(val, dtype=ref.dtype)
            if ref.shape and arr.size == int(np.prod(ref.shape)):
                return np.asarray(arr, dtype=ref.dtype).reshape(ref.shape, order="F")
            return np.asarray(arr, dtype=ref.dtype)
        arr = np.asarray(val, dtype=np.float64)
        if ref.shape and arr.size == int(np.prod(ref.shape)):
            return np.asarray(arr, dtype=np.float64).reshape(ref.shape, order="F")
        return np.asarray(arr, dtype=np.float64)
    if isinstance(ref, (int, float, np.integer, np.floating)):
        if isinstance(ref, (bool, np.bool_)):
            return bool(np.asarray(val).item())
        if isinstance(ref, (np.integer, int)):
            return int(np.asarray(val).item())
        return float(np.asarray(val).item())
    if isinstance(ref, dict):
        if not isinstance(val, dict):
            return copy.deepcopy(ref)
        return _align_nested_to_reference(val, ref)
    if isinstance(ref, list):
        if not isinstance(val, list):
            return copy.deepcopy(ref)
        out: list[Any] = []
        for i in range(len(ref)):
            vi = val[i] if i < len(val) else val[-1]
            out.append(_cast_leaf_like_reference(vi, ref[i]))
        if len(val) > len(ref):
            out.extend(val[len(ref) :])
        return out
    return val


def _align_nested_to_reference(val: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, ref_v in ref.items():
        if key in val:
            out[key] = _cast_leaf_like_reference(val[key], ref_v)
    for key, val_v in val.items():
        if key not in out:
            out[key] = val_v
    return out


def _spm_MDP_checkX_transform_align(mdp: dict[str, Any], reference: dict[str, Any]) -> None:
    """Align checked ``mdp`` nested types to MATLAB ``loadmat`` / ``mat_nested_to_py`` template."""
    aligned = _align_nested_to_reference(mdp, reference)
    mdp.clear()
    mdp.update(aligned)


def spm_MDP_checkX(
    MDP: Union[dict, List[Any]],
    transform: bool = False,
    transform_reference: Any | None = None,
):
    """
    FORMAT MDP = spm_MDP_checkX(MDP)

    ``transform`` (Entry 12 only, provisional): after standard checking, coerce container
    types to match ``transform_reference`` (typically ``mat_nested_to_py(loadmat(RDP))``).
    """
    single, grid = _normalize_mdp_argument(MDP)
    if grid is not None:
        rows = len(grid)
        cols = len(grid[0])
        if rows * cols > 1:
            out: List[List[dict]] = [[None] * cols for _ in range(rows)]
            for m in range(rows):
                for i in range(cols):
                    out[m][i] = spm_MDP_checkX(
                        copy.deepcopy(grid[m][i]),
                        transform=transform,
                        transform_reference=transform_reference,
                    )
            return out
        single = grid[0][0]

    _spm_MDP_checkX_single(single)
    if transform:
        if not isinstance(transform_reference, dict):
            raise TypeError(
                "transform_reference must be a dict when transform=True (MATLAB nested RDP template)"
            )
        _spm_MDP_checkX_transform_align(single, transform_reference)
    return single


def _spm_MDP_checkX_single(MDP: dict) -> None:
    if not _hasfield(MDP, "A"):
        try:
            _setfield(MDP, "A", copy.deepcopy(_getfield(MDP, "a")))
        except (KeyError, AttributeError):
            pass
    if not _hasfield(MDP, "B"):
        try:
            _setfield(MDP, "B", copy.deepcopy(_getfield(MDP, "b")))
        except (KeyError, AttributeError):
            pass

    a_field = _getfield(MDP, "A")
    if not _iscell_like(a_field):
        _setfield(MDP, "A", [_to_dense_double(a_field)])
    b_field = _getfield(MDP, "B")
    if not _iscell_like(b_field):
        _setfield(MDP, "B", [_to_dense_double(b_field)])

    if not _hasfield(MDP, "B"):
        a1 = _getfield(MDP, "A")[0]
        if a1.ndim < 2:
            a1 = np.reshape(a1, (a1.size, 1), order="F")
        ns_dims = list(a1.shape[1:])
        b_list = []
        for f in range(len(ns_dims)):
            n = int(ns_dims[f])
            # MATLAB: MDP.B{f} = eye(Ns(f),Ns(f)) — 2-D, no singleton third dim.
            b_list.append(np.eye(n, n, dtype=np.float64))
        _setfield(MDP, "B", b_list)
        b_field = _getfield(MDP, "B")
        if not _iscell_like(b_field):
            _setfield(MDP, "B", [_to_dense_double(b_field)])

    if _hasfield(MDP, "a"):
        a_h = _getfield(MDP, "a")
        if not _iscell_like(a_h):
            _setfield(MDP, "a", [_to_dense_double(a_h)])
    if _hasfield(MDP, "b"):
        b_h = _getfield(MDP, "b")
        if not _iscell_like(b_h):
            _setfield(MDP, "b", [_to_dense_double(b_h)])

    A = _getfield(MDP, "A")
    for g in range(len(A)):
        ag = A[g]
        if _isnumeric_like(ag):
            ag = _to_dense_double(ag)
            A[g] = np.asarray(spm_dir_norm(ag), dtype=np.float64)
    _setfield(MDP, "A", A)

    B = _getfield(MDP, "B")
    for f in range(len(B)):
        bf = B[f]
        if isinstance(bf, (int, float, np.integer, np.floating)):
            bf = np.asarray(float(bf), dtype=np.float64).reshape(1, 1)
            B[f] = bf
            continue
        if _isnumeric_like(bf):
            bf = _to_dense_double(bf)
            if bf.ndim == 0:
                bf = np.atleast_2d(bf)
            bf = np.asarray(spm_dir_norm(bf), dtype=np.float64)
            # MATLAB drops a trailing Nu=1 dimension (e.g. ones(n,n,1) is stored as n×n).
            if bf.ndim == 3 and bf.shape[2] == 1:
                bf = bf.reshape((bf.shape[0], bf.shape[1]))
            B[f] = bf
    _setfield(MDP, "B", B)

    ng = len(_getfield(MDP, "A"))
    nf = len(_getfield(MDP, "B"))
    no = np.zeros(ng, dtype=np.int64)
    ns = np.zeros(nf, dtype=np.int64)
    nu = np.zeros(nf, dtype=np.int64)
    for g in range(ng):
        no[g] = _getfield(MDP, "A")[g].shape[0]
    for f in range(nf):
        bf = _getfield(MDP, "B")[f]
        ns[f] = bf.shape[0]
        nu[f] = bf.shape[2] if bf.ndim >= 3 else 1

    if not _hasfield(MDP, "U"):
        _setfield(MDP, "U", np.zeros((1, nf), dtype=np.float64))

    if not _hasfield(MDP, "C"):
        c_list = []
        for g in range(ng):
            c_list.append(
                np.asarray(
                    spm_dir_norm(np.ones((int(no[g]), 1), dtype=np.float64)),
                    dtype=np.float64,
                )
            )
        _setfield(MDP, "C", c_list)
    C = _getfield(MDP, "C")
    for g in range(ng):
        cg = np.asarray(C[g], dtype=np.float64)
        if cg.ndim == 1:
            cg = cg.reshape(-1, 1, order="F")
        C[g] = np.asarray(spm_dir_norm(cg), dtype=np.float64)
    _setfield(MDP, "C", C)

    if not _hasfield(MDP, "D"):
        d_list = []
        for f in range(nf):
            d_list.append(
                np.asarray(
                    spm_dir_norm(np.ones((int(ns[f]), 1), dtype=np.float64)),
                    dtype=np.float64,
                )
            )
        _setfield(MDP, "D", d_list)
    else:
        D = _getfield(MDP, "D")
        for f in range(nf):
            df = D[f]
            if df is None or (isinstance(df, np.ndarray) and df.size == 0):
                D[f] = np.asarray(
                    spm_dir_norm(np.ones((int(ns[f]), 1), dtype=np.float64)),
                    dtype=np.float64,
                )
        _setfield(MDP, "D", D)
    D = _getfield(MDP, "D")
    for f in range(nf):
        df = D[f]
        if sparse.issparse(df):
            df = mfull(df)
        col = np.asarray(df, dtype=np.float64).reshape(-1, 1, order="F")
        D[f] = col
    _setfield(MDP, "D", D)

    if not _hasfield(MDP, "E"):
        e_list = []
        for f in range(nf):
            if int(nu[f]) <= 0:
                e_list.append(np.zeros((0, 1), dtype=np.float64))
            else:
                e_list.append(
                    np.asarray(
                        spm_dir_norm(np.ones((int(nu[f]), 1), dtype=np.float64)),
                        dtype=np.float64,
                    )
                )
        _setfield(MDP, "E", e_list)
    else:
        E = _getfield(MDP, "E")
        for f in range(nf):
            ef = E[f]
            if ef is None or (isinstance(ef, np.ndarray) and ef.size == 0):
                if int(nu[f]) <= 0:
                    E[f] = np.zeros((0, 1), dtype=np.float64)
                else:
                    E[f] = np.asarray(
                        spm_dir_norm(np.ones((int(nu[f]), 1), dtype=np.float64)),
                        dtype=np.float64,
                    )
        _setfield(MDP, "E", E)
    E = _getfield(MDP, "E")
    for f in range(nf):
        ef = E[f]
        if sparse.issparse(ef):
            ef = mfull(ef)
        col = np.asarray(ef, dtype=np.float64).reshape(-1, 1, order="F")
        E[f] = col
    _setfield(MDP, "E", E)

    if not _hasfield(MDP, "id"):
        idd: dict = {"g": [], "A": [], "C": []}
        idd["g"] = [np.arange(1, ng + 1, dtype=np.float64).reshape(1, -1)]
        for g in range(ng):
            ag = _getfield(MDP, "A")[g]
            ndm = int(matlab_ndims(ag))
            idd["A"].append(np.arange(1, ndm, dtype=np.float64).reshape(1, -1))
        for g in range(ng):
            idd["C"].append(np.array([], dtype=np.float64))
        _setfield(MDP, "id", idd)

    idd = _getfield(MDP, "id")
    if "C" not in idd:
        idd["C"] = []
        for g in range(ng):
            idd["C"].append(np.array([], dtype=np.float64))
        _setfield(MDP, "id", idd)

    try:
        idd["g"] = _id_g_cell_partitions(idd["g"])
        for g in range(len(idd["g"])):
            v = np.asarray(idd["g"][g], dtype=np.float64).reshape(-1, 1, order="F").T
            idd["g"][g] = v
    except Exception:
        idd["g"] = [np.arange(1, ng + 1, dtype=np.float64).reshape(1, -1)]

    for g in range(ng):
        try:
            row = np.asarray(idd["A"][g], dtype=np.float64).reshape(-1, 1, order="F").T
            idd["A"][g] = row
        except Exception:
            ag = _getfield(MDP, "A")[g]
            ndm = int(matlab_ndims(ag))
            idd["A"][g] = np.arange(1, ndm, dtype=np.float64).reshape(1, -1)
        if idd["A"][g].size == 0:
            ag = _getfield(MDP, "A")[g]
            ndm = int(matlab_ndims(ag))
            idd["A"][g] = np.arange(1, ndm, dtype=np.float64).reshape(1, -1)

    _setfield(MDP, "id", idd)
