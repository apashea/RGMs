"""W2 Phase 5-S-1 — optim-owned MATLAB-local VB primitives.

Ported from ``spm_MDP_VB_XXX.m`` local subs (one-time copy). **No** runtime import of
``python_src.toolbox.DEM.spm_MDP_VB_XXX``.
"""
from __future__ import annotations

import warnings
from typing import Any

import numpy as np
from scipy import sparse
from scipy.special import digamma

from matlab_compat import full as mfull
from python_src.spm_dot import spm_dot
from python_src.spm_softmax import spm_softmax
from python_src.toolbox.DEM.spm_VBX import _a_colon_s_coerce_likelihood_
from python_src.toolbox.DEM.spm_parents import spm_parents

def _vb_as_float64_array(x: Any) -> np.ndarray:
    if sparse.issparse(x):
        return np.asarray(mfull(x), dtype=np.float64)
    return np.asarray(x, dtype=np.float64)

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
            out = int(flat[0] + 1)
        else:
            r1 = float(np.random.rand())
            if k <= 4:
                float(np.random.rand())
            pos = int(np.floor(r1 * k))
            if pos >= k:
                pos = k - 1
            out = int(flat[pos] + 1)
        return out
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
    out = idx + 1
    return out


def _vb_sample_column_for_spm_sample(p: Any) -> np.ndarray:
    """Column for ``_spm_sample`` preserving source dtype semantics."""
    pv = np.asarray(p)
    if pv.dtype == bool:
        return np.asarray(pv, dtype=bool).reshape(-1, 1, order="F")
    return np.asarray(p, dtype=np.float64).reshape(-1, 1, order="F")


def _vb_spm_sample_column(p: Any) -> int:
    """Sample from a column vector; preserve logical dtype for ``randperm`` replay."""
    return _spm_sample(_vb_sample_column_for_spm_sample(p))


def _vb_gp_outcome_sample_index(col: np.ndarray) -> int:
    """``spm_sample`` for ``GP(m).A{g}(:,ind)`` outcome columns (12E / generation)."""
    if isinstance(col, np.ndarray) and col.dtype == bool:
        sample_col = col
    elif sparse.issparse(col):
        sample_col = col
    else:
        sample_col = np.asarray(col)
    return _vb_spm_sample_column(sample_col)


def spm_children(id_dict: dict[str, Any]) -> np.ndarray:
    """Local ``spm_children`` from ``spm_MDP_VB_XXX.m`` (~2584)."""
    if "g" in id_dict:
        gcell = id_dict["g"]
        if "i" in id_dict:
            ii = int(np.asarray(id_dict["i"], dtype=np.int64).ravel()[0])
            gi = gcell[ii - 1]
            arr = np.atleast_1d(np.asarray(gi, dtype=np.int64).ravel())
            return arr.astype(np.int64).reshape(1, -1)
        flat: list[int] = []
        for gi in gcell:
            flat.extend(np.asarray(gi, dtype=np.int64).ravel().tolist())
        if len(flat) == 0:
            return np.zeros((1, 0), dtype=np.int64)
        u = np.unique(np.asarray(flat, dtype=np.int64))
        return u.astype(np.int64).reshape(1, -1)
    na = len(id_dict.get("A", []))
    return np.arange(1, na + 1, dtype=np.int64).reshape(1, -1)


def _numel(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, (list, tuple)):
        return len(x)
    return int(np.asarray(x, dtype=object).size)


def _cell_get_Qj(Q: list[Any], j: Any) -> list[Any]:
    jv = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
    return [Q[int(jj) - 1] for jj in jv.tolist()]

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


def _gb_predicted_state_qs(Gb: Any, s_ft: int, u_f: int) -> np.ndarray:
    """MATLAB ``MDP.GB{f}(:, MDP.s(f,t), MDP.u(f))`` — ``Gb`` may be 2-D or 3-D."""
    arr = _vb_as_float64_array(Gb)
    if arr.ndim >= 3:
        return np.asarray(arr[:, s_ft - 1, u_f - 1], dtype=np.float64).reshape(-1, 1)
    if arr.ndim == 2:
        return np.asarray(arr[:, s_ft - 1], dtype=np.float64).reshape(-1, 1)
    return np.asarray(arr, dtype=np.float64).reshape(-1, 1)


