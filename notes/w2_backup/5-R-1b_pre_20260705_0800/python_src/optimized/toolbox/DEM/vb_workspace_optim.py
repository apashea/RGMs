"""Phase 4-W / 5-R-1 — contiguous Q/P workspace for optim VB (input-general).

Preallocates belief columns like ``spm_MDP_VB_XXX.m`` ~685–689 (``Q{m,f,t}=D{m,f}``)
but stores each ``(m,f)`` factor as ``(state_dim, T)`` float64 — column ``t`` is time ``t``.

**5-R-1:** ``VbWorkspace`` is sole hot-path authority for Q/P; legacy ``bundle['Q']``/``['P']``
nested lists sync only at boundaries via ``ws_to_bundle`` (cold teardown, dumps, output).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _col_size(entry: Any) -> int:
    if entry is None:
        return 0
    arr = np.asarray(entry, dtype=np.float64)
    return int(arr.size)


def _write_column(dst: Any, col: np.ndarray) -> None:
    """Write ``col`` into legacy bundle slot (preserve shape when possible)."""
    flat = np.asarray(col, dtype=np.float64).reshape(-1)
    if isinstance(dst, np.ndarray):
        if dst.size == flat.size:
            np.copyto(np.asarray(dst, dtype=np.float64).reshape(-1), flat)
            return
    if isinstance(dst, list) and len(dst) == flat.size:
        for i, v in enumerate(flat):
            dst[i] = float(v)
        return
    if flat.size == 0:
        return
    if isinstance(dst, np.ndarray):
        dst[...] = flat.reshape(dst.shape)
    else:
        raise TypeError(f"unsupported Q/P slot type: {type(dst)!r}")


@dataclass
class VbWorkspace:
    """Optim-native belief storage — one contiguous ``(dim, T)`` array per ``(m, f)``."""

    T: int
    nm: int
    Q: list[list[np.ndarray]]
    P: list[list[np.ndarray]]
    X: list[list[np.ndarray]]
    S: list[list[np.ndarray]]


def ws_alloc_from_bundle(bundle: dict[str, Any]) -> VbWorkspace:
    """Allocate empty workspace from ``bundle`` metadata (``.m`` init semantics)."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    d_t = bundle["D"]
    e_t = bundle["E"]
    x_t = bundle.get("X")
    s_t = bundle.get("S")

    q_out: list[list[np.ndarray]] = []
    p_out: list[list[np.ndarray]] = []
    x_out: list[list[np.ndarray]] = []
    s_out: list[list[np.ndarray]] = []

    for m in range(nm):
        nf_m = len(d_t[m])
        q_m: list[np.ndarray] = []
        p_m: list[np.ndarray] = []
        x_m: list[np.ndarray] = []
        s_m: list[np.ndarray] = []
        for f_idx in range(nf_m):
            dmf = d_t[m][f_idx]
            emf = e_t[m][f_idx]
            ns = _col_size(dmf)
            npth = _col_size(emf)
            q_m.append(np.zeros((ns, t_int), dtype=np.float64))
            p_m.append(np.zeros((npth, t_int), dtype=np.float64))
            if x_t is not None and m < len(x_t) and f_idx < len(x_t[m]):
                x_m.append(np.asarray(x_t[m][f_idx], dtype=np.float64).copy())
            else:
                x_m.append(np.zeros((ns, t_int), dtype=np.float64))
            if s_t is not None and m < len(s_t) and f_idx < len(s_t[m]):
                s_m.append(np.asarray(s_t[m][f_idx], dtype=np.float64).copy())
            else:
                s_m.append(np.zeros((npth, t_int), dtype=np.float64))
        q_out.append(q_m)
        p_out.append(p_m)
        x_out.append(x_m)
        s_out.append(s_m)

    return VbWorkspace(T=t_int, nm=nm, Q=q_out, P=p_out, X=x_out, S=s_out)


def _fill_from_legacy_list(
    dest: np.ndarray,
    legacy: list[Any],
    t_int: int,
) -> None:
    for t_idx in range(t_int):
        col = np.asarray(legacy[t_idx], dtype=np.float64).reshape(-1)
        if col.size == 0:
            continue
        if dest.shape[0] < col.size:
            raise ValueError(
                f"workspace row dim {dest.shape[0]} < legacy column size {col.size} at t={t_idx}"
            )
        dest[: col.size, t_idx] = col


