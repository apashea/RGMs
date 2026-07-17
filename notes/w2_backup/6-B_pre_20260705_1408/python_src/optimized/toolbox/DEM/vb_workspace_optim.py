"""Phase 4-W / 5-R-1 — contiguous Q/P workspace for optim VB (input-general).

Preallocates belief columns like ``spm_MDP_VB_XXX.m`` ~685–689 (``Q{m,f,t}=D{m,f}``)
but stores each ``(m,f)`` factor as ``(state_dim, T)`` float64 — column ``t`` is time ``t``.

**5-R-1:** ``VbWorkspace`` is sole hot-path authority for Q/P/O; legacy ``bundle['Q']``/``['P']``/``['O']``
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
    """Optim-native belief storage — one contiguous ``(dim, T)`` array per ``(m, f)`` or ``(m, g)``."""

    T: int
    nm: int
    Q: list[list[np.ndarray]]
    P: list[list[np.ndarray]]
    O: list[list[np.ndarray]]
    X: list[list[np.ndarray]]
    S: list[list[np.ndarray]]


def _o_dim_from_bundle(bundle: dict[str, Any], m: int, g: int) -> int:
    no_t = bundle.get("No")
    if no_t is not None:
        arr = np.asarray(no_t, dtype=np.int64)
        if arr.ndim >= 2 and m < arr.shape[0] and g < arr.shape[1]:
            return max(1, int(arr[m, g]))
    o_legacy = bundle.get("O")
    if isinstance(o_legacy, list) and m < len(o_legacy) and g < len(o_legacy[m]):
        row = o_legacy[m][g]
        if isinstance(row, list) and row:
            return max(1, int(np.asarray(row[0], dtype=np.float64).size))
    return 1


def ws_alloc_from_bundle(bundle: dict[str, Any]) -> VbWorkspace:
    """Allocate empty workspace from ``bundle`` metadata (``.m`` init semantics)."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    d_t = bundle["D"]
    e_t = bundle["E"]
    x_t = bundle.get("X")
    s_t = bundle.get("S")
    ng_t = bundle.get("Ng")

    q_out: list[list[np.ndarray]] = []
    p_out: list[list[np.ndarray]] = []
    o_out: list[list[np.ndarray]] = []
    x_out: list[list[np.ndarray]] = []
    s_out: list[list[np.ndarray]] = []

    for m in range(nm):
        nf_m = len(d_t[m])
        ng_m = int(np.asarray(ng_t[m]).reshape(-1)[0]) if ng_t is not None else 0
        q_m: list[np.ndarray] = []
        p_m: list[np.ndarray] = []
        o_m: list[np.ndarray] = []
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
        for g_idx in range(ng_m):
            no_g = _o_dim_from_bundle(bundle, m, g_idx)
            o_m.append(np.zeros((no_g, t_int), dtype=np.float64))
        q_out.append(q_m)
        p_out.append(p_m)
        o_out.append(o_m)
        x_out.append(x_m)
        s_out.append(s_m)

    return VbWorkspace(T=t_int, nm=nm, Q=q_out, P=p_out, O=o_out, X=x_out, S=s_out)


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
    """Copy legacy nested-list ``Q``/``P``/``O``/``X``/``S`` into contiguous workspace (cold init only)."""
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
        o_legacy = bundle.get("O")
        if isinstance(o_legacy, list) and m < len(o_legacy):
            for g_idx in range(len(ws.O[m])):
                if g_idx < len(o_legacy[m]):
                    _fill_from_legacy_list(ws.O[m][g_idx], o_legacy[m][g_idx], t_int)

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
    # ``O`` — ws mirror populated at init; hot path still writes legacy ``bundle['O']`` until
    # forwards uses ``ws_assign_o_slot`` (**5-C-arena** forwards half — gated separately).


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


def _sync_ws_q_from_slot(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    slot: Any,
) -> None:
    """Refresh ``ws.Q(m,f,t)`` from a legacy slot object (after slot **replace**)."""
    flat = np.asarray(slot, dtype=np.float64).reshape(-1)
    n = int(flat.size)
    ws.Q[m][f][:, t] = 0.0
    if n:
        dim = int(ws.Q[m][f].shape[0])
        ws.Q[m][f][: min(n, dim), t] = flat[:dim]


