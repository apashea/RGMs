"""
Oracle tests for file-local ``spm_sample`` used by ``spm_MDP_VB_XXX``.

MATLAB reference: ``spm_MDP_VB_XXX.m`` local ``spm_sample`` matches
``spm_MDP_generate.m``; Python duplicates ``spm_MDP_generate._spm_sample`` inside
``spm_MDP_VB_XXX.py`` for Pass 1 auditability.

RNG: replay MATLAB ``rand`` after ``rng(0,'twister')`` into ``numpy.random.rand``,
consistent with ``test_spm_MDP_generate.py`` and branch notes on ``spm_sample``.
"""

import copy
from unittest.mock import patch

import numpy as np
import pytest

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vbxxx_mod
from python_src.toolbox.DEM.spm_MDP_generate import _spm_sample as gen_spm_sample
from scipy import sparse

from python_src.spm_cross import spm_cross
from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
    _default_options_vb,
    _spm_multiply as vb_spm_multiply,
    _spm_is_process,
    _spm_log as vb_spm_log,
    _spm_sample as vb_spm_sample,
    _spm_MDP_get_M,
    _vb_fill_BP_IP_at_t,
    _vb_generation_paths_states_share,
    _vb_hierarchical_apply_S_as_O_if_present,
    _vb_hierarchical_update_parent_Q_from_child,
    _vb_hierarchical_subordinate_outcomes,
    _vb_in_loop_id_ig_and_sn,
    _vb_models_after_checkx,
    _vb_placeholder_pu_carry_softmax,
    _vb_prealloc_BP_IP,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.spm_softmax import spm_softmax


def test_vb_local_spm_multiply_is_softmax_log_sum() -> None:
    """
    MATLAB ``spm_MDP_VB_XXX.m`` ~2603–2606: ``spm_multiply`` uses ``spm_softmax(spm_log(p)+spm_log(q))``,
    not ``spm_norm(p.*q)``.
    """
    p = np.array([[0.2], [0.3], [0.5]], dtype=np.float64)
    q = np.array([[0.1], [0.3], [0.6]], dtype=np.float64)
    ref = np.asarray(spm_softmax(vb_spm_log(p) + vb_spm_log(q)), dtype=np.float64)
    got = np.asarray(vb_spm_multiply(p, q), dtype=np.float64)
    np.testing.assert_allclose(got, ref, rtol=0.0, atol=1e-12)


def test_vb_spm_multiply_matches_matlab_softmax_log_chain(eng) -> None:
    """SPM ``spm_softmax(spm_log(p)+spm_log(q))`` vs local ``_spm_multiply`` (strict log must match engine)."""
    eng.eval("p = [0.2;0.3;0.5]; q = [0.1;0.3;0.6]; r = spm_softmax(spm_log(p) + spm_log(q));", nargout=0)
    r_m = np.asarray(eng.eval("r"), dtype=np.float64).ravel()
    p = np.array([[0.2], [0.3], [0.5]], dtype=np.float64)
    q = np.array([[0.1], [0.3], [0.6]], dtype=np.float64)
    r_p = np.asarray(vb_spm_multiply(p, q), dtype=np.float64).ravel()
    np.testing.assert_allclose(r_p, r_m, rtol=0.0, atol=1e-10)


def test_vb_hierarchical_S_to_O_no_Q_seg_is_1_to_T() -> None:
    """MATLAB ``spm_MDP_VB_XXX.m`` ~1144–1151: without ``Q``, ``seg = (1:mdp.T)``."""
    S = np.arange(12, dtype=np.float64).reshape(4, 3, order="F")
    child = {"T": 2, "L": 1, "S": S}
    _vb_hierarchical_apply_S_as_O_if_present(child)
    assert child["O"].shape == (4, 2)
    np.testing.assert_array_equal(child["O"], S[:, 0:2])


def test_vb_hierarchical_S_to_O_with_Q_column_offset() -> None:
    """``seg = (1:mdp.T) + size(mdp.Q.O{mdp.L},2)`` (~1142–1143)."""
    # Two outcome rows; S has 8 columns. Q.O{L} width 5 → seg = 6,7 for T=2.
    S = np.arange(2 * 8, dtype=np.float64).reshape(2, 8, order="F")
    prev_block = np.zeros((3, 5), dtype=np.float64)
    child = {
        "T": 2,
        "L": 2,
        "S": S,
        "Q": {"O": [np.zeros((1, 1)), prev_block]},
    }
    _vb_hierarchical_apply_S_as_O_if_present(child)
    np.testing.assert_array_equal(child["O"], S[:, 5:7])