def ws_from_bundle(bundle: dict[str, Any]) -> VbWorkspace:
    """Copy legacy nested-list ``Q``/``P``/``X``/``S`` into contiguous workspace (cold init only)."""
    ws = ws_alloc_from_bundle(bundle)
    t_int = ws.T

    for m in range(ws.nm):
        for f_idx in range(len(ws.Q[m])):
            _fill_from_legacy_list(ws.Q[m][f_idx], bundle["Q"][m][f_idx], t_int)
            _fill_from_legacy_list(ws.P[m][f_idx], bundle["P"][m][f_idx], t_int)
            if m < len(bundle.get("X", [])) and f_idx < len(bundle["X"][m]):
                x_arr = np.asarray(bundle["X"][m][f_idx], dtype=np.float64)
                if x_arr.shape == ws.X[m][f_idx].shape:
                    ws.X[m][f_idx][...] = x_arr
                else:
                    ws.X[m][f_idx] = x_arr.copy()
            if m < len(bundle.get("S", [])) and f_idx < len(bundle["S"][m]):
                s_arr = np.asarray(bundle["S"][m][f_idx], dtype=np.float64)
                if s_arr.shape == ws.S[m][f_idx].shape:
                    ws.S[m][f_idx][...] = s_arr
                else:
                    ws.S[m][f_idx] = s_arr.copy()

    return ws


def ws_to_bundle(ws: VbWorkspace, bundle: dict[str, Any]) -> None:
    """Sync workspace columns into legacy ``bundle['Q']`` / ``bundle['P']`` (boundary only)."""
    t_int = int(bundle["T"])
    if t_int != ws.T:
        raise ValueError(f"bundle T={t_int} != workspace T={ws.T}")

    for m in range(ws.nm):
        for f_idx in range(len(ws.Q[m])):
            q_legacy = bundle["Q"][m][f_idx]
            p_legacy = bundle["P"][m][f_idx]
            if len(q_legacy) != t_int or len(p_legacy) != t_int:
                raise ValueError(f"legacy Q/P list length mismatch at m={m} f={f_idx}")
            for t_idx in range(t_int):
                _write_column(q_legacy[t_idx], ws.Q[m][f_idx][:, t_idx])
                _write_column(p_legacy[t_idx], ws.P[m][f_idx][:, t_idx])
            if m < len(bundle.get("X", [])) and f_idx < len(bundle["X"][m]):
                bundle["X"][m][f_idx] = ws.X[m][f_idx].copy()
            if m < len(bundle.get("S", [])) and f_idx < len(bundle["S"][m]):
                bundle["S"][m][f_idx] = ws.S[m][f_idx].copy()


def ws_get(bundle: dict[str, Any]) -> VbWorkspace | None:
    """Return attached workspace (required on optim 12F hot path)."""
    ws = bundle.get("_vb_workspace_optim")
    return ws if isinstance(ws, VbWorkspace) else None


def ws_require(bundle: dict[str, Any]) -> VbWorkspace:
    ws = ws_get(bundle)
    if ws is None:
        raise RuntimeError("optim hot path requires bundle['_vb_workspace_optim']")
    return ws


def _ws_write_matrix_column(mat: np.ndarray, t: int, values: np.ndarray) -> None:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    n = int(flat.size)
    dim = int(mat.shape[0])
    if n > dim:
        raise ValueError(f"workspace column dim {dim} < value size {n}")
    mat[:, t] = 0.0
    if n:
        mat[:n, t] = flat[:n]


def ws_set_q_column(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    values: np.ndarray,
    bundle: dict[str, Any] | None = None,
) -> None:
    """In-place ``Q(m,f,t)`` on ``ws``; optional legacy slot sync when ``bundle`` given."""
    _ws_write_matrix_column(ws.Q[m][f], t, values)
    if bundle is not None:
        _write_column(bundle["Q"][m][f][t], ws.Q[m][f][:, t])


def ws_set_p_column(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    values: np.ndarray,
    bundle: dict[str, Any] | None = None,
) -> None:
    """In-place ``P(m,f,t)`` on ``ws``; optional legacy slot sync when ``bundle`` given."""
    _ws_write_matrix_column(ws.P[m][f], t, values)
    if bundle is not None:
        _write_column(bundle["P"][m][f][t], ws.P[m][f][:, t])