def _id_control_g_indices(id_upper: dict[str, Any], n_a: int) -> list[int]:
    """``ID.control`` may be ``1:Ng`` vector or a scalar index from generative-process ``GDP.id``."""
    ctrl = id_upper.get("control")
    if ctrl is None:
        return [i + 1 for i in range(int(n_a))]
    if isinstance(ctrl, (int, np.integer)):
        return [int(ctrl)]
    arr = np.asarray(ctrl, dtype=np.int64).ravel(order="F")
    if arr.size == 0:
        return [i + 1 for i in range(int(n_a))]
    return [int(x) for x in arr.tolist()]


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

    a_sizes = id_m.get("A", [])
    n_a = len(a_sizes) if isinstance(a_sizes, (list, tuple)) else int(np.size(np.asarray(a_sizes)))
    if "control" not in id_upper:
        id_upper["control"] = [i + 1 for i in range(int(n_a))]
    control_g = _id_control_g_indices(id_upper, int(n_a))

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
    for g in control_g:
        g_i = int(g)
        j_par, _ = spm_parents(id_m, g_i, Q_list)
        jv = np.atleast_1d(np.asarray(j_par)).ravel().astype(np.int64)
        q_cells = [Q_list[int(jj) - 1] for jj in jv.tolist()]
        qo[g_i] = np.asarray(spm_dot(A_list[g_i - 1], q_cells), dtype=np.float64).reshape(-1, 1)

    GB = MDP["GB"]
    GV = _vb_as_float64_array(MDP["GV"])
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
            qs_list[f0] = _gb_predicted_state_qs(GB[f0], s_ft, u_f)

        F[k, 0] = 0.0
        for g in control_g:
            g_i = int(g)
            # MATLAB ~2819: ``spm_parents(MDP.ID, g, qs)`` (domain struct, not ``mdp.id``).
            j_inner, _ = spm_parents(id_upper, g_i, qs_list)
            jv2 = np.atleast_1d(np.asarray(j_inner)).ravel().astype(np.int64)
            for f in jv2.tolist():
                f0 = int(f) - 1
                s_ft = int(round(float(s_mat[f0, t_col])))
                u_f = int(round(float(u_work[f0])))
                qs_list[f0] = _gb_predicted_state_qs(GB[f0], s_ft, u_f)
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

def _spm_norm_inplace(a: np.ndarray) -> np.ndarray:
    """MATLAB ``spm_norm`` (~2633–2639): column-normalise **in place** (returns same array)."""
    if a.size == 0 or (a.ndim >= 1 and int(a.shape[0]) == 0):
        return a
    s = np.sum(a, axis=0, keepdims=True)
    np.divide(a, s, out=a, where=s != 0)
    nan_m = np.isnan(a)
    if np.any(nan_m):
        a[nan_m] = 1.0 / int(a.shape[0])
    return a


def _spm_norm(a: Any) -> Any:
    """Local ``spm_norm`` (~2633–2639): column-normalise stochastic matrix (out-of-place)."""
    if sparse.issparse(a):
        a = np.asarray(mfull(a), dtype=np.float64)
    if not (isinstance(a, np.ndarray) and np.issubdtype(a.dtype, np.number)):
        return a
    if a.size == 0 or (a.ndim >= 1 and int(a.shape[0]) == 0):
        return np.asarray(a, dtype=np.float64)
    work = np.asarray(a, dtype=np.float64)
    if not work.flags.writeable:
        work = work.copy(order="F")
    return _spm_norm_inplace(work)


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


def _spm_one_hot(o: Any, no: int) -> np.ndarray:
    """File-local ``spm_one_hot`` from ``spm_MDP_VB_XXX.m`` (~2660): ``O(o)=1``, ``No x 1``."""
    oi = int(round(float(o)))
    ni = int(no)
    if ni < 1:
        raise ValueError("spm_one_hot: No must be positive")
    if oi < 1 or oi > ni:
        raise ValueError(f"spm_one_hot: index {oi} out of range 1..{ni}")
    mat = sparse.csr_matrix(([1.0], ([oi - 1], [0])), shape=(ni, 1))
    return np.asarray(mat.toarray(), dtype=np.float64)


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