def test_vb_spm_action_updates_u_from_selected_policy(monkeypatch) -> None:
    """MATLAB ``spm_MDP_VB_XXX.m`` ~2763–2766: ``MDP.u(h,t) = MDP.GV(k,h)`` after ``spm_sample(softmax(F,chi))``."""
    monkeypatch.setattr(vbxxx_mod, "_spm_sample", lambda p: 1)
    nf = 2
    Na = 3
    n_out = 5
    Ns = 4
    Nu = 3
    rng = np.random.default_rng(0)
    GB0 = rng.random((Ns, Ns, Nu))
    GV = rng.random((Na, nf))
    h = np.any(GV != 0.0, axis=0)
    A0 = vbxxx_mod._spm_norm(rng.random((n_out, Ns)))
    D0 = vbxxx_mod._spm_norm(rng.random((Ns, 1)))
    GA0 = rng.random((n_out, Ns))
    mdp = {
        "id": {"A": [np.array([1], dtype=np.int64)]},
        "ID": {"control": [1]},
        "chi": 512.0,
        "GB": [GB0],
        "GV": GV,
        "GA": [GA0],
        "A": [A0],
        "D": [D0],
        "u": np.ones((nf, 5), dtype=np.float64),
        "s": np.ones((nf, 5), dtype=np.float64),
    }
    out = vbxxx_mod._spm_action(mdp, mdp["A"], mdp["D"], t=5)
    u_col = out["u"][:, 4]
    np.testing.assert_allclose(u_col[h], GV[0, h])


def test_vb_gen_control_main_loop_passes_Q_slice_and_t_idx(monkeypatch) -> None:
    """MATLAB ~816: ``spm_action(MDP,A,Q,t-1)`` uses ``Q(m,:,t)``; fourth arg equals Python ``t_idx``."""
    recorded: dict[str, int] = {}
    real_action = vbxxx_mod._spm_action

    def wrap(md, A_list, Q_in, t_arg):
        A_seq = list(A_list) if isinstance(A_list, (list, tuple)) else [A_list]
        Q_seq = list(Q_in) if isinstance(Q_in, (list, tuple)) else [Q_in]
        recorded["n_A"] = len(A_seq)
        recorded["n_Q"] = len(Q_seq)
        recorded["t"] = int(t_arg)
        return real_action(md, A_list, Q_in, t_arg)

    monkeypatch.setattr(vbxxx_mod, "_spm_action", wrap)

    t_int = 4
    nf = 2
    Ns = 3
    n_out = 4
    rng = np.random.default_rng(42)
    GV = rng.random((3, nf))
    md = {
        "GV": GV,
        "GB": [rng.random((Ns, Ns, 2)) for _ in range(nf)],
        "GA": [rng.random((n_out, Ns))],
        "GU": np.ones(nf),
        "GE": [np.ones((2, 1)) for _ in range(nf)],
        "GD": [np.ones((Ns, 1)) for _ in range(nf)],
        "id": {"A": [np.array([1], dtype=np.int64)]},
        "chi": 512.0,
        "u": np.ones((nf, t_int)),
        "s": np.ones((nf, t_int)),
    }
    Q_m = []
    for _f in range(nf):
        Q_m.append([np.ones((Ns, 1), dtype=np.float64) * float(tt) for tt in range(t_int)])
    bundle = {
        "process": np.array([1.0]),
        "T": t_int,
        "Nf": np.array([nf]),
        "Q": [Q_m],
        "A": [[np.ones((n_out, Ns), dtype=np.float64)]],
        "id": [{"fu": np.array([], dtype=np.int64)}],
    }
    vbxxx_mod._vb_gen_control_one_model(0, [md], bundle, t_idx=2)
    assert recorded["t"] == 2
    assert recorded["n_Q"] == nf
    assert recorded["n_A"] == 1


def test_vb_hierarchical_S_to_O_all_seg_out_of_range_empty_O() -> None:
    """``j = seg <= size(mdp.S,2)`` all false → ``mdp.S(:,seg(j))`` is ``n``×``0``."""
    S = np.ones((3, 2), dtype=np.float64)
    child = {
        "T": 1,
        "L": 1,
        "S": S,
        "Q": {"O": [np.zeros((1, 5), dtype=np.float64)]},
    }
    # seg = (1:1) + 5 = 6 > size(S,2)
    _vb_hierarchical_apply_S_as_O_if_present(child)
    assert child["O"].shape == (3, 0)


def _matlab_rand_stream_after_reset(eng, n: int) -> list[float]:
    """First ``n`` MATLAB ``rand`` scalars after ``rng(0,'twister')``."""
    eng.eval(f"rng(0,'twister'); rgms_rand_buf = rand({int(n)}, 1);", nargout=0)
    return np.asarray(eng.eval("rgms_rand_buf"), dtype=float).ravel().tolist()


