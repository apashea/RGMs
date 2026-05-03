"""Per-file oracle: `spm_RDP_sort` MATLAB vs Python (Entry 10 dependency).

Capture build / reuse lives in `test_DEM_AtariIII_entry10.py` (Entry-10–scoped only).
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from matlab import double as ml_double

from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    entry10_sort_capture_path,
    load_or_build_entry10_sort_artifact,
)


@pytest.fixture
def dem_eng(eng):
    repo = Path(__file__).resolve().parents[4]
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        yield eng
    finally:
        eng.cd(old_cd, nargout=0)


def _make_matlab_spm_RDP_sort_eig(eng: Any):
    """Return ``(B,) -> (w, V)`` using MATLAB ``eig(B,'nobalance')`` (oracle only).

    Mirrors ``[e,v]=eig(B,'nobalance')`` in ``spm_RDP_sort.m`` so NESS ``p`` and
    pruning match MATLAB when NumPy/OpenBLAS eigenvectors differ at ULP-level ties
    (see ``notes/andrew Python Matlab Translation Issues.md``).
    """
    call_i = {"n": 0}

    def _eig(B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        B = np.asarray(B, dtype=np.float64)
        n = int(B.shape[0])
        if B.shape != (n, n):
            raise ValueError("eig expects a square B")
        call_i["n"] = call_i["n"] + 1
        tag = f"{call_i['n']}_{id(B) & 0xFFFFFF:x}"
        mname = f"rgms_Brdp_{tag}"
        ename = f"rgms_erdp_{tag}"
        vname = f"rgms_vrdp_{tag}"
        eng.workspace[mname] = ml_double(B.tolist())
        eng.eval(f"[{ename},{vname}] = eig({mname},'nobalance');", nargout=0)
        lam = eng.eval(f"diag({vname})")
        w = np.asarray(lam, dtype=np.complex128).reshape(-1, order="F").ravel()
        evecs = np.asarray(eng.eval(ename), dtype=np.complex128)
        if evecs.size != n * n:
            raise RuntimeError(
                f"MATLAB eig returned size {evecs.size}, expected {n * n} for n={n}"
            )
        if evecs.shape != (n, n):
            evecs = np.reshape(evecs, (n, n), order="F")
        eng.eval(f"clear {mname} {ename} {vname}", nargout=0)
        return w, evecs

    return _eig


@pytest.mark.slow
def test_spm_RDP_sort_flow_B_and_p_match_capture(dem_eng):
    """Flow matrix `B` and NESS vector `p` match MATLAB (capture); independent of pruning loop."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = load_or_build_entry10_sort_artifact(dem_eng, training_t, n_outer)
    from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort_flow_B

    b_py = spm_RDP_sort_flow_B(copy.deepcopy(artifact["mdp10_pre"]))
    if "B_mat" in artifact:
        np.testing.assert_allclose(b_py, artifact["B_mat"], rtol=0.0, atol=1e-12)
    if "p_mat" in artifact:
        w, v = np.linalg.eig(b_py)
        ji = int(np.argmax(np.real(w)))
        vec = np.abs(v[:, ji])
        from python_src.spm_dir_norm import spm_dir_norm

        p_py = np.asarray(
            spm_dir_norm(np.reshape(vec, (-1, 1), order="F")), dtype=np.float64
        ).ravel(order="F")
        np.testing.assert_allclose(p_py, artifact["p_mat"].ravel(order="F"), rtol=0.0, atol=1e-12)


@pytest.mark.slow
def test_spm_RDP_sort_matlab_boundary_oracle(dem_eng):
    """Full ``MDP`` / ``j`` vs MATLAB capture; MATLAB ``eig(B,'nobalance')`` for NESS."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    artifact = load_or_build_entry10_sort_artifact(dem_eng, training_t, n_outer)
    matlab_eig = _make_matlab_spm_RDP_sort_eig(dem_eng)
    mdp_py, j_py = spm_RDP_sort(
        copy.deepcopy(artifact["mdp10_pre"]), eig=matlab_eig
    )
    _assert_mdp_full_equal(mdp_py, artifact["mdp10_post_mat"], 1)
    j_mat = np.asarray(artifact["j_mat"], dtype=np.int64).ravel(order="F")
    j_out = np.asarray(j_py, dtype=np.int64).ravel(order="F")
    assert j_out.shape == j_mat.shape, f"j shape py={j_out.shape} mat={j_mat.shape}"
    assert np.array_equal(j_out, j_mat), "spm_RDP_sort second output j mismatch vs MATLAB"
    assert entry10_sort_capture_path(training_t, n_outer).is_file()
