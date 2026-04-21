"""Oracle tests: spm_dir_MI.m vs python_src.spm_dir_MI."""

import numpy as np

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
