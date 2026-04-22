"""Oracle tests: spm_dir_MI.m vs python_src.spm_dir_MI."""

from pathlib import Path

import matlab
import numpy as np
import pytest
from scipy.special import psi as scipy_psi

import python_src.spm_dir_MI as sdm_dir_mi
from python_src.spm_dir_MI import spm_dir_MI


def test_spm_dir_MI_dense_only_oracle(eng):
    eng.eval(
        "a_dir_mi = [1 2; 3 4] * 0.5; "
        "E_dir_mi = spm_dir_MI(a_dir_mi);",
        nargout=0,
    )
    a = np.array([[0.5, 1.0], [1.5, 2.0]], dtype=np.float64)
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI(a)
    assert abs(e_m - e_p) < 1e-9


def test_spm_dir_MI_with_c_oracle(eng):
    eng.eval(
        "a_dir_mi = [1 2; 3 4] * 0.5; "
        "c_dir_mi = [0.6; 0.4]; "
        "E_dir_mi = spm_dir_MI(a_dir_mi, c_dir_mi);",
        nargout=0,
    )
    a = np.array([[0.5, 1.0], [1.5, 2.0]], dtype=np.float64)
    c = np.array([[0.6], [0.4]], dtype=np.float64)
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI(a, c)
    assert abs(e_m - e_p) < 1e-9


def test_spm_dir_MI_with_c_and_h_oracle(eng):
    eng.eval(
        "a_dir_mi = [1 2; 3 4] * 0.5; "
        "c_dir_mi = [0.6; 0.4]; "
        "h_dir_mi = {0.6; 0.4}; "
        "E_dir_mi = spm_dir_MI(a_dir_mi, c_dir_mi, h_dir_mi);",
        nargout=0,
    )
    a = np.array([[0.5, 1.0], [1.5, 2.0]], dtype=np.float64)
    c = np.array([[0.6], [0.4]], dtype=np.float64)
    h = [[np.array([[0.6]])], [np.array([[0.4]])]]
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI(a, c, h)
    assert abs(e_m - e_p) < 1e-9


def test_spm_dir_MI_empty_c_with_h_oracle(eng):
    eng.eval(
        "a_dir_mi = [1 2; 3 4] * 0.5; "
        "h_dir_mi = {0.6; 0.4}; "
        "E_dir_mi = spm_dir_MI(a_dir_mi, [], h_dir_mi);",
        nargout=0,
    )
    a = np.array([[0.5, 1.0], [1.5, 2.0]], dtype=np.float64)
    h = [[np.array([[0.6]])], [np.array([[0.4]])]]
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI(a, [], h)
    assert abs(e_m - e_p) < 1e-9


def test_spm_dir_MI_tensor_reshape_oracle(eng):
    eng.eval(
        "a_dir_mi = reshape(0.1:0.1:1.2, [2 3 2]); "
        "E_dir_mi = spm_dir_MI(a_dir_mi);",
        nargout=0,
    )
    a = np.arange(0.1, 1.3, 0.1, dtype=np.float64).reshape((2, 3, 2), order="F")
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI(a)
    assert abs(e_m - e_p) < 1e-9


def test_spm_dir_MI_cell_two_arg_oracle(eng):
    eng.eval(
        "a1 = [1 2; 3 4] * 0.2; a2 = [1 1; 1 2] * 0.3; "
        "c1 = [0.5; 0.5]; c2 = [0.25; 0.75]; "
        "E_dir_mi = spm_dir_MI({a1, a2}, {c1, c2});",
        nargout=0,
    )
    a1 = np.array([[0.2, 0.4], [0.6, 0.8]], dtype=np.float64)
    a2 = np.array([[0.3, 0.3], [0.3, 0.6]], dtype=np.float64)
    c1 = np.array([[0.5], [0.5]], dtype=np.float64)
    c2 = np.array([[0.25], [0.75]], dtype=np.float64)
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI([a1, a2], [c1, c2])
    assert abs(e_m - e_p) < 1e-9