@pytest.mark.parametrize(
    "p_column",
    [
        np.array([[0.25], [0.25], [0.25], [0.25]], dtype=np.float64),
        np.array([[0.1], [0.2], [0.7]], dtype=np.float64),
        np.array([[1.0]], dtype=np.float64),
    ],
)
def test_vb_spm_sample_matches_generate_numeric(p_column: np.ndarray, eng) -> None:
    """Both modules’ helpers stay identical under the same replayed draws."""
    n_draws = 5
    buf = _matlab_rand_stream_after_reset(eng, n_draws)
    with patch("numpy.random.rand", side_effect=buf):
        a = gen_spm_sample(p_column)
    with patch("numpy.random.rand", side_effect=list(buf)):
        b = vb_spm_sample(p_column)
    assert a == b


def test_vb_spm_sample_matches_generate_logical_masks(eng) -> None:
    masks = [
        np.array([[True], [False], [True]], dtype=bool),
        np.array([[True], [True], [True], [False]], dtype=bool),
        np.array([[False], [True]], dtype=bool),
    ]
    buf = _matlab_rand_stream_after_reset(eng, 32)
    for m in masks:
        with patch("numpy.random.rand", side_effect=list(buf)):
            a = gen_spm_sample(m)
        with patch("numpy.random.rand", side_effect=list(buf)):
            b = vb_spm_sample(m)
        assert a == b


def test_numeric_path_matches_matlab_inline(eng) -> None:
    """
    One-shot numeric ``spm_sample``: MATLAB ``cumsum`` + ``rand`` path vs Python
    with the first draw from the same twister stream.
    """
    eng.eval(
        "rng(0,'twister'); "
        "rgms_p0 = [0.1; 0.2; 0.7]; "
        "rgms_pc = cumsum(rgms_p0); "
        "rgms_i = find(rand*rgms_pc(end) < rgms_pc, 1);",
        nargout=0,
    )
    i_m = int(np.asarray(eng.eval("rgms_i")).ravel()[0])
    p_py = np.array([[0.1], [0.2], [0.7]], dtype=np.float64)
    r0 = _matlab_rand_stream_after_reset(eng, 1)[0]
    with patch("numpy.random.rand", side_effect=[r0]):
        i_py = vb_spm_sample(p_py)
    assert i_py == i_m


def test_logical_k1_matches_matlab_inline(eng) -> None:
    """Single ``true``: deterministic index; no ``rand`` consumption (see branch notes)."""
    eng.eval(
        "rng(0,'twister'); "
        "rgms_p = logical([0;1;0]); "
        "rgms_i = find(rgms_p); "
        "rgms_i = rgms_i(randperm(numel(rgms_i),1));",
        nargout=0,
    )
    i_m = int(np.asarray(eng.eval("rgms_i")).ravel()[0])
    p_py = np.array([[False], [True], [False]], dtype=bool)
    i_py = vb_spm_sample(p_py)
    assert i_py == i_m


def test_logical_k3_matches_matlab_inline(eng) -> None:
    """``k==3`` logical path: ``randperm`` uses two twister scalars (``2<=k<=4``)."""
    eng.eval(
        "rng(0,'twister'); "
        "rgms_p = logical([1;1;1;0]); "
        "rgms_i = find(rgms_p); "
        "rgms_i = rgms_i(randperm(numel(rgms_i),1));",
        nargout=0,
    )
    i_m = int(np.asarray(eng.eval("rgms_i")).ravel()[0])
    rbuf = _matlab_rand_stream_after_reset(eng, 2)
    p_py = np.array([[True], [True], [True], [False]], dtype=bool)
    with patch("numpy.random.rand", side_effect=rbuf):
        i_py = vb_spm_sample(p_py)
    assert i_py == i_m


