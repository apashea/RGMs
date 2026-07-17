"""W2 — optim ``_spm_induction_vb`` (band **12F** profile hotspot #2).

**Phase 3-I-1 (2026-07-04):** drop ``p_store``; in-place backward; row-slice ``Bf`` propagation.
**Phase 3-I-2 (2026-07-04):** build ``qf_ravel`` via ``np.kron`` (skip sparse ``Qf`` chain).
**Phase 3-I-3 (2026-07-04):** dense ``Bf`` via ``np.kron`` when square ``(l_dim,l_dim)`` — 1d factors ``(1,ns)`` keep sparse ``spm_kron``.
**Phase 4-I-4 (2026-07-04):** read factor columns from ``VbWorkspace``; dense ``Bf`` for all ``bf_nelem <= threshold``; sparse ``Bf`` never ``toarray``.

Gate order after edit: **3f** only during dev.

**ENDGAME-1 tranche 3 (2026-07-06):** ``cid`` ``D`` mask reads ``ws.Q`` columns when ``ws`` + ``ws_t_col`` supplied.

**ENDGAME-1 tranche 4 (2026-07-06):** ``InductionModelStatic`` — hoisted ``b_map``/``Bf`` kron + ``Pf`` per model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy import sparse

from matlab_compat import full as mfull
from python_src.spm_kron import spm_kron
from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM import vb_primitives_optim as _prim
from python_src.optimized.toolbox.DEM.vb_contract_optim import ind_backward_paths_into
from python_src.optimized.toolbox.DEM.vb_workspace_optim import ws_q_compact_column

if TYPE_CHECKING:
    from python_src.optimized.toolbox.DEM.vb_workspace_optim import VbWorkspace

# Below this element count, dense ``Bf.toarray()*D`` matches fidelity and can be faster.
_DENSE_BF_ELEM_THRESHOLD = 16384


@dataclass
class InductionModelStatic:
    """Per-model induction invariants — ``b_map``/``Bf`` kron + ``Pf`` (**ENDGAME-1 t4**)."""

    branch: str
    hif_list: list[int]
    has_cid: bool
    hif_kept: list[int]
    ns_by_pos: list[int]
    l_dim: int
    bf_nelem: int
    use_dense_bf: bool
    Bf_bool: Any
    hid: np.ndarray
    Pf: np.ndarray


def _induction_hid_hif(H: list[Any], id_dict: dict[str, Any]) -> tuple[np.ndarray, Any, np.ndarray]:
    """Shared hid/hif resolution (no ``Q`` / ``ws``)."""
    if "hid" in id_dict and id_dict["hid"] is not None:
        hid_m = id_dict["hid"]
        if callable(hid_m):
            raise NotImplementedError("spm_induction: id.hid function_handle not translated")
        hid_full = np.asarray(hid_m, dtype=np.float64)
        if hid_full.ndim < 2:
            nf_h = len(H)
            if nf_h == 1:
                hid_full = np.reshape(hid_full, (1, -1), order="F")
            else:
                hid_full = np.reshape(hid_full, (-1, 1), order="F")
        hif = (np.flatnonzero(np.any(hid_full != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
        hid = hid_full
    else:
        hid_list: list[float] = []
        hif_list: list[int] = []
        for f in range(len(H)):
            Hf = H[f]
            if _prim._numel(Hf) > 0:
                hf = np.asarray(mfull(Hf), dtype=np.float64).reshape(-1, order="F")
                s = int(np.argmax(hf) + 1)
                hid_list.append(float(s))
                hif_list.append(int(f + 1))
        if not hid_list:
            hid = np.zeros((0, 0), dtype=np.float64)
        else:
            hid = np.asarray(hid_list, dtype=np.float64).reshape(-1, 1)
        hif = np.asarray(hif_list, dtype=np.int64).reshape(1, -1)

    if "cid" in id_dict and id_dict["cid"] is not None:
        cid_raw = id_dict["cid"]
        if callable(cid_raw):
            raise NotImplementedError("spm_induction: id.cid function_handle not translated")
        cid_arr = np.asarray(cid_raw, dtype=np.float64)
        if cid_arr.size != 0:
            hif = (np.flatnonzero(np.all(cid_arr != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)

    hif_list = [int(x) for x in np.asarray(hif, dtype=np.int64).ravel().tolist()]
    hid = np.asarray(hid, dtype=np.float64)
    if hid.ndim == 2 and hid.shape[0] > len(hif_list) and len(hif_list) > 0:
        hid = hid[np.asarray(hif_list, dtype=int) - 1, :]
    return hid, hif, np.asarray(hif_list, dtype=np.int64)


def induction_model_static(
    B: list[list[np.ndarray]],
    H: list[Any],
    id_dict: dict[str, Any],
    nk: int,
) -> InductionModelStatic:
    """Build per-model ``b_map``/``Bf``/``Pf`` — invariant across ``t`` within one VB run."""
    u_thr = 1.0 / 32.0
    hid, _hif, hif_list_arr = _induction_hid_hif(H, id_dict)
    hif_list = [int(x) for x in hif_list_arr.ravel().tolist()]
    has_cid = bool(
        "cid" in id_dict
        and id_dict["cid"] is not None
        and np.asarray(id_dict["cid"], dtype=np.float64).size > 0
    )

    if len(hif_list) == 0:
        return InductionModelStatic(
            branch="empty_hif",
            hif_list=[],
            has_cid=has_cid,
            hif_kept=[],
            ns_by_pos=[],
            l_dim=0,
            bf_nelem=0,
            use_dense_bf=True,
            Bf_bool=None,
            hid=hid,
            Pf=np.zeros((0, 0), dtype=bool),
        )
    if hid.size == 0:
        return InductionModelStatic(
            branch="empty_hid",
            hif_list=hif_list,
            has_cid=has_cid,
            hif_kept=[],
            ns_by_pos=[],
            l_dim=0,
            bf_nelem=0,
            use_dense_bf=True,
            Bf_bool=None,
            hid=hid,
            Pf=np.zeros((0, 0), dtype=bool),
        )

    b_map: dict[int, np.ndarray] = {}
    for f in hif_list:
        if f < 1 or f > len(B) or len(B[f - 1]) == 0:
            continue
        acc = None
        nk_f = len(B[f - 1])
        for k in range(min(int(nk), nk_f)):
            try:
                bfk = np.asarray(B[f - 1][k], dtype=np.float64)
            except Exception:
                bfk = np.asarray(B[f - 1][0], dtype=np.float64)
            thr = bfk > u_thr
            acc = thr if acc is None else (acc | thr)
        if acc is not None:
            b_map[f] = np.asarray(acc, dtype=bool)
    if not b_map:
        return InductionModelStatic(
            branch="no_bmap",
            hif_list=hif_list,
            has_cid=has_cid,
            hif_kept=[],
            ns_by_pos=[],
            l_dim=0,
            bf_nelem=0,
            use_dense_bf=True,
            Bf_bool=None,
            hid=hid,
            Pf=np.zeros((0, 0), dtype=bool),
        )

    hif_kept = [f for f in hif_list if f in b_map]
    hid_kept = hid
    if hid.ndim == 2 and len(hif_kept) > 0:
        idx_kept = [hif_list.index(f) for f in hif_kept]
        hid_kept = hid[np.asarray(idx_kept, dtype=int), :]

    ns_by_pos = [int(B[f - 1][0].shape[0]) for f in hif_kept]
    l_dim = int(np.prod(ns_by_pos, dtype=np.int64)) if ns_by_pos else 1
    bf_rows, bf_cols = _ind_bf_kron_shape(hif_kept, b_map)
    bf_nelem = int(bf_rows * bf_cols)
    use_dense_bf = bf_nelem <= _DENSE_BF_ELEM_THRESHOLD
    if use_dense_bf:
        Bf_bool = _ind_bf_dense_build(hif_kept, b_map)
    else:
        Bf_bool = sparse.csr_matrix([[1.0]], dtype=np.float64)
        for f in hif_kept:
            Bf_bool = spm_kron(b_map[f], Bf_bool)

    hid_arr = np.asarray(hid_kept, dtype=np.float64)
    if hid_arr.ndim == 1:
        hid_arr = hid_arr.reshape(-1, 1)
    nh = int(hid_arr.shape[1])
    Pf = np.zeros((l_dim, nh), dtype=bool)
    for i in range(nh):
        Pf[:, i] = _ind_pf_column_ravel(hid_arr[:, i], ns_by_pos)

    return InductionModelStatic(
        branch="full",
        hif_list=hif_list,
        has_cid=has_cid,
        hif_kept=hif_kept,
        ns_by_pos=ns_by_pos,
        l_dim=l_dim,
        bf_nelem=bf_nelem,
        use_dense_bf=use_dense_bf,
        Bf_bool=Bf_bool,
        hid=hid_kept,
        Pf=Pf,
    )


def _ind_bf_prop_from_bool(
    ist: InductionModelStatic,
    d_flat: Any,
) -> Any:
    if ist.use_dense_bf:
        if d_flat is None:
            d_mul = np.ones(ist.bf_nelem, dtype=np.float64)
        else:
            d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")
            if d_mul.size != ist.bf_nelem:
                raise ValueError("spm_induction: D size mismatch with Bf")
        return _ind_bf_apply_d_mask_dense(ist.Bf_bool, d_flat, d_mul)
    if d_flat is None:
        d_mul = np.ones(int(ist.Bf_bool.shape[0] * ist.Bf_bool.shape[1]), dtype=np.float64)
    else:
        d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")
        if d_mul.size != int(ist.Bf_bool.shape[0] * ist.Bf_bool.shape[1]):
            raise ValueError("spm_induction: D size mismatch with Bf")
    return _bf_apply_d_mask_sparse(ist.Bf_bool, d_flat, d_mul)


def _ind_pf_column_ravel(hid_col: np.ndarray, ns_by_pos: list[int]) -> np.ndarray:
    """Build one ``Pf`` column — equivalent to repeated ``spm_kron(hvec, I).toarray().ravel(F)``."""
    I = np.ones(1, dtype=bool)
    for pos, nsf in enumerate(ns_by_pos):
        hvec = np.zeros(nsf, dtype=bool)
        hidx = int(hid_col[pos])
        if hidx > 0:
            hvec[hidx - 1] = True
        I = np.kron(hvec, I)
    return I


def _ind_backward_paths_into(
    pf_col: np.ndarray,
    Bf_prop: Any,
    N: int,
    I_big: np.ndarray,
    prev_f: np.ndarray | None,
) -> None:
    """In-place backwards bool propagation — delegates to **6-C** fused matvec."""
    if prev_f is None:
        prev_f = np.empty(int(I_big.shape[0]), dtype=np.float64)
    ind_backward_paths_into(pf_col, Bf_prop, N, I_big, prev_f)


def _ind_kron_factor_like_spm(b_map_entry: np.ndarray) -> np.ndarray:
    """Layout for ``np.kron`` matching ``spm_kron`` / ``_as_sparse`` (1d → row ``(1,ns)``)."""
    arr = np.asarray(b_map_entry, dtype=bool)
    if arr.ndim == 1:
        return arr.reshape(1, -1)
    return arr


def _ind_bf_kron_shape(hif_kept: list[int], b_map: dict[int, np.ndarray]) -> tuple[int, int]:
    """Predict ``spm_kron`` product shape without building ``Bf``."""
    nrows, ncols = 1, 1
    for f in hif_kept:
        fac = _ind_kron_factor_like_spm(b_map[f])
        nrows *= int(fac.shape[0])
        ncols *= int(fac.shape[1])
    return nrows, ncols


def _ind_bf_dense_build(hif_kept: list[int], b_map: dict[int, np.ndarray]) -> np.ndarray:
    """Dense bool ``Bf`` — byte-identical to ``spm_kron`` chain ``.toarray(F) > 0``."""
    Bf = np.array([[True]], dtype=bool)
    for f in hif_kept:
        Bf = np.kron(_ind_kron_factor_like_spm(b_map[f]), Bf)
    return Bf


def _ind_bf_apply_d_mask_dense(
    Bf_dense: np.ndarray,
    d_flat: Any,
    d_mul: np.ndarray,
) -> np.ndarray:
    """``Bf .* D`` on dense bool/float — same as ``_bf_apply_d_mask_sparse`` after ``toarray``."""
    if d_flat is None:
        return np.asarray(Bf_dense, dtype=np.float64)
    nrows, ncols = Bf_dense.shape
    d_2d = d_mul.reshape((nrows, ncols), order="F")
    return np.asarray(Bf_dense, dtype=np.float64) * d_2d


def _ind_qf_ravel_build(hif_kept: list[int], Q: list[Any]) -> np.ndarray:
    """``Qf.toarray().ravel(F)`` without constructing sparse ``Qf`` (``spm_kron`` chain)."""
    qf = np.array([1.0], dtype=np.float64)
    for f in hif_kept:
        Qcol = np.asarray(Q[f - 1], dtype=np.float64).ravel(order="F")
        qf = np.kron(Qcol, qf)
    return qf


def _ind_qf_ravel_from_ws(
    ws: VbWorkspace,
    m: int,
    hif_kept: list[int],
    t_col: int,
    ns_by_pos: list[int],
) -> np.ndarray:
    """``qf_ravel`` from contiguous ``ws.Q(m,f,t)`` columns — no legacy list ``asarray``."""
    qf = np.array([1.0], dtype=np.float64)
    for f, nsf in zip(hif_kept, ns_by_pos):
        Qcol = ws.Q[m][f - 1][:nsf, t_col]
        qf = np.kron(Qcol, qf)
    return qf


def _ind_g_column_from_qf_ravel(I_big: np.ndarray, qf_ravel: np.ndarray, ncols: int) -> np.ndarray:
    """``G(:,i) = I' * qf`` — one ``l_dim`` dot per goal column (BLAS gemv)."""
    vec = np.dot(I_big.astype(np.float64).T, qf_ravel)
    return np.asarray(vec, dtype=np.float64).ravel(order="F")[:ncols]


