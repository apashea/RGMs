"""Oracle tests: spm_dir_MI.m vs python_src.spm_dir_MI."""

from pathlib import Path
import pickle
import subprocess
import sys
from typing import Any, Iterator

import matlab
import numpy as np
import pytest
from scipy.special import psi as scipy_psi

import python_src.spm_dir_MI as sdm_dir_mi
from python_src.spm_dir_MI import spm_dir_MI


def _latest_link_diag_dump(repo: Path) -> Path | None:
    dump_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_tmp_link_mi"
    if not dump_dir.is_dir():
        return None
    candidates = sorted(dump_dir.glob("*B2_diag_pull*.npy"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return None
    return candidates[-1]


def _spm_dir_mi_subprocess_from_npy(npy_path: Path) -> float:
    script = (
        "import numpy as np; "
        "from python_src.spm_dir_MI import spm_dir_MI; "
        f"a=np.load(r'''{str(npy_path)}''',allow_pickle=False); "
        "print(repr(float(np.real(spm_dir_MI(a)))))"
    )
    cp = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    out = cp.stdout.strip().splitlines()
    if not out:
        raise RuntimeError("subprocess spm_dir_MI produced no stdout")
    return float(out[-1].strip())


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


def _float64_ulps_from_to(x: float, y: float, *, max_steps: int = 20_000) -> int | None:
    """Count ULP steps along ``np.nextafter`` from ``x`` toward ``y`` (inclusive of ``y``)."""
    fx = np.float64(x)
    fy = np.float64(y)
    if fx == fy:
        return 0
    n = 0
    cur = fx
    while n < max_steps and cur != fy:
        cur = np.nextafter(cur, fy)
        n += 1
    if cur != fy:
        return None
    return int(n)


def _uint64_bits(x: float) -> int:
    return int(np.asarray([np.float64(x)], dtype=np.float64).view(np.uint64)[0])


def _python_one_arg_mi_decomposition(a: np.ndarray) -> dict[str, Any]:
    """Mirror ``spm_dir_MI`` one-arg 2D path (Fortran-order copy + MATLAB-like marginals)."""
    a2 = np.asfortranarray(np.array(np.asarray(a, dtype=np.float64), dtype=np.float64, copy=True))
    col_s, row_s = sdm_dir_mi._marginals_sum_matlab_like(a2)
    flat = np.reshape(a2, (-1, 1), order="F")
    h_col = float(sdm_dir_mi._spm_H(col_s))
    h_row = float(sdm_dir_mi._spm_H(row_s))
    h_flat = float(sdm_dir_mi._spm_H(flat))
    return {
        "a": a2,
        "col_s": col_s,
        "row_s": row_s,
        "flat": flat,
        "h_col": h_col,
        "h_row": h_row,
        "h_flat": h_flat,
        "e_mi": h_col + h_row - h_flat,
    }


def _matlab_one_arg_mi_decomposition(eng, a: np.ndarray) -> dict[str, float]:
    """MATLAB ``spm_dir_MI`` one-arg decomposition (inline ``spm_H`` formula, same as dump test)."""
    nr, nc = int(a.shape[0]), int(a.shape[1])
    eng.workspace["rgms_wa"] = matlab.double(
        np.asarray(a, dtype=np.float64).tolist(), size=(nr, nc)
    )
    eng.eval(
        "rgms_wcol = sum(rgms_wa,2); "
        "rgms_wrow = sum(rgms_wa,1); "
        "rgms_wflat = rgms_wa(:); "
        "rgms_wh_col = psi(sum(rgms_wcol)+1) - sum(rgms_wcol .* psi(rgms_wcol + 1)) / sum(rgms_wcol); "
        "rgms_wh_row = psi(sum(rgms_wrow)+1) - sum(rgms_wrow .* psi(rgms_wrow + 1)) / sum(rgms_wrow); "
        "rgms_wh_flat = psi(sum(rgms_wflat)+1) - sum(rgms_wflat .* psi(rgms_wflat + 1)) / sum(rgms_wflat); "
        "rgms_w_e_terms = rgms_wh_col + rgms_wh_row - rgms_wh_flat; "
        "rgms_w_E = spm_dir_MI(rgms_wa);",
        nargout=0,
    )
    return {
        "h_col": float(np.asarray(eng.eval("rgms_wh_col"), dtype=np.float64).reshape(-1)[0]),
        "h_row": float(np.asarray(eng.eval("rgms_wh_row"), dtype=np.float64).reshape(-1)[0]),
        "h_flat": float(np.asarray(eng.eval("rgms_wh_flat"), dtype=np.float64).reshape(-1)[0]),
        "e_terms": float(np.asarray(eng.eval("rgms_w_e_terms"), dtype=np.float64).reshape(-1)[0]),
        "e_spm": float(np.asarray(eng.eval("rgms_w_E"), dtype=np.float64).reshape(-1)[0]),
    }


def _iter_link_mi_workload_records(repo: Path) -> Iterator[tuple[str, int, dict[str, Any]]]:
    ck_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data"
    for ck in sorted(ck_dir.glob("fsl_link_mi_workload*.pkl")):
        with ck.open("rb") as f:
            payload = pickle.load(f)
        for idx, rec in enumerate(list(payload.get("records", []))):
            yield ck.name, idx, rec


@pytest.mark.slow
def test_spm_dir_MI_checkpoint_link_a_psi_vs_scipy(eng):
    """Investigate ss.ID gate: MATLAB ``psi`` vs SciPy on ``MDP{2}.a{21}`` marginals.

    Uses the same MATLAB-only FSL reference as the snippet exhaustive checkpoint
    (``O_fsl_sx`` / ``S_fsl_sx``). **Must** mirror ``dem_eng_fsl_pdp`` in
    ``test_spm_faster_structure_learning.py`` (``addpath(matlab_src)``, ``cd`` to
    ``matlab_src/toolbox/DEM``) so the staged ``.m`` tree resolves like the
    exhaustive oracle, not a mixed SPM install path.
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
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        mdp_name = "MDP_fsl_snip_exact"
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

        # After MATLAB-like marginal ``sum`` in ``spm_dir_MI``, Python should match
        # MATLAB on this checkpoint link matrix (same symptom class as ``ss.ID`` gate).
        assert abs(e_dir_m - e_dir_p) < 1e-12, (
            f"checkpoint link ``spm_dir_MI``: matlab={e_dir_m:.17g} python={e_dir_p:.17g} "
            f"diff={e_dir_m - e_dir_p:.3e}"
        )
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
    finally:
        eng.cd(old_cd, nargout=0)


def test_spm_dir_MI_link_diag_dump_fast_oracle(eng):
    """Fast diagnostic loop on the latest dumped Lane-C link matrix."""
    repo = Path(__file__).resolve().parents[2]
    dump = _latest_link_diag_dump(repo)
    if dump is None:
        pytest.skip(
            "no link diag dump found under tests/oracle/toolbox/DEM/_tmp_link_mi "
            "(run Lane C once with RGMS_FSL_LINK_MI_DUMP=1)"
        )
    a = np.load(dump, allow_pickle=False)
    if a.shape != (2, 441):
        pytest.skip(f"latest dump shape is {a.shape}; expected (2, 441) link fixture")
    nr, nc = int(a.shape[0]), int(a.shape[1])
    eng.workspace["rgms_a_dump"] = matlab.double(np.asarray(a, dtype=np.float64).tolist(), size=(nr, nc))
    eng.eval(
        "rgms_col = sum(rgms_a_dump,2); "
        "rgms_row = sum(rgms_a_dump,1); "
        "rgms_flat = rgms_a_dump(:); "
        "rgms_h_col = psi(sum(rgms_col)+1) - sum(rgms_col .* psi(rgms_col+1)) / sum(rgms_col); "
        "rgms_h_row = psi(sum(rgms_row)+1) - sum(rgms_row .* psi(rgms_row+1)) / sum(rgms_row); "
        "rgms_h_flat = psi(sum(rgms_flat)+1) - sum(rgms_flat .* psi(rgms_flat+1)) / sum(rgms_flat); "
        "rgms_e_terms = rgms_h_col + rgms_h_row - rgms_h_flat;",
        nargout=0,
    )
    h_col_m = float(np.asarray(eng.eval("rgms_h_col"), dtype=np.float64).reshape(-1)[0])
    h_row_m = float(np.asarray(eng.eval("rgms_h_row"), dtype=np.float64).reshape(-1)[0])
    h_flat_m = float(np.asarray(eng.eval("rgms_h_flat"), dtype=np.float64).reshape(-1)[0])
    e_terms_m = float(np.asarray(eng.eval("rgms_e_terms"), dtype=np.float64).reshape(-1)[0])
    a0_row_m = float(np.asarray(eng.eval("sum(rgms_row)"), dtype=np.float64).reshape(-1)[0])
    a0_flat_m = float(np.asarray(eng.eval("sum(rgms_flat)"), dtype=np.float64).reshape(-1)[0])
    inner_row_m = float(
        np.asarray(eng.eval("sum(rgms_row .* psi(rgms_row + 1))"), dtype=np.float64).reshape(-1)[0]
    )
    inner_flat_m = float(
        np.asarray(eng.eval("sum(rgms_flat .* psi(rgms_flat + 1))"), dtype=np.float64).reshape(-1)[0]
    )
    eng.eval("rgms_e_dump_m = spm_dir_MI(rgms_a_dump);", nargout=0)
    e_m = float(np.asarray(eng.eval("rgms_e_dump_m"), dtype=np.float64).reshape(-1)[0])
    col_s, row_s = sdm_dir_mi._marginals_sum_matlab_like(a)
    h_col_p = float(sdm_dir_mi._spm_H(col_s))
    h_row_p = float(sdm_dir_mi._spm_H(row_s))
    h_flat_p = float(sdm_dir_mi._spm_H(np.reshape(a, (-1, 1), order="F")))
    inner_row_p = float(
        np.asarray(row_s, dtype=np.float64).reshape(-1, order="F")
        @ np.asarray(
            scipy_psi(np.asarray(row_s, dtype=np.float64).reshape(-1, order="F") + 1.0),
            dtype=np.float64,
        )
    )
    inner_flat_p = float(
        np.asarray(a, dtype=np.float64).reshape(-1, order="F")
        @ np.asarray(
            scipy_psi(np.asarray(a, dtype=np.float64).reshape(-1, order="F") + 1.0),
            dtype=np.float64,
        )
    )
    e_p = float(np.real(spm_dir_MI(a)))
    e_sub = _spm_dir_mi_subprocess_from_npy(dump)
    assert e_p == e_sub, f"parent/subprocess mismatch on dumped link matrix: {e_p:.17g} vs {e_sub:.17g}"
    # Decomposition parity check: MATLAB local spm_H terms must recombine to MATLAB MI.
    assert abs(e_m - e_terms_m) < 1e-15, (
        f"MATLAB decomposition mismatch on dump: spm_dir_MI={e_m:.17g} terms={e_terms_m:.17g} "
        f"(h_col={h_col_m:.17g} h_row={h_row_m:.17g} h_flat={h_flat_m:.17g})"
    )
    # Current isolated signature: MATLAB has a one-ULP row-vs-flat split,
    # while Python row/flat terms are byte-equal on this dump.
    h_row_m_u = int(np.asarray([h_row_m], dtype=np.float64).view(np.uint64)[0])
    h_flat_m_u = int(np.asarray([h_flat_m], dtype=np.float64).view(np.uint64)[0])
    h_row_p_u = int(np.asarray([h_row_p], dtype=np.float64).view(np.uint64)[0])
    h_flat_p_u = int(np.asarray([h_flat_p], dtype=np.float64).view(np.uint64)[0])
    assert h_row_m_u == h_flat_m_u + 1, (
        f"expected MATLAB one-ULP h_row/h_flat split on dump; "
        f"h_row={h_row_m:.17g} ({h_row_m_u:#x}) h_flat={h_flat_m:.17g} ({h_flat_m_u:#x})"
    )
    assert h_row_p_u == h_flat_p_u, (
        f"expected Python h_row/h_flat equality on dump; "
        f"h_row={h_row_p:.17g} ({h_row_p_u:#x}) h_flat={h_flat_p:.17g} ({h_flat_p_u:#x})"
    )
    assert a0_row_m == a0_flat_m, f"expected equal a0 terms in MATLAB decomposition, got {a0_row_m} vs {a0_flat_m}"
    assert inner_row_m != inner_flat_m and inner_row_p == inner_flat_p, (
        f"inner-term signature mismatch: "
        f"mat_row={inner_row_m:.17g} mat_flat={inner_flat_m:.17g} "
        f"py_row={inner_row_p:.17g} py_flat={inner_flat_p:.17g}"
    )
    b_m = np.asarray([e_m], dtype=np.float64).tobytes()
    b_p = np.asarray([e_p], dtype=np.float64).tobytes()
    assert b_m != b_p, (
        f"expected current Lane-C scalar-byte mismatch to persist on dumped fixture; "
        f"matlab={e_m:.17g} python={e_p:.17g} "
        f"(h_col={h_col_m:.17g} h_row={h_row_m:.17g} h_flat={h_flat_m:.17g} "
        f"e_terms={e_terms_m:.17g}) dump={dump.name}"
    )
    assert e_m != 0.0 and e_p == 0.0, (
        f"unexpected dumped-link MI class; matlab={e_m:.17g} python={e_p:.17g} "
        f"(h_col={h_col_m:.17g} h_row={h_row_m:.17g} h_flat={h_flat_m:.17g} "
        f"e_terms={e_terms_m:.17g}) "
        f"dump={dump.name}"
    )


def test_spm_dir_MI_link_diag_dump_row_ulp_experiment_fast_oracle(eng, monkeypatch):
    """Experimental-only: one-ULP row adjustment should match MATLAB on dump."""
    repo = Path(__file__).resolve().parents[2]
    dump = _latest_link_diag_dump(repo)
    if dump is None:
        pytest.skip(
            "no link diag dump found under tests/oracle/toolbox/DEM/_tmp_link_mi "
            "(run Lane C once with RGMS_FSL_LINK_MI_DUMP=1)"
        )
    a = np.load(dump, allow_pickle=False)
    if a.shape != (2, 441):
        pytest.skip(f"latest dump shape is {a.shape}; expected (2, 441) link fixture")
    nr, nc = int(a.shape[0]), int(a.shape[1])
    eng.workspace["rgms_a_dump"] = matlab.double(np.asarray(a, dtype=np.float64).tolist(), size=(nr, nc))
    eng.eval("rgms_e_dump_m = spm_dir_MI(rgms_a_dump);", nargout=0)
    e_m = float(np.asarray(eng.eval("rgms_e_dump_m"), dtype=np.float64).reshape(-1)[0])
    monkeypatch.setenv("RGMS_DIR_MI_EXPERIMENT_ROW_ULP", "1")
    e_p_exp = float(np.real(spm_dir_MI(a)))
    assert abs(e_m - e_p_exp) < 1e-15, (
        f"row-ulp experiment did not match MATLAB on dump; "
        f"matlab={e_m:.17g} python_exp={e_p_exp:.17g} dump={dump.name}"
    )


def test_spm_dir_MI_link_workload_checkpoint_fast_replay_oracle():
    """Replay all captured link-MI workloads without rerunning full Lane C."""
    repo = Path(__file__).resolve().parents[2]
    ck_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data"
    cks = sorted(ck_dir.glob("fsl_link_mi_workload*.pkl"))
    if not cks:
        pytest.skip(
            "link MI workload checkpoint missing "
            "(run Lane C once with RGMS_FSL_CAPTURE_LINK_MI_WORKLOAD=1)"
        )
    total_records = 0
    total_mismatch = 0
    max_abs = 0.0
    for ck in cks:
        with ck.open("rb") as f:
            payload = pickle.load(f)
        records = list(payload.get("records", []))
        if not records:
            continue
        mismatch_count = 0
        local_max = 0.0
        for rec in records:
            a = np.asarray(rec["a_mat"], dtype=np.float64)
            e_p = float(np.real(spm_dir_MI(a)))
            e_m = float(rec["matlab_mi"])
            d = abs(e_m - e_p)
            local_max = max(local_max, d)
            if np.asarray([e_m], dtype=np.float64).tobytes() != np.asarray(
                [e_p], dtype=np.float64
            ).tobytes():
                mismatch_count += 1
        total_records += len(records)
        total_mismatch += mismatch_count
        max_abs = max(max_abs, local_max)
        print(
            "[DIR-MI-WORKLOAD] file="
            f"{ck.name} records={len(records)} mismatches={mismatch_count} "
            f"max_abs_diff={local_max:.3e}",
            flush=True,
        )
    assert total_records > 0
    print(
        "[DIR-MI-WORKLOAD] total_records="
        f"{total_records} total_mismatches={total_mismatch} max_abs_diff={max_abs:.3e}",
        flush=True,
    )


def test_spm_dir_MI_link_workload_matlab_python_H_trace_oracle(eng):
    """Per-record MATLAB vs Python ``spm_H`` / marginal traces on link-MI workload pkls.

    Documents why ``12/24`` byte mismatches are **not** a random half-and-half split:
    the same three logical slots (record indices ``0``, ``1``, ``2``) fail in every
    workload file, while indices ``3``–``5`` match. Also quantifies whether final MI
    gaps are single-ULP and correlates them with MATLAB's row-vs-flat ``spm_H``
    bit pattern (often exactly one ULP apart on near-cancellation matrices).
    """
    repo = Path(__file__).resolve().parents[2]
    cks = sorted(
        (repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data").glob(
            "fsl_link_mi_workload*.pkl"
        )
    )
    if not cks:
        pytest.skip(
            "link MI workload checkpoint missing "
            "(run Lane C once with RGMS_FSL_CAPTURE_LINK_MI_WORKLOAD=1)"
        )

    n_total = 0
    n_byte_match = 0
    n_byte_mismatch = 0
    ulp_hist: dict[int, int] = {}
    matlab_hrow_hflat_ulps: list[int] = []
    py_hrow_hflat_ulps: list[int] = []
    mismatch_slots: list[tuple[str, int, str]] = []
    match_slots: list[tuple[str, int, str]] = []

    for ck_name, rec_idx, rec in _iter_link_mi_workload_records(repo):
        a = np.asarray(rec["a_mat"], dtype=np.float64)
        e_m_stored = float(rec["matlab_mi"])
        kind = str(rec.get("kind", "?"))

        py_d = _python_one_arg_mi_decomposition(a)
        ml_d = _matlab_one_arg_mi_decomposition(eng, a)
        e_p = float(np.real(spm_dir_MI(a)))

        assert abs(ml_d["e_spm"] - ml_d["e_terms"]) < 1e-14, (
            f"MATLAB spm_dir_MI vs inline H decomposition: e_spm={ml_d['e_spm']:.17g} "
            f"e_terms={ml_d['e_terms']:.17g} ck={ck_name} idx={rec_idx}"
        )
        assert abs(ml_d["e_spm"] - e_m_stored) < 1e-14, (
            f"pkl matlab_mi vs live MATLAB spm_dir_MI: stored={e_m_stored:.17g} "
            f"live={ml_d['e_spm']:.17g} ck={ck_name} idx={rec_idx} kind={kind}"
        )

        u_m = _uint64_bits(ml_d["h_row"])
        v_m = _uint64_bits(ml_d["h_flat"])
        matlab_hrow_hflat_ulps.append(abs(int(u_m) - int(v_m)))

        u_p = _uint64_bits(py_d["h_row"])
        v_p = _uint64_bits(py_d["h_flat"])
        py_hrow_hflat_ulps.append(abs(int(u_p) - int(v_p)))

        b_m = np.asarray([e_m_stored], dtype=np.float64).tobytes()
        b_p = np.asarray([e_p], dtype=np.float64).tobytes()
        n_total += 1
        if b_m == b_p:
            n_byte_match += 1
            match_slots.append((ck_name, rec_idx, kind))
        else:
            n_byte_mismatch += 1
            mismatch_slots.append((ck_name, rec_idx, kind))
            steps = _float64_ulps_from_to(e_p, e_m_stored)
            assert steps is not None, (
                f"MI ULP distance exceeded cap: py={e_p:.17g} matlab={e_m_stored:.17g} "
                f"ck={ck_name} idx={rec_idx}"
            )
            ulp_hist[steps] = ulp_hist.get(steps, 0) + 1

        print(
            "[DIR-MI-H-TRACE] "
            f"file={ck_name} idx={rec_idx} kind={kind} "
            f"byte_match={b_m == b_p} "
            f"e_py={e_p:.17g} e_ml={e_m_stored:.17g} "
            f"ulps_py_to_ml={_float64_ulps_from_to(e_p, e_m_stored) if b_m != b_p else 0} "
            f"ml_hrow={ml_d['h_row']:.17g} ml_hflat={ml_d['h_flat']:.17g} "
            f"|uint64(hrow)-uint64(hflat)|_ml={abs(_uint64_bits(ml_d['h_row']) - _uint64_bits(ml_d['h_flat']))} "
            f"py_hrow={py_d['h_row']:.17g} py_hflat={py_d['h_flat']:.17g} "
            f"|uint64(hrow)-uint64(hflat)|_py={abs(_uint64_bits(py_d['h_row']) - _uint64_bits(py_d['h_flat']))}",
            flush=True,
        )

    assert n_total == 24, f"expected 24 workload records, got {n_total}"
    assert n_byte_match == 12 and n_byte_mismatch == 12, (
        f"expected 12 byte matches and 12 mismatches on default Python path, "
        f"got match={n_byte_match} mismatch={n_byte_mismatch}"
    )

    mismatch_indices = {idx for _, idx, _ in mismatch_slots}
    match_indices = {idx for _, idx, _ in match_slots}
    assert mismatch_indices == {0, 1, 2}, (
        "mismatches should occupy the same three record indices in every pkl "
        f"(structural), got mismatch idx set={mismatch_indices}"
    )
    assert match_indices == {3, 4, 5}, (
        f"expected matching tail indices {{3,4,5}}, got {match_indices}"
    )

    assert ulp_hist == {1: 12}, (
        "every byte mismatch should be exactly **one float64 ULP** apart on final MI "
        f"(near-cancellation at machine precision); got histogram {ulp_hist}"
    )

    assert all(x == 1 for x in matlab_hrow_hflat_ulps), (
        "MATLAB ``h_row`` vs ``h_flat`` bit distance: expected **exactly 1 ULP** "
        f"for all 24 workload matrices (same structural split as dump oracle); "
        f"got {sorted(set(matlab_hrow_hflat_ulps))}"
    )
    assert all(x == 0 for x in py_hrow_hflat_ulps), (
        "Python ``h_row`` vs ``h_flat``: expected **0 ULP** (byte-equal row and flat "
        f"``spm_H`` terms on this corpus); got nonzero set={sorted(set(py_hrow_hflat_ulps))}"
    )

    print(
        "[DIR-MI-H-TRACE] summary: "
        f"12/24 structural (idx 0–2 only); all MI gaps are 1 ULP; "
        f"MATLAB always h_row!=h_flat by 1 ULP; Python always h_row==h_flat (0 ULP).",
        flush=True,
    )