def _minimal_mdp_for_checkx() -> dict:
    return {
        "T": 2,
        "A": [np.eye(2, dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.25],
        "D": [np.ones((2, 1), dtype=np.float64) * 0.5],
        "E": [np.ones((1, 1), dtype=np.float64)],
        "U": np.array([[1.0]], dtype=np.float64),
        "s": np.array([[1.0, 1.0]], dtype=np.float64),
        "u": np.array([[1.0, 1.0]], dtype=np.float64),
    }


def test_spm_MDP_VB_XXX_full_mode_returns_assembled_output_after_checkX() -> None:
    """Default mode now returns assembled output (no global terminal stub)."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {})
    assert isinstance(out, dict)
    assert "X" in out and "P" in out and "O" in out
    assert "_rgms_partial_v" not in out


def test_spm_MDP_VB_XXX_multi_epoch_not_implemented() -> None:
    """``size(MDP,2) > 1`` trial grid is deferred."""
    m = _minimal_mdp_for_checkx()
    with pytest.raises(NotImplementedError, match="multiple epochs"):
        spm_MDP_VB_XXX([[m, copy.deepcopy(m)]], {})


def test_spm_MDP_VB_XXX_hierarchical_branch_continues_to_global_stub() -> None:
    """
    Entry-12 hierarchical slice (~973+): ``MDP.MDP`` path continues through staged recursion
    and returns assembled output in default mode.
    """
    parent = _minimal_mdp_for_checkx()
    child = _minimal_mdp_for_checkx()
    # MATLAB-style first child entry: MDP(m).MDP(1)
    parent["MDP"] = [child]
    out = spm_MDP_VB_XXX(parent, {})
    assert isinstance(out, dict)
    assert "MDP" in out


def test_spm_MDP_VB_XXX_options_B_calls_spm_backwards_in_partial_mode(monkeypatch) -> None:
    """`OPTIONS.B==1` triggers replay hook and stores returned `F` on model output."""
    m = _minimal_mdp_for_checkx()
    called = {"n": 0}

    def _fake_backwards(O, P, Q, D, E, pa, pb, U, m_idx, id_list):
        called["n"] += 1
        assert int(m_idx) == 1
        return Q, P, pa, pb, np.array([-1.0, -2.0], dtype=np.float64)

    monkeypatch.setattr(vbxxx_mod, "spm_backwards", _fake_backwards)
    out = spm_MDP_VB_XXX(m, {"B": 1, "_rgms_partial_ok": 1})
    assert called["n"] == 1
    assert "F" in out
    np.testing.assert_allclose(np.asarray(out["F"], dtype=np.float64), np.array([-1.0, -2.0]))


def test_spm_MDP_VB_XXX_options_Y_partial_fills_Y_j_i() -> None:
    """``OPTIONS.Y`` default-on path: ``Y{o,t}``, ``j{g,t}``, ``i{g,t}`` mirror ``spm_dot(A,Q)``."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1})
    assert "Y" in out and "j" in out and "i" in out
    Y = out["Y"]
    assert Y[0][0] is not None
    assert Y[0][0].shape[0] == 2
    assert out["j"][0][0] is not None
    assert out["i"][0][0] is not None


def test_spm_MDP_VB_XXX_partial_X_columns_match_Q_after_sync() -> None:
    """After ~1613–1617 sync, partial ``X`` columns match per-t ``Q`` from bundle semantics."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1, "Y": 0})
    x0 = np.asarray(out["X"][0], dtype=np.float64)
    q0 = np.asarray(out["Q"][0], dtype=np.float64)
    assert x0.shape == q0.shape
    np.testing.assert_allclose(x0, q0, rtol=1e-9)


def test_spm_MDP_VB_XXX_partial_assemble_1691_R_v_w_U_O() -> None:
    """MATLAB ~1693–1704: partial PDP exposes ``T``, ``U``, ``R``, ``v``, ``w``, ``shiftdim(O)``."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1, "Y": 0})
    assert float(out["T"]) == 2.0
    assert out["R"].ndim == 2 and out["R"].shape[1] == 2
    assert out["v"].shape == (1, 2) and out["w"].shape == (1, 2)
    assert out["U"] is not None
    assert len(out["O"]) == 2
    assert len(out["O"][0]) == 1


def test_spm_MDP_VB_XXX_options_N_partial_neural_shapes() -> None:
    """MATLAB ~1623–1688 / ~1723–1728: ``OPTIONS.N`` attaches ``xn``, ``wn``, ``dn``, ``un``."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1, "Y": 0, "N": 1})
    n = 16
    t_int = 2
    np_pol = int(np.asarray(out["R"], dtype=np.float64).shape[0])
    assert len(out["xn"]) == 1
    assert out["xn"][0].shape == (n, 2, t_int, t_int)
    assert out["wn"].ravel().size == t_int * n
    assert out["dn"].ravel().size == out["wn"].ravel().size
    assert out["un"].shape == (np_pol, (t_int - 1) * n)


def test_spm_MDP_VB_XXX_options_N_partial_sn_last_slice_matches_Q_columns() -> None:
    """MATLAB ~1426–1431: ``sn{m,f}(:,i,T)`` equals current ``Q{m,f,i}`` after the last ``t`` step."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1, "Y": 0, "N": 1})
    assert "sn" in out
    Qm = np.asarray(out["Q"][0], dtype=np.float64)
    # Assembled as ``md["sn"]{f}`` list — one (Ns,T,T) tensor per factor.
    sn0 = np.asarray(out["sn"][0], dtype=np.float64)
    t_int = int(out["T"])
    ti = t_int - 1
    for i in range(t_int):
        np.testing.assert_allclose(sn0[:, i, ti].ravel(), Qm[:, i].ravel(), rtol=1e-5, atol=1e-10)


def test_vb_in_loop_id_ig_writes_attention_trace() -> None:
    """MATLAB ~1420–1422: ``id.ig(t) = id.i`` when ``id.i`` exists."""
    qcol = np.array([[0.25], [0.75]], dtype=np.float64)
    bundle = {
        "T": 3,
        "Nf": np.array([1], dtype=np.int64),
        "options_vb": _default_options_vb(),
        "id": [{"i": 2.0, "A": [np.array([[1.0]])], "g": [np.array([[1.0]])]}],
        "Q": [[[qcol.copy(), qcol.copy(), qcol.copy()]]],
        "sn": [[np.zeros((2, 3, 3), dtype=np.float64)]],
    }
    bundle["options_vb"] = {**bundle["options_vb"], "N": 1}
    _vb_in_loop_id_ig_and_sn(0, bundle, 1)
    ig = np.asarray(bundle["id"][0]["ig"], dtype=np.float64).ravel()
    assert ig.size == 3
    assert float(ig[1]) == 2.0


def test_spm_MDP_VB_XXX_partial_trim_o_s_u_columns_at_T() -> None:
    """MATLAB ~1438–1443: ``o``, ``s``, ``u`` keep exactly ``T`` columns at terminal ``t``."""
    m = _minimal_mdp_for_checkx()
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1, "Y": 0})
    t_int = int(out["T"])
    assert np.asarray(out["o"]).shape[1] == t_int
    assert np.asarray(out["s"]).shape[1] == t_int
    assert np.asarray(out["u"]).shape[1] == t_int