def _unwrap_gp_elem(x: Any) -> Any:
    """Single-element MATLAB cell wrapper → inner array."""
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    return x


def _vb_gp_A_outcome_column(Ag: Any, ind_parts: list[int]) -> np.ndarray:
    """
    ``GP(m).A{g}(:, ind{:})`` (~961–967): column-major outcome vector for parent states ``s(j,t)``.

    ``ind_parts`` are 0-based state indices (from MATLAB 1-based ``num2cell(s(j,t))``).
    Preserve logical dtype for ``spm_sample`` / ``randperm`` replay (see ``spm_MDP_generate``).
    """
    if hasattr(Ag, "toarray"):
        Ag_work = Ag.toarray()
    else:
        Ag_work = np.asarray(Ag)
    if Ag_work.ndim == 1:
        # MATLAB ``A{g}`` as ``Nx1`` column can arrive flat from ``loadmat``; ``(:, ind)`` is the whole column.
        col = np.asarray(Ag_work)
    elif Ag_work.ndim == 2 and len(ind_parts) == 1:
        col = np.asarray(Ag_work[:, ind_parts[0]])
    else:
        col = np.asarray(Ag_work[(slice(None),) + tuple(ind_parts)])
    col = col.reshape(-1, 1, order="F")
    if col.dtype == bool:
        return col.astype(bool)
    return np.asarray(col, dtype=np.float64)


def _vb_gp_transition_column(Bg: Any, s_1based: int, u_1based: int) -> np.ndarray:
    """MATLAB ``GP.B{f}(:, s, u)`` with 1-based indices; column ``Ns x 1``."""
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


def _tensor_nonempty(x: Any) -> bool:
    """MATLAB ``numel(X) > 0``."""
    if x is None:
        return False
    return bool(np.asarray(x).size > 0)


def _vb_no_list_from_mdp(md: dict[str, Any]) -> list[int]:
    """``No(m,g) = size(MDP(m).A{g},1)`` (~386) for hierarchical ``Q.O`` cell splits."""
    A = md.get("A", [])
    if not isinstance(A, list):
        return []
    out: list[int] = []
    for ag in A:
        try:
            out.append(int(_a_colon_s_coerce_likelihood_(ag).shape[0]))
        except Exception:
            out.append(1)
    return out


def _vb_o_cell_to_column(part: Any, n_g: int) -> np.ndarray:
    """One ``O{m,g,t}`` leaf as ``No(g)x1`` column (pad/truncate to ``size(A{g},1)``)."""
    col = np.asarray(part, dtype=np.float64).reshape(-1, 1, order="F")
    if n_g < 1:
        return col
    if col.shape[0] < n_g:
        col = np.vstack([col, np.zeros((n_g - col.shape[0], 1), dtype=np.float64)])
    elif col.shape[0] > n_g:
        col = col[:n_g, :]
    return col


def _vb_workspace_A_like_mdp_shape(qa_arr: np.ndarray, Ag_mdp: Any) -> np.ndarray:
    """Shape ``A`` like ``MDP.A{g}`` for workspace ``qa`` (~workspace init)."""
    qa = np.asarray(qa_arr, dtype=np.float64)
    if hasattr(Ag_mdp, "toarray"):
        Ag = Ag_mdp.toarray()
    else:
        Ag = np.asarray(Ag_mdp)
    if Ag.ndim == 1:
        n_row = int(Ag.shape[0])
    else:
        n_row = int(Ag.shape[0])
    if qa.ndim == 1:
        return qa.reshape(n_row, 1, order="F")
    if int(qa.shape[0]) != n_row:
        return qa.reshape(n_row, -1, order="F")
    return qa


def _spm_is_process(mdp: dict) -> bool:
    """Local ``spm_is_process`` (~2608–2611)."""
    return all(k in mdp for k in ("GA", "GB", "GU"))


def _b_nu_third_dim(Bg: Any) -> int:
    """MATLAB ``size(B{f},3)`` including trailing singleton omitted in NumPy."""
    arr = np.asarray(Bg)
    if arr.ndim >= 3:
        return int(arr.shape[2])
    return 1