def ws_set_p_onehot(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    u_mark_1based: int,
    bundle: dict[str, Any] | None = None,
) -> None:
    """``.m`` ~830–831: ``P{m,f,t}(:)=0; P{m,f,t}(u)=1`` in-place."""
    mat = ws.P[m][f]
    mat[:, t] = 0.0
    u = int(u_mark_1based)
    if 1 <= u <= mat.shape[0]:
        mat[u - 1, t] = 1.0
    if bundle is not None:
        _write_column(bundle["P"][m][f][t], mat[:, t])


def ws_copy_p_column(
    ws: VbWorkspace,
    m: int,
    f: int,
    t_dst: int,
    t_src: int,
    bundle: dict[str, Any] | None = None,
) -> None:
    """Copy ``P(m,f,t_src)`` → ``P(m,f,t_dst)`` without ``deepcopy``."""
    ws.P[m][f][:, t_dst] = ws.P[m][f][:, t_src]
    if bundle is not None:
        _write_column(bundle["P"][m][f][t_dst], ws.P[m][f][:, t_dst])


def ws_pull_q_column_from_bundle(
    bundle: dict[str, Any],
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
) -> None:
    """Refresh one ``ws.Q`` column from legacy bundle after VBX slot assign."""
    col = np.asarray(bundle["Q"][m][f][t], dtype=np.float64).reshape(-1)
    n = int(col.size)
    if n:
        ws.Q[m][f][:n, t] = col[:n]


def ws_pull_model_q_at_t(
    bundle: dict[str, Any],
    ws: VbWorkspace,
    m: int,
    t: int,
) -> None:
    """Refresh all factor ``Q(m,*,t)`` columns from bundle."""
    for f_idx in range(len(ws.Q[m])):
        ws_pull_q_column_from_bundle(bundle, ws, m, f_idx, t)


def ws_q_column(ws: VbWorkspace, m: int, f: int, t: int) -> np.ndarray:
    """View of ``Q(m,f,t)`` as 1-D float64 (0-based ``t``)."""
    return ws.Q[m][f][:, t]


def ws_p_column(ws: VbWorkspace, m: int, f: int, t: int) -> np.ndarray:
    """View of ``P(m,f,t)`` as 1-D float64 (0-based ``t``)."""
    return ws.P[m][f][:, t]


def ws_q_cell(ws: VbWorkspace, m: int, f: int, t: int) -> np.ndarray:
    """``Q(m,f,t)`` as ``No×1`` column for ``spm_dot`` / ``spm_parents``."""
    return ws.Q[m][f][:, t].reshape(-1, 1, order="F")


def ws_p_cell(ws: VbWorkspace, m: int, f: int, t: int) -> np.ndarray:
    """``P(m,f,t)`` as column for ``spm_dot``."""
    return ws.P[m][f][:, t].reshape(-1, 1, order="F")


def ws_q_row_at_t(ws: VbWorkspace, m: int, t: int, nf: int | None = None) -> list[np.ndarray]:
    """Factor ``Q(m,*,t)`` columns — ``spm_parents`` / active-learning row."""
    nf_use = len(ws.Q[m]) if nf is None else int(nf)
    return [ws_q_cell(ws, m, f, t) for f in range(nf_use)]


def ws_bridge_max_abs_diff(ws: VbWorkspace, bundle: dict[str, Any]) -> float:
    """Max |ws − bundle| over Q/P columns (parity audit helper)."""
    t_int = ws.T
    mx = 0.0
    for m in range(ws.nm):
        for f_idx in range(len(ws.Q[m])):
            for t_idx in range(t_int):
                leg_q = np.asarray(bundle["Q"][m][f_idx][t_idx], dtype=np.float64).reshape(-1)
                leg_p = np.asarray(bundle["P"][m][f_idx][t_idx], dtype=np.float64).reshape(-1)
                nq = min(leg_q.size, ws.Q[m][f_idx].shape[0])
                np_ = min(leg_p.size, ws.P[m][f_idx].shape[0])
                if nq:
                    mx = max(mx, float(np.max(np.abs(ws.Q[m][f_idx][:nq, t_idx] - leg_q[:nq]))))
                if np_:
                    mx = max(mx, float(np.max(np.abs(ws.P[m][f_idx][:np_, t_idx] - leg_p[:np_]))))
    return mx