def _sync_ws_p_from_slot(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    slot: Any,
) -> None:
    flat = np.asarray(slot, dtype=np.float64).reshape(-1)
    n = int(flat.size)
    ws.P[m][f][:, t] = 0.0
    if n:
        dim = int(ws.P[m][f].shape[0])
        ws.P[m][f][: min(n, dim), t] = flat[:dim]


def ws_assign_q_belief_slot(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    f: int,
    t: int,
    col: Any,
) -> None:
    """
    **5-R-1b:** replace ``bundle['Q']`` slot (VBX / forwards) — not ``_write_column`` in-place.

    Matches ``_fwd_write_belief_col`` / ``Q_all[m][f][t] = col`` fidelity semantics.
    """
    bundle["Q"][m][f][t] = col
    _sync_ws_q_from_slot(ws, m, f, t, col)


def ws_assign_p_belief_slot(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    f: int,
    t: int,
    col: Any,
) -> None:
    """Replace ``bundle['P']`` slot then sync ``ws`` (post-forwards / policy columns)."""
    bundle["P"][m][f][t] = col
    _sync_ws_p_from_slot(ws, m, f, t, col)


def ws_set_q_column(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    values: np.ndarray,
    bundle: dict[str, Any] | None = None,
) -> None:
    """Write ``Q(m,f,t)`` — slot **replace** on ``bundle`` when given (**5-R-1b**)."""
    arr = np.asarray(values, dtype=np.float64)
    if bundle is not None:
        bundle["Q"][m][f][t] = arr.copy()
        _sync_ws_q_from_slot(ws, m, f, t, arr)
    else:
        _ws_write_matrix_column(ws.Q[m][f], t, arr)


def ws_set_p_column(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    values: np.ndarray,
    bundle: dict[str, Any] | None = None,
) -> None:
    """Write ``P(m,f,t)`` — slot **replace** on ``bundle`` when given."""
    arr = np.asarray(values, dtype=np.float64)
    if bundle is not None:
        if arr.ndim == 1:
            slot = arr.reshape(-1, 1, order="F")
        else:
            slot = arr.copy()
        ws_assign_p_belief_slot(ws, bundle, m, f, t, slot)
    else:
        _ws_write_matrix_column(ws.P[m][f], t, arr)


def ws_set_p_onehot(
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
    u_mark_1based: int,
    bundle: dict[str, Any] | None = None,
) -> None:
    """``.m`` ~830–831: ``P{m,f,t}(:)=0; P{m,f,t}(u)=1`` — slot replace when ``bundle`` given."""
    nu = int(ws.P[m][f].shape[0])
    col = np.zeros((nu, 1), dtype=np.float64)
    u = int(u_mark_1based)
    if 1 <= u <= nu:
        col[u - 1, 0] = 1.0
    if bundle is not None:
        ws_assign_p_belief_slot(ws, bundle, m, f, t, col)
    else:
        ws.P[m][f][:, t] = col[:, 0]


def ws_copy_p_column(
    ws: VbWorkspace,
    m: int,
    f: int,
    t_dst: int,
    t_src: int,
    bundle: dict[str, Any] | None = None,
) -> None:
    """Copy ``P(m,f,t_src)`` → ``P(m,f,t_dst)`` without ``deepcopy``."""
    src_slot = (
        np.asarray(bundle["P"][m][f][t_src], dtype=np.float64).copy()
        if bundle is not None
        else ws.P[m][f][:, t_src].reshape(-1, 1, order="F")
    )
    if bundle is not None:
        ws_assign_p_belief_slot(ws, bundle, m, f, t_dst, src_slot)
    else:
        ws.P[m][f][:, t_dst] = ws.P[m][f][:, t_src]


def ws_pull_q_column_from_bundle(
    bundle: dict[str, Any],
    ws: VbWorkspace,
    m: int,
    f: int,
    t: int,
) -> None:
    """Refresh one ``ws.Q`` column from legacy bundle after VBX slot assign."""
    _sync_ws_q_from_slot(ws, m, f, t, bundle["Q"][m][f][t])


