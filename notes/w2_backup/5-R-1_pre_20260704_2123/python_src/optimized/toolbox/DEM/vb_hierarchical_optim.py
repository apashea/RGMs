"""W2 Tier 1 — hierarchical 12E/12F cluster (``_vb_hierarchical_subordinate_outcomes``).

**MATLAB anchor:** ``spm_MDP_VB_XXX.m`` lines 1019–1259 — ``mdp = MDP(m).MDP(1)`` (alias),
in-place field updates, ``mdp.Q = MDP(m).Q`` (shared), nested ``spm_MDP_VB_XXX(mdp)``,
``MDP(m).Q = mdp.Q``, ``MDP(m).MDP = mdp``.

See ``XXX_optim.md``. **No** full-tree ``deepcopy`` on child extract (fidelity transliteration
over-copies vs ``.m``).

Gate during bring-up: **``3f`` only**.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np
from scipy import sparse

from python_src.optimized.toolbox.DEM import vb_hierarchical_field_optim as _hf
from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst
from python_src.optimized.toolbox.DEM import vb_primitives_optim as _prim
from python_src.spm_dot import spm_dot
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size
from python_src.toolbox.DEM.spm_VBX import _a_colon_s_coerce_likelihood_
from python_src.toolbox.DEM.spm_parents import spm_parents


def _vb_alias_child_from_mdp_field(mdp_field: Any) -> dict[str, Any]:
    """
    **P0 — MATLAB line 1019:** ``mdp = MDP(m).MDP(1)`` — alias nested child, no clone.
    """
    if isinstance(mdp_field, list) and len(mdp_field) > 0:
        child = mdp_field[0]
    elif isinstance(mdp_field, np.ndarray) and mdp_field.dtype == object and mdp_field.size > 0:
        child = mdp_field.ravel(order="F")[0]
    elif isinstance(mdp_field, dict):
        child = mdp_field
    else:
        raise NotImplementedError("hierarchical MDP.MDP layout not yet supported")
    if not isinstance(child, dict):
        raise NotImplementedError("hierarchical MDP.MDP child must be a dict-like MDP")
    return child


def _vb_q_copy_leaf(value: Any) -> Any:
    """Copy one Q leaf for append paths — not a whole ``qrec`` tree."""
    if isinstance(value, np.ndarray):
        return np.asarray(value, dtype=np.float64).copy()
    if isinstance(value, list):
        return [_vb_q_copy_leaf(x) for x in value]
    if isinstance(value, tuple):
        return tuple(_vb_q_copy_leaf(x) for x in value)
    import copy

    return copy.deepcopy(value)


def _vb_hierarchical_q_concat_optim(existing: Any, new_value: Any) -> Any:
    """Append Q segments without cloning the existing side of the concat."""
    if existing is None:
        return _vb_q_copy_leaf(new_value)
    if isinstance(existing, list) and isinstance(new_value, list):
        return list(existing) + [_vb_q_copy_leaf(x) for x in new_value]
    try:
        ea = np.asarray(existing, dtype=np.float64)
        na = np.asarray(new_value, dtype=np.float64)
        if ea.ndim == 1:
            ea = ea.reshape(-1, 1)
        if na.ndim == 1:
            na = na.reshape(-1, 1)
        if ea.size == 0:
            return na.copy()
        if na.size == 0:
            return ea.copy()
        return np.hstack([ea, na])
    except Exception:
        if isinstance(existing, list):
            return list(existing) + [_vb_q_copy_leaf(new_value)]
        if isinstance(new_value, list):
            return [_vb_q_copy_leaf(existing)] + [_vb_q_copy_leaf(x) for x in new_value]
        return [_vb_q_copy_leaf(existing), _vb_q_copy_leaf(new_value)]


def _vb_hierarchical_q_O_ng_t_hstack_optim(
    old: Any,
    new_rows: list[list[np.ndarray]],
) -> list[list[np.ndarray]]:
    """Optim ``Q.O`` row append — array copies only."""
    if old is None:
        return [[np.asarray(x, dtype=np.float64).copy() for x in row] for row in new_rows]
    if isinstance(old, np.ndarray):
        ng_guess = len(new_rows)
        old_rows = _hf._vb_hierarchical_O_field_to_ng_t_rows(
            old,
            t_child=int(old.shape[1]) if old.ndim >= 2 else 1,
            ng=ng_guess,
        )
        return _vb_hierarchical_q_O_ng_t_hstack_optim(old_rows, new_rows)
    if isinstance(old, list) and old and _hf._vb_hierarchical_q_O_is_ng_t_rows(old):
        ng = max(len(old), len(new_rows))
        out: list[list[np.ndarray]] = []
        for g in range(ng):
            row_old = list(old[g]) if g < len(old) else []
            row_new = list(new_rows[g]) if g < len(new_rows) else []
            out.append(
                [np.asarray(x, dtype=np.float64).copy() for x in row_old]
                + [np.asarray(x, dtype=np.float64).copy() for x in row_new]
            )
        return out
    return [[np.asarray(x, dtype=np.float64).copy() for x in row] for row in new_rows]


def _vb_hierarchical_q_append_level_optim(
    qv: list[Any],
    li: int,
    child_upd: dict[str, Any],
    ck: str,
    t_child: int,
) -> None:
    """In-place append into ``qrec[qk]{li}`` — fidelity field helpers, optim concat/hstack."""
    if ck not in child_upd:
        return
    while len(qv) <= li:
        qv.append(None)
    if ck == "O":
        ng_m = len(child_upd.get("A", [])) if isinstance(child_upd.get("A"), list) else 0
        no = _hf._vb_no_list_from_mdp(child_upd)
        new_rows = _hf._vb_hierarchical_O_field_to_ng_t_rows(
            child_upd[ck],
            t_child,
            ng=ng_m,
            no=no,
        )
        if not new_rows or not new_rows[0]:
            return
        if qv[li] is None:
            qv[li] = new_rows
        else:
            qv[li] = _vb_hierarchical_q_O_ng_t_hstack_optim(qv[li], new_rows)
        return
    if ck in ("P", "X"):
        new_level = _hf._vb_hierarchical_q_field_to_cell_row(child_upd[ck], t_child=t_child, kind=ck)
        if qv[li] is None:
            qv[li] = new_level
        elif isinstance(qv[li], list) and new_level and isinstance(qv[li][0], np.ndarray):
            merged: list[Any] = []
            for f in range(len(new_level)):
                old_f = np.asarray(qv[li][f], dtype=np.float64) if f < len(qv[li]) else qv[li][-1]
                new_f = np.asarray(new_level[f], dtype=np.float64)
                merged.append(
                    np.asfortranarray(np.hstack([old_f, new_f]))
                    if old_f.size and new_f.size
                    else (new_f if new_f.size else old_f)
                )
            qv[li] = merged
        else:
            qv[li] = _vb_hierarchical_q_concat_optim(qv[li], new_level)
        return
    if ck in ("s", "u", "o"):
        new_m = np.asarray(child_upd[ck], dtype=np.float64)
        if new_m.ndim == 1:
            new_m = new_m.reshape(-1, 1, order="F")
        elif new_m.ndim == 2 and int(new_m.shape[1]) > t_child:
            new_m = np.asfortranarray(new_m[:, :t_child].copy())
        if qv[li] is None:
            qv[li] = np.asfortranarray(new_m.copy())
            return
        old = qv[li]
        if isinstance(old, list):
            if old and _hf._vb_hierarchical_q_O_is_ng_t_rows(old):
                old_m = _hf._vb_hierarchical_q_O_level_to_matrix(
                    old,
                    t_child=max(len(old[0]) for row in old if row),
                    ng=len(old),
                    no=[1] * len(old),
                )
            else:
                mats = [np.asarray(x, dtype=np.float64) for x in old if x is not None]
                old_m = (
                    np.hstack(mats)
                    if mats
                    else np.zeros((new_m.shape[0], 0), dtype=np.float64, order="F")
                )
        else:
            old_m = np.asarray(old, dtype=np.float64)
        qv[li] = np.asfortranarray(np.hstack([old_m, new_m]))
        return
    if ck in ("Y", "j", "i"):
        new_nested = _hf._vb_hierarchical_field_to_ot_nested(child_upd[ck], t_child=t_child)
        if qv[li] is None:
            qv[li] = new_nested
        else:
            qv[li] = _hf._vb_hierarchical_q_ot_nested_hstack(qv[li], new_nested)
        return
    new_cells = _hf._vb_hierarchical_q_field_to_cell_row(child_upd[ck], t_child=t_child, kind=ck)
    if qv[li] is None:
        qv[li] = new_cells
    elif isinstance(qv[li], list):
        qv[li] = list(qv[li]) + list(new_cells)
    else:
        qv[li] = _vb_hierarchical_q_concat_optim(qv[li], new_cells)


def _vb_hierarchical_update_parent_Q_from_child_optim(
    parent: dict[str, Any],
    child_upd: dict[str, Any],
) -> None:
    """
    **MATLAB lines 1226–1255:** append into ``mdp.Q`` at level ``L``; ``MDP(m).Q = mdp.Q``.
    """
    parent_q = parent.get("Q")
    if "Q" in child_upd and isinstance(child_upd.get("Q"), dict):
        qrec = child_upd["Q"]
    elif isinstance(parent_q, dict):
        qrec = parent_q
    else:
        qrec = {}
    if not isinstance(qrec, dict):
        parent["Q"] = qrec
        return
    L = max(1, int(np.asarray(child_upd.get("L", 1)).ravel()[0]))
    li = L - 1
    t_child = int(np.asarray(child_upd.get("T", 1)).ravel()[0])

    if "a" in child_upd:
        qa = qrec.get("a", [])
        if not isinstance(qa, list):
            qa = list(np.asarray(qa, dtype=object).ravel(order="F"))
        while len(qa) <= li:
            qa.append(None)
        qa[li] = _vb_q_copy_leaf(child_upd["a"])
        qrec["a"] = qa

    mapping = {
        "s": "s",
        "u": "u",
        "P": "P",
        "X": "X",
        "Y": "Y",
        "O": "O",
        "o": "o",
        "j": "j",
        "E": "F",
    }

    try:
        for qk, ck in mapping.items():
            qv = qrec.get(qk, [])
            if not isinstance(qv, list):
                qv = list(np.asarray(qv, dtype=object).ravel(order="F"))
            _vb_hierarchical_q_append_level_optim(qv, li, child_upd, ck, t_child)
            qrec[qk] = qv

        f_old = float(np.sum(np.asarray(qrec.get("F", 0.0), dtype=np.float64)))
        f_new = float(np.sum(np.asarray(child_upd.get("F", 0.0), dtype=np.float64)))
        qrec["F"] = f_old + f_new
    except Exception:
        for qk, ck in mapping.items():
            qv = qrec.get(qk, [])
            if not isinstance(qv, list):
                qv = list(np.asarray(qv, dtype=object).ravel(order="F"))
            try:
                _vb_hierarchical_q_append_level_optim(qv, li, child_upd, ck, t_child)
            except Exception:
                if ck in child_upd:
                    while len(qv) <= li:
                        qv.append(None)
                    qv[li] = _vb_q_copy_leaf(child_upd[ck])
            qrec[qk] = qv
        qrec["F"] = float(np.sum(np.asarray(child_upd.get("F", 0.0), dtype=np.float64)))

    parent["Q"] = qrec
    child_upd["Q"] = qrec


def vb_hierarchical_subordinate_outcomes_optim(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
    recurse_partial: bool,
    *,
    reuse_matlab_draws: bool = False,
) -> None:
    """Optim lane — ``.m`` 1011–1259 hierarchical subordinate outcomes."""
    from python_src.optimized.toolbox.DEM.vb_entry_optim import run_child_vb

    _spm_norm = _prim._spm_norm
    _spm_multiply = _prim._spm_multiply
    _spm_is_process = _prim._spm_is_process
    _spm_action = _prim._spm_action
    _vb_spm_sample_column = _prim._vb_spm_sample_column
    _b_nu_third_dim = _prim._b_nu_third_dim
    _gb_predicted_state_qs = _prim._gb_predicted_state_qs
    _default_options_vb = _prim._default_options_vb
    _vb_hierarchical_apply_S_as_O_if_present = _hf._vb_hierarchical_apply_S_as_O_if_present
    _vb_monitoring_active = _inst._vb_monitoring_active
    _vb_monitor_snapshot = _inst._vb_monitor_snapshot
    _vb_timing_add_12e = _inst._vb_timing_add_12e
    _vb_dump_active = _inst._vb_dump_active
    _entry12_record_phase = _inst._entry12_record_phase
    _vb_o_cell_to_column = _prim._vb_o_cell_to_column

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    O_shell = bundle["O"]
    t_int = int(bundle["T"])

    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        parent = models[mi]
        if "MDP" not in parent or parent["MDP"] is None:
            continue

        # MATLAB 1019: mdp = MDP(m).MDP(1) — alias, no clone
        child = _vb_alias_child_from_mdp_field(parent["MDP"])

        nf, ns, nu, _, _ = spm_MDP_size(child)
        nf_i = int(nf)
        ns_v = np.asarray(ns, dtype=np.int64).reshape(-1)
        nu_v = np.asarray(nu, dtype=np.int64).reshape(-1)

        if "B" not in child:
            child["B"] = []
            for f in range(nf_i):
                child["B"].append(_spm_norm(np.asarray(child["b"][f], dtype=np.float64)))
        if "D" not in child:
            child["D"] = []
            for f in range(nf_i):
                child["D"].append(_spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64)))
        if "E" not in child:
            child["E"] = []
            for f in range(nf_i):
                child["E"].append(_spm_norm(np.ones((int(nu_v[f]), 1), dtype=np.float64)))

        for f in range(nf_i):
            if "P" in child:
                T_child = int(np.asarray(child.get("T", 1)).reshape(-1)[0])
                U_raw = child.get("U", np.zeros((1, nf_i)))
                if sparse.issparse(U_raw):
                    U_raw = U_raw.toarray()
                U_child = np.asarray(U_raw, dtype=np.float64)
                if U_child.ndim == 1:
                    U_child = U_child.reshape(1, -1)
                has_u = bool(f < U_child.shape[1] and np.any(U_child[:, f]))

                if T_child > 1:
                    if has_u:
                        child["E"][f] = np.asarray(child["P"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                        ps = np.asarray(child["X"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                        pu = np.asarray(child["E"][f], dtype=np.float64).reshape(-1, 1)
                        if pu.size > 1:
                            child["D"][f] = np.asarray(spm_dot(child["B"][f], [pu]), dtype=np.float64) @ ps
                        else:
                            child["D"][f] = np.asarray(child["B"][f], dtype=np.float64) @ ps
                    else:
                        child["E"][f] = _spm_norm(np.ones((int(nu_v[f]), 1), dtype=np.float64))
                        child["D"][f] = _spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64))
                else:
                    if has_u:
                        child["E"][f] = np.asarray(child["P"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                    else:
                        child["E"][f] = _spm_norm(np.ones((int(nu_v[f]), 1), dtype=np.float64))
                    ps = np.asarray(child["X"][f], dtype=np.float64)[:, T_child - 1 : T_child]
                    pu = np.asarray(child["E"][f], dtype=np.float64).reshape(-1, 1)
                    if pu.size > 1:
                        child["D"][f] = np.asarray(spm_dot(child["B"][f], [pu]), dtype=np.float64) @ ps
                    else:
                        child["D"][f] = np.asarray(child["B"][f], dtype=np.float64) @ ps
                    child["D"][f] = _spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64))

            id_child = child.get("id", {})
            idE = id_child.get("E", [])
            if isinstance(idE, (list, tuple)) and f < len(idE):
                for g in np.atleast_1d(np.asarray(idE[f], dtype=np.int64).ravel()).tolist():
                    j = spm_parents(
                        bundle["id"][mi],
                        int(g),
                        [bundle["Q"][mi][ff][t_idx] for ff in range(len(bundle["Q"][mi]))],
                    )[0]
                    j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                    q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr]
                    Ag = _a_colon_s_coerce_likelihood_(bundle["A"][mi][int(g) - 1])
                    po = np.asarray(spm_dot(Ag, q_list), dtype=np.float64).reshape(-1, 1)
                    child["E"][f] = _spm_multiply(child["E"][f], po)

            idD = id_child.get("D", [])
            if isinstance(idD, (list, tuple)) and f < len(idD):
                for g in np.atleast_1d(np.asarray(idD[f], dtype=np.int64).ravel()).tolist():
                    j = spm_parents(
                        bundle["id"][mi],
                        int(g),
                        [bundle["Q"][mi][ff][t_idx] for ff in range(len(bundle["Q"][mi]))],
                    )[0]
                    j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                    q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr]
                    Ag = _a_colon_s_coerce_likelihood_(bundle["A"][mi][int(g) - 1])
                    po = np.asarray(spm_dot(Ag, q_list), dtype=np.float64).reshape(-1, 1)
                    child["D"][f] = _spm_multiply(child["D"][f], po)

        if _spm_is_process(child):
            if "GV" in child:
                t_act = int(np.asarray(child.get("T", 1)).ravel()[0])
                nf_gp = len(child["GB"])
                for key, fill in (("u", 1.0), ("s", 1.0)):
                    if key not in child or child[key] is None:
                        child[key] = np.full((nf_gp, t_act), fill, dtype=np.float64)
                    else:
                        arr = np.asarray(child[key], dtype=np.float64)
                        if arr.ndim == 1:
                            arr = arr.reshape(-1, 1)
                        if arr.shape[0] < nf_gp:
                            arr = np.vstack(
                                [arr, np.full((nf_gp - arr.shape[0], arr.shape[1]), fill, dtype=np.float64)]
                            )
                        if arr.shape[1] < t_act:
                            arr = np.hstack(
                                [arr, np.full((arr.shape[0], t_act - arr.shape[1]), fill, dtype=np.float64)]
                            )
                        child[key] = arr

                child = _spm_action(child, child["A"], child["D"], t_act)

                u_full = np.asarray(child["u"], dtype=np.float64)
                s_full = np.asarray(child["s"], dtype=np.float64)
                if u_full.ndim == 1:
                    u_full = u_full.reshape(-1, 1)
                if s_full.ndim == 1:
                    s_full = s_full.reshape(-1, 1)
                child["u"] = u_full[:, t_act - 1 : t_act].copy()
                child["s"] = s_full[:, t_act - 1 : t_act].copy()

                GU = np.asarray(child["GU"], dtype=np.float64).ravel()
                nfu = int(child["u"].shape[0])
                if "GE" not in child or not isinstance(child.get("GE"), (list, tuple)):
                    child["GE"] = [None] * nfu
                ge_list = child["GE"]
                if len(ge_list) < nfu:
                    ge_list = list(ge_list) + [None] * (nfu - len(ge_list))
                    child["GE"] = ge_list
                for f in range(nfu):
                    if f < GU.size and float(GU[f]) != 0.0:
                        nu = _b_nu_third_dim(child["GB"][f])
                        Ge = np.zeros((nu, 1), dtype=np.float64, order="F")
                        uf = int(round(float(child["u"][f, 0])))
                        if 1 <= uf <= nu:
                            Ge[uf - 1, 0] = 1.0
                        ge_list[f] = Ge

                    sf = int(round(float(child["s"][f, 0])))
                    uf2 = int(round(float(child["u"][f, 0])))
                    child["GD"][f] = _gb_predicted_state_qs(child["GB"][f], sf, uf2)
                    child["s"][f, 0] = float(_vb_spm_sample_column(child["GD"][f]))
                for f in range(nfu):
                    if ge_list[f] is None:
                        ge_list[f] = np.zeros((1, 0), dtype=np.float64, order="F")
        else:
            child["u"] = np.ones((nf_i, 1), dtype=np.float64)
            child["s"] = np.ones((nf_i, 1), dtype=np.float64)
            for f in range(nf_i):
                child["u"][f, 0] = float(_vb_spm_sample_column(child["E"][f]))
                child["s"][f, 0] = float(_vb_spm_sample_column(child["D"][f]))

        # MATLAB 1163–1165: mdp.Q = MDP(m).Q — shared reference
        if "Q" in parent:
            child["Q"] = parent["Q"]

        child.pop("O", None)
        child.pop("o", None)
        _vb_hierarchical_apply_S_as_O_if_present(child)

        t_1based = t_idx + 1
        t_last = t_int
        if _vb_monitoring_active() and t_1based in (1, t_last):
            _vb_monitor_snapshot("12E", child, mi + 1, t_1based, "before")
        child_opts = _default_options_vb()
        if recurse_partial:
            child_opts["_rgms_partial_ok"] = 1
        t_child = time.perf_counter()
        # MATLAB 1203: mdp = spm_MDP_VB_XXX(mdp) — 4-N-1 child kernel (no public re-entry)
        child_upd = run_child_vb(
            child,
            child_opts,
            reuse_matlab_draws=reuse_matlab_draws,
        )
        if _vb_monitoring_active() and t_1based in (1, t_last):
            _vb_monitor_snapshot("12E", child_upd, mi + 1, t_1based, "after")
        _vb_timing_add_12e(time.perf_counter() - t_child)

        id_child = child_upd.get("id", {})
        no_arr = np.asarray(bundle["No"], dtype=np.int64)
        idD = id_child.get("D", [])
        for f in range(len(idD)):
            for g in np.atleast_1d(np.asarray(idD[f], dtype=np.int64).ravel()).tolist():
                gi = int(g) - 1
                no_g = int(no_arr[mi, gi]) if no_arr.ndim >= 2 and gi < no_arr.shape[1] else 1
                O_shell[mi][gi][t_idx] = _vb_o_cell_to_column(
                    np.asarray(child_upd["X"][f], dtype=np.float64)[:, 0:1],
                    no_g,
                )

        idE = id_child.get("E", [])
        for f in range(len(idE)):
            for g in np.atleast_1d(np.asarray(idE[f], dtype=np.int64).ravel()).tolist():
                gi = int(g) - 1
                no_g = int(no_arr[mi, gi]) if no_arr.ndim >= 2 and gi < no_arr.shape[1] else 1
                Pf = np.asarray(child_upd["P"][f], dtype=np.float64)
                O_shell[mi][gi][t_idx] = _vb_o_cell_to_column(Pf[:, -1:], no_g)

        _vb_hierarchical_update_parent_Q_from_child_optim(parent, child_upd)
        # MATLAB 1259: MDP(m).MDP = mdp
        parent["MDP"] = child_upd
        if _vb_dump_active():
            _entry12_record_phase(mi, t_idx + 1, "post_hierarchical", bundle)