def test_spm_MDP_VB_XXX_learning_a_beta_zero_partial(monkeypatch) -> None:
    """
    MATLAB ~1501–1506 with ``beta==0``: ``Pa = [0,1]`` →
    ``a{g} = qa*eta/(eta+1)``. Isolate **post-loop** Dirichlet blend by disabling the
    separate in-loop ``qa`` update (~1349–1387), which would move ``qa`` before this blend.
    """
    monkeypatch.setattr(vbxxx_mod, "_vb_active_learning_in_loop", lambda *_a, **_k: None)
    m = _minimal_mdp_for_checkx()
    q0 = np.ones((2, 2), dtype=np.float64) * 100.0
    m["a"] = [q0.copy()]
    out = spm_MDP_VB_XXX(m, {"_rgms_partial_ok": 1, "Y": 0})
    eta = 512.0
    a_out = out["a"][0]
    a_out = a_out[0] if isinstance(a_out, (list, tuple)) and len(a_out) == 1 else a_out
    expected = q0 * eta / (eta + 1.0)
    np.testing.assert_allclose(np.asarray(a_out, dtype=np.float64), expected, rtol=1e-9)
    assert out["Fa"].shape == (1,)
    assert float(out["Fa"][0]) < 0.0


def test_spm_cross_VB_in_loop_da_O_Qj_matches_matlab(eng) -> None:
    """``da += spm_cross(O{m,i,t},Q{m,j,t})`` (~1367): SPM ``spm_cross`` vs Python."""
    eng.eval("Oi = [0.2;0.8]; Qj = [0.3;0.7]; dam = spm_cross(Oi,Qj);", nargout=0)
    dam = np.asarray(eng.eval("dam"), dtype=np.float64).ravel()
    Oi = np.array([[0.2], [0.8]], dtype=np.float64)
    Qj = np.array([[0.3], [0.7]], dtype=np.float64)
    dap = np.asarray(spm_cross(Oi, Qj), dtype=np.float64).ravel()
    np.testing.assert_allclose(dap, dam, rtol=0.0, atol=1e-12)


def test_spm_cross_VB_in_loop_db_transition_matches_matlab(eng) -> None:
    """``db = spm_cross(spm_cross(Q{t},Q{t-1}),P{t-1})`` (~1396): SPM vs Python."""
    eng.eval(
        "Q1 = [0.3;0.7]; Q0 = [0.2;0.8]; P0 = [0.4;0.6]; "
        "dbm = spm_cross(spm_cross(Q1,Q0),P0);",
        nargout=0,
    )
    dbm = np.asarray(eng.eval("dbm"), dtype=np.float64).ravel()
    Q1 = np.array([[0.3], [0.7]], dtype=np.float64)
    Q0 = np.array([[0.2], [0.8]], dtype=np.float64)
    P0 = np.array([[0.4], [0.6]], dtype=np.float64)
    dbp = np.asarray(spm_cross(spm_cross(Q1, Q0), P0), dtype=np.float64).ravel()
    np.testing.assert_allclose(dbp, dbm, rtol=0.0, atol=1e-12)


def test_spm_is_process_requires_ga_gb_gu() -> None:
    base = _minimal_mdp_for_checkx()
    assert _spm_is_process(base) is False
    assert _spm_is_process({**base, "GA": [], "GB": [], "GU": []}) is True


