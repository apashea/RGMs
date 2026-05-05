"""
Variational Bayes active inference (`spm_MDP_VB_XXX.m`).

Pass 1 transliteration in progress: MATLAB source of truth is
``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` (staged from SPM).

Visualization: MATLAB calls ``spm_figure`` in some branches — **out of scope** for
this port; do not add ``spm_figure`` (or related UI) in Python.

Local helpers at the end of the MATLAB file (`spm_sample`, `spm_norm`, …) are kept
as private Python functions in this module.
"""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
from scipy import sparse
from scipy import stats
from scipy.special import digamma

from matlab_compat import full as mfull, matlab_ndims
from python_src.spm_combinations import spm_combinations
from python_src.spm_cross import spm_cross
from python_src.spm_dot import spm_dot
from python_src.spm_Gcdf import spm_Gcdf
from python_src.spm_zeros import spm_zeros
from python_src.spm_KL_dir import spm_KL_dir
from python_src.spm_MDP_MI import spm_MDP_MI
from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_backwards import spm_backwards
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from python_src.toolbox.DEM.spm_forwards import spm_children, spm_forwards
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size
from python_src.toolbox.DEM.spm_parents import spm_parents


def _spm_sample(p: Any) -> int:
    """
    File-local ``spm_sample`` from ``spm_MDP_VB_XXX.m`` (lines ~2613–2621).

    Mirrors ``spm_MDP_generate._spm_sample`` and MATLAB’s implementation in both
    files: logical masks use ``find`` + ``randperm`` semantics; numeric columns use
    ``cumsum`` + one ``rand`` (see ``notes/andrew Python Matlab Translation Issues.md``,
    RNG subsection).
    """
    if isinstance(p, np.ndarray) and p.dtype == bool:
        flat = np.flatnonzero(p.ravel(order="F"))
        k = int(flat.size)
        if k == 0:
            raise ValueError("spm_sample: empty logical mask")
        if k == 1:
            return int(flat[0] + 1)
        r1 = float(np.random.rand())
        if k <= 4:
            float(np.random.rand())
        pos = int(np.floor(r1 * k))
        if pos >= k:
            pos = k - 1
        return int(flat[pos] + 1)
    pv = np.asarray(p, dtype=np.float64).ravel(order="F")
    total = float(np.sum(pv))
    if (not np.isfinite(total)) or total <= 0.0 or (not np.all(np.isfinite(pv))):
        n = int(pv.size)
        if n <= 0:
            raise ValueError("spm_sample: empty numeric probability vector")
        # Degenerate / zero-mass (e.g. ``spm_norm`` of all-zero ``GP.E{f}``): uniform over supports.
        pv = np.ones((n,), dtype=np.float64) / float(n)
    cs = np.cumsum(pv)
    r = float(np.random.rand())
    hit = np.flatnonzero(r < cs)
    if hit.size == 0:
        idx = int(pv.size) - 1
    else:
        idx = int(hit[0])
    return idx + 1