def test_spm_dir_MI_cell_three_arg_matches_matlab_sum_of_parts(eng):
    """SPM multimodal + h cell recursion passes whole `h` (see python docstring)."""
    eng.eval(
        "a1 = [1 2; 3 4] * 0.2; a2 = [1 1; 1 2] * 0.3; "
        "c1 = [0.5; 0.5]; c2 = [0.25; 0.75]; "
        "H1 = {0.5; 0.5}; H2 = {0.25; 0.75}; "
        "E_dir_mi = spm_dir_MI(a1, c1, H1) + spm_dir_MI(a2, c2, H2);",
        nargout=0,
    )
    a1 = np.array([[0.2, 0.4], [0.6, 0.8]], dtype=np.float64)
    a2 = np.array([[0.3, 0.3], [0.3, 0.6]], dtype=np.float64)
    c1 = np.array([[0.5], [0.5]], dtype=np.float64)
    c2 = np.array([[0.25], [0.75]], dtype=np.float64)
    h1 = [[np.array([[0.5]])], [np.array([[0.5]])]]
    h2 = [[np.array([[0.25]])], [np.array([[0.75]])]]
    e_m = float(np.asarray(eng.eval("E_dir_mi"), dtype=float).reshape(-1)[0])
    e_p = spm_dir_MI([a1, a2], [c1, c2], [h1, h2])
    assert abs(e_m - e_p) < 1e-9


def _matlab_psi_vector(eng, z: np.ndarray) -> np.ndarray:
    """Elementwise MATLAB ``psi`` on a 1-D float64 vector (column-major flatten)."""
    zv = np.asarray(z, dtype=np.float64).reshape(-1, order="F")
    eng.workspace["rgms_psi_z"] = matlab.double(zv.tolist(), size=(zv.size, 1))
    eng.eval("rgms_psi_out = psi(rgms_psi_z);", nargout=0)
    return np.asarray(eng.eval("rgms_psi_out"), dtype=np.float64).reshape(-1, order="F")


def _matlab_spm_H_column(eng, v_col: np.ndarray) -> float:
    """Mirror local ``spm_H`` in ``spm_dir_MI.m`` for a column vector ``v``."""
    v_col = np.asarray(v_col, dtype=np.float64).reshape(-1, 1, order="F")
    eng.workspace["rgms_hv"] = matlab.double(v_col.tolist(), size=v_col.shape)
    eng.eval(
        "rgms_ha0 = sum(rgms_hv); "
        "rgms_Hout = psi(rgms_ha0 + 1) - sum(rgms_hv .* psi(rgms_hv + 1)) / rgms_ha0;",
        nargout=0,
    )
    return float(np.asarray(eng.eval("rgms_Hout"), dtype=np.float64).reshape(-1)[0])