def _ind_g_column(I_big: np.ndarray, qf_ravel: np.ndarray, ncols: int) -> np.ndarray:
    return _ind_g_column_from_qf_ravel(I_big, qf_ravel, ncols)


def _bf_apply_d_mask_sparse(Bf: sparse.csr_matrix, d_flat: Any, d_mul: np.ndarray) -> sparse.csr_matrix:
    """Fidelity-equivalent ``Bf .* D`` without ``Bf.toarray()`` when ``Bf`` is large."""
    if d_flat is None:
        return Bf
    nrows, ncols = Bf.shape
    nelem = int(nrows * ncols)
    if int(d_mul.size) != nelem:
        raise ValueError("spm_induction: D size mismatch with Bf")
    d_2d = d_mul.reshape((nrows, ncols), order="F")
    if nelem <= _DENSE_BF_ELEM_THRESHOLD:
        bf_dense = Bf.toarray(order="F") * d_2d
        return sparse.csr_matrix(bf_dense)
    return sparse.csr_matrix(Bf.multiply(d_2d))


def _spm_induction_vb_optim(
    B: list[list[np.ndarray]],
    H: list[Any],
    Q: list[Any],
    N: int,
    id_dict: dict[str, Any],
    *,
    ws: VbWorkspace | None = None,
    ws_m: int | None = None,
    ws_t_col: int | None = None,
    ind_static: InductionModelStatic | None = None,
) -> tuple[Any, np.ndarray]:
    """Optim lane — fidelity semantics; **4-I-4** optional ``ws`` column reads."""
    _PROBE_12F_PARENT = _inst._PROBE_12F_PARENT
    _probe_ind = bool(os.getenv("RGMS_PROBE_12F_PARENT_T1")) and _PROBE_12F_PARENT is not None

    if ind_static is not None and ind_static.branch == "empty_hif":
        if _probe_ind:
            _PROBE_12F_PARENT["ind_branch"] = "empty_hif"
        return np.array([]), np.array([], dtype=np.int64)

    if "hid" in id_dict and id_dict["hid"] is not None:
        hid_m = id_dict["hid"]
        if callable(hid_m):
            raise NotImplementedError("spm_induction: id.hid function_handle not translated")
        hid_full = np.asarray(hid_m, dtype=np.float64)
        if hid_full.ndim < 2:
            nf_h = len(H)
            if nf_h == 1:
                hid_full = np.reshape(hid_full, (1, -1), order="F")
            else:
                hid_full = np.reshape(hid_full, (-1, 1), order="F")
        hif = (np.flatnonzero(np.any(hid_full != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
        hid = hid_full
    else:
        hid_list: list[float] = []
        hif_list: list[int] = []
        for f in range(len(H)):
            Hf = H[f]
            if _prim._numel(Hf) > 0:
                hf = np.asarray(mfull(Hf), dtype=np.float64).reshape(-1, order="F")
                s = int(np.argmax(hf) + 1)
                hid_list.append(float(s))
                hif_list.append(int(f + 1))
        if not hid_list:
            hid = np.zeros((0, 0), dtype=np.float64)
        else:
            hid = np.asarray(hid_list, dtype=np.float64).reshape(-1, 1)
        hif = np.asarray(hif_list, dtype=np.int64).reshape(1, -1)

    if "cid" in id_dict and id_dict["cid"] is not None:
        cid_raw = id_dict["cid"]
        if callable(cid_raw):
            raise NotImplementedError("spm_induction: id.cid function_handle not translated")
        cid_arr = np.asarray(cid_raw, dtype=np.float64)
        if cid_arr.size == 0:
            d_tensor: Any = True
            d_flat = None
        else:
            cid = cid_arr
            nid = cid.copy()
            hif = (np.flatnonzero(np.all(cid != 0, axis=1)) + 1).astype(np.int64).reshape(1, -1)
            for f in hif.ravel().tolist():
                nid[int(f) - 1, :] = 0
            ns_list = [int(B[int(f) - 1][0].shape[0]) for f in hif.ravel().tolist()] + [1]
            ns_tuple = tuple(ns_list)
            d_tensor = np.ones(ns_tuple, dtype=bool)
            for i in range(cid.shape[1]):
                qv = 1.0
                for f0 in range(cid.shape[0]):
                    if nid[f0, i] != 0:
                        f1 = f0 + 1
                        cidx = int(nid[f0, i])
                        if ws is not None and ws_m is not None and ws_t_col is not None:
                            qcol = ws_q_compact_column(ws, ws_m, f1 - 1, ws_t_col, None)
                        else:
                            qcol = np.asarray(Q[f1 - 1], dtype=np.float64).reshape(-1, order="F")
                        qv *= float(qcol[cidx - 1])
                if qv > (1.0 - 1.0 / 8.0):
                    inds = [int(cid[int(f) - 1, i]) for f in hif.ravel().tolist()]
                    lin = int(np.ravel_multi_index(tuple(x - 1 for x in inds), tuple(ns_list[:-1]), order="F"))
                    d_tensor[np.unravel_index(lin, d_tensor.shape, order="F")] = False
            d_flat = d_tensor.reshape(-1, order="F")
    else:
        d_tensor = True
        d_flat = None

    hif_list = [int(x) for x in np.asarray(hif, dtype=np.int64).ravel().tolist()]
    hid = np.asarray(hid, dtype=np.float64)
    if hid.ndim == 2 and hid.shape[0] > len(hif_list) and len(hif_list) > 0:
        hid = hid[np.asarray(hif_list, dtype=int) - 1, :]

    if len(hif_list) == 0:
        if _probe_ind:
            _PROBE_12F_PARENT["ind_branch"] = "empty_hif"
        return np.array([]), np.array([], dtype=np.int64)
    if hid.size == 0:
        if _probe_ind:
            _PROBE_12F_PARENT["ind_branch"] = "empty_hid"
            _PROBE_12F_PARENT["hid_shape"] = list(np.asarray(hid).shape)
            _PROBE_12F_PARENT["hid_all_zero"] = bool(np.all(hid == 0)) if hid.size else False
            _PROBE_12F_PARENT["D_is_scalar"] = d_tensor is True
            if d_flat is not None:
                d_arr = np.asarray(d_flat, dtype=bool).ravel(order="F")
                _PROBE_12F_PARENT["D_nnz"] = int(np.count_nonzero(d_arr))
            else:
                _PROBE_12F_PARENT["D_nnz"] = 1
        if d_tensor is True:
            return np.asarray(32.0, dtype=np.float64), np.asarray(hif_list, dtype=np.int64)
        r32 = (32.0 * np.asarray(d_flat, dtype=np.float32).ravel(order="F")).astype(np.float32)
        return r32, np.asarray(hif_list, dtype=np.int64)

    N = int(min(int(N), 64))
    if "D" in id_dict and N < 4:
        N = 64
    if N <= 0:
        return np.array([]), np.asarray(hif_list, dtype=np.int64)

    u_thr = 1.0 / 32.0
    use_ind_static = (
        ind_static is not None
        and ind_static.branch == "full"
        and hif_list == ind_static.hif_list
    )
    if use_ind_static:
        hif_kept = ind_static.hif_kept
        ns_by_pos = ind_static.ns_by_pos
        l_dim = ind_static.l_dim
        Bf_prop = _ind_bf_prop_from_bool(ind_static, d_flat)
        Pf = ind_static.Pf
        hid = ind_static.hid
    else:
        if ind_static is not None and ind_static.branch == "no_bmap":
            return np.array([]), np.array([], dtype=np.int64)
        if not B or len(B) == 0:
            return np.array([]), np.array([], dtype=np.int64)
        nk = len(B[0])
        if nk == 0:
            return np.array([]), np.array([], dtype=np.int64)
        b_map: dict[int, np.ndarray] = {}
        for f in hif_list:
            if f < 1 or f > len(B) or len(B[f - 1]) == 0:
                continue
            acc = None
            nk_f = len(B[f - 1])
            for k in range(min(nk, nk_f)):
                try:
                    bfk = np.asarray(B[f - 1][k], dtype=np.float64)
                except Exception:
                    bfk = np.asarray(B[f - 1][0], dtype=np.float64)
                thr = bfk > u_thr
                acc = thr if acc is None else (acc | thr)
            if acc is None:
                continue
            b_map[f] = np.asarray(acc, dtype=bool)
        if not b_map:
            return np.array([]), np.array([], dtype=np.int64)
        hif_kept = [f for f in hif_list if f in b_map]

        hid = np.asarray(hid, dtype=np.float64)
        if hid.ndim == 2 and len(hif_kept) > 0:
            idx_kept = [hif_list.index(f) for f in hif_kept]
            hid = hid[np.asarray(idx_kept, dtype=int), :]

        ns_by_pos = [int(B[f - 1][0].shape[0]) for f in hif_kept]
        l_dim = int(np.prod(ns_by_pos, dtype=np.int64)) if ns_by_pos else 1
        bf_rows, bf_cols = _ind_bf_kron_shape(hif_kept, b_map)
        bf_nelem = int(bf_rows * bf_cols)
        use_dense_bf = bf_nelem <= _DENSE_BF_ELEM_THRESHOLD
        if use_dense_bf:
            Bf_dense_bool = _ind_bf_dense_build(hif_kept, b_map)
            if d_flat is None:
                d_mul = np.ones(bf_nelem, dtype=np.float64)
            else:
                d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")
                if d_mul.size != bf_nelem:
                    raise ValueError("spm_induction: D size mismatch with Bf")
            Bf_prop = _ind_bf_apply_d_mask_dense(Bf_dense_bool, d_flat, d_mul)
        else:
            Bf = sparse.csr_matrix([[1.0]], dtype=np.float64)
            for f in hif_kept:
                Bf = spm_kron(b_map[f], Bf)
            if d_flat is None:
                d_mul = np.ones(int(Bf.shape[0] * Bf.shape[1]), dtype=np.float64)
            else:
                d_mul = np.asarray(d_flat, dtype=np.float64).ravel(order="F")
                if d_mul.size != int(Bf.shape[0] * Bf.shape[1]):
                    raise ValueError("spm_induction: D size mismatch with Bf")
            Bf = _bf_apply_d_mask_sparse(Bf, d_flat, d_mul)
            Bf_prop = Bf

        hid_arr = np.asarray(hid, dtype=np.float64)
        if hid_arr.ndim == 1:
            hid_arr = hid_arr.reshape(-1, 1)
        nh = int(hid_arr.shape[1])
        Pf = np.zeros((l_dim, nh), dtype=bool)
        for i in range(nh):
            Pf[:, i] = _ind_pf_column_ravel(hid_arr[:, i], ns_by_pos)

    if ws is not None and ws_m is not None and ws_t_col is not None:
        qf_ravel = _ind_qf_ravel_from_ws(ws, ws_m, hif_kept, ws_t_col, ns_by_pos)
    else:
        qf_ravel = _ind_qf_ravel_build(hif_kept, Q)

    hid_arr = np.asarray(hid, dtype=np.float64)
    if hid_arr.ndim == 1:
        hid_arr = hid_arr.reshape(-1, 1)
    nh = int(hid_arr.shape[1])
    ncols = N + 1
    if not use_ind_static:
        Pf = np.zeros((l_dim, nh), dtype=bool)
        for i in range(nh):
            Pf[:, i] = _ind_pf_column_ravel(hid_arr[:, i], ns_by_pos)

    G = np.zeros((ncols, nh), dtype=np.float64)
    I_big = np.zeros((l_dim, ncols), dtype=bool)
    prev_f = np.empty(l_dim, dtype=np.float64)

    for i in range(nh):
        _ind_backward_paths_into(Pf[:, i], Bf_prop, N, I_big, prev_f)
        G[:, i] = _ind_g_column(I_big, qf_ravel, ncols)

    G[0, :] = 0.0
    dmx = np.max(G, axis=0)
    nmx = np.argmax(G, axis=0)
    mask = dmx > u_thr
    if not np.any(mask):
        return np.array([]), np.asarray(hif_kept, dtype=np.int64)

    masked_goals = [j for j in range(nh) if mask[j]]
    n_sel = nmx[mask]
    j0 = int(np.argmin(n_sel))
    orig_j = masked_goals[j0]
    n_use = int(n_sel[j0])
    col_idx = max(int(n_use) - 1, 0)
    _ind_backward_paths_into(Pf[:, orig_j], Bf_prop, N, I_big, prev_f)
    p_vec = I_big[:, col_idx].astype(np.float64)
    p_col = p_vec.reshape(-1, 1, order="F")
    if d_tensor is True:
        d_col = np.ones_like(p_col, dtype=bool)
    else:
        d_col = np.asarray(d_tensor, dtype=bool).reshape(p_col.shape, order="F")
    R = (32.0 * np.logical_and(p_col.astype(bool), d_col.astype(bool))).astype(np.float64)
    if os.getenv("RGMS_INDUCTION_DBG"):
        _inst._INDUCTION_DBG = {
            "goal_i": int(j0),
            "n_col": int(n_use),
            "col_idx": int(col_idx),
            "P_nz": np.flatnonzero(p_col.ravel() > 0).tolist(),
            "dmx": np.asarray(dmx, dtype=np.float64).ravel().tolist(),
            "nmx": np.asarray(nmx, dtype=np.int64).ravel().tolist(),
            "Pf_col0_nnz": int(np.count_nonzero(Pf[:, 0])) if Pf.size else 0,
            "G_shape": list(G.shape),
        }
    if _probe_ind:
        _PROBE_12F_PARENT["ind_branch"] = "full_induction"
        _PROBE_12F_PARENT["hid_shape"] = list(np.asarray(hid).shape)
        _PROBE_12F_PARENT["hid_all_zero"] = bool(np.all(hid == 0))
        _PROBE_12F_PARENT["Nh"] = int(nh)
        _PROBE_12F_PARENT["D_is_scalar"] = d_tensor is True
        if d_flat is not None:
            _PROBE_12F_PARENT["D_nnz"] = int(np.count_nonzero(np.asarray(d_flat, dtype=bool)))
        else:
            _PROBE_12F_PARENT["D_nnz"] = int(np.count_nonzero(d_col))
        Rv = np.asarray(R, dtype=np.float64).ravel(order="F")
        _PROBE_12F_PARENT["R_nnz_ind"] = int(np.count_nonzero(Rv > 0.0))
    return R, np.asarray(hif_kept, dtype=np.int64)