def _spm_log(a: Any) -> np.ndarray | Any:
    """Local ``spm_log`` (~2624–2631)."""
    if isinstance(a, np.ndarray) and a.dtype == bool:
        return (-32.0 * (~a)).astype(np.float64)
    arr = np.asarray(a, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        lx = np.real(np.log(arr.astype(np.complex128)))
    out = np.maximum(lx, -32.0)
    return np.asarray(out, dtype=np.float64)


def _spm_multiply(p: Any, q: Any) -> np.ndarray:
    """
    Local ``spm_multiply`` (~2603–2606): renormalised product of probability distributions.

    MATLAB: ``p = spm_softmax(spm_log(p) + spm_log(q));`` — **not** elementwise ``p.*q`` then normalise.
    Used in hierarchical child ``id.E`` / ``id.D`` empirical prior updates (~1063, ~1071).
    """
    pc = np.asarray(p, dtype=np.float64).reshape(-1, 1, order="F")
    qc = np.asarray(q, dtype=np.float64).reshape(-1, 1, order="F")
    lp = np.asarray(_spm_log(pc), dtype=np.float64)
    lq = np.asarray(_spm_log(qc), dtype=np.float64)
    return np.asarray(spm_softmax(lp + lq), dtype=np.float64)


def _spm_action(
    MDP: dict[str, Any],
    A: list[Any] | Any,
    Q_in: list[Any] | Any,
    t: int,
) -> dict[str, Any]:
    """
    Nested ``spm_action`` from ``spm_MDP_VB_XXX.m`` ~2688–2766.

    ``FORMAT MDP = spm_action(MDP,A,Q,t)`` — explicit control for generative process models.
    Call sites: hierarchical (~1087) passes ``A = mdp.A``, ``Q = mdp.D``, ``t = mdp.T``;
    main generation loop (~816) passes ``A(m,:)``, ``Q(m,:,t)``, ``t - 1`` (mapped here as
    ``bundle['A'][m]``, per-factor ``Q`` at timestep ``t_idx``, fourth arg ``t_idx`` when
    ``t_idx`` is the Python time index matching MATLAB ``t-1``).
    """
    id_m = MDP.get("id")
    if id_m is None:
        id_m = {}
        MDP["id"] = id_m

    id_upper = MDP.get("ID")
    if id_upper is None:
        id_upper = {}
        MDP["ID"] = id_upper

    if "control" not in id_upper:
        a_sizes = id_m.get("A", [])
        n_a = len(a_sizes) if isinstance(a_sizes, (list, tuple)) else int(np.size(np.asarray(a_sizes)))
        id_upper["control"] = [i + 1 for i in range(int(n_a))]

    if "chi" not in MDP:
        MDP["chi"] = 512.0
    chi = float(np.asarray(MDP["chi"], dtype=np.float64).ravel()[0])

    A_list = list(A) if isinstance(A, (list, tuple)) else [A]
    if isinstance(Q_in, np.ndarray) and Q_in.dtype == object:
        Q_list = list(Q_in.ravel(order="F"))
    elif isinstance(Q_in, (list, tuple)):
        Q_list = list(Q_in)
    else:
        Q_list = [Q_in]

    qo: dict[int, np.ndarray] = {}
    for g in id_upper["control"]:
        g_i = int(g)
        j_par, _ = spm_parents(id_m, g_i, Q_list)
        jv = np.atleast_1d(np.asarray(j_par)).ravel().astype(np.int64)
        q_cells = [Q_list[int(jj) - 1] for jj in jv.tolist()]
        qo[g_i] = np.asarray(spm_dot(A_list[g_i - 1], q_cells), dtype=np.float64).reshape(-1, 1)

    GB = MDP["GB"]
    GV = np.asarray(MDP["GV"], dtype=np.float64)
    if GV.ndim == 1:
        GV = GV.reshape(-1, 1)
    Na = int(GV.shape[0])
    Nf = len(GB)
    h = np.any(GV != 0.0, axis=0)
    F = np.zeros((Na, 1), dtype=np.float64)

    t_mat = int(t)
    t_col = t_mat - 1
    u_mat = np.asarray(MDP["u"], dtype=np.float64)
    if u_mat.ndim == 1:
        u_mat = u_mat.reshape(-1, 1)
    s_mat = np.asarray(MDP["s"], dtype=np.float64)
    if s_mat.ndim == 1:
        s_mat = s_mat.reshape(-1, 1)

    if "ff" in id_upper:
        ff_arr = np.atleast_1d(np.asarray(id_upper["ff"], dtype=np.int64)).ravel()
        ff_iter = [int(x) for x in ff_arr.tolist()]
    else:
        ff_iter = list(range(1, Nf + 1))

    for k in range(Na):
        u_work = u_mat[:, t_col].astype(np.float64).copy()
        u_work[h] = GV[k, h]
        qs_list: list[Any] = [None] * Nf
        for f in ff_iter:
            f0 = int(f) - 1
            s_ft = int(round(float(s_mat[f0, t_col])))
            u_f = int(round(float(u_work[f0])))
            Gb = np.asarray(GB[f0], dtype=np.float64)
            qs_list[f0] = Gb[:, s_ft - 1, u_f - 1].reshape(-1, 1)

        F[k, 0] = 0.0
        for g in id_upper["control"]:
            g_i = int(g)
            # MATLAB ~2753 uses ``spm_parents(MDP.ID, ...)``; likelihood indices live on ``id``.
            j_inner, _ = spm_parents(id_m, g_i, qs_list)
            jv2 = np.atleast_1d(np.asarray(j_inner)).ravel().astype(np.int64)
            for f in jv2.tolist():
                f0 = int(f) - 1
                s_ft = int(round(float(s_mat[f0, t_col])))
                u_f = int(round(float(u_work[f0])))
                Gb = np.asarray(GB[f0], dtype=np.float64)
                qs_list[f0] = Gb[:, s_ft - 1, u_f - 1].reshape(-1, 1)
            q_dot = [qs_list[int(jj) - 1] for jj in jv2.tolist()]
            GA_g = np.asarray(MDP["GA"][g_i - 1], dtype=np.float64)
            po = np.asarray(spm_dot(GA_g, q_dot), dtype=np.float64).reshape(-1, 1)
            qog = qo[g_i]
            F[k, 0] += float(np.asarray(qog, dtype=np.float64).ravel() @ np.asarray(_spm_log(po), dtype=np.float64).ravel())

    k_one = int(_spm_sample(np.asarray(spm_softmax(F, chi), dtype=np.float64).reshape(-1, 1)))
    k0 = k_one - 1
    u_out = u_mat.copy()
    u_out[h, t_col] = GV[k0, h]
    MDP["u"] = u_out
    return MDP


def _spm_norm(a: Any) -> Any:
    """Local ``spm_norm`` (~2633–2639): column-normalise stochastic matrix."""
    if sparse.issparse(a):
        a = np.asarray(mfull(a), dtype=np.float64)
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return a
    if a.size == 0 or (a.ndim >= 1 and int(a.shape[0]) == 0):
        return np.asarray(a, dtype=np.float64)
    s = np.sum(a, axis=0, keepdims=True)
    out = np.divide(a, s, out=np.zeros_like(a, dtype=np.float64), where=s != 0)
    out = np.where(np.isnan(out), 1.0 / int(a.shape[0]), out)
    return out


def _spm_wnorm(a: Any) -> np.ndarray | Any:
    """Local ``spm_wnorm`` (~2641–2657)."""
    if sparse.issparse(a):
        a = np.asarray(mfull(a), dtype=np.float64)
    else:
        a = np.asarray(a, dtype=np.float64)
    if a.size == 0:
        return a
    if np.nanmin(np.max(a, axis=0)) >= 256:
        return np.array([])
    a0 = np.sum(a, axis=0, keepdims=True)
    term = np.log(a0) - np.log(a) + (1.0 / a - 1.0 / a0) + (digamma(a) - digamma(a0))
    out = np.maximum(term, 0.0)
    out = np.where(np.isnan(out), 0.0, out)
    return out


def _spm_hnorm(a: Any) -> np.ndarray | Any:
    """Local ``spm_hnorm`` (~2665–2676)."""
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return np.array([])
    n = _spm_norm(a)
    ent = np.sum(n * _spm_log(n), axis=0)
    ent = np.asarray(mfull(ent), dtype=np.float64).ravel()
    if not np.any(ent):
        return np.array([])
    return ent


def _default_options_vb() -> dict[str, Any]:
    """MATLAB ``try/catch`` defaults on ``OPTIONS.*`` (``spm_MDP_VB_XXX.m`` ~197–203)."""
    return {
        "B": 0,
        "C": 0,
        "D": 0,
        "N": 0,
        "O": 1,
        "P": 0,
        "Y": 1,
    }


def _merge_options_vb(options: Any | None) -> dict[str, Any]:
    if options is None:
        return _default_options_vb()
    if not isinstance(options, dict):
        raise TypeError("OPTIONS must be a dict or None")
    out = _default_options_vb()
    out.update(options)
    return out


def _vb_has_multiple_epoch_columns(mdp_in: Any) -> bool:
    """True when MATLAB ``size(MDP,2) > 1`` (multi-trial loop; ``spm_MDP_VB_XXX.m`` ~212)."""
    if isinstance(mdp_in, list) and mdp_in and isinstance(mdp_in[0], list):
        return len(mdp_in[0]) > 1
    return False


def _spm_is_process(mdp: dict) -> bool:
    """Local ``spm_is_process`` (~2608–2611)."""
    return all(k in mdp for k in ("GA", "GB", "GU"))


def _vb_models_after_checkx(mdp_checked: Any) -> list[dict]:
    """MATLAB ``MDP(m)`` as a list of model dicts."""
    if isinstance(mdp_checked, dict):
        return [mdp_checked]
    if isinstance(mdp_checked, list) and mdp_checked and isinstance(mdp_checked[0], list):
        col: list[dict] = []
        for row in mdp_checked:
            if len(row) != 1:
                raise ValueError(
                    "spm_MDP_VB_XXX: expected exactly one epoch column from spm_MDP_checkX"
                )
            col.append(row[0])
        return col
    raise TypeError("spm_MDP_VB_XXX: unexpected layout returned by spm_MDP_checkX")


def _try_mdp_scalar(mdp: dict, name: str, default: float | int) -> float | int:
    """MATLAB ``try, MDP(1).field; catch, default; end``."""
    if name not in mdp:
        return default
    v = mdp[name]
    if v is None:
        return default
    if isinstance(default, bool):
        return bool(v)
    if isinstance(default, int) and not isinstance(default, bool):
        return int(np.asarray(v).reshape(-1)[0])
    return float(np.asarray(v).reshape(-1)[0])


def _vb_hyperparameters_mdp1(m1: dict) -> dict[str, Any]:
    """MATLAB defaults ~285–289."""
    return {
        "alpha": float(_try_mdp_scalar(m1, "alpha", 512.0)),
        "beta": float(_try_mdp_scalar(m1, "beta", 0.0)),
        "chi": float(_try_mdp_scalar(m1, "chi", 512.0)),
        "eta": float(_try_mdp_scalar(m1, "eta", 512.0)),
        "N": int(_try_mdp_scalar(m1, "N", 0)),
    }


def _vb_coerce_U_dense(U_raw: Any) -> np.ndarray:
    """``MDP.U`` / ``GP.U`` may be ``csr_matrix`` after assemble (~1694 ``U``←``V``); coerce for numeric ops."""
    if U_raw is None:
        return np.zeros((0, 0), dtype=np.float64)
    if sparse.issparse(U_raw):
        U_raw = U_raw.toarray()
    return np.asarray(U_raw, dtype=np.float64)


def _vb_mdp_U_as_float_array(md: dict[str, Any]) -> np.ndarray:
    """See ``_vb_coerce_U_dense``."""
    return _vb_coerce_U_dense(md["U"])


def _unwrap_id_a_entry(id_a_g: Any) -> Any:
    """MATLAB ``id.A{g}`` may be wrapped ``{1}`` in Python."""
    if isinstance(id_a_g, (list, tuple)) and len(id_a_g) == 1:
        return id_a_g[0]
    return id_a_g


def _b_nu_third_dim(Bg: Any) -> int:
    """MATLAB ``size(B{f},3)`` including trailing singleton omitted in NumPy."""
    arr = np.asarray(Bg)
    if arr.ndim >= 3:
        return int(arr.shape[2])
    return 1


def _numel_like_matlab(x: Any) -> int:
    """MATLAB ``numel`` for tensor / None."""
    if x is None:
        return 0
    return int(np.asarray(x).size)


def _vb_id_and_policy_blocks(
    *,
    nm: int,
    models: list[dict],
    Ng: np.ndarray,
    Nf: np.ndarray,
    NF: np.ndarray,
    NU: np.ndarray,
    Nu: np.ndarray,
    K_t: list[list[Any]],
    W_t: list[list[Any]],
    H_t: list[list[Any]],
    I_t: list[list[Any]],
    gp: list[dict[str, Any]],
    id_list: list[dict[str, Any]],
    ID_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    MATLAB ~597–652: ``id`` bookkeeping, ``GV`` / ``V`` via ``spm_combinations``,
    ``fu`` / ``fp`` indices.
    """
    GV_rows: list[sparse.csr_matrix] = []
    V_rows: list[sparse.csr_matrix] = []
    GU_rows: list[np.ndarray] = []
    U_dom_rows: list[np.ndarray] = []
    Na = np.zeros(nm, dtype=np.int64)
    Np = np.zeros(nm, dtype=np.int64)

    for m in range(nm):
        md = models[m]
        gpm = gp[m]
        ng_m = int(Ng[m])
        nf_m = int(Nf[m])
        idm = id_list[m]
        IDm = ID_list[m]

        if "control" not in IDm:
            IDm["control"] = np.arange(1, ng_m + 1, dtype=np.int64)

        ik = np.zeros(ng_m, dtype=np.int64)
        iw = np.zeros(ng_m, dtype=np.int64)
        for g_idx in range(ng_m):
            ik[g_idx] = _numel_like_matlab(K_t[m][g_idx])
            iw[g_idx] = _numel_like_matlab(W_t[m][g_idx])
        idm["iK"] = (np.flatnonzero(ik) + 1).astype(np.int64)
        idm["iW"] = (np.flatnonzero(iw) + 1).astype(np.int64)

        ih = np.zeros(nf_m, dtype=np.int64)
        ii = np.zeros(nf_m, dtype=np.int64)
        for f_idx in range(nf_m):
            ih[f_idx] = _numel_like_matlab(H_t[m][f_idx])
            ii[f_idx] = _numel_like_matlab(I_t[m][f_idx])
        idm["iH"] = (np.flatnonzero(ih) + 1).astype(np.int64)
        idm["iI"] = (np.flatnonzero(ii) + 1).astype(np.int64)

        nf_m_gp = int(NF[m])
        Ugp = _vb_coerce_U_dense(gpm["U"])
        if Ugp.ndim == 1:
            Ugp = Ugp.reshape(1, -1)
        GU_row = np.zeros(nf_m_gp, dtype=bool)
        if Ugp.size and nf_m_gp > 0:
            nc = min(int(Ugp.shape[1]), nf_m_gp)
            GU_row[:nc] = np.any(Ugp[:, :nc] != 0, axis=0)
        GU_rows.append(GU_row.astype(np.float64))
        k_gp = np.flatnonzero(GU_row) + 1
        if k_gp.size == 0:
            u_gen = np.zeros((0, 0), dtype=np.float64)
        else:
            nu_sel = NU[m, k_gp - 1].astype(np.int64).ravel()
            u_gen = spm_combinations(nu_sel)
        nug = int(u_gen.shape[0])
        GV = sparse.lil_matrix((nug, nf_m_gp))
        if u_gen.size and k_gp.size:
            for j, kf in enumerate(k_gp):
                GV[:, int(kf) - 1] = u_gen[:, j : j + 1]
        GV_csr = GV.tocsr()
        GV_rows.append(GV_csr)
        Na[m] = GV_csr.shape[0]

        U_md = _vb_mdp_U_as_float_array(md)
        if U_md.ndim == 1:
            U_md = U_md.reshape(1, -1)
        U_dom = np.zeros(nf_m, dtype=bool)
        if U_md.size and nf_m > 0:
            nc_u = min(int(U_md.shape[1]), nf_m)
            U_dom[:nc_u] = np.any(U_md[:, :nc_u] != 0, axis=0)
        U_dom_rows.append(U_dom.astype(np.float64))
        k_ld = np.flatnonzero(U_dom) + 1
        if k_ld.size == 0:
            u_lat = np.zeros((0, 0), dtype=np.float64)
        else:
            nu_lat = Nu[m, k_ld - 1].astype(np.int64).ravel()
            u_lat = spm_combinations(nu_lat)
        nvl = int(u_lat.shape[0])
        V = sparse.lil_matrix((nvl, nf_m))
        if u_lat.size and k_ld.size:
            for j, kf in enumerate(k_ld):
                V[:, int(kf) - 1] = u_lat[:, j : j + 1]

        if "V" in md:
            V_src = md["V"]
            if sparse.issparse(V_src):
                V = V_src.tocsr()
            else:
                V = sparse.csr_matrix(np.asarray(V_src, dtype=np.float64))
            Vd = V.toarray()
            U_dom = np.any(Vd != 0, axis=0)
            if U_dom.size < nf_m:
                pad = np.zeros(nf_m, dtype=bool)
                pad[: U_dom.size] = U_dom
                U_dom = pad
            elif U_dom.size > nf_m:
                U_dom = U_dom[:nf_m]
            U_dom_rows[m] = U_dom.astype(np.float64)

        V_csr = V.tocsr() if sparse.issparse(V) else sparse.csr_matrix(V)
        V_rows.append(V_csr)
        Np[m] = V_csr.shape[0]

        vd = V_csr.toarray()
        idm["fu"] = (np.flatnonzero(np.any(vd != 0, axis=0)) + 1).astype(np.int64)
        idm["fp"] = (np.flatnonzero(~np.any(vd != 0, axis=0)) + 1).astype(np.int64)
        gvd = GV_csr.toarray()
        IDm["fu"] = (np.flatnonzero(np.any(gvd != 0, axis=0)) + 1).astype(np.int64)
        IDm["fp"] = (np.flatnonzero(~np.any(gvd != 0, axis=0)) + 1).astype(np.int64)

    return {
        "GV": GV_rows,
        "V": V_rows,
        "GU": GU_rows,
        "Um": U_dom_rows,
        "Na": Na,
        "Np": Np,
    }


def _vb_mdp_field_matrix(md: dict[str, Any], key: str, n_rows: int, t_int: int) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~674–699: ``k = zeros(...); try i = find(MDP.s); k(i)=MDP.s(i); end``.

    Column-major linear indexing (MATLAB ``find`` / ``(:)``).
    """
    k = np.zeros((n_rows, t_int), dtype=np.float64)
    try:
        if key not in md or md[key] is None:
            md[key] = k
            return
        s = np.asarray(md[key], dtype=np.float64)
        if s.size == 0:
            md[key] = k
            return
        if s.size != n_rows * t_int:
            md[key] = k
            return
        s_mat = np.reshape(s, (n_rows, t_int), order="F")
        idx = np.flatnonzero(s_mat.ravel(order="F"))
        k.ravel(order="F")[idx] = s_mat.ravel(order="F")[idx]
    except Exception:
        pass
    md[key] = k


def _get_mdp_O_gt(O_field: Any, g_idx: int, t_idx: int) -> Any:
    """MATLAB ``MDP.O{g,t}`` with zero-based ``g_idx``, ``t_idx``."""
    if isinstance(O_field, np.ndarray) and O_field.dtype == object:
        return O_field[g_idx, t_idx]
    row = O_field[g_idx]
    if isinstance(row, (list, tuple)):
        return row[t_idx]
    arr = np.asarray(row)
    if arr.ndim == 0:
        return arr.item()
    return arr[t_idx]


def _mode_matlab_dim1(arr: np.ndarray) -> np.ndarray:
    """MATLAB ``mode(A,1)``: mode along rows, length ``size(A,2)``."""
    a = np.asarray(arr, dtype=np.float64)
    if a.size == 0:
        return np.zeros((0,), dtype=np.float64)
    res = stats.mode(a, axis=0, keepdims=False)
    mo = res.mode
    return np.asarray(mo, dtype=np.float64).ravel()


def _spm_MDP_get_M(
    models: list[dict[str, Any]],
    t_int: int,
    Ng: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """
    Local ``spm_MDP_get_M`` from ``spm_MDP_VB_XXX.m`` (~2769–2819).

    Returns ``M`` with shape ``(T, Nm)`` — MATLAB ``M(t,:)`` is 1-based agent order per time.
    Mutates each ``models[m]['n']`` to ``Ng[m]``×``T``.
    """
    nm = len(models)
    n_acc = np.zeros((nm, t_int), dtype=np.float64)
    for m in range(nm):
        md = models[m]
        ng_m = int(Ng[m])
        if "n" not in md or md["n"] is None:
            md["n"] = np.zeros((ng_m, t_int), dtype=np.float64)
        else:
            arr = np.asarray(md["n"], dtype=np.float64)
            if arr.size == 0:
                md["n"] = np.zeros((ng_m, t_int), dtype=np.float64)
            else:
                if arr.ndim == 0:
                    arr = arr.reshape(1, 1)
                elif arr.ndim == 1:
                    arr = arr.reshape(1, -1)
                nr, nc = int(arr.shape[0]), int(arr.shape[1])
                if nr < ng_m:
                    arr = np.tile(arr[0:1, :], (ng_m, 1))
                if nc < t_int:
                    arr = np.tile(arr[:, 0:1], (1, t_int))
                md["n"] = arr

        n_mat = np.asarray(md["n"], dtype=np.float64)
        masked = n_mat * (n_mat > 0.0)
        n_acc[m, :] = _mode_matlab_dim1(masked)

    n_global = _mode_matlab_dim1(n_acc)
    if n_global.size < t_int:
        pad = np.zeros(t_int, dtype=np.float64)
        pad[: n_global.size] = n_global
        n_global = pad

    M = np.zeros((t_int, nm), dtype=np.int64)
    idx1 = np.arange(1, nm + 1, dtype=np.int64)
    for t in range(t_int):
        nt = float(n_global[t])
        if nt > 0.0:
            M[t, :] = np.roll(idx1, int(1 - nt))
        else:
            M[t, :] = idx1

    return M, models


def _vb_prealloc_BP_IP(bundle: dict[str, Any]) -> tuple[list, list]:
    """
    MATLAB ~742–743: ``BP = cell(Nm, Nf(m), Np(m));`` with ``m = Nm`` (value of ``m`` after ``for m=1:Nm``).

    When ``Np(m)==0``, MATLAB's cell still supports ``BP{m,f,1}`` on the uncontrolled
    factors branch (~1243–1249); allocate at least one slot in the policy dimension so
    ``BP[..., 0]`` / ``IP[..., 0]`` writes do not index an empty list.
    """
    nm = int(bundle["Nm"])
    m_last = nm - 1
    nf = int(bundle["Nf"][m_last])
    npp = int(bundle["Np"][m_last])
    npp_shell = max(1, npp)
    BP = [[[None for _ in range(npp_shell)] for _ in range(nf)] for _ in range(nm)]
    IP = [[[None for _ in range(npp_shell)] for _ in range(nf)] for _ in range(nm)]
    return BP, IP


def _vb_policy_depth_and_get_M(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """MATLAB ~737–743: ``N = min(N,T)``, ``spm_MDP_get_M``, ``BP``/``IP`` shells."""
    t_int = int(bundle["T"])
    n_mdp = int(hp["N"])
    n_depth = int(min(n_mdp, t_int))
    M_upd, _ = _spm_MDP_get_M(models, t_int, bundle["Ng"])
    BP, IP = _vb_prealloc_BP_IP(bundle)
    nm = int(bundle["Nm"])
    Np_arr = bundle["Np"]
    R_policy = [np.zeros((int(Np_arr[m]), t_int), dtype=np.float64) for m in range(nm)]
    w_policy = [np.zeros(t_int, dtype=np.float64) for _ in range(nm)]
    v_policy = [np.zeros(t_int, dtype=np.float64) for _ in range(nm)]
    return {
        "N_policy_depth": n_depth,
        "M_update": M_upd,
        "BP": BP,
        "IP": IP,
        "R_policy": R_policy,
        "w_policy": w_policy,
        "v_policy": v_policy,
    }


def _unwrap_gp_elem(x: Any) -> Any:
    """Single-element MATLAB cell wrapper → inner array."""
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _vb_gp_transition_column(Bg: Any, s_1based: int, u_1based: int) -> np.ndarray:
    """MATLAB ``GP.B{f}(:, s, u)`` with 1-based indices; column ``Ns×1``."""
    Barr = np.asarray(_unwrap_gp_elem(Bg), dtype=np.float64)
    if Barr.ndim == 2:
        Barr = Barr[:, :, np.newaxis]
    nu_third = int(Barr.shape[2])
    if nu_third == 0:
        ns = int(Barr.shape[0])
        return np.zeros((max(ns, 1), 1), dtype=np.float64)
    si = max(0, min(int(s_1based) - 1, int(Barr.shape[1]) - 1))
    ui = max(0, min(int(u_1based) - 1, nu_third - 1))
    col = Barr[:, si, ui]
    return np.asarray(col.reshape(-1, 1), dtype=np.float64)


def _vb_gen_u_paths_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """MATLAB ~756–775: GP path dimension ``NF``."""
    md = models[mi]
    gpm = bundle["gp"][mi]
    nf_gp = int(bundle["NF"][mi])
    for f_idx in range(nf_gp):
        if float(md["u"][f_idx, t_idx]) != 0.0:
            continue
        if t_idx > 0:
            md["u"][f_idx, t_idx] = float(md["u"][f_idx, t_idx - 1])
        else:
            Ef = _unwrap_gp_elem(gpm["E"][f_idx])
            pu = _spm_norm(Ef)
            if int(np.asarray(pu).size) == 0:
                continue
            md["u"][f_idx, t_idx] = float(_spm_sample(pu))


def _vb_prior_QP_paths_states_one_model(
    mi: int,
    bundle: dict[str, Any],
    t_idx: int,
    Pu_vec: np.ndarray,
) -> None:
    """MATLAB ~779–804: policy sample ``Pu``, update ``P`` / ``Q`` over **generative** ``Nf`` factors."""
    Um = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
    vd = bundle["V"][mi].toarray()
    nf_gen = int(bundle["Nf"][mi])
    Nu_m = bundle["Nu"]
    Q_all = bundle["Q"]
    P_all = bundle["P"]
    B_t = bundle["B"]

    pu_col = np.asarray(Pu_vec, dtype=np.float64).reshape(-1, 1)
    if pu_col.size == 0:
        # ``Np==0``: no policy simplex; controlled rows are inactive for ``Vu`` with empty ``V``.
        k_pol = 1
    else:
        k_pol = _spm_sample(pu_col)

    for f_idx in range(nf_gen):
        if f_idx < Um.size and float(Um[f_idx]) != 0.0:
            if vd.shape[0] == 0:
                continue
            u_mark = int(round(float(vd[k_pol - 1, f_idx])))
            P_arr = np.asarray(P_all[mi][f_idx][t_idx - 1], dtype=np.float64).ravel()
            P_arr[:] = 0.0
            if 1 <= u_mark <= P_arr.size:
                P_arr[u_mark - 1] = 1.0
            P_all[mi][f_idx][t_idx - 1] = P_arr.reshape(-1, 1)

        nu_mf = int(Nu_m[mi, f_idx])
        Q_prev = np.asarray(Q_all[mi][f_idx][t_idx - 1], dtype=np.float64)
        Bmf = B_t[mi][f_idx]
        if nu_mf > 1:
            P_prev = P_all[mi][f_idx][t_idx - 1]
            tp = np.asarray(spm_dot(Bmf, P_prev), dtype=np.float64)
            Q_new = tp @ Q_prev
        else:
            Bm = np.asarray(_unwrap_gp_elem(Bmf), dtype=np.float64)
            Q_new = Bm @ Q_prev
        Q_all[mi][f_idx][t_idx] = Q_new


def _vb_gen_control_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """MATLAB ~806–827: ``spm_action`` (process) or sample ``u(:,t-1)`` from ``P`` (implicit)."""
    md = models[mi]
    if float(bundle["process"][mi]) > 0.0:
        if "GV" not in md:
            raise NotImplementedError(
                "spm_MDP_VB_XXX: process model without GV (nested spm_action requires GV)"
            )
        t_int = int(bundle["T"])
        nf = int(bundle["Nf"][mi])
        A_list = bundle["A"][mi]
        Q_all = bundle["Q"]
        Q_slice = [Q_all[mi][f][t_idx] for f in range(nf)]
        nf_gp = len(md["GB"])
        for key, fill in (("u", 1.0), ("s", 1.0)):
            if key not in md or md[key] is None:
                md[key] = np.full((nf_gp, t_int), fill, dtype=np.float64)
            else:
                arr = np.asarray(md[key], dtype=np.float64)
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)
                if arr.shape[0] < nf_gp:
                    arr = np.vstack(
                        [arr, np.full((nf_gp - arr.shape[0], arr.shape[1]), fill, dtype=np.float64)]
                    )
                if arr.shape[1] < t_int:
                    arr = np.hstack(
                        [arr, np.full((arr.shape[0], t_int - arr.shape[1]), fill, dtype=np.float64)]
                    )
                md[key] = arr
        # Fourth argument: MATLAB ``t-1`` with loop ``t`` = ``t_idx + 1`` → pass ``t_idx``.
        _spm_action(md, A_list, Q_slice, t_idx)
        return
    idm = bundle["id"][mi]
    P_all = bundle["P"]
    fu = np.asarray(idm.get("fu", np.zeros(0, dtype=np.int64)), dtype=np.int64).ravel()
    for f_1 in fu:
        f_idx = int(f_1) - 1
        md["u"][f_idx, t_idx - 1] = float(_spm_sample(P_all[mi][f_idx][t_idx - 1]))


def _vb_gen_states_one_model(mi: int, models: list[dict[str, Any]], bundle: dict[str, Any], t_idx: int) -> None:
    """MATLAB ~830–851: sample ``s`` from ``GP``; ``NF`` factors."""
    md = models[mi]
    gpm = bundle["gp"][mi]
    nf_gp = int(bundle["NF"][mi])
    for f_idx in range(nf_gp):
        if float(md["s"][f_idx, t_idx]) != 0.0:
            continue
        if t_idx > 0:
            Bg = gpm["B"][f_idx]
            su = int(round(float(md["s"][f_idx, t_idx - 1])))
            uu = int(round(float(md["u"][f_idx, t_idx - 1])))
            ps = _vb_gp_transition_column(Bg, su, uu)
        else:
            Df = _unwrap_gp_elem(gpm["D"][f_idx])
            ps = _spm_norm(Df)
        md["s"][f_idx, t_idx] = float(_spm_sample(ps))


def _vb_generation_paths_states_share(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` inner ``for m = M(t,:)``: ~756–855 (partial), then ~858–869.

    Order per model: **u** (``NF``) → if ``t>1``: **Pu**/**Q**/**P** (``Nf``, needs ``bundle['Pu_carry'][m]``),
    **control** → **s** (``NF``). ``Pu_carry[m]`` is ``None`` until the belief phase sets it (MATLAB: persists from prior ``t``).

    Outcomes (~873+) and ``spm_forwards`` are separate.
    """
    nm = int(bundle.get("Nm", len(models)))
    bundle.setdefault("Pu_carry", [None] * nm)
    Pu_carry: list[Any] = bundle["Pu_carry"]
    NF_arr = bundle["NF"]

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        _vb_gen_u_paths_one_model(mi, models, bundle, t_idx)
        if t_idx > 0:
            pu_v = Pu_carry[mi]
            if pu_v is not None:
                _vb_prior_QP_paths_states_one_model(mi, bundle, t_idx, np.asarray(pu_v, dtype=np.float64))
            _vb_gen_control_one_model(mi, models, bundle, t_idx)
        _vb_gen_states_one_model(mi, models, bundle, t_idx)

    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        if "m" not in md:
            continue
        m_src = np.asarray(md["m"], dtype=np.float64).ravel()
        nf_gp = int(NF_arr[mi])
        for f_idx in range(min(nf_gp, int(m_src.size))):
            n_agent = int(round(float(m_src[f_idx])))
            if n_agent > 0:
                md["s"][f_idx, t_idx] = float(models[n_agent - 1]["s"][f_idx, t_idx])


def _tensor_nonempty(x: Any) -> bool:
    """MATLAB ``numel(X) > 0``."""
    if x is None:
        return False
    return bool(np.asarray(x).size > 0)


def _vb_fill_BP_IP_at_t(bundle: dict[str, Any], t_idx: int) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1224–1256: belief propagators ``BP`` / ``IP`` from ``B``, ``I``, ``V``, ``P``.

    Uses generative-model factors ``Nf``, ``Um``, ``Nu``, policy matrix ``V``, and ``P{m,f,t}``.
    """
    nm = int(bundle["Nm"])
    Nf = bundle["Nf"]
    Nu = bundle["Nu"]
    Um_list = bundle["Um"]
    V_list = bundle["V"]
    B_t = bundle["B"]
    I_t = bundle["I"]
    P_all = bundle["P"]
    BP = bundle["BP"]
    IP = bundle["IP"]
    Np = bundle["Np"]

    for m in range(nm):
        nf_m = int(Nf[m])
        npp = int(Np[m])
        Um = np.asarray(Um_list[m], dtype=np.float64).ravel()
        V_csr = V_list[m]
        vd = V_csr.toarray()

        for f_idx in range(nf_m):
            controllable = f_idx < Um.size and float(Um[f_idx]) != 0.0
            Bmf = _unwrap_gp_elem(B_t[m][f_idx])
            Imf = I_t[m][f_idx]

            if controllable:
                Barr = np.asarray(Bmf, dtype=np.float64)
                if Barr.ndim == 2:
                    Barr = Barr[:, :, np.newaxis]
                Iarr = None
                if _tensor_nonempty(Imf):
                    Iarr = np.asarray(_unwrap_gp_elem(Imf), dtype=np.float64)
                    if Iarr.ndim == 2:
                        Iarr = Iarr[:, :, np.newaxis]
                for k in range(npp):
                    u_sel = int(round(float(vd[k, f_idx])))
                    if u_sel < 1:
                        u_sel = 1
                    nu_third = Barr.shape[2]
                    if u_sel > nu_third:
                        u_sel = nu_third
                    BP[m][f_idx][k] = np.asarray(Barr[:, :, u_sel - 1], dtype=np.float64)
                    if Iarr is not None:
                        IP[m][f_idx][k] = np.asarray(Iarr[:, :, u_sel - 1], dtype=np.float64)
            else:
                Pmf_t = P_all[m][f_idx][t_idx]
                if int(Nu[m, f_idx]) > 1:
                    BP[m][f_idx][0] = spm_dot(Bmf, Pmf_t)
                    if _tensor_nonempty(Imf):
                        dotted = spm_dot(Imf, Pmf_t)
                        for k in range(npp):
                            IP[m][f_idx][k] = dotted
                else:
                    BP[m][f_idx][0] = np.asarray(Bmf, dtype=np.float64)
                    if _tensor_nonempty(Imf):
                        Imf_u = _unwrap_gp_elem(Imf)
                        for k in range(npp):
                            IP[m][f_idx][k] = np.asarray(Imf_u, dtype=np.float64)


def _vb_placeholder_pu_carry_softmax(
    bundle: dict[str, Any],
    M_row: np.ndarray,
    alpha: float,
) -> None:
    """
    MATLAB ``Pu = spm_softmax(G,alpha)`` (~1326) after ``spm_forwards`` (~1261).

    **Interim:** ``G`` is not computed yet (no ``spm_forwards`` / ``spm_VBX``); use
    ``G = 0`` so ``spm_softmax(G,alpha)`` is **uniform** over ``Np(m)`` — placeholder
    until the belief phase is ported. See ``notes/andrew Python Matlab Translation Issues.md``.
    """
    nm = int(bundle.get("Nm", 1))
    bundle.setdefault("Pu_carry", [None] * nm)
    Pu_carry: list[Any] = bundle["Pu_carry"]
    Np_arr = bundle["Np"]
    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        npp = int(Np_arr[mi])
        if npp < 1:
            Pu_carry[mi] = np.ones((1, 1), dtype=np.float64)
            continue
        g0 = np.zeros((npp, 1), dtype=np.float64)
        Pu_carry[mi] = np.asarray(spm_softmax(g0, float(alpha)), dtype=np.float64)


def _vb_o_row_ready_for_model(O_m: list, t_idx: int) -> bool:
    """True when ``O{m,:,t}`` cells are populated (numeric / non-empty) for ``spm_VBX``."""
    for g in range(len(O_m)):
        cell = O_m[g][t_idx]
        if cell is None:
            return False
        if isinstance(cell, (list, tuple)) and len(cell) == 0:
            return False
    return True


def _vb_ensure_per_t_traces(models: list[dict[str, Any]], mi: int, t_int: int) -> None:
    """Preallocate MATLAB-like ``MDP(m).F(t)``, ``G{t}``, ``Z(t)`` slots (length ``T``)."""
    md = models[mi]
    if md.get("G") is None or (not isinstance(md["G"], list)) or (len(md["G"]) != t_int):
        md["G"] = [None] * t_int
    ff = md.get("F")
    if ff is None or (not isinstance(ff, np.ndarray)) or (int(ff.size) != t_int):
        md["F"] = np.zeros((t_int,), dtype=np.float64)
    zz = md.get("Z")
    if zz is None or (not isinstance(zz, np.ndarray)) or (int(zz.size) != t_int):
        md["Z"] = np.zeros((t_int,), dtype=np.float64)


def _vb_in_loop_id_ig_and_sn(
    mi: int,
    bundle: dict[str, Any],
    t_idx: int,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1418–1431 (after ``F``/``G``/``Z`` logging): ``id.ig`` and ``sn`` when
    ``OPTIONS.N``.
    """
    t_int = int(bundle["T"])
    id_m = bundle["id"][mi]
    if "i" in id_m:
        if "ig" not in id_m or id_m["ig"] is None:
            id_m["ig"] = np.zeros((t_int,), dtype=np.float64)
        else:
            ig0 = np.asarray(id_m["ig"], dtype=np.float64).ravel()
            if ig0.size < t_int:
                id_m["ig"] = np.concatenate([ig0, np.zeros(t_int - ig0.size, dtype=np.float64)])
            else:
                id_m["ig"] = ig0[:t_int].copy()
        iv = np.asarray(id_m["i"], dtype=np.float64).ravel()
        id_m["ig"][t_idx] = float(iv[0]) if iv.size > 0 else 0.0

    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("N", 0)) == 0:
        return
    sn_all = bundle.get("sn")
    if sn_all is None:
        return
    for f_idx in range(int(bundle["Nf"][mi])):
        snmf = sn_all[mi][f_idx]
        if snmf is None:
            continue
        ns = int(snmf.shape[0])
        for ii in range(t_int):
            q_src = np.asarray(bundle["Q"][mi][f_idx][ii], dtype=np.float64).reshape(-1)
            if ns <= 0:
                continue
            take = min(ns, int(q_src.size))
            if take <= 0:
                continue
            snmf[:take, ii, t_idx] = q_src[:take]
            if take < ns:
                snmf[take:, ii, t_idx] = 0.0


def _vb_trim_mdp_o_s_u_at_terminal_horizon(models: list[dict[str, Any]], bundle: dict[str, Any]) -> None:
    """MATLAB ``spm_MDP_VB_XXX.m`` ~1438–1443 when ``t == T``: keep first ``T`` outcome/state/control columns."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    Ng = bundle["Ng"]
    NF = bundle["NF"]
    for mi in range(nm):
        md = models[mi]
        ng_m = int(Ng[mi])
        nf_m = int(NF[mi])
        for key, n_rows in (("o", ng_m), ("s", nf_m), ("u", nf_m)):
            if key not in md:
                continue
            arr = np.asarray(md[key], dtype=np.float64)
            if arr.ndim < 2:
                continue
            if arr.shape[1] > t_int:
                md[key] = np.asarray(arr[:, :t_int], dtype=np.float64).copy()


def _vb_active_learning_in_loop(
    mi: int,
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    t_m: int,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1349–1409: online Dirichlet updates for ``a`` / ``b`` after
    control priors and **before** ``MDP(m).F(t)``/``G``/``Z`` logging (~1412–1416).
    """
    md = models[mi]
    id_m = bundle["id"][mi]
    nf_m = int(bundle["Nf"][mi])
    O_m = bundle["O"][mi]
    Q_row: list[Any] = [bundle["Q"][mi][f][t_idx] for f in range(nf_m)]

    if "a" in md:
        for g_1 in np.ravel(spm_children(id_m)).astype(np.int64):
            g_idx = int(g_1) - 1
            if g_idx < 0:
                continue
            jdom, kcod = spm_parents(id_m, int(g_1), Q_row)
            k_flat = np.atleast_1d(np.asarray(kcod, dtype=np.float64).ravel()).astype(np.int64).ravel()
            if k_flat.size == 0:
                continue
            j_flat = np.atleast_1d(np.asarray(jdom, dtype=np.float64).ravel()).astype(np.int64).ravel()
            if j_flat.size == 0:
                continue
            q_parts: list[np.ndarray] = []
            for jj in j_flat:
                ji = int(jj)
                if ji < 1 or ji > nf_m:
                    continue
                q_parts.append(np.asarray(Q_row[ji - 1], dtype=np.float64))
            if not q_parts:
                continue
            if len(q_parts) == 1:
                Qj = q_parts[0]
            else:
                Qj = spm_cross(*q_parts)

            qa_slot = bundle["qa"][mi][g_idx]
            qa_base = _unwrap_gp_elem(qa_slot)
            qa_arr = np.asarray(qa_base, dtype=np.float64)
            if qa_arr.size == 0:
                continue
            da = np.zeros_like(qa_arr, dtype=np.float64)
            for i_out in k_flat:
                io = int(i_out)
                if io < 1:
                    continue
                ocell = O_m[io - 1][t_idx]
                if ocell is None or not _tensor_nonempty(ocell):
                    continue
                Oi = np.asarray(ocell, dtype=np.float64)
                term = np.asarray(spm_cross(Oi, Qj), dtype=np.float64)
                if term.shape != da.shape:
                    term = np.reshape(term, qa_arr.shape, order="F")
                da = da + term
            supp = qa_arr != 0.0
            da = np.where(supp, da, 0.0)
            qa_new = qa_arr + da
            if isinstance(qa_slot, list) and len(qa_slot) == 1:
                qa_slot[0] = qa_new
            else:
                bundle["qa"][mi][g_idx] = qa_new
            A_norm = _spm_norm(qa_new)
            if "A" in md:
                Agf = md["A"][g_idx]
                Agf = Agf[0] if isinstance(Agf, list) and len(Agf) == 1 else Agf
                if isinstance(Agf, np.ndarray) and Agf.dtype == bool:
                    A_norm = A_norm.astype(bool)
            A_slot = bundle["A"][mi][g_idx]
            if isinstance(A_slot, list) and len(A_slot) == 1:
                A_slot[0] = A_norm
            else:
                bundle["A"][mi][g_idx] = A_norm
            if "a" in md:
                a_sl = md["a"][g_idx]
                if isinstance(a_sl, list) and len(a_sl) == 1:
                    a_sl[0] = qa_new.copy()
                else:
                    md["a"][g_idx] = qa_new.copy()
            if "A" in md:
                ag = md["A"][g_idx]
                an = np.array(A_norm, copy=True)
                if isinstance(ag, list) and len(ag) == 1:
                    ag[0] = an
                else:
                    md["A"][g_idx] = an
            bundle["W"][mi][g_idx] = _spm_wnorm(qa_new)
            bundle["K"][mi][g_idx] = _spm_hnorm(A_norm)

    if "b" in md and t_m > 1:
        for f_idx in range(nf_m):
            Qt = np.asarray(bundle["Q"][mi][f_idx][t_idx], dtype=np.float64)
            Qtm1 = np.asarray(bundle["Q"][mi][f_idx][t_idx - 1], dtype=np.float64)
            Ptm1 = np.asarray(bundle["P"][mi][f_idx][t_idx - 1], dtype=np.float64)
            db = np.asarray(
                spm_cross(spm_cross(Qt, Qtm1), Ptm1),
                dtype=np.float64,
            )
            qb_slot = bundle["qb"][mi][f_idx]
            qb_arr = np.asarray(_unwrap_gp_elem(qb_slot), dtype=np.float64)
            if qb_arr.size == 0:
                continue
            if db.shape != qb_arr.shape:
                db = np.reshape(db, qb_arr.shape, order="F")
            supp_b = qb_arr != 0.0
            db = np.where(supp_b, db, 0.0)
            qb_new = qb_arr + db
            if isinstance(qb_slot, list) and len(qb_slot) == 1:
                qb_slot[0] = qb_new
            else:
                bundle["qb"][mi][f_idx] = qb_new
            B_norm = _spm_norm(qb_new)
            if "B" in md:
                Bgf = md["B"][f_idx]
                Bgf = Bgf[0] if isinstance(Bgf, list) and len(Bgf) == 1 else Bgf
                if isinstance(Bgf, np.ndarray) and Bgf.dtype == bool:
                    B_norm = B_norm.astype(bool)
            bundle["B"][mi][f_idx] = B_norm
            I_w = _spm_wnorm(qb_new)
            bundle["I"][mi][f_idx] = I_w
            if "b" in md:
                b_sl = md["b"][f_idx]
                if isinstance(b_sl, list) and len(b_sl) == 1:
                    b_sl[0] = qb_new.copy()
                else:
                    md["b"][f_idx] = qb_new.copy()
            if "B" in md:
                bg = md["B"][f_idx]
                bn = np.array(B_norm, copy=True)
                if isinstance(bg, list) and len(bg) == 1:
                    bg[0] = bn
                else:
                    md["B"][f_idx] = bn


def _vb_belief_after_forwards(
    mi: int,
    bundle: dict[str, Any],
    t_m: int,
    t_idx: int,
    G_m: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, float]:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1264–1346 immediately after ``spm_forwards``.

    Augment ``G`` at ``t==1`` with log priors over policy rows from ``E`` / ``V``;
    ``R = spm_softmax(G)``, ``w``, ``v``; path posteriors ``P{m,f,t-1}`` when ``t>1``;
    path complexity ``Z`` (~1285–1317); ``Pu = spm_softmax(G,alpha)`` and current ``P{m,f,t}``
    from ``Pu`` and ``V``.

    Returns policy-column ``G`` after augmentation (for ``MDP(m).G{t}``) and scalar ``Z``.
    """
    Pu_carry: list[Any] = bundle["Pu_carry"]
    npp = int(bundle["Np"][mi])
    G_flat = np.asarray(G_m, dtype=np.float64).copy().ravel(order="F")
    if npp > 0:
        G_work = G_flat.reshape(npp, -1, order="F")
        if G_work.shape[1] != 1:
            G_work = np.sum(G_work, axis=1, keepdims=True)
        G_work = G_work.reshape(npp, 1)
    else:
        # No policy rows (``V`` is ``0×Nf``): ``spm_forwards`` may still return a scalar ``G``.
        G_work = np.zeros((0, 1), dtype=np.float64)

    V_csr = bundle["V"][mi]
    Vd = V_csr.toarray()
    Um_row = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
    E_list = bundle["gp"][mi]["E"]
    nf_m = int(bundle["Nf"][mi])
    Nu_arr = bundle["Nu"]

    if t_m == 1:
        for k in range(npp):
            le_acc = 0.0
            for f_idx in range(nf_m):
                if f_idx >= Um_row.size or Um_row[f_idx] == 0.0:
                    continue
                Ef = np.asarray(_unwrap_gp_elem(E_list[f_idx]), dtype=np.float64).reshape(-1, 1, order="F")
                vk = int(round(float(Vd[k, f_idx])))
                if vk < 1 or vk > Ef.shape[0]:
                    continue
                ev = float(Ef[vk - 1, 0])
                le_acc += float(np.asarray(_spm_log(np.array([[ev]], dtype=np.float64))).reshape(-1)[0])
            G_work[k, 0] += le_acc

    R_col = np.asarray(spm_softmax(G_work), dtype=np.float64).reshape(npp, 1)
    bundle["R_policy"][mi][:, t_idx] = R_col.reshape(-1)
    bundle["w_policy"][mi][t_idx] = float(
        (R_col.T @ np.asarray(_spm_log(R_col), dtype=np.float64).reshape(-1, 1)).reshape(-1)[0]
    )
    bundle["v_policy"][mi][t_idx] = float((R_col.T @ G_work).reshape(-1)[0])

    Q_all = bundle["Q"]
    P_all = bundle["P"]
    B_t = bundle["B"]

    Z_acc = 0.0
    if t_m > 1:
        for f_idx in range(nf_m):
            nu_mf = int(Nu_arr[mi, f_idx])
            if nu_mf > 1:
                Bmf = _unwrap_gp_elem(B_t[mi][f_idx])
                Qt = np.asarray(Q_all[mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1, order="F")
                Qtm1 = np.asarray(Q_all[mi][f_idx][t_idx - 1], dtype=np.float64).reshape(-1, 1, order="F")
                LL = np.asarray(spm_dot(spm_dot(Bmf, Qt), Qtm1), dtype=np.float64)
                LL = np.asarray(_spm_log(LL), dtype=np.float64).reshape(-1, 1)
                LP = np.asarray(_spm_log(P_all[mi][f_idx][t_idx - 1]), dtype=np.float64).reshape(-1, 1)
                post = np.asarray(spm_softmax(LL + LP), dtype=np.float64).reshape(-1, 1)
                P_all[mi][f_idx][t_idx - 1] = post
                logp = np.asarray(_spm_log(post), dtype=np.float64).reshape(-1, 1)
                Z_acc += float((post.T @ (LL + LP - logp)).reshape(-1)[0])
            else:
                P_all[mi][f_idx][t_idx - 1] = np.array([[1.0]], dtype=np.float64)

    Pu = np.asarray(spm_softmax(G_work, float(alpha)), dtype=np.float64).reshape(npp, 1)
    Pu_carry[mi] = Pu

    for f_idx in range(nf_m):
        if f_idx < Um_row.size and Um_row[f_idx] != 0.0:
            nu = int(Nu_arr[mi, f_idx])
            col = np.zeros((nu, 1), dtype=np.float64)
            for u in range(1, nu + 1):
                mask = (Vd[:, f_idx] == float(u)).astype(np.float64).reshape(npp, 1)
                col[u - 1, 0] = float((Pu.T @ mask).reshape(-1)[0])
            P_all[mi][f_idx][t_idx] = col
        else:
            if t_m > 1:
                P_all[mi][f_idx][t_idx] = copy.deepcopy(P_all[mi][f_idx][t_idx - 1])

    return np.asarray(G_work, dtype=np.float64).copy(), float(Z_acc)


def _vb_generate_outcomes_if_options_o(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~873–949 (first ``if OPTIONS.O`` block), **before** ``BP``/``IP``.

    Generates ``O{m,o,t}`` / ``MDP(m).o(o,t)`` where needed. Partial Pass 1:
    ``n(o,t) > 0`` with ``n == m`` (ELBO softmax), ``n > 0`` copy from agent ``n``,
    ``n(o,t) < 0`` stores ``Fm`` for ``_vb_shared_probabilistic_outcomes`` (~952–969),
    ``n == 0`` samples from tensor ``GP.A{g}`` given ``s``. Function-handle ``A`` not translated.
    """
    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("O", 1)) == 0:
        return

    ID_list = bundle["ID"]
    gp_list = bundle["gp"]
    O_shell = bundle["O"]
    Ng_arr = bundle["Ng"]
    t_int = int(bundle["T"])
    Fm_store: dict[tuple[int, int, int], np.ndarray] = bundle.setdefault("_vb_Fm_neg_t_o_m", {})

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        gpm = gp_list[mi]
        ng_m = int(Ng_arr[mi])
        n_mat = np.asarray(md.get("n", np.zeros((ng_m, t_int))), dtype=np.float64)
        if n_mat.size == 0:
            n_mat = np.zeros((ng_m, t_int), dtype=np.float64)
        if n_mat.ndim == 1:
            n_mat = n_mat.reshape(ng_m, -1)
        if n_mat.shape[0] < ng_m:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[: n_mat.shape[0], :] = n_mat
            n_mat = pad
        if n_mat.shape[1] < t_int:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[:, : n_mat.shape[1]] = n_mat
            n_mat = pad

        for g_idx in range(ng_m):
            g_1 = g_idx + 1
            s_col = np.asarray(md["s"][:, t_idx], dtype=np.float64).reshape(-1, 1)
            j_p, i_ch = spm_parents(ID_list[mi], g_1, s_col)
            i_vals = np.atleast_1d(np.asarray(i_ch, dtype=float)).ravel().tolist()
            for o_1based in i_vals:
                o_idx = int(round(float(o_1based))) - 1
                if o_idx < 0 or o_idx >= ng_m:
                    continue
                if float(md["o"][o_idx, t_idx]) != 0.0:
                    # MATLAB ~933–939: when outcome realization is already specified,
                    # fill O{m,o,t} with one-hot if currently empty.
                    if not _tensor_nonempty(O_shell[mi][o_idx][t_idx]):
                        no_mo = int(bundle["No"][mi, o_idx])
                        oi = int(round(float(md["o"][o_idx, t_idx])))
                        if no_mo > 0 and oi > 0 and oi <= no_mo:
                            hot = np.zeros((no_mo, 1), dtype=np.float64)
                            hot[oi - 1, 0] = 1.0
                            O_shell[mi][o_idx][t_idx] = hot
                    continue
                n_ot = float(n_mat[o_idx, t_idx])

                if n_ot > 0:
                    ni = int(round(n_ot)) - 1
                    if ni == mi:
                        j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                        q_list = [bundle["Q"][mi][int(jv) - 1][t_idx] for jv in j_arr if int(jv) > 0]
                        Amg = _unwrap_gp_elem(bundle["A"][mi][g_idx])
                        if callable(Amg) and not isinstance(Amg, np.ndarray):
                            raise NotImplementedError(
                                "OPTIONS.O: likelihood function_handle A{g} not translated"
                            )
                        F = np.asarray(spm_dot(Amg, q_list), dtype=np.float64).reshape(-1, 1)
                        Fl = np.asarray(_spm_log(F), dtype=np.float64).reshape(-1, 1)
                        Ocell = np.asarray(spm_softmax(Fl * 512.0), dtype=np.float64).reshape(-1, 1)
                        O_shell[mi][o_idx][t_idx] = Ocell
                        md["o"][o_idx, t_idx] = float(_spm_sample(Ocell))
                    else:
                        O_shell[mi][o_idx][t_idx] = O_shell[ni][o_idx][t_idx]
                        md["o"][o_idx, t_idx] = float(models[ni]["o"][o_idx, t_idx])
                    continue

                if n_ot < 0:
                    j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                    q_list = [bundle["Q"][mi][int(jv) - 1][t_idx] for jv in j_arr if int(jv) > 0]
                    Amg = _unwrap_gp_elem(bundle["A"][mi][g_idx])
                    if callable(Amg) and not isinstance(Amg, np.ndarray):
                        raise NotImplementedError(
                            "OPTIONS.O: likelihood function_handle A{g} not translated (Fm branch)"
                        )
                    Fm_store[(t_idx, o_idx, mi)] = np.asarray(
                        _spm_log(np.asarray(spm_dot(Amg, q_list), dtype=np.float64)),
                        dtype=np.float64,
                    ).reshape(-1, 1)
                    continue

                Ag_raw = _unwrap_gp_elem(gpm["A"][g_idx])
                if callable(Ag_raw) and not isinstance(Ag_raw, np.ndarray):
                    raise NotImplementedError("OPTIONS.O: GP.A{g} function_handle not translated")
                Ag = np.asarray(Ag_raw, dtype=np.float64)
                j_arr = np.atleast_1d(np.asarray(j_p, dtype=np.float64)).ravel()
                ind_parts: list[int] = []
                for jx in j_arr:
                    jxi = int(round(float(jx)))
                    sv = float(md["s"][jxi - 1, t_idx])
                    ind_parts.append(int(round(sv)) - 1)
                ind_tup = tuple(ind_parts)
                try:
                    col = np.asarray(Ag[(slice(None),) + ind_tup], dtype=np.float64).reshape(-1, 1)
                except (IndexError, TypeError):
                    raise
                O_shell[mi][o_idx][t_idx] = col
                md["o"][o_idx, t_idx] = float(_spm_sample(col))


def _vb_shared_probabilistic_outcomes(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~952–969: ``Fm{g,j}`` from the ``n(o,t) < 0`` path (~914–917),
    summed over agents ``j ~= m``, ``O{m,g,t} = spm_softmax(F)``, sample ``o`` from ``spm_softmax(F*512)``.
    """
    opts = bundle.get("options_vb", _default_options_vb())
    if int(opts.get("O", 1)) == 0:
        return

    Fm_store: dict[tuple[int, int, int], np.ndarray] = bundle.get("_vb_Fm_neg_t_o_m", {})
    O_shell = bundle["O"]
    Ng_arr = bundle["Ng"]
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])

    M_vec = np.asarray(M_row, dtype=np.int64).ravel()
    for mm in M_vec:
        mi = int(mm) - 1
        if mi < 0:
            continue
        md = models[mi]
        ng_m = int(Ng_arr[mi])
        n_mat = np.asarray(md.get("n", np.zeros((ng_m, t_int))), dtype=np.float64)
        if n_mat.size == 0:
            n_mat = np.zeros((ng_m, t_int), dtype=np.float64)
        if n_mat.ndim == 1:
            n_mat = n_mat.reshape(ng_m, -1)
        if n_mat.shape[0] < ng_m:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[: n_mat.shape[0], :] = n_mat
            n_mat = pad
        if n_mat.shape[1] < t_int:
            pad = np.zeros((ng_m, t_int), dtype=np.float64)
            pad[:, : n_mat.shape[1]] = n_mat
            n_mat = pad

        for g_idx in range(ng_m):
            if float(n_mat[g_idx, t_idx]) >= 0.0:
                continue
            acc: np.ndarray | None = None
            for j_other in range(nm):
                if j_other == mi:
                    continue
                key = (t_idx, g_idx, j_other)
                vec = Fm_store.get(key)
                if vec is None:
                    continue
                v = np.asarray(vec, dtype=np.float64).reshape(-1, 1)
                acc = v.copy() if acc is None else (acc + v)
            if acc is None:
                continue
            F = acc
            O_dist = np.asarray(spm_softmax(F), dtype=np.float64).reshape(-1, 1)
            po = np.asarray(spm_softmax(F * 512.0), dtype=np.float64).reshape(-1, 1)
            O_shell[mi][g_idx][t_idx] = O_dist
            md["o"][g_idx, t_idx] = float(_spm_sample(po))


def _vb_hierarchical_apply_S_as_O_if_present(child: dict[str, Any]) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1136–1151: if ``mdp.S`` (stimuli) is present after ``O``/``o`` are cleared,
    set ``mdp.O = mdp.S(:,seg(j))`` with ``j = (seg <= size(mdp.S,2))`` and
    ``seg = (1:mdp.T) + size(mdp.Q.O{mdp.L},2)`` when ``mdp.Q`` exists, else ``seg = (1:mdp.T)``.

    ``Q.O`` at level ``L`` is approximated as a list index ``L-1`` of prior outcome time-blocks (width = last axis).
    """
    if "S" not in child or child.get("S") is None:
        return
    S = np.asarray(child["S"], dtype=np.float64)
    if S.size == 0:
        return
    t_md = int(np.asarray(child.get("T", 1)).ravel()[0])
    L = max(1, int(np.asarray(child.get("L", 1)).ravel()[0]))
    S2 = S.reshape(S.shape[0], -1, order="F") if S.ndim >= 2 else S.reshape(-1, 1, order="F")
    n_col_s = int(S2.shape[1])
    prev_cols = 0
    qrec = child.get("Q")
    if isinstance(qrec, dict) and "O" in qrec:
        Oc = qrec.get("O")
        if isinstance(Oc, (list, tuple)) and len(Oc) >= L:
            try:
                ol = Oc[L - 1]
                arr = np.asarray(ol, dtype=np.float64)
                if arr.size and arr.ndim >= 2:
                    prev_cols = int(arr.shape[1])
            except Exception:
                prev_cols = 0
    seg = np.arange(1, t_md + 1, dtype=np.int64) + int(prev_cols)
    mask = seg <= n_col_s
    use = seg[mask]
    n_row = int(S2.shape[0])
    if use.size == 0:
        child["O"] = np.zeros((n_row, 0), dtype=np.float64, order="F")
        return
    idx0 = (use - 1).astype(np.int64, copy=False)
    child["O"] = np.asfortranarray(np.asarray(S2[:, idx0], dtype=np.float64))


def _vb_hierarchical_q_concat(existing: Any, new_value: Any) -> Any:
    """MATLAB ``[old new]`` append used for hierarchical ``mdp.Q`` records (~1186–1207)."""
    if existing is None:
        return copy.deepcopy(new_value)
    if isinstance(existing, list) and isinstance(new_value, list):
        return copy.deepcopy(existing) + copy.deepcopy(new_value)
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
            return copy.deepcopy(existing) + [copy.deepcopy(new_value)]
        if isinstance(new_value, list):
            return [copy.deepcopy(existing)] + copy.deepcopy(new_value)
        return [copy.deepcopy(existing), copy.deepcopy(new_value)]


def _vb_hierarchical_update_parent_Q_from_child(parent: dict[str, Any], child_upd: dict[str, Any]) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~1180–1209: update and append child trajectory record in ``mdp.Q``.
    """
    if "Q" not in child_upd:
        return
    qrec = copy.deepcopy(child_upd["Q"])
    if not isinstance(qrec, dict):
        parent["Q"] = qrec
        return
    L = max(1, int(np.asarray(child_upd.get("L", 1)).ravel()[0]))
    li = L - 1

    if "a" in child_upd:
        qa = qrec.get("a", [])
        if not isinstance(qa, list):
            qa = list(np.asarray(qa, dtype=object).ravel(order="F"))
        while len(qa) <= li:
            qa.append(None)
        qa[li] = copy.deepcopy(child_upd["a"])
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
            if ck not in child_upd:
                continue
            qv = qrec.get(qk, [])
            if not isinstance(qv, list):
                qv = list(np.asarray(qv, dtype=object).ravel(order="F"))
            while len(qv) <= li:
                qv.append(None)
            if qv[li] is None:
                qv[li] = copy.deepcopy(child_upd[ck])
            else:
                qv[li] = _vb_hierarchical_q_concat(qv[li], child_upd[ck])
            qrec[qk] = qv

        f_old = float(np.sum(np.asarray(qrec.get("F", 0.0), dtype=np.float64)))
        f_new = float(np.sum(np.asarray(child_upd.get("F", 0.0), dtype=np.float64)))
        qrec["F"] = f_old + f_new
    except Exception:
        for qk, ck in mapping.items():
            if ck not in child_upd:
                continue
            qv = qrec.get(qk, [])
            if not isinstance(qv, list):
                qv = list(np.asarray(qv, dtype=object).ravel(order="F"))
            while len(qv) <= li:
                qv.append(None)
            qv[li] = copy.deepcopy(child_upd[ck])
            qrec[qk] = qv
        qrec["F"] = float(np.sum(np.asarray(child_upd.get("F", 0.0), dtype=np.float64)))

    parent["Q"] = qrec


def _vb_hierarchical_subordinate_outcomes(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    t_idx: int,
    M_row: np.ndarray,
    recurse_partial: bool,
) -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~973+ (hierarchical ``MDP(m).MDP`` branch), partial Pass 1.

    Implemented here:
    - child extraction / B,D,E defaults
    - prior forwarding from child P/X into D/E
    - empirical prior updates from parent outcomes into child D/E (id.D/id.E)
    - non-process child path/state initial sampling
    - optional pass-through of ``MDP(m).Q`` to child
    - ``mdp.S`` → ``mdp.O`` transcription (~1138–1151) before child VB
    - process child with ``GV``: nested ``spm_action`` (~1087) then ``u``/``s`` narrowing (~1089–1105)
    - recurse into child ``spm_MDP_VB_XXX`` and map child posteriors back to parent O

    Still blocked:
    - none in this translated hierarchy window (~973–1210) beyond global partial-stub boundaries
    """
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

        mdp_field = parent["MDP"]
        if isinstance(mdp_field, list) and len(mdp_field) > 0:
            child = copy.deepcopy(mdp_field[0])
        elif isinstance(mdp_field, np.ndarray) and mdp_field.dtype == object and mdp_field.size > 0:
            child = copy.deepcopy(mdp_field.ravel(order="F")[0])
        elif isinstance(mdp_field, dict):
            child = copy.deepcopy(mdp_field)
        else:
            raise NotImplementedError("hierarchical MDP.MDP layout not yet supported")

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

        # ~1003–1074 update priors, initial states and paths of child
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
                    # MATLAB line ~1053 overwrite retained for fidelity.
                    child["D"][f] = _spm_norm(np.ones((int(ns_v[f]), 1), dtype=np.float64))

            id_child = child.get("id", {})
            idE = id_child.get("E", [])
            if isinstance(idE, (list, tuple)) and f < len(idE):
                for g in np.atleast_1d(np.asarray(idE[f], dtype=np.int64).ravel()).tolist():
                    j = spm_parents(bundle["id"][mi], int(g), [bundle["Q"][mi][ff][t_idx] for ff in range(len(bundle["Q"][mi]))])[0]
                    j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                    q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr]
                    po = np.asarray(spm_dot(bundle["A"][mi][int(g) - 1], q_list), dtype=np.float64).reshape(-1, 1)
                    child["E"][f] = _spm_multiply(child["E"][f], po)

            idD = id_child.get("D", [])
            if isinstance(idD, (list, tuple)) and f < len(idD):
                for g in np.atleast_1d(np.asarray(idD[f], dtype=np.int64).ravel()).tolist():
                    j = spm_parents(bundle["id"][mi], int(g), [bundle["Q"][mi][ff][t_idx] for ff in range(len(bundle["Q"][mi]))])[0]
                    j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                    q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr]
                    po = np.asarray(spm_dot(bundle["A"][mi][int(g) - 1], q_list), dtype=np.float64).reshape(-1, 1)
                    child["D"][f] = _spm_multiply(child["D"][f], po)

        # ~1077–1119 states and paths of child process
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
                for f in range(nfu):
                    if f < GU.size and float(GU[f]) != 0.0:
                        Ge = np.asarray(child["GE"][f], dtype=np.float64).reshape(-1, 1).copy()
                        Ge[:] = 0.0
                        uf = int(round(float(child["u"][f, 0])))
                        if 1 <= uf <= Ge.shape[0]:
                            Ge[uf - 1, 0] = 1.0
                        child["GE"][f] = Ge

                    GBf = np.asarray(child["GB"][f], dtype=np.float64)
                    sf = int(round(float(child["s"][f, 0])))
                    uf2 = int(round(float(child["u"][f, 0])))
                    child["GD"][f] = np.asarray(GBf[:, sf - 1, uf2 - 1], dtype=np.float64).reshape(-1, 1)
                    child["s"][f, 0] = float(_spm_sample(child["GD"][f]))
        else:
            child["u"] = np.ones((nf_i, 1), dtype=np.float64)
            child["s"] = np.ones((nf_i, 1), dtype=np.float64)
            for f in range(nf_i):
                child["u"][f, 0] = float(_spm_sample(np.asarray(child["E"][f], dtype=np.float64).reshape(-1, 1)))
                child["s"][f, 0] = float(_spm_sample(np.asarray(child["D"][f], dtype=np.float64).reshape(-1, 1)))

        if "Q" in parent:
            child["Q"] = copy.deepcopy(parent["Q"])
        child.pop("O", None)
        child.pop("o", None)
        _vb_hierarchical_apply_S_as_O_if_present(child)

        # MATLAB ~1160 recurses with full ``spm_MDP_VB_XXX(mdp)``; keep staged partial recurse only when parent run is partial.
        child_opts = {"_rgms_partial_ok": 1} if recurse_partial else {}
        child_upd = spm_MDP_VB_XXX(child, child_opts)

        id_child = child_upd.get("id", {})
        idD = id_child.get("D", [])
        for f in range(len(idD)):
            for g in np.atleast_1d(np.asarray(idD[f], dtype=np.int64).ravel()).tolist():
                O_shell[mi][int(g) - 1][t_idx] = np.asarray(child_upd["X"][f], dtype=np.float64)[:, 0:1]

        idE = id_child.get("E", [])
        for f in range(len(idE)):
            for g in np.atleast_1d(np.asarray(idE[f], dtype=np.int64).ravel()).tolist():
                Pf = np.asarray(child_upd["P"][f], dtype=np.float64)
                O_shell[mi][int(g) - 1][t_idx] = Pf[:, -1:].reshape(-1, 1)

        _vb_hierarchical_update_parent_Q_from_child(parent, child_upd)
        parent["MDP"] = child_upd


def _vb_build_partial_output(models: list[dict[str, Any]], bundle: dict[str, Any]) -> Any:
    """
    Internal staged return used for recursive child calls before full solver completion.

    Produces a MATLAB-like single-model struct shape from current partial state so
    hierarchical mapping can continue while the top-level function remains stubbed.
    """
    if len(models) != 1:
        return copy.deepcopy(models)
    out = copy.deepcopy(models[0])
    out["id"] = copy.deepcopy(bundle["id"][0])
    # ``~1693–1705``: ``X`` / ``P`` (paths ``S``) already assembled on ``models[0]`` by ``_vb_assemble_mdp_results_1691``.
    out["X"] = [np.asarray(x, dtype=np.float64).copy() for x in models[0]["X"]]
    out["P"] = [np.asarray(x, dtype=np.float64).copy() for x in models[0]["P"]]

    Q_cells: list[np.ndarray] = []
    for f in range(len(bundle["Q"][0])):
        cols = [np.asarray(bundle["Q"][0][f][t], dtype=np.float64).reshape(-1, 1) for t in range(int(bundle["T"]))]
        Q_cells.append(np.hstack(cols))
    out["Q"] = Q_cells
    if "Y" in models[0]:
        out["Y"] = copy.deepcopy(models[0]["Y"])
    if "j" in models[0]:
        out["j"] = copy.deepcopy(models[0]["j"])
    if "i" in models[0]:
        out["i"] = copy.deepcopy(models[0]["i"])
    for _k in ("xn", "wn", "dn", "un"):
        if _k in models[0]:
            out[_k] = copy.deepcopy(models[0][_k])
    if "sn" in models[0]:
        out["sn"] = copy.deepcopy(models[0]["sn"])
    out["_rgms_partial_v"] = 1
    return out


def _vb_run_partial_t_loop(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    alpha: float,
    recurse_partial: bool,
) -> None:
    """Per ``t``: generation → outcomes ~873–949 → ~952–969 → ``BP``/``IP`` → ``spm_forwards`` → belief."""
    M_upd = bundle["M_update"]
    t_int = int(bundle["T"])
    n_depth = int(bundle["N_policy_depth"])
    for t_idx in range(t_int):
        row = M_upd[t_idx, :]
        _vb_generation_paths_states_share(models, bundle, t_idx, row)
        _vb_generate_outcomes_if_options_o(models, bundle, t_idx, row)
        _vb_shared_probabilistic_outcomes(models, bundle, t_idx, row)
        _vb_hierarchical_subordinate_outcomes(models, bundle, t_idx, row, recurse_partial)
        _vb_fill_BP_IP_at_t(bundle, t_idx)
        t_m = t_idx + 1
        n_horiz = int(min(t_int, t_m + n_depth))
        bundle.setdefault("Pu_carry", [None] * int(bundle["Nm"]))
        Pu_carry: list[Any] = bundle["Pu_carry"]
        qa_b = bundle.get("qa")
        for mm in np.asarray(row, dtype=np.int64).ravel():
            if int(mm) < 1:
                continue
            mi = int(mm) - 1
            if not _vb_o_row_ready_for_model(bundle["O"][mi], t_idx):
                _vb_placeholder_pu_carry_softmax(bundle, np.array([int(mm)], dtype=np.int64), alpha)
                continue
            G_m, _, F_elbo, _, Pa_step = spm_forwards(
                bundle["O"],
                bundle["Q"],
                bundle["A"],
                bundle["BP"],
                bundle["C"],
                bundle["H"],
                bundle["K"],
                bundle["W"],
                bundle["IP"],
                t_m,
                t_int,
                n_horiz,
                int(mm),
                bundle["id"],
                bundle["pA"],
                qa_b,
            )
            Gw, Zt = _vb_belief_after_forwards(
                mi, bundle, t_m, t_idx, np.asarray(G_m, dtype=np.float64), float(alpha)
            )
            _vb_active_learning_in_loop(mi, models, bundle, t_idx, t_m)
            _vb_ensure_per_t_traces(models, mi, t_int)
            models[mi]["F"][t_idx] = float(F_elbo)
            models[mi]["G"][t_idx] = np.asarray(Gw, dtype=np.float64).copy()
            models[mi]["Z"][t_idx] = float(Zt)
            models[mi]["Pa"] = copy.deepcopy(Pa_step)
            _vb_in_loop_id_ig_and_sn(mi, bundle, t_idx)

        if t_idx + 1 == t_int:
            _vb_trim_mdp_o_s_u_at_terminal_horizon(models, bundle)


def _vb_optional_backwards_replay(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """MATLAB ~1463–1481: optional ``OPTIONS.B`` replay via ``spm_backwards``."""
    if int(options_vb.get("B", 0)) == 0:
        return
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    for mi in range(nm):
        u_row = np.asarray(bundle["Um"][mi], dtype=np.float64).ravel()
        nf_m = int(bundle["Nf"][mi])
        for f_idx in range(nf_m):
            if f_idx < u_row.size and int(u_row[f_idx]) == 0:
                p_last = copy.deepcopy(bundle["P"][mi][f_idx][t_int - 1])
                for t_idx in range(t_int):
                    bundle["P"][mi][f_idx][t_idx] = copy.deepcopy(p_last)

        Q_upd, P_upd, qa_upd, qb_upd, Fm = spm_backwards(
            bundle["O"],
            bundle["P"],
            bundle["Q"],
            bundle["D"],
            bundle["E"],
            bundle["pa"],
            bundle["pb"],
            bundle["Um"],
            mi + 1,
            bundle["id"],
        )
        bundle["Q"] = Q_upd
        bundle["P"] = P_upd
        bundle["qa"] = qa_upd
        bundle["qb"] = qb_upd
        models[mi]["F"] = np.asarray(Fm, dtype=np.float64).copy()


def _vb_mi_scalar_e(res: Any) -> float:
    """First element of ``spm_MDP_MI`` return (expected free-energy scalar)."""
    e = res[0] if isinstance(res, tuple) else res
    return float(np.asarray(e, dtype=np.float64).reshape(-1)[0])


def _vb_accumulate_dirichlet_parameter_learning(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """
    MATLAB ~1485–1587: accumulate Dirichlet parameters for ``a``/``b``/``c``/``d``/``e``
    and parameter KL terms ``Fa``–``Fe``. Posterior predictive ``Y`` is handled separately.
    """
    eta = float(hp["eta"])
    beta = float(hp["beta"])
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])

    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        nf_m = int(bundle["Nf"][mi])
        id_m = bundle["id"][mi]
        h_row = [bundle["H"][mi][ff] for ff in range(nf_m)]

        if "a" in md:
            for g_idx in range(ng_m):
                pa_mg = bundle["pa"][mi][g_idx]
                qa_mg = bundle["qa"][mi][g_idx]
                c_mg = bundle["C"][mi][g_idx]
                if beta != 0.0:
                    fa = np.zeros((2, 1), dtype=np.float64)
                    fa[0, 0] = _vb_mi_scalar_e(spm_MDP_MI(pa_mg, c_mg, h_row))
                    fa[1, 0] = _vb_mi_scalar_e(spm_MDP_MI(qa_mg, c_mg, h_row))
                    pa_w = spm_softmax(fa, beta)
                else:
                    pa_w = np.array([[0.0], [1.0]], dtype=np.float64)
                blend = (
                    pa_w[0, 0] * np.asarray(pa_mg, dtype=np.float64)
                    + pa_w[1, 0] * np.asarray(qa_mg, dtype=np.float64)
                ) * eta / (eta + pa_w[1, 0])
                ag = md["a"][g_idx]
                if isinstance(ag, (list, tuple)) and len(ag) == 1:
                    md["a"][g_idx] = [np.asarray(blend, dtype=np.float64).copy()]
                else:
                    md["a"][g_idx] = np.asarray(blend, dtype=np.float64).copy()

        if "b" in md:
            for f_idx in range(nf_m):
                pb_mf = bundle["pb"][mi][f_idx]
                qb_mf = bundle["qb"][mi][f_idx]
                h_mf = bundle["H"][mi][f_idx]
                if beta != 0.0:
                    fa_b = np.zeros((2, 1), dtype=np.float64)
                    # MATLAB ``spm_MI(pb,H)``: two-arg call maps to ``spm_MDP_MI``'s ``c`` slot.
                    fa_b[0, 0] = _vb_mi_scalar_e(spm_MDP_MI(pb_mf, h_mf))
                    fa_b[1, 0] = _vb_mi_scalar_e(spm_MDP_MI(qb_mf, h_mf))
                    pa_w = spm_softmax(fa_b, beta)
                else:
                    pa_w = np.array([[0.0], [1.0]], dtype=np.float64)
                blend_b = (
                    pa_w[0, 0] * np.asarray(pb_mf, dtype=np.float64)
                    + pa_w[1, 0] * np.asarray(qb_mf, dtype=np.float64)
                ) * eta / (eta + pa_w[1, 0])
                bf = md["b"][f_idx]
                if isinstance(bf, (list, tuple)) and len(bf) == 1:
                    md["b"][f_idx] = [np.asarray(blend_b, dtype=np.float64).copy()]
                else:
                    md["b"][f_idx] = np.asarray(blend_b, dtype=np.float64).copy()

        if "c" in md:
            for g_1b in np.ravel(spm_children(id_m)).astype(np.int64):
                g_idx = int(g_1b) - 1
                if g_idx < 0 or g_idx >= ng_m:
                    continue
                dc = np.asarray(bundle["O"][mi][g_idx][t_int - 1], dtype=np.float64)
                pc_mg = np.asarray(bundle["pc"][mi][g_idx], dtype=np.float64)
                if dc.size == 0 or pc_mg.size == 0:
                    continue
                dc = dc.reshape(pc_mg.shape) * (pc_mg > 0)
                c_new = (pc_mg + dc) * eta / (eta + 1.0)
                cg = md["c"][g_idx]
                if isinstance(cg, (list, tuple)) and len(cg) == 1:
                    md["c"][g_idx] = [np.asarray(c_new, dtype=np.float64).copy()]
                else:
                    md["c"][g_idx] = np.asarray(c_new, dtype=np.float64).copy()

        if "d" in md:
            for f_idx in range(nf_m):
                dd = np.asarray(bundle["Q"][mi][f_idx][0], dtype=np.float64)
                pd_mf = np.asarray(bundle["pd"][mi][f_idx], dtype=np.float64)
                if dd.size == 0 or pd_mf.size == 0:
                    continue
                dd = dd.reshape(pd_mf.shape) * (pd_mf > 0)
                d_new = (pd_mf + dd) * eta / (eta + 1.0)
                df = md["d"][f_idx]
                if isinstance(df, (list, tuple)) and len(df) == 1:
                    md["d"][f_idx] = [np.asarray(d_new, dtype=np.float64).copy()]
                else:
                    md["d"][f_idx] = np.asarray(d_new, dtype=np.float64).copy()

        if "e" in md:
            for f_idx in range(nf_m):
                de = np.asarray(bundle["P"][mi][f_idx][0], dtype=np.float64)
                pe_mf = np.asarray(bundle["pe"][mi][f_idx], dtype=np.float64)
                if de.size == 0 or pe_mf.size == 0:
                    continue
                de = de.reshape(pe_mf.shape) * (pe_mf > 0)
                e_new = (pe_mf + de) * eta / (eta + 1.0)
                ef = md["e"][f_idx]
                if isinstance(ef, (list, tuple)) and len(ef) == 1:
                    md["e"][f_idx] = [np.asarray(e_new, dtype=np.float64).copy()]
                else:
                    md["e"][f_idx] = np.asarray(e_new, dtype=np.float64).copy()

        learn_any = any(k in md for k in ("a", "b", "c", "d", "e"))
        if learn_any:
            md["Fa"] = np.zeros(ng_m, dtype=np.float64)
            md["Fb"] = np.zeros(nf_m, dtype=np.float64)
            md["Fc"] = np.zeros(ng_m, dtype=np.float64)
            md["Fd"] = np.zeros(nf_m, dtype=np.float64)
            md["Fe"] = np.zeros(nf_m, dtype=np.float64)

            for g_idx in range(ng_m):
                if "a" in md:
                    amg = md["a"][g_idx]
                    amg = amg[0] if isinstance(amg, (list, tuple)) and len(amg) == 1 else amg
                    pam = bundle["pa"][mi][g_idx]
                    md["Fa"][g_idx] = -float(
                        spm_KL_dir(np.asarray(amg, dtype=np.float64), np.asarray(pam, dtype=np.float64))
                    )
                if "c" in md:
                    cmg = md["c"][g_idx]
                    cmg = cmg[0] if isinstance(cmg, (list, tuple)) and len(cmg) == 1 else cmg
                    pcm = bundle["pc"][mi][g_idx]
                    md["Fc"][g_idx] = -float(
                        spm_KL_dir(np.asarray(cmg, dtype=np.float64), np.asarray(pcm, dtype=np.float64))
                    )

            for f_idx in range(nf_m):
                if "b" in md:
                    bmf = md["b"][f_idx]
                    bmf = bmf[0] if isinstance(bmf, (list, tuple)) and len(bmf) == 1 else bmf
                    pbm = bundle["pb"][mi][f_idx]
                    md["Fb"][f_idx] = -float(
                        spm_KL_dir(np.asarray(bmf, dtype=np.float64), np.asarray(pbm, dtype=np.float64))
                    )
                if "d" in md:
                    dmf = md["d"][f_idx]
                    dmf = dmf[0] if isinstance(dmf, (list, tuple)) and len(dmf) == 1 else dmf
                    pdm = bundle["pd"][mi][f_idx]
                    md["Fd"][f_idx] = -float(
                        spm_KL_dir(np.asarray(dmf, dtype=np.float64), np.asarray(pdm, dtype=np.float64))
                    )
                if "e" in md:
                    emf = md["e"][f_idx]
                    emf = emf[0] if isinstance(emf, (list, tuple)) and len(emf) == 1 else emf
                    pem = bundle["pe"][mi][f_idx]
                    md["Fe"][f_idx] = -float(
                        spm_KL_dir(np.asarray(emf, dtype=np.float64), np.asarray(pem, dtype=np.float64))
                    )


def _vb_q_row_for_parents(Qmi: list, t_idx: int) -> list:
    """MATLAB ``Q(m,:,t)`` as a list of length ``Nf`` (one entry per factor)."""
    return [Qmi[ff][t_idx] for ff in range(len(Qmi))]


def _vb_posterior_predictive_Y(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """MATLAB ~1591–1606: optional posterior predictive ``Y`` plus ``j`` / ``i`` bookkeeping."""
    if int(options_vb.get("Y", 0)) == 0:
        return
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        if ng_m <= 0:
            continue
        max_o = int(np.max(bundle["No"][mi]))
        if max_o < 1:
            max_o = 1
        md["Y"] = [[None for _ in range(t_int)] for _ in range(max_o)]
        md["j"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        md["i"] = [[None for _ in range(t_int)] for _ in range(ng_m)]
        id_m = bundle["id"][mi]
        for g_1b in range(1, ng_m + 1):
            g_idx = g_1b - 1
            Ag = bundle["A"][mi][g_idx]
            for t_idx in range(t_int):
                Qrow = _vb_q_row_for_parents(bundle["Q"][mi], t_idx)
                j, i_ch = spm_parents(id_m, g_1b, Qrow)
                md["j"][g_idx][t_idx] = copy.deepcopy(j)
                md["i"][g_idx][t_idx] = copy.deepcopy(i_ch)
                if callable(Ag):
                    raise NotImplementedError(
                        "spm_MDP_VB_XXX: OPTIONS.Y with likelihood function_handle A{g} is not translated yet"
                    )
                j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
                q_list = [bundle["Q"][mi][int(jj) - 1][t_idx] for jj in j_arr.tolist()]
                pred = np.asarray(
                    spm_dot(np.asarray(Ag, dtype=np.float64), q_list),
                    dtype=np.float64,
                ).reshape(-1, 1)
                for o in np.atleast_1d(np.asarray(i_ch, dtype=np.float64).ravel()):
                    o_int = int(np.round(float(o)))
                    if o_int < 1 or o_int > max_o:
                        continue
                    md["Y"][o_int - 1][t_idx] = pred.copy()


def _vb_reorganize_X_S_from_QP(bundle: dict[str, Any]) -> None:
    """MATLAB ~1613–1617: ``X{m,f}(:,t) = Q{m,f,t}``, ``S{m,f}(:,t) = P{m,f,t}``."""
    t_int = int(bundle["T"])
    nm = int(bundle["Nm"])
    for mi in range(nm):
        nf_m = int(bundle["Nf"][mi])
        for f_idx in range(nf_m):
            Xmf = bundle["X"][mi][f_idx]
            Smf = bundle["S"][mi][f_idx]
            nrx, ncx = Xmf.shape
            nrs, ncs = Smf.shape
            for t_idx in range(t_int):
                qcol = np.asarray(bundle["Q"][mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1)
                pcol = np.asarray(bundle["P"][mi][f_idx][t_idx], dtype=np.float64).reshape(-1, 1)
                if qcol.shape[0] == nrx and ncx > t_idx:
                    Xmf[:, t_idx : t_idx + 1] = qcol
                if pcol.shape[0] == nrs and ncs > t_idx:
                    Smf[:, t_idx : t_idx + 1] = pcol


def _vb_options_N_neural_simulated_responses(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options_vb: dict[str, Any],
) -> None:
    """MATLAB ~1623–1688: simulated electrophysiological responses when ``OPTIONS.N``."""
    if int(options_vb.get("N", 0)) == 0:
        return

    n = 16
    nm = int(bundle["Nm"])
    t_int = int(bundle["T"])
    Np_arr = bundle["Np"]
    Ns_arr = bundle["Ns"]

    for mi in range(nm):
        md = models[mi]
        nf_m = int(bundle["Nf"][mi])
        npp = int(Np_arr[mi])
        w_row = np.asarray(bundle["w_policy"][mi], dtype=np.float64).reshape(-1)
        R_mat = np.asarray(bundle["R_policy"][mi], dtype=np.float64)
        if R_mat.ndim == 1:
            R_mat = R_mat.reshape(-1, 1)

        h_exp = np.exp(-(np.arange(n, dtype=np.float64)) / 2.0)
        h_exp = h_exp / np.sum(h_exp)
        hz = np.asarray(spm_zeros(h_exp.reshape(-1, 1)), dtype=np.float64).ravel()
        kern = np.concatenate([hz, h_exp.ravel()])
        wn = np.kron(w_row.reshape(1, -1), np.ones((1, n))).ravel()
        wn = np.convolve(wn, kern, mode="same")
        dn = np.gradient(wn.astype(np.float64))

        x_axis = np.arange(0, n, dtype=np.float64)
        h_gamma = np.asarray(spm_Gcdf(x_axis, float(n) / 4.0, 1.0), dtype=np.float64).ravel()
        if h_gamma.size != n:
            h_gamma = np.reshape(h_gamma, (-1,))[:n]

        xn_cells: list[np.ndarray] = []
        for f_idx in range(nf_m):
            ns_mf = int(Ns_arr[mi, f_idx])
            xnf = np.zeros((n, ns_mf, t_int, t_int), dtype=np.float64)
            snmf = bundle["sn"][mi][f_idx]
            if snmf is None:
                snmf = np.zeros((max(1, ns_mf), t_int, t_int), dtype=np.float64)
            for ii in range(ns_mf):
                for j in range(t_int):
                    for k in range(t_int):
                        if k == 0:
                            h0 = 1.0 / max(ns_mf, 1)
                        else:
                            h0 = float(snmf[ii, j, k - 1])
                        ht = float(snmf[ii, j, k])
                        xnf[:, ii, j, k] = h_gamma * (ht - h0) + h0
            xn_cells.append(xnf)

        # MATLAB ~1663–1670: ``f`` left over from last ``for f = 1:Nf(m)`` loop is ``Nf(m)`` only.
        f_last = nf_m - 1
        xnf_last = xn_cells[f_last]
        for i in range(n):
            for j in range(t_int):
                for k in range(t_int):
                    row = xnf_last[i, :, j, k].reshape(-1, 1)
                    xnf_last[i, :, j, k] = np.asarray(_spm_norm(row), dtype=np.float64).ravel()
        xn_cells[f_last] = xnf_last

        u0 = np.asarray(spm_softmax(np.ones((max(npp, 1), 1))), dtype=np.float64).reshape(-1, 1)
        un_m = np.zeros((npp, max((t_int - 1) * n, 1)), dtype=np.float64)
        for k_pol in range(npp):
            for t_m in range(1, t_int):
                if t_m == 1:
                    h0 = float(u0[k_pol, 0])
                else:
                    h0 = float(R_mat[k_pol, t_m - 2])
                ht = float(R_mat[k_pol, t_m - 1])
                jcols = np.arange(n, dtype=np.int64) + (t_m - 1) * n
                un_m[k_pol, jcols] = h_gamma * (ht - h0) + h0

        md["xn"] = xn_cells
        md["wn"] = np.asarray(wn, dtype=np.float64).copy()
        md["dn"] = np.asarray(dn, dtype=np.float64).copy()
        md["un"] = np.asarray(un_m, dtype=np.float64).copy()


def _vb_shiftdim_o_ng_t_cells(O_mi: list[list[Any]], ng: int, t_int: int) -> list[list[Any]]:
    """
    MATLAB ``shiftdim(O, 1)`` on an ``Ng×T`` cell block → ``T×Ng`` (same cells, permuted indices).

    Internal ``O{m,g,t}`` uses Python layout ``O_mi[g][t]``; returned layout is ``out[t][g]``.
    """
    return [[copy.deepcopy(O_mi[g][t]) for g in range(ng)] for t in range(t_int)]


def _vb_normalize_AB_from_ab_if_missing(md: dict[str, Any], ng_m: int, nf_m: int) -> None:
    """MATLAB ~1710–1718: fill ``A``/``B`` from Dirichlet ``a``/``b`` when explicit tensors absent."""
    if "a" in md and "A" not in md:
        md["A"] = []
        for g_idx in range(ng_m):
            ag = md["a"][g_idx]
            ag = ag[0] if isinstance(ag, (list, tuple)) and len(ag) == 1 else ag
            md["A"].append(np.asarray(_spm_norm(np.asarray(ag, dtype=np.float64)), dtype=np.float64).copy())
    if "b" in md and "B" not in md:
        md["B"] = []
        for f_idx in range(nf_m):
            bf = md["b"][f_idx]
            bf = bf[0] if isinstance(bf, (list, tuple)) and len(bf) == 1 else bf
            md["B"].append(np.asarray(_spm_norm(np.asarray(bf, dtype=np.float64)), dtype=np.float64).copy())


def _vb_assemble_mdp_results_1691(models: list[dict[str, Any]], bundle: dict[str, Any]) -> None:
    """
    MATLAB ~1691–1718 (plus ~1721–1730 when ``OPTIONS.N`` filled ``xn``/``un``/``wn``/``dn`` on ``md``): populate ``MDP(m)``
    fields before plot/aux sections.

    Uses bundle ``R_policy`` / ``v_policy`` / ``w_policy`` (belief bookkeeping), ``V`` as policies ``U``,
    ``shiftdim`` on ``O``, and optional ``A``/``B`` from ``a``/``b``.
    """
    nm = int(bundle["Nm"])
    for mi in range(nm):
        md = models[mi]
        ng_m = int(bundle["Ng"][mi])
        nf_m = int(bundle["Nf"][mi])
        t_int = int(bundle["T"])
        md["T"] = float(t_int)
        md["U"] = copy.deepcopy(bundle["V"][mi])
        md["R"] = np.asarray(bundle["R_policy"][mi], dtype=np.float64).copy()
        md["X"] = [np.asarray(bundle["X"][mi][f], dtype=np.float64).copy() for f in range(nf_m)]
        md["P"] = [np.asarray(bundle["S"][mi][f], dtype=np.float64).copy() for f in range(nf_m)]
        md["O"] = _vb_shiftdim_o_ng_t_cells(bundle["O"][mi], ng_m, t_int)
        md["v"] = np.asarray(bundle["v_policy"][mi], dtype=np.float64).reshape(1, -1).copy()
        md["w"] = np.asarray(bundle["w_policy"][mi], dtype=np.float64).reshape(1, -1).copy()
        md["id"] = copy.deepcopy(bundle["id"][mi])
        opts_a = bundle.get("options_vb", _default_options_vb())
        if int(opts_a.get("N", 0)) != 0 and "sn" in bundle:
            md["sn"] = [
                copy.deepcopy(bundle["sn"][mi][f]) if bundle["sn"][mi][f] is not None else None
                for f in range(nf_m)
            ]
        _vb_normalize_AB_from_ab_if_missing(md, ng_m, nf_m)


def _vb_init_QXSP_outcomes_and_process(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    options: dict[str, Any],
    chi: float,
) -> dict[str, Any]:
    """
    MATLAB ~652–733: ``Q``/``X``/``S``/``P``/``sn``, ``s``/``u``/``o`` matrices,
    probabilistic ``O`` outcome sampling, ``GP`` ``GV``/``chi`` on process models.
    """
    nm = int(bundle["Nm"])
    Ng = bundle["Ng"]
    Nf = bundle["Nf"]
    NF = bundle["NF"]
    Ns = bundle["Ns"]
    D_t = bundle["D"]
    E_t = bundle["E"]
    O_shell = bundle["O"]
    proc = bundle["process"]

    t_int = int(bundle["T"])

    Q: list[list[list[Any]]] = []
    X: list[list[np.ndarray]] = []
    S: list[list[np.ndarray]] = []
    P: list[list[list[Any]]] = []
    sn: list[list[np.ndarray | None]] = []
    opt_neural = int(options.get("N", 0)) != 0

    for m in range(nm):
        md = models[m]
        nf_m = int(Nf[m])
        ng_m = int(Ng[m])
        nf_proc = int(NF[m])

        Q.append([])
        X.append([])
        S.append([])
        P.append([])
        sn.append([])

        for f_idx in range(nf_m):
            Dmf = D_t[m][f_idx]
            Emf = E_t[m][f_idx]
            D_arr = np.asarray(Dmf, dtype=np.float64) if Dmf is not None else np.zeros((0, 0), dtype=np.float64)
            E_arr = np.asarray(Emf, dtype=np.float64) if Emf is not None else np.zeros((0, 0), dtype=np.float64)

            Q[m].append([copy.deepcopy(Dmf) for _ in range(t_int)])

            if D_arr.size == 0:
                Xmf = np.zeros((0, t_int), dtype=np.float64)
            else:
                dcol = np.asarray(D_arr.reshape(-1, 1, order="F"), dtype=np.float64)
                Xmf = np.tile(dcol, (1, t_int))
            X[m].append(Xmf)

            if E_arr.size == 0:
                Smf = np.zeros((0, t_int), dtype=np.float64)
            else:
                ecol = np.asarray(E_arr.reshape(-1, 1, order="F"), dtype=np.float64)
                Smf = np.tile(ecol, (1, t_int))
            S[m].append(Smf)

            if opt_neural:
                ns_mf = int(Ns[m, f_idx])
                if ns_mf > 0:
                    sn_mf = np.zeros((ns_mf, t_int, t_int), dtype=np.float64) + (1.0 / ns_mf)
                else:
                    sn_mf = np.zeros((0, t_int, t_int), dtype=np.float64)
                sn[m].append(sn_mf)
            else:
                sn[m].append(None)

            P[m].append([copy.deepcopy(Emf) for _ in range(t_int)])

        _vb_mdp_field_matrix(md, "s", nf_proc, t_int)
        _vb_mdp_field_matrix(md, "u", nf_proc, t_int)
        _vb_mdp_field_matrix(md, "o", ng_m, t_int)

        if "O" in md:
            options["O"] = False
            O_src = md["O"]
            for g_idx in range(ng_m):
                for t_idx in range(t_int):
                    try:
                        entry = _get_mdp_O_gt(O_src, g_idx, t_idx)
                        O_shell[m][g_idx][t_idx] = entry
                        md["o"][g_idx, t_idx] = float(_spm_sample(entry))
                    except Exception:
                        O_shell[m][g_idx][t_idx] = []
                        options["O"] = True

    for m in range(nm):
        if proc[m] > 0:
            models[m]["GV"] = bundle["GV"][m]
            models[m]["chi"] = chi

    return {"Q": Q, "X": X, "S": S, "P": P, "sn": sn}


def _any_u_factor_cols(U: np.ndarray, factor_cols_1based: np.ndarray) -> bool:
    """MATLAB ``any(MDP.U(:,f))`` for columns ``f`` (1-based)."""
    fc = np.asarray(factor_cols_1based, dtype=np.int64).ravel()
    if fc.size == 0:
        return False
    cols = fc - 1
    uu = np.asarray(U, dtype=np.float64)
    if uu.ndim == 1:
        uu = uu.reshape(1, -1)
    return bool(np.any(uu[:, cols]))


def _vb_tensors_through_H(
    models: list[dict],
    nm: int,
    t_h: float,
) -> dict[str, Any]:
    """
    MATLAB ~302–652: GP/id sizing, allocate ``O`` / likelihood / transition tensors through ``H``,
    then ``id`` domains / ``GV`` / ``V`` / ``spm_combinations``.

    Stops before ``Q`` / ``X`` / ``S`` / ``P`` (call ``_vb_init_QXSP_outcomes_and_process`` in the entrypoint).
    """
    proc = np.array([1.0 if _spm_is_process(models[m]) else 0.0 for m in range(nm)])
    gp: list[dict[str, Any]] = [{} for _ in range(nm)]
    id_list: list[dict[str, Any]] = []
    ID_list: list[dict[str, Any]] = []

    Ng = np.zeros(nm, dtype=np.int64)
    Nf = np.zeros(nm, dtype=np.int64)
    NG = np.zeros(nm, dtype=np.int64)
    NF = np.zeros(nm, dtype=np.int64)

    max_guess_ng = 1
    max_guess_nf = 1
    for m in range(nm):
        md = models[m]
        max_guess_ng = max(max_guess_ng, len(md.get("A", [])))
        max_guess_nf = max(max_guess_nf, len(md.get("B", [])))

    No = np.zeros((nm, max_guess_ng), dtype=np.int64)
    Ns = np.zeros((nm, max_guess_nf), dtype=np.int64)
    Nu = np.zeros((nm, max_guess_nf), dtype=np.int64)
    NS = np.zeros((nm, max_guess_nf), dtype=np.int64)
    NU = np.zeros((nm, max_guess_nf), dtype=np.int64)

    for m in range(nm):
        md = models[m]
        gpm = gp[m]
        if proc[m] > 0:
            gpm["A"] = md["GA"]
            gpm["B"] = md["GB"]
            gpm["U"] = md["GU"]
            id_m = copy.deepcopy(md["id"])
            id_list.append(id_m)
            if "ID" in md:
                ID_m = copy.deepcopy(md["ID"])
            else:
                n_g = len(gpm["A"])
                NG[m] = n_g
                ID_m = {
                    "g": [np.arange(1, n_g + 1, dtype=np.int64)],
                    "A": [],
                }
                for g_idx in range(n_g):
                    Ag = gpm["A"][g_idx]
                    Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
                    nda = int(matlab_ndims(np.asarray(Ag)))
                    ID_m["A"].append(np.arange(1, nda, dtype=np.int64))
                md["ID"] = ID_m
            ID_list.append(copy.deepcopy(md["ID"]))
        else:
            gpm["A"] = md["A"]
            gpm["B"] = md["B"]
            gpm["D"] = md["D"]
            gpm["E"] = md["E"]
            gpm["U"] = md["U"]
            id_m = copy.deepcopy(md["id"])
            id_list.append(id_m)
            ID_m = copy.deepcopy(md["id"])
            ID_list.append(ID_m)

        Ng[m] = len(md["A"])
        Nf[m] = len(md["B"])
        NG[m] = len(gpm["A"])
        NF[m] = len(gpm["B"])

        for g_idx in range(int(Ng[m])):
            Ag = md["A"][g_idx]
            Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
            No[m, g_idx] = int(np.asarray(Ag).shape[0])
        for f_idx in range(int(Nf[m])):
            Bg = md["B"][f_idx]
            Bg = Bg[0] if isinstance(Bg, list) and len(Bg) == 1 else Bg
            Barr = np.asarray(Bg)
            Ns[m, f_idx] = int(Barr.shape[0])
            Nu[m, f_idx] = _b_nu_third_dim(Barr)

        for f_idx in range(int(NF[m])):
            GBf = gpm["B"][f_idx]
            GBf = GBf[0] if isinstance(GBf, list) and len(GBf) == 1 else GBf
            Barr = np.asarray(GBf)
            NS[m, f_idx] = int(Barr.shape[0])
            NU[m, f_idx] = _b_nu_third_dim(Barr)

        if proc[m] > 0:
            if "GD" in md:
                gpm["D"] = md["GD"]
            else:
                gpm["D"] = []
                for _ in range(int(NF[m])):
                    gpm["D"].append(None)
                for f_idx in range(int(NF[m])):
                    gpm["D"][f_idx] = _spm_norm(np.ones((int(NS[m, f_idx]), 1), dtype=np.float64))
            if "GE" in md:
                gpm["E"] = md["GE"]
            else:
                gpm["E"] = []
                for _ in range(int(NF[m])):
                    gpm["E"].append(None)
                for f_idx in range(int(NF[m])):
                    gpm["E"][f_idx] = _spm_norm(np.ones((int(NU[m, f_idx]), 1), dtype=np.float64))

    max_ng = int(np.max(Ng))
    max_nf = int(np.max(Nf))
    t_int = max(1, int(round(float(t_h))))

    O = [[[None for _ in range(t_int)] for _ in range(max_ng)] for _ in range(nm)]

    def cell_nm_ng() -> list[list[Any]]:
        return [[None for _ in range(max_ng)] for _ in range(nm)]

    def cell_nm_nf() -> list[list[Any]]:
        return [[None for _ in range(max_nf)] for _ in range(nm)]

    A_t = cell_nm_ng()
    qa_t = cell_nm_ng()
    pa_t = cell_nm_ng()
    C_t = cell_nm_ng()
    qc_t = cell_nm_ng()
    pc_t = cell_nm_ng()
    K_t = cell_nm_ng()
    W_t = cell_nm_ng()

    B_t = cell_nm_nf()
    qb_t = cell_nm_nf()
    pb_t = cell_nm_nf()
    D_t = cell_nm_nf()
    qd_t = cell_nm_nf()
    pd_t = cell_nm_nf()
    E_t = cell_nm_nf()
    qe_t = cell_nm_nf()
    pe_t = cell_nm_nf()
    H_t = cell_nm_nf()
    qh_t = cell_nm_nf()
    ph_t = cell_nm_nf()
    I_t = cell_nm_nf()

    pA_rows: list[list[Any]] = []

    for m in range(nm):
        md = models[m]
        ng_m = int(Ng[m])
        nf_m = int(Nf[m])

        if "pA" in md:
            pA_rows.append(copy.deepcopy(md["pA"]))
        else:
            pA_rows.append([None] * ng_m)

        U_arr = _vb_mdp_U_as_float_array(md)

        for g_idx in range(ng_m):
            id_ag = _unwrap_id_a_entry(md["id"]["A"][g_idx])
            f_parents = np.asarray(id_ag, dtype=np.int64).ravel()

            if "a" in md:
                qa_mg = md["a"][g_idx]
                qa_mg = qa_mg[0] if isinstance(qa_mg, list) and len(qa_mg) == 1 else qa_mg
            else:
                Ag = md["A"][g_idx]
                Ag = Ag[0] if isinstance(Ag, list) and len(Ag) == 1 else Ag
                Ag_arr = np.asarray(Ag)
                if np.issubdtype(Ag_arr.dtype, np.number) and Ag_arr.dtype != bool:
                    qa_mg = Ag_arr.astype(np.float64) * 512.0
                else:
                    qa_mg = Ag

            pa_t[m][g_idx] = qa_mg
            qa_t[m][g_idx] = qa_mg

            A_norm = _spm_norm(qa_mg)
            if "A" in md:
                Agf = md["A"][g_idx]
                Agf = Agf[0] if isinstance(Agf, list) and len(Agf) == 1 else Agf
                if isinstance(Agf, np.ndarray) and Agf.dtype == bool:
                    A_norm = A_norm.astype(bool)
            A_t[m][g_idx] = A_norm

            if _any_u_factor_cols(U_arr, f_parents):
                if "a" in md:
                    qa_src = md["a"][g_idx]
                    qa_src = qa_src[0] if isinstance(qa_src, list) and len(qa_src) == 1 else qa_src
                    W_t[m][g_idx] = _spm_wnorm(qa_src)
                K_t[m][g_idx] = _spm_hnorm(A_norm)

            if "c" in md:
                qc_m = md["c"][g_idx]
                qc_m = qc_m[0] if isinstance(qc_m, list) and len(qc_m) == 1 else qc_m
            elif "C" in md:
                Cg = md["C"][g_idx]
                Cg = Cg[0] if isinstance(Cg, list) and len(Cg) == 1 else Cg
                qc_m = np.asarray(Cg, dtype=np.float64) * 512.0
            else:
                qc_m = np.zeros((0, 0), dtype=np.float64)

            qc_t[m][g_idx] = qc_m
            pc_t[m][g_idx] = qc_m

            if isinstance(qc_m, np.ndarray) and qc_m.size == 0:
                C_t[m][g_idx] = qc_m
            else:
                C_t[m][g_idx] = _spm_norm(qc_m)

        for f_idx in range(nf_m):
            if "b" in md:
                qb_m = md["b"][f_idx]
                qb_m = qb_m[0] if isinstance(qb_m, list) and len(qb_m) == 1 else qb_m
            else:
                Bg = md["B"][f_idx]
                Bg = Bg[0] if isinstance(Bg, list) and len(Bg) == 1 else Bg
                qb_m = np.asarray(Bg, dtype=np.float64) * 512.0

            qb_t[m][f_idx] = qb_m
            pb_t[m][f_idx] = qb_m

            B_norm = _spm_norm(qb_m)
            if "B" in md:
                Bgf = md["B"][f_idx]
                Bgf = Bgf[0] if isinstance(Bgf, list) and len(Bgf) == 1 else Bgf
                if isinstance(Bgf, np.ndarray) and Bgf.dtype == bool:
                    B_norm = B_norm.astype(bool)
            B_t[m][f_idx] = B_norm

            if "b" in md:
                if bool(np.any(U_arr[:, f_idx])):
                    qb_src = md["b"][f_idx]
                    qb_src = qb_src[0] if isinstance(qb_src, list) and len(qb_src) == 1 else qb_src
                    I_t[m][f_idx] = _spm_wnorm(qb_src)

            if "d" in md:
                qd_m = md["d"][f_idx]
                qd_m = qd_m[0] if isinstance(qd_m, list) and len(qd_m) == 1 else qd_m
            elif "D" in md:
                Dg = md["D"][f_idx]
                Dg = Dg[0] if isinstance(Dg, list) and len(Dg) == 1 else Dg
                qd_m = np.asarray(Dg, dtype=np.float64) * 512.0
            else:
                qd_m = np.ones((int(Ns[m, f_idx]), 1), dtype=np.float64)

            qd_t[m][f_idx] = qd_m
            pd_t[m][f_idx] = qd_m
            D_t[m][f_idx] = _spm_norm(qd_m)

            if "e" in md:
                qe_m = md["e"][f_idx]
                qe_m = qe_m[0] if isinstance(qe_m, list) and len(qe_m) == 1 else qe_m
            elif "E" in md:
                Eg = md["E"][f_idx]
                Eg = Eg[0] if isinstance(Eg, list) and len(Eg) == 1 else Eg
                qe_m = np.asarray(Eg, dtype=np.float64) * 512.0
            else:
                qe_m = np.ones((int(Nu[m, f_idx]), 1), dtype=np.float64)

            qe_t[m][f_idx] = qe_m
            pe_t[m][f_idx] = qe_m
            E_t[m][f_idx] = _spm_norm(qe_m)

            if "h" in md:
                qh_m = md["h"][f_idx]
                qh_m = qh_m[0] if isinstance(qh_m, list) and len(qh_m) == 1 else qh_m
            elif "H" in md:
                Hg = md["H"][f_idx]
                Hg = Hg[0] if isinstance(Hg, list) and len(Hg) == 1 else Hg
                qh_m = np.asarray(Hg, dtype=np.float64) * 512.0
            else:
                qh_m = np.zeros((0, 0), dtype=np.float64)

            qh_t[m][f_idx] = qh_m
            ph_t[m][f_idx] = qh_m

            if isinstance(qh_m, np.ndarray) and qh_m.size == 0:
                H_t[m][f_idx] = qh_m
            else:
                H_t[m][f_idx] = _spm_norm(qh_m)

    pol = _vb_id_and_policy_blocks(
        nm=nm,
        models=models,
        Ng=Ng,
        Nf=Nf,
        NF=NF,
        NU=NU,
        Nu=Nu,
        K_t=K_t,
        W_t=W_t,
        H_t=H_t,
        I_t=I_t,
        gp=gp,
        id_list=id_list,
        ID_list=ID_list,
    )

    return {
        "Nm": nm,
        "T": t_int,
        "Ng": Ng,
        "Nf": Nf,
        "No": No,
        "Ns": Ns,
        "Nu": Nu,
        "NG": NG,
        "NF": NF,
        "NS": NS,
        "NU": NU,
        "process": proc,
        "gp": gp,
        "id": id_list,
        "ID": ID_list,
        "O": O,
        "A": A_t,
        "qa": qa_t,
        "pa": pa_t,
        "C": C_t,
        "qc": qc_t,
        "pc": pc_t,
        "K": K_t,
        "W": W_t,
        "B": B_t,
        "qb": qb_t,
        "pb": pb_t,
        "D": D_t,
        "qd": qd_t,
        "pd": pd_t,
        "E": E_t,
        "qe": qe_t,
        "pe": pe_t,
        "H": H_t,
        "qh": qh_t,
        "ph": ph_t,
        "I": I_t,
        "pA": pA_rows,
        **pol,
    }


def spm_MDP_VB_XXX(mdp_in: Any, options: Any | None = None) -> Any:
    """
    FORMAT ``MDP = spm_MDP_VB_XXX(MDP, OPTIONS)``

    Pass 1: OPTIONS, ``spm_MDP_checkX``, GP/id sizing, likelihood / transition tensors through ``H``,
    ``id`` / ``ID`` domains, ``GV`` / ``V`` policies, ``Q`` / ``X`` / ``S`` / ``P`` / ``sn``,
    ``s`` / ``u`` / ``o``, probabilistic ``O`` sampling, process-model ``GV``/``chi``,
    local ``spm_MDP_get_M``, ``N = min(N,T)``, ``BP``/``IP`` preallocation,
    then a partial **per-t** sweep: per-model **GP ``u`` → (``Pu``/**``Q``**/**``P``** if ``Pu_carry[m]``)
    → implicit control → GP ``s`` (~756–855); agent share (~858–869); ``BP``/``IP`` (~1224–1256);
    when ``O`` is ready, ``spm_forwards`` then belief bookkeeping **~1264–1346** (``R``/``w``/``v``,
    path ``P``, ``Pu``, policy ``P`` at ``t``); active likelihood / transition learning **~1349–1409**
    (``spm_cross`` updates to ``qa``/``qb`` and tensors ``A``/``B``, ``W``/``K``, ``I``); per-time **``F``**/**``G``**/**``Z``**.

    ``Pu_carry`` is filled after ``BP``/``IP`` using ``spm_softmax(0, alpha)`` (uniform) when the
    ``O{m,:,t}`` row is not ready; otherwise ``spm_forwards`` (which calls ``spm_VBX``) supplies ``G``
    and ``Pu_carry = spm_softmax(G, alpha)``.

    Outcomes: ``if OPTIONS.O`` blocks ~873–949 then ~952–969 run **before** ``BP``/``IP``.
    ``OPTIONS.B`` replay (~1463–1481) now calls standalone ``spm_backwards``.
    Dirichlet learning (~1485–1587): accumulate ``a``/``b``/``c``/``d``/``e`` and ``Fa``–``Fe``
    (via ``spm_MDP_MI`` when ``beta``, ``spm_softmax``, ``spm_KL_dir``).
    Predictive density (~1591–1606): ``OPTIONS.Y`` fills ``Y`` / ``j`` / ``i`` via ``spm_parents`` +
    ``spm_dot`` (function-handle ``A{g}`` not translated).
    Posterior layout (~1613–1617): ``X`` / ``S`` columns align with ``Q`` / ``P`` at each ``t``.
    Simulated electrophysiology (~1623–1688 when ``OPTIONS.N``): ``xn``/``wn``/``dn``/``un`` (uses ``spm_Gcdf``,
    ``spm_zeros``; sum-to-one on **last** factor only per MATLAB).

    Assemble (~1691–1718 plus neural carry-forward): ``T``, ``U``←``V``, ``R``/``v``/``w``, ``X``/``P``/``O``
    (with ``O`` ``shiftdim``), ``id``, optional ``A``/``B`` from ``a``/``b`` when partial return is allowed.

    Hierarchical ``MDP.MDP`` (~971+) is translated through the current staged scope; child recurse follows parent
    mode (partial recurse only when caller is partial). Main generation-time ``spm_action`` (~814–816) is wired
    through ``_vb_gen_control_one_model`` + ``_spm_action``.

    ``spm_figure`` / graphics branches from MATLAB are intentionally omitted.
    """
    opts = _merge_options_vb(options)
    partial_ok = bool(int(opts.pop("_rgms_partial_ok", 0)))
    if _vb_has_multiple_epoch_columns(mdp_in):
        raise NotImplementedError(
            "spm_MDP_VB_XXX: multiple epochs (size(MDP,2)>1) are not translated yet"
        )
    mdp_checked = spm_MDP_checkX(copy.deepcopy(mdp_in))
    models = _vb_models_after_checkx(mdp_checked)
    nm = len(models)
    hp = _vb_hyperparameters_mdp1(models[0])
    t_h = float(models[0]["T"])
    bundle = _vb_tensors_through_H(models, nm, t_h)
    post = _vb_init_QXSP_outcomes_and_process(
        models, bundle, opts, float(hp["chi"])
    )
    bundle.update(post)
    bundle.update(_vb_policy_depth_and_get_M(models, bundle, hp))
    bundle["options_vb"] = opts
    _vb_run_partial_t_loop(models, bundle, float(hp["alpha"]), partial_ok)
    _vb_optional_backwards_replay(models, bundle, opts)
    _vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
    _vb_posterior_predictive_Y(models, bundle, opts)
    _vb_reorganize_X_S_from_QP(bundle)
    _vb_options_N_neural_simulated_responses(models, bundle, opts)
    _vb_assemble_mdp_results_1691(models, bundle)
    if partial_ok:
        return _vb_build_partial_output(models, bundle)
    if len(models) == 1:
        return copy.deepcopy(models[0])
    return copy.deepcopy(models)


__all__ = ["spm_MDP_VB_XXX", "_spm_sample"]