def ws_pull_model_q_at_t(
    bundle: dict[str, Any],
    ws: VbWorkspace,
    m: int,
    t: int,
) -> None:
    """Refresh all factor ``Q(m,*,t)`` columns from bundle."""
    for f_idx in range(len(ws.Q[m])):
        ws_pull_q_column_from_bundle(bundle, ws, m, f_idx, t)


def ws_q_compact_column(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    f: int,
    t: int,
) -> np.ndarray:
    """Compact ``Q(m,f,t)`` from ``ws`` — ``numel`` from legacy slot shape (**5-R-1b**)."""
    n = int(np.asarray(bundle["Q"][m][f][t], dtype=np.float64).size)
    if n < 1:
        return np.zeros(0, dtype=np.float64)
    return np.asarray(ws.Q[m][f][:n, t], dtype=np.float64).reshape(-1, order="F")


def ws_p_compact_column(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    f: int,
    t: int,
) -> np.ndarray:
    n = int(np.asarray(bundle["P"][m][f][t], dtype=np.float64).size)
    if n < 1:
        return np.zeros(0, dtype=np.float64)
    return np.asarray(ws.P[m][f][:n, t], dtype=np.float64).reshape(-1, order="F")


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


def _sync_ws_o_from_slot(
    ws: VbWorkspace,
    m: int,
    g: int,
    t: int,
    slot: Any,
) -> None:
    flat = np.asarray(slot, dtype=np.float64).reshape(-1)
    n = int(flat.size)
    ws.O[m][g][:, t] = 0.0
    if n:
        dim = int(ws.O[m][g].shape[0])
        ws.O[m][g][: min(n, dim), t] = flat[:dim]


def ws_assign_o_slot(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    g: int,
    t: int,
    col: Any,
) -> None:
    """Replace ``bundle['O']`` slot (forwards EFE / hierarchical writes) — sync ``ws.O``."""
    bundle["O"][m][g][t] = col
    _sync_ws_o_from_slot(ws, m, g, t, col)


def ws_o_compact_column(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    g: int,
    t: int,
) -> np.ndarray:
    """Compact ``O(m,g,t)`` from ``ws`` — ``numel`` from legacy slot shape."""
    n = int(np.asarray(bundle["O"][m][g][t], dtype=np.float64).size)
    if n < 1:
        return np.zeros(0, dtype=np.float64)
    return np.asarray(ws.O[m][g][:n, t], dtype=np.float64).reshape(-1, order="F")


def ws_o_cell(ws: VbWorkspace, m: int, g: int, t: int) -> np.ndarray:
    """``O(m,g,t)`` as ``No×1`` column for VBX / ``spm_dot``."""
    return ws.O[m][g][:, t].reshape(-1, 1, order="F")


def ws_o_row_at_t(
    ws: VbWorkspace,
    bundle: dict[str, Any],
    m: int,
    t: int,
) -> list[np.ndarray]:
    """Modality ``O(m,*,t)`` from dense ``ws.O`` — ``numel`` from legacy slot shape."""
    row: list[np.ndarray] = []
    for g in range(len(ws.O[m])):
        n = int(np.asarray(bundle["O"][m][g][t], dtype=np.float64).size)
        if n < 1:
            row.append(np.zeros((0, 1), dtype=np.float64))
        else:
            col = np.asarray(ws.O[m][g][:n, t], dtype=np.float64).reshape(-1, 1, order="F")
            row.append(col)
    return row


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
    o_legacy = bundle.get("O")
    if isinstance(o_legacy, list):
        for m in range(ws.nm):
            if m >= len(o_legacy):
                continue
            for g_idx in range(len(ws.O[m])):
                if g_idx >= len(o_legacy[m]):
                    continue
                for t_idx in range(t_int):
                    leg_o = np.asarray(o_legacy[m][g_idx][t_idx], dtype=np.float64).reshape(-1)
                    no = min(leg_o.size, ws.O[m][g_idx].shape[0])
                    if no:
                        mx = max(
                            mx,
                            float(np.max(np.abs(ws.O[m][g_idx][:no, t_idx] - leg_o[:no]))),
                        )
    return mx
