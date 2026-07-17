"""W2 â€” optim ``spm_forwards`` (band **12F** profile hotspot #3).

**Phase 2g (2026-07-03):** fidelity-equivalent body with hoisted invariants:
``_spm_log(Hf)``, ``P{f,t}`` for ``id_fu`` / ``id_iI``, int id lists.

**Phase 2g edit 2 (2026-07-03):** ``_forwards_spm_dot`` tried and **reverted** â€” parity PASS but
call4 production **~71 s** vs e1 **~48 s**; cProfile **164 s** vs **157 s**.

**Tier 2b T2-f1 (2026-07-03):** pre-cache ``B{m,f,k}`` / ``I{m,f,k}`` float64 slices for policy
loops (no ``spm_dot`` shortcut â€” e2 lesson).

**Tier 2b T2-f2 (2026-07-03):** per-``k`` ``spm_parents`` / ``_cell_get_Qj`` memo; pre-convert
``A`` / ``C`` / ``K`` / ``W`` likelihood tensors to float64 once per call.

**Phase 3-F-1 (2026-07-04):** direct ``_spm_induction_vb_optim`` call (no ``_vb_mod`` patch indirection).

**Phase 3-F-3 (2026-07-04):** EFE recursion memo â€” key ``(m, t+1, k, fi, Qp boundary)``; per top-level call dict.

**Phase 3-F-4 (2026-07-04):** runtime rank dispatch for policy-loop ``spm_dot`` â€” explicit
``len(qj)`` / matching-dim paths; ``spm_dot`` fallback (not 2g-e2 generic wrapper).

**Phase 4-I-4 (2026-07-04):** pass ``VbWorkspace`` into induction; sync ``ws.Q`` after VBX.
**Phase 5-R-1b (2026-07-05):** belief writes via ``ws_assign_q_belief_slot`` (slot replace); compact ``ws`` reads.

**Phase 5-R-2 r1 (2026-07-05):** ``_ForwardsRunCtx`` + per-model ``_ForwardsModelStatic`` (hoist
``A``/``C``/``K``/``W``/``B``/``I``/``H`` tensors across EFE recursion); EFE memo key ``(m,t,k,fi)`` only.

**Phase 5-C-arena (2026-07-05):** ``O`` via ``ws``; ``_ForwardsDriver`` explicit ``t`` stack for EFE subcalls.

**Phase 6-C-2 (2026-07-05):** policy-loop ``spm_dot`` â†’ ``vb_contract_optim`` (removed ``nq<=3`` cap).

**ENDGAME-1 tranche 1 (2026-07-06):** fix missing ``spm_softmax`` import on EFE path.

**ENDGAME-1 tranche 2 (2026-07-06):** ``vb_policy_engine_optim.policy_engine_step`` â€” unified VBX+induction+``G``; ``B_fk_stacked`` hoisted in model static.

Gate: ``--vb-optim-tier3f`` during dev.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM import vb_primitives_optim as _prim
from python_src.spm_cross import spm_cross
from python_src.optimized.toolbox.DEM.vb_contract_optim import (
    forwards_dot_A_qj as _forwards_dot_A_qj,
    forwards_dot_R_qcells as _forwards_dot_R_qcells,
    forwards_dot_vec_match as _forwards_dot_vec_match,
)
from python_src.toolbox.DEM.spm_MDP_BMR import spm_MDP_BMR
from python_src.optimized.toolbox.DEM.vb_induction_optim import induction_model_static
from python_src.optimized.toolbox.DEM.vb_VBX_optim import spm_VBX_optim as spm_VBX
from python_src.optimized.toolbox.DEM.vb_induction_optim import _spm_induction_vb_optim
from python_src.optimized.toolbox.DEM.vb_workspace_optim import (
    VbWorkspace,
    ws_assign_o_slot,
    ws_assign_q_belief_slot,
    ws_q_vbx_writable_slot,
    ws_q_zero_inactive_tail,
    ws_o_row_at_t,
    ws_q_cell,
    ws_q_compact_column,
    ws_q_row_at_t,
)
from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_index import spm_index
from python_src.toolbox.DEM.spm_parents import spm_parents

_EXP_NEG8 = np.exp(-8.0)


@dataclass
class _ForwardsModelStatic:
    """Per-model tensors and id lists â€” invariant across ``t`` within one VB run."""

    nf: int
    nk: int
    id_fp_list: list[int]
    id_fu_list: list[int]
    id_iH_list: list[int]
    id_iI_list: list[int]
    a_f64: list[np.ndarray | None]
    c_f64: list[np.ndarray | None]
    k_f64: list[np.ndarray | None]
    w_f64: list[np.ndarray | None]
    log_hf: dict[int, np.ndarray]
    B_fk: dict[int, list[np.ndarray]]
    B_fk_stacked: dict[int, np.ndarray]
    B_fp0: dict[int, np.ndarray]
    I_fk: dict[int, list[np.ndarray]]
    ge_set: set[int] | None
    ind_static: Any


@dataclass
class _ForwardsDriver:
    """Explicit ``t`` stack for EFE ``t+1`` subcalls (**5-C-arena**)."""

    t_stack: list[int] = field(default_factory=list)


@dataclass
class _ForwardsRunCtx:
    """Shared state for one top-level ``spm_forwards`` invocation (incl. EFE recursion)."""

    memo: dict[tuple[Any, ...], np.ndarray] = field(default_factory=dict)
    static_by_mi: dict[int, _ForwardsModelStatic] = field(default_factory=dict)
    driver: _ForwardsDriver = field(default_factory=_ForwardsDriver)
    induction_cache: dict[tuple[Any, ...], tuple[Any, Any]] = field(default_factory=dict)


def _forwards_efe_subcall_g(
    _run_ctx: _ForwardsRunCtx,
    *,
    use_ws: bool,
    ws: VbWorkspace | None,
    ws_m: int | None,
    bundle: dict[str, Any] | None,
    O: list[Any],
    P: list[Any],
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    t_next: int,
    T: int,
    N: int,
    m: int,
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None,
) -> np.ndarray:
    """
    EFE ``t+1`` subcall â€” invoke ``_forwards_compute`` directly (not ``_forwards_ws`` re-entry).
    """
    driver = _run_ctx.driver
    driver.t_stack.append(int(t_next))
    try:
        g_out, _, _, _, _ = _forwards_compute(
            O,
            P,
            A,
            B,
            C,
            H,
            K,
            W,
            I,
            int(t_next),
            T,
            N,
            m,
            id_list,
            pA,
            qa,
            _run_ctx,
            ws=ws,
            ws_m=ws_m,
            bundle=bundle,
            use_ws=use_ws,
        )
        return np.asarray(g_out, dtype=np.float64)
    finally:
        driver.t_stack.pop()


def _forwards_model_static(
    mi: int,
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    idm: dict[str, Any],
) -> _ForwardsModelStatic:
    B_slice = B[mi]
    H_slice = H[mi]
    nf = len(B_slice)
    nk = len(B_slice[0])

    id_fp = np.asarray(idm.get("fp", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_fu = np.asarray(idm.get("fu", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_iH = np.asarray(idm.get("iH", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_iI = np.asarray(idm.get("iI", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    id_fp_list = [int(x) for x in id_fp.tolist()]
    id_fu_list = [int(x) for x in id_fu.tolist()]
    id_iH_list = [int(x) for x in id_iH.tolist()]
    id_iI_list = [int(x) for x in id_iI.tolist()]

    log_hf: dict[int, np.ndarray] = {}
    for f in id_iH_list:
        fi = int(f) - 1
        Hf = np.asarray(H_slice[fi], dtype=np.float64).reshape(-1, 1, order="F")
        log_hf[fi] = _prim._spm_log(Hf)

    B_fk: dict[int, list[np.ndarray]] = {}
    for f in id_fu_list:
        fi = int(f) - 1
        B_fk[fi] = [np.asarray(B_slice[fi][k], dtype=np.float64) for k in range(nk)]

    I_fk: dict[int, list[np.ndarray]] = {}
    for f in id_iI_list:
        fi = int(f) - 1
        I_fk[fi] = [np.asarray(I[mi][fi][k], dtype=np.float64) for k in range(nk)]

    B_fk_stacked: dict[int, np.ndarray] = {}
    for f in id_fu_list:
        fi = int(f) - 1
        B_fk_stacked[fi] = np.stack(B_fk[fi], axis=0)

    ng_a = len(A[mi])
    a_f64: list[np.ndarray | None] = [None] * ng_a
    c_f64: list[np.ndarray | None] = [None] * len(C[mi])
    k_f64: list[np.ndarray | None] = [None] * len(K[mi])
    w_f64: list[np.ndarray | None] = [None] * len(W[mi])
    for gi in range(ng_a):
        ag = A[mi][gi]
        if not callable(ag) and _prim._numel(ag) > 0:
            a_f64[gi] = np.asarray(ag, dtype=np.float64, order="F")
    for gi in range(len(C[mi])):
        cg = C[mi][gi]
        if _prim._numel(cg) > 0:
            c_f64[gi] = np.asarray(cg, dtype=np.float64, order="F")
    for gi in range(len(K[mi])):
        kg = K[mi][gi]
        if _prim._numel(kg) > 0:
            k_f64[gi] = np.asarray(kg, dtype=np.float64, order="F")
    for gi in range(len(W[mi])):
        wg = W[mi][gi]
        if _prim._numel(wg) > 0:
            w_f64[gi] = np.asarray(wg, dtype=np.float64, order="F")

    ge_set: set[int] | None = None
    if "ge" in idm:
        ge_set = set(int(x) for x in np.asarray(idm["ge"], dtype=np.int64).ravel().tolist())

    B_fp0: dict[int, np.ndarray] = {}
    for f in id_fp_list:
        fi = int(f) - 1
        B_fp0[fi] = np.asarray(B_slice[fi][0], dtype=np.float64)

    ind_static = induction_model_static(B_slice, H_slice, idm, nk)

    return _ForwardsModelStatic(
        nf=nf,
        nk=nk,
        id_fp_list=id_fp_list,
        id_fu_list=id_fu_list,
        id_iH_list=id_iH_list,
        id_iI_list=id_iI_list,
        a_f64=a_f64,
        c_f64=c_f64,
        k_f64=k_f64,
        w_f64=w_f64,
        log_hf=log_hf,
        B_fk=B_fk,
        B_fk_stacked=B_fk_stacked,
        B_fp0=B_fp0,
        I_fk=I_fk,
        ge_set=ge_set,
        ind_static=ind_static,
    )


def _efe_memo_key(
    m: int,
    t_next: int,
    k: int,
    fi: np.ndarray,
) -> tuple[Any, ...]:
    """Cache key for recursive EFE subproblems â€” ``fi`` fixes hidden-state combo at ``t+1``."""
    return (int(m), int(t_next), int(k), tuple(int(x) for x in fi.tolist()))


def _fwd_col_vec(
    ws: VbWorkspace | None,
    ws_m: int | None,
    P: list[Any],
    mi: int,
    f: int,
    t_col: int,
    *,
    use_ws: bool,
    bundle: dict[str, Any] | None = None,
) -> np.ndarray:
    if use_ws:
        assert ws is not None and ws_m is not None
        return ws_q_compact_column(ws, ws_m, f, t_col, None)
    return np.asarray(P[mi][f][t_col], dtype=np.float64).reshape(-1, order="F")


def _fwd_col_mat(
    ws: VbWorkspace | None,
    ws_m: int | None,
    P: list[Any],
    mi: int,
    f: int,
    t_col: int,
    *,
    use_ws: bool,
    bundle: dict[str, Any] | None = None,
) -> np.ndarray:
    return _fwd_col_vec(
        ws, ws_m, P, mi, f, t_col, use_ws=use_ws, bundle=bundle
    ).reshape(-1, 1, order="F")


def _fwd_p_row(
    P: list[Any],
    mi: int,
    nf: int,
    t_col: int,
) -> list[Any]:
    """VBX input row â€” legacy bundle slots (``.m`` aliasing); unchanged from pre-4-F-1."""
    return [P[mi][f][t_col] for f in range(nf)]


def _fwd_belief_row_at_t(
    ws: VbWorkspace | None,
    ws_m: int | None,
    bundle: dict[str, Any] | None,
    P: list[Any],
    mi: int,
    nf: int,
    t_col: int,
    *,
    use_ws: bool,
) -> list[Any]:
    """VBX ``P(m,:,t)`` row â€” dense ``ws.Q`` when on workspace path."""
    if use_ws and ws is not None and ws_m is not None and bundle is not None:
        return ws_q_row_at_t(ws, ws_m, t_col, nf, bundle)
    return _fwd_p_row(P, mi, nf, t_col)


def _induction_cached(
    run_ctx: _ForwardsRunCtx,
    mi: int,
    t: int,
    horizon: int,
    P_now: list[Any] | None,
    B_slice: list[Any],
    H_slice: list[Any],
    idm: dict[str, Any],
    *,
    ws: VbWorkspace | None,
    ws_m: int | None,
    ws_t_col: int | None,
    nf: int = 0,
    ind_static: Any = None,
) -> tuple[Any, Any]:
    """Induction with memo — **ENDGAME-1 t3** ws-native cache key skips ``P_now`` list build."""
    key_parts: list[Any] = [int(mi), int(t), int(horizon)]
    if ws is not None and ws_m is not None and ws_t_col is not None:
        for f in range(int(nf)):
            key_parts.append(ws_q_compact_column(ws, ws_m, f, ws_t_col, None).tobytes())
        q_pass: list[Any] = []
    else:
        if P_now is None:
            raise ValueError("_induction_cached: P_now required when ws path unavailable")
        for col in P_now:
            key_parts.append(np.asarray(col, dtype=np.float64).ravel().tobytes())
        q_pass = P_now
    key = tuple(key_parts)
    hit = run_ctx.induction_cache.get(key)
    if hit is not None:
        return hit
    R, r = _spm_induction_vb_optim(
        B_slice,
        H_slice,
        q_pass,
        int(horizon),
        idm,
        ws=ws,
        ws_m=ws_m,
        ws_t_col=ws_t_col,
        ind_static=ind_static,
    )
    run_ctx.induction_cache[key] = (R, r)
    return R, r


def _vbx_belief_row_ws_writable(
    ws: VbWorkspace,
    ws_m: int,
    t_col: int,
    nf: int,
    bundle: dict[str, Any],
) -> list[np.ndarray]:
    """VBX hidden-state row â€” writable ``ws.Q`` views for in-place update (**6-B r5**)."""
    return [ws_q_vbx_writable_slot(ws, ws_m, f, t_col, None) for f in range(nf)]


def _fwd_write_belief_col(
    ws: VbWorkspace | None,
    ws_m: int | None,
    bundle: dict[str, Any] | None,
    P: list[Any],
    mi: int,
    f: int,
    t_col: int,
    col: Any,
    *,
    use_ws: bool,
) -> None:
    if use_ws:
        assert ws is not None and ws_m is not None
        ws_assign_q_belief_slot(ws, None, ws_m, f, t_col, col)
    else:
        P[mi][f][t_col] = col


def _forwards_ws(
    ws: VbWorkspace,
    ws_m: int,
    bundle: dict[str, Any],
    O: list[Any],
    P: list[Any],
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    t: int,
    T: int,
    N: int,
    m: int,
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None = None,
    _efe_memo: dict[tuple[Any, ...], np.ndarray] | None = None,
    _run_ctx: _ForwardsRunCtx | None = None,
) -> tuple[np.ndarray, Any, float, list[Any], dict[int, Any]]:
    """**4-F-1** â€” ``spm_forwards`` on ``VbWorkspace`` path beliefs (``ws.Q`` â‰¡ bundle ``Q``)."""
    if _run_ctx is None:
        if _efe_memo is not None:
            _run_ctx = _ForwardsRunCtx(memo=_efe_memo)
        else:
            _run_ctx = _ForwardsRunCtx()
    return _forwards_compute(
        O,
        P,
        A,
        B,
        C,
        H,
        K,
        W,
        I,
        t,
        T,
        N,
        m,
        id_list,
        pA,
        qa,
        _run_ctx,
        ws=ws,
        ws_m=ws_m,
        bundle=bundle,
        use_ws=True,
    )


def spm_forwards_optim(
    O: list[Any],
    P: list[Any],
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    t: int,
    T: int,
    N: int,
    m: int,
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None = None,
    _efe_memo: dict[tuple[Any, ...], np.ndarray] | None = None,
    *,
    ws: VbWorkspace | None = None,
    ws_m: int | None = None,
    bundle: dict[str, Any] | None = None,
    _run_ctx: _ForwardsRunCtx | None = None,
) -> tuple[np.ndarray, Any, float, list[Any], dict[int, Any]]:
    """Patch-table entry â€” delegates to ``_forwards_ws`` when ``ws`` + ``bundle`` supplied."""
    use_ws = ws is not None and ws_m is not None and bundle is not None
    if _run_ctx is None:
        if _efe_memo is not None:
            _run_ctx = _ForwardsRunCtx(memo=_efe_memo)
        else:
            _run_ctx = _ForwardsRunCtx()
    return _forwards_compute(
        O,
        P,
        A,
        B,
        C,
        H,
        K,
        W,
        I,
        t,
        T,
        N,
        m,
        id_list,
        pA,
        qa,
        _run_ctx,
        ws=ws,
        ws_m=ws_m,
        bundle=bundle,
        use_ws=use_ws,
    )


def _forwards_compute(
    O: list[Any],
    P: list[Any],
    A: list[Any],
    B: list[Any],
    C: list[Any],
    H: list[Any],
    K: list[Any],
    W: list[Any],
    I: list[Any],
    t: int,
    T: int,
    N: int,
    m: int,
    id_list: list[Any],
    pA: list[Any],
    qa: Any | None,
    _run_ctx: _ForwardsRunCtx,
    *,
    ws: VbWorkspace | None,
    ws_m: int | None,
    bundle: dict[str, Any] | None,
    use_ws: bool,
) -> tuple[np.ndarray, Any, float, list[Any], dict[int, Any]]:
    """Optim lane â€” delegates hot body to **ENDGAME-1** ``policy_engine_step``."""
    from python_src.optimized.toolbox.DEM.vb_policy_engine_optim import policy_engine_step

    mi = int(m) - 1
    idm = id_list[mi]
    if mi not in _run_ctx.static_by_mi:
        _run_ctx.static_by_mi[mi] = _forwards_model_static(
            mi, A, B, C, H, K, W, I, idm
        )
    mstat = _run_ctx.static_by_mi[mi]
    return policy_engine_step(
        O,
        P,
        A,
        B,
        C,
        H,
        K,
        W,
        I,
        t,
        T,
        N,
        m,
        mi,
        idm,
        id_list,
        pA,
        qa,
        _run_ctx,
        mstat,
        ws=ws,
        ws_m=ws_m,
        bundle=bundle,
        use_ws=use_ws,
    )
