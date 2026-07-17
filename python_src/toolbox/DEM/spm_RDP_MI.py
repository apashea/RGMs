"""Pass 1 transliteration of ``spm_RDP_MI.m``."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_dir_reduce import spm_dir_reduce
from python_src.toolbox.DEM.spm_RDP_compress import spm_RDP_compress


@dataclass(frozen=True)
class MiCausalSnap:
    """Causal steps 1--4 inside ``spm_RDP_MI`` (OPTIM1.md § 11.5.1)."""

    B_ambig: np.ndarray
    B_norm: np.ndarray
    C_n: int
    C_shapes: np.ndarray
    C_sums: np.ndarray
    R: np.ndarray


def spm_RDP_MI(MDP: list[dict[str, Any]], o: int | None = None) -> list[dict[str, Any]]:
    """MATLAB ``[MDP] = spm_RDP_MI(MDP,o)``."""
    if o is None:
        o = 1
    snap = _build_mi_causal_snap(copy.deepcopy(MDP), o)
    return spm_RDP_compress(copy.deepcopy(MDP), snap.R)


def _build_mi_causal_snap(mdp: list[dict[str, Any]], o: int) -> MiCausalSnap:
    """``spm_RDP_MI.m`` lines 29--88 without ``spm_RDP_compress``."""
    n = len(mdp)
    mdp_n = mdp[n - 1]

    try:
        a_raw = mdp_n["a"]
    except KeyError:
        a_raw = mdp_n["A"]

    try:
        b_raw = mdp_n["b"][0]
    except (KeyError, IndexError, TypeError):
        b_raw = mdp_n["B"][0]

    b = np.array(_unwrap_cell(b_raw), dtype=np.float64, copy=True)
    if b.ndim == 2:
        b = np.reshape(b, (b.shape[0], b.shape[1], 1), order="F")
    ns = int(b.shape[1])
    nu = int(b.shape[2])

    for u in range(1, nu + 1):
        for s in range(1, ns + 1):
            if not np.any(b[:, s - 1, u - 1]):
                slab = np.squeeze(b[:, s - 1, :])
                if slab.ndim == 1:
                    col_max = np.asarray(slab, dtype=np.float64)
                else:
                    col_max = np.max(slab, axis=1)
                i = int(np.argmax(col_max))
                j = int(col_max[i])
                b[i, s - 1, u - 1] = j

    b_ambig = np.array(b, copy=True)
    a = spm_dir_norm(a_raw)
    b = spm_dir_norm(b)

    sb_top = _as_int_list(mdp[0]["sB"])
    sb_max = max(sb_top) if sb_top else 1
    mdp_nm1 = mdp[n - 2]
    c_blocks: list[np.ndarray] = []

    for s in range(2, sb_max + 1):
        pd_vals = _id_de_values(mdp_nm1, "D", s)
        pe_vals = _id_de_values(mdp_nm1, "E", s)
        ps = _modalities_first_stream_index(mdp_n)
        pd = [p for p in ps if p in pd_vals]
        pe = [p for p in ps if p in pe_vals]

        if pd:
            for p in range(0, int(o) + 1):
                for u_idx in range(1, nu + 1):
                    b_pow = np.linalg.matrix_power(b[:, :, u_idx - 1], p)
                    for p_idx in pd:
                        a_pd = np.asarray(_unwrap_cell(a[p_idx - 1]), dtype=np.float64)
                        c_blocks.append(a_pd @ b_pow)
                    for e_idx in pe:
                        a_pe = np.asarray(_unwrap_cell(a[e_idx - 1]), dtype=np.float64)
                        c_blocks.append(a_pe @ b_pow)

    c_n = len(c_blocks)
    c_shapes = np.zeros((c_n, 2), dtype=np.int64)
    c_sums = np.zeros((c_n, 1), dtype=np.float64)
    for k, blk in enumerate(c_blocks):
        c_shapes[k, :] = np.asarray(blk.shape, dtype=np.int64).reshape(2)
        c_sums[k, 0] = float(np.sum(blk))

    r_mat = spm_dir_reduce([[blk] for blk in c_blocks])
    r_dense = np.asarray(
        r_mat.toarray() if hasattr(r_mat, "toarray") else r_mat, dtype=np.float64
    )

    return MiCausalSnap(
        B_ambig=b_ambig,
        B_norm=np.asarray(b, dtype=np.float64),
        C_n=c_n,
        C_shapes=c_shapes,
        C_sums=c_sums,
        R=r_dense,
    )


def _unwrap_cell(x: Any) -> Any:
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _as_int_list(x: Any) -> list[int]:
    arr = np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")
    return [int(v) for v in arr.tolist()]


def _cell_scalar_int(x: Any) -> int:
    return int(np.asarray(_unwrap_cell(x), dtype=np.int64).ravel(order="F")[0])


def _id_de_values(mdp_prev: dict[str, Any], field: str, stream_s: int) -> list[int]:
    sb = _as_int_list(mdp_prev["sB"])
    id_field = mdp_prev["id"][field]
    out: list[int] = []
    for idx, sb_val in enumerate(sb):
        if sb_val == stream_s:
            vec = np.asarray(_unwrap_cell(id_field[idx]), dtype=np.int64).ravel(order="F")
            out.extend(int(v) for v in vec.tolist())
    return out


def _modalities_first_stream_index(mdp_n: dict[str, Any]) -> list[int]:
    sb = _as_int_list(mdp_n["sB"])
    first_idx = 1
    for i, val in enumerate(sb):
        if val == 1:
            first_idx = i + 1
            break
    out: list[int] = []
    for g, item in enumerate(mdp_n["id"]["A"], start=1):
        if _cell_scalar_int(item) == first_idx:
            out.append(g)
    return out


__all__ = ["MiCausalSnap", "spm_RDP_MI", "_build_mi_causal_snap"]