def test_vb_hierarchical_child_mapping_updates_parent_O(monkeypatch) -> None:
    """
    Hierarchical slice (~1162–1176): map child posteriors back to parent outcomes.

    Uses a stubbed child ``spm_MDP_VB_XXX`` return so this checks mapping semantics
    (``id.D`` -> ``X(:,1)``, ``id.E`` -> ``P(:,end)``) without requiring full solver completion.
    """
    child = {
        "T": 1,
        "A": [np.ones((2, 2), dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.5],
        "D": [np.array([[0.5], [0.5]], dtype=np.float64)],
        "E": [np.array([[1.0]], dtype=np.float64)],
        "U": np.array([[0.0]], dtype=np.float64),
        "id": {"D": [np.array([], dtype=np.int64)], "E": [np.array([], dtype=np.int64)]},
    }
    parent = {"MDP": [child], "Q": {"seed": 1}}
    models = [parent]
    O_shell = [[[None], [None]]]
    bundle = {"Nm": 1, "T": 1, "Ng": np.array([2], dtype=np.int64), "O": O_shell}

    def _fake_child_solver(_mdp_in, _options=None):
        return {
            "id": {"D": [np.array([1], dtype=np.int64)], "E": [np.array([2], dtype=np.int64)]},
            "X": [np.array([[0.7], [0.3]], dtype=np.float64)],
            "P": [np.array([[0.1, 0.9], [0.9, 0.1]], dtype=np.float64)],
            "Q": {"child": 1},
        }

    monkeypatch.setattr(vbxxx_mod, "spm_MDP_VB_XXX", _fake_child_solver)
    _vb_hierarchical_subordinate_outcomes(models, bundle, 0, np.array([1], dtype=np.int64), True)

    np.testing.assert_allclose(np.asarray(bundle["O"][0][0][0], dtype=np.float64), np.array([[0.7], [0.3]]))
    np.testing.assert_allclose(np.asarray(bundle["O"][0][1][0], dtype=np.float64), np.array([[0.9], [0.1]]))
    assert models[0]["Q"]["child"] == 1


def test_vb_hierarchical_child_recurse_option_follows_parent_mode(monkeypatch) -> None:
    """Hierarchy recurse ~1160: use staged partial options only when parent run is partial."""
    child = {
        "T": 1,
        "A": [np.ones((2, 2), dtype=np.float64)],
        "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.5],
        "D": [np.array([[0.5], [0.5]], dtype=np.float64)],
        "E": [np.array([[1.0]], dtype=np.float64)],
        "U": np.array([[0.0]], dtype=np.float64),
        "id": {"D": [np.array([], dtype=np.int64)], "E": [np.array([], dtype=np.int64)]},
    }
    captured: list[dict] = []

    def _fake_child_solver(_mdp_in, _options=None):
        captured.append(dict(_options or {}))
        return {
            "id": {"D": [np.array([], dtype=np.int64)], "E": [np.array([], dtype=np.int64)]},
            "X": [np.array([[0.7], [0.3]], dtype=np.float64)],
            "P": [np.array([[0.1, 0.9], [0.9, 0.1]], dtype=np.float64)],
            "Q": {"child": 1},
        }

    monkeypatch.setattr(vbxxx_mod, "spm_MDP_VB_XXX", _fake_child_solver)
    for recurse_partial in (True, False):
        parent = {"MDP": [copy.deepcopy(child)], "Q": {"seed": 1}}
        models = [parent]
        O_shell = [[[None], [None]]]
        bundle = {"Nm": 1, "T": 1, "Ng": np.array([2], dtype=np.int64), "O": O_shell}
        _vb_hierarchical_subordinate_outcomes(
            models, bundle, 0, np.array([1], dtype=np.int64), recurse_partial
        )
    assert captured[0].get("_rgms_partial_ok", 0) == 1
    assert "_rgms_partial_ok" not in captured[1]


def test_vb_hierarchical_update_parent_Q_append_and_accumulate_F() -> None:
    """MATLAB ~1186–1207: append ``s,u,P,X,Y,O,o,j,E`` at level ``L`` and add ``Q.F``."""
    parent = {}
    child_upd = {
        "L": 2,
        "a": [np.array([[1.0]])],
        "s": np.array([[1.0], [2.0]]),
        "u": np.array([[1.0]]),
        "P": [np.array([[0.2], [0.8]])],
        "X": [np.array([[0.6], [0.4]])],
        "Y": [np.array([[0.9], [0.1]])],
        "O": np.array([[1.0], [0.0]]),
        "o": np.array([[1.0]]),
        "j": np.array([[2.0]]),
        "F": np.array([0.3, 0.2], dtype=np.float64),
        "Q": {
            "s": [np.array([[9.0]]), np.array([[5.0], [6.0]])],
            "u": [np.array([[9.0]]), np.array([[7.0]])],
            "P": [[], [np.array([[0.1], [0.9]])]],
            "X": [[], [np.array([[0.3], [0.7]])]],
            "Y": [[], [np.array([[0.4], [0.6]])]],
            "O": [[], [np.array([[0.5], [0.5]])]],
            "o": [[], [np.array([[0.0]])]],
            "j": [[], [np.array([[1.0]])]],
            "E": [[], np.array([[0.05]])],
            "F": 1.25,
            "a": [None, None],
        },
    }
    _vb_hierarchical_update_parent_Q_from_child(parent, child_upd)
    q = parent["Q"]
    np.testing.assert_allclose(q["s"][1], np.array([[5.0, 1.0], [6.0, 2.0]]))
    np.testing.assert_allclose(q["u"][1], np.array([[7.0, 1.0]]))
    e_level = q["E"][1]
    if isinstance(e_level, list):
        np.testing.assert_allclose(np.asarray(e_level[0], dtype=np.float64), np.array([[0.05]]))
        np.testing.assert_allclose(np.asarray(e_level[-1], dtype=np.float64).reshape(-1), np.array([0.3, 0.2]))
    else:
        np.testing.assert_allclose(np.asarray(e_level, dtype=np.float64), np.array([[0.05, 0.3, 0.2]]))
    np.testing.assert_allclose(q["a"][1], np.array([[[1.0]]]))
    assert abs(float(q["F"]) - (1.25 + 0.5)) < 1e-12


def test_vb_hierarchical_update_parent_Q_fallback_assign_on_concat_failure() -> None:
    """MATLAB catch branch (~1197+): if append fails, assign current child records directly."""
    parent = {}
    child_upd = {
        "L": 1,
        "s": np.array([[1.0]]),
        "u": np.array([[2.0]]),
        "F": np.array([0.7], dtype=np.float64),
        "Q": {
            "s": [np.array([[3.0]])],
            "u": [np.array([[4.0]])],
            "F": 10.0,
        },
    }
    old = vbxxx_mod._vb_hierarchical_q_concat
    try:
        vbxxx_mod._vb_hierarchical_q_concat = lambda *_a, **_k: (_ for _ in ()).throw(ValueError("boom"))
        _vb_hierarchical_update_parent_Q_from_child(parent, child_upd)
    finally:
        vbxxx_mod._vb_hierarchical_q_concat = old
    q = parent["Q"]
    np.testing.assert_allclose(q["s"][0], np.array([[1.0]]))
    np.testing.assert_allclose(q["u"][0], np.array([[2.0]]))
    assert abs(float(q["F"]) - 0.7) < 1e-12


def test_vb_models_after_checkx_single_dict_and_column_grid() -> None:
    d = {"x": 1}
    assert _vb_models_after_checkx(d) == [d]
    assert _vb_models_after_checkx([[d], [d]]) == [d, d]


def test_spm_MDP_get_M_single_model_natural_order() -> None:
    """Zero ``n`` → ``n(t)==0`` → ``M(t,:)==1`` (local ``spm_MDP_get_M``)."""
    t_int = 4
    Ng = np.array([2], dtype=np.int64)
    models = [{"n": np.zeros((2, t_int))}]
    M, _ = _spm_MDP_get_M(models, t_int, Ng)
    assert M.shape == (t_int, 1)
    np.testing.assert_array_equal(M, np.ones((t_int, 1), dtype=np.int64))


def test_spm_MDP_get_M_two_models_all_zero_n_rows_natural() -> None:
    """``mode`` aggregate zero → each ``M(t,:) == [1, 2]``."""
    t_int = 3
    Ng = np.array([1, 1], dtype=np.int64)
    models = [{"n": None}, {"n": None}]
    M, _ = _spm_MDP_get_M(models, t_int, Ng)
    row = np.array([[1, 2]], dtype=np.int64)
    np.testing.assert_array_equal(M, np.tile(row, (t_int, 1)))


def test_vb_prior_QP_runs_when_Pu_carry_set() -> None:
    """``~779–804``: uniform ``Pu``, ``t>1``, updates ``Q`` / one-hot ``P``."""
    np.random.seed(0)
    D1 = np.ones((2, 1), dtype=np.float64) * 0.5
    E1 = np.ones((2, 1), dtype=np.float64) * 0.5
    bundle = {
        "Nm": 1,
        "Nf": np.array([1], dtype=np.int64),
        "NF": np.array([1], dtype=np.int64),
        "Nu": np.array([[2]], dtype=np.int64),
        "Um": [np.array([[1.0]])],
        "V": [sparse.csr_matrix(np.eye(2, 1))],
        "B": [[[np.ones((2, 2, 2), dtype=np.float64) * 0.25]]],
        "Q": [[[copy.deepcopy(D1), copy.deepcopy(D1)]]],
        "P": [[[copy.deepcopy(E1), copy.deepcopy(E1)]]],
        "Pu_carry": [np.ones((2, 1), dtype=np.float64) * 0.5],
        "gp": [
            {
                "E": [np.ones((2, 1), dtype=np.float64) * 0.5],
                "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.25],
                "D": [np.ones((2, 1), dtype=np.float64) * 0.5],
            }
        ],
        "id": [{"fu": np.array([], dtype=np.int64)}],
        "process": np.array([0.0]),
    }
    models = [
        {
            "u": np.ones((1, 2), dtype=np.float64),
            "s": np.ones((1, 2), dtype=np.float64),
        }
    ]
    _vb_generation_paths_states_share(models, bundle, 1, np.array([1], dtype=np.int64))
    assert np.asarray(bundle["Q"][0][0][1]).size > 0


def test_vb_generation_paths_states_t0_fills_u_and_s() -> None:
    """Local slice: ``t=1`` samples from ``GP.E`` / ``GP.D`` when ``u,s`` are zero."""
    np.random.seed(42)
    T = 2
    NF = np.array([1], dtype=np.int64)
    gp = [
        {
            "E": [np.array([[0.5], [0.5]], dtype=np.float64)],
            "B": [np.ones((2, 2, 1), dtype=np.float64) * 0.25],
            "D": [np.array([[0.6], [0.4]], dtype=np.float64)],
        }
    ]
    models = [{"u": np.zeros((1, T)), "s": np.zeros((1, T))}]
    bundle = {"gp": gp, "NF": NF, "process": np.array([0.0])}
    _vb_generation_paths_states_share(models, bundle, 0, np.array([1], dtype=np.int64))
    assert float(models[0]["u"][0, 0]) != 0.0
    assert float(models[0]["s"][0, 0]) != 0.0


def test_vb_placeholder_pu_carry_softmax_uniform() -> None:
    """Interim ``Pu`` uses ``spm_softmax(0,alpha)`` → uniform ``Np`` vector."""
    bundle = {"Nm": 1, "Np": np.array([4], dtype=np.int64), "Pu_carry": [None]}
    _vb_placeholder_pu_carry_softmax(bundle, np.array([1], dtype=np.int64), 512.0)
    pc = bundle["Pu_carry"][0]
    assert pc.shape == (4, 1)
    np.testing.assert_allclose(float(np.sum(pc)), 1.0, rtol=1e-9)


def test_vb_fill_BP_IP_uncontrolled_nu_gt1_uses_spm_dot() -> None:
    """MATLAB ~1243–1247: ``BP = spm_dot(B,P)`` when ``~U(f)`` and ``Nu>1``."""
    P0 = np.ones((3, 1), dtype=np.float64) / 3.0
    bundle = {
        "Nm": 1,
        "Nf": np.array([1], dtype=np.int64),
        "Nu": np.array([[3]], dtype=np.int64),
        "Np": np.array([2], dtype=np.int64),
        "Um": [np.array([[0.0]], dtype=np.float64)],
        "V": [sparse.csr_matrix(np.eye(2, 1))],
        "B": [[[np.ones((2, 2, 3), dtype=np.float64) * 0.1]]],
        "I": [[[np.ones((2, 2, 3), dtype=np.float64) * 0.05]]],
        "P": [[[P0]]],
        "BP": [[[None, None]]],
        "IP": [[[None, None]]],
    }
    _vb_fill_BP_IP_at_t(bundle, 0)
    assert bundle["BP"][0][0][0] is not None
    assert bundle["IP"][0][0][0] is not None


def test_vb_prealloc_BP_IP_uses_last_model_Nf_Np() -> None:
    """MATLAB ``cell(Nm,Nf(m),Np(m))`` with ``m = Nm``."""
    bundle = {
        "Nm": 2,
        "Nf": np.array([3, 5], dtype=np.int64),
        "Np": np.array([2, 7], dtype=np.int64),
    }
    BP, IP = _vb_prealloc_BP_IP(bundle)
    assert len(BP) == 2
    assert len(BP[0]) == 5
    assert len(BP[0][0]) == 7
    assert BP is not IP


def test_vb_prealloc_BP_IP_np_zero_reserves_slot_for_uncontrolled_bp() -> None:
    """``Np==0``: policy loops are empty but ``BP{m,f,1}`` still written (~1243–1249)."""
    bundle = {
        "Nm": 1,
        "Nf": np.array([2], dtype=np.int64),
        "Np": np.array([0], dtype=np.int64),
    }
    BP, IP = _vb_prealloc_BP_IP(bundle)
    assert len(BP[0][0]) == 1
    assert len(IP[0][0]) == 1