@pytest.mark.slow
def test_spm_dir_MI_checkpoint_link_a_psi_vs_scipy(eng):
    """Investigate ss.ID gate: MATLAB ``psi`` vs SciPy on ``MDP{2}.a{21}`` marginals.

    Uses the same MATLAB-only FSL reference as the snippet exhaustive checkpoint
    (``O_fsl_sx`` / ``S_fsl_sx``). Does **not** assert full MI parity—records whether
    ``psi`` disagreements exist on the arguments that feed ``spm_H``.
    """
    repo = Path(__file__).resolve().parents[2]
    ck_mat = (
        repo
        / "tests"
        / "oracle"
        / "toolbox"
        / "DEM"
        / "_checkpoint_data"
        / "fsl_snippet_t1000_matlab_inputs.mat"
    )
    if not ck_mat.is_file():
        pytest.skip("checkpoint mat missing (fsl_snippet_t1000_matlab_inputs.mat)")

    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)

    mdp_name = "MDP_psi_probe_ck"
    eng.eval(f"load('{ck_mat.as_posix()}','O_fsl_sx','S_fsl_sx');", nargout=0)
    eng.eval(f"{mdp_name} = spm_faster_structure_learning(O_fsl_sx,S_fsl_sx,9);", nargout=0)

    eng.eval(f"rgms_a_link = full({mdp_name}{{2}}.a{{21}});", nargout=0)
    a_m = np.asarray(eng.eval("rgms_a_link"), dtype=np.float64)
    assert a_m.shape == (2, 441), f"expected linked (2,441) checkpoint shape, got {a_m.shape}"

    col_s, row_s = sdm_dir_mi._marginals_sum_matlab_like(a_m)
    flat = np.reshape(a_m, (-1, 1), order="F")

    # All scalar arguments t where psi(t) appears in the three spm_H evaluations.
    z_list: list[float] = []
    for block in (col_s, row_s, flat):
        bv = np.asarray(block, dtype=np.float64).reshape(-1, order="F")
        z_list.append(float(np.sum(bv)) + 1.0)  # a0+1
        for x in bv:
            z_list.append(float(x) + 1.0)
    z_arr = np.unique(np.asarray(z_list, dtype=np.float64))

    psi_ml = _matlab_psi_vector(eng, z_arr)
    psi_py = scipy_psi(z_arr)
    max_psi_diff = float(np.max(np.abs(psi_ml - psi_py)))

    h_col_m = _matlab_spm_H_column(eng, col_s)
    h_row_m = _matlab_spm_H_column(eng, row_s)
    h_flat_m = _matlab_spm_H_column(eng, flat)

    h_col_p = sdm_dir_mi._spm_H(col_s)
    h_row_p = sdm_dir_mi._spm_H(row_s)
    h_flat_p = sdm_dir_mi._spm_H(flat)

    e_mi_m = h_col_m + h_row_m - h_flat_m
    e_mi_p = h_col_p + h_row_p - h_flat_p

    eng.workspace["rgms_a_mi"] = matlab.double(a_m.tolist(), size=a_m.shape)
    eng.eval("rgms_E_mi_m = spm_dir_MI(rgms_a_mi);", nargout=0)
    e_dir_m = float(np.asarray(eng.eval("rgms_E_mi_m"), dtype=np.float64).ravel()[0])
    e_dir_p = float(np.real(spm_dir_MI(a_m)))

    # Reproduce the exhaustive-gate symptom: Python MI is exact zero, MATLAB is ~1 ULP residual.
    assert e_dir_p == 0.0, f"expected Python spm_dir_MI==0 on checkpoint link a, got {e_dir_p!r}"
    assert abs(e_dir_m) < 1e-14 and e_dir_m != 0.0, f"expected tiny nonzero MATLAB MI, got {e_dir_m!r}"

    # If SciPy psi matched MATLAB psi on every argument, max_psi_diff should be ~0;
    # otherwise psi is a contributor to H / MI divergence.
    assert max_psi_diff < 1e-14, (
        f"MATLAB vs SciPy psi max|diff|={max_psi_diff:.3e} on {z_arr.size} unique args "
        f"(H_col diff={h_col_m - h_col_p:.3e} H_row={h_row_m - h_row_p:.3e} "
        f"H_flat={h_flat_m - h_flat_p:.3e} MI_recomb={e_mi_m - e_mi_p:.3e})"
    )

    # When psi agrees, remaining MI gap is from ``spm_H`` combination / inner sums.
    # Compare MATLAB vectorized ``sum(v.*psi(v+1))`` vs Python sequential inner loop
    # for the column marginal (same ``psi`` values via SciPy).
    v_col = np.asarray(col_s, dtype=np.float64).reshape(-1, order="F")
    eng.workspace["rgms_vc"] = matlab.double(v_col.tolist(), size=(v_col.size, 1))
    eng.eval(
        "rgms_inner_m = sum(rgms_vc .* psi(rgms_vc + 1));",
        nargout=0,
    )
    inner_m = float(np.asarray(eng.eval("rgms_inner_m"), dtype=np.float64).ravel()[0])
    inner_seq_py = 0.0
    for i in range(v_col.size):
        inner_seq_py += float(v_col[i]) * float(scipy_psi(float(v_col[i]) + 1.0))
    inner_vec_np = float(np.sum(v_col * scipy_psi(v_col + 1.0)))
    assert abs(inner_m - inner_seq_py) < 1e-12, (
        f"column marginal inner sum: matlab={inner_m:.17g} python_seq={inner_seq_py:.17g}"
    )
    assert abs(inner_m - inner_vec_np) < 1e-12, (
        f"numpy vec sum inner={inner_vec_np:.17g} vs matlab={inner_m:.17g}"
    )
