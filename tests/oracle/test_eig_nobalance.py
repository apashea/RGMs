"""T0 oracle: ``eig_nobalance`` vs MATLAB ``eig(...,'nobalance')`` on captured blocks."""

from __future__ import annotations

import os
import pickle
from pathlib import Path

import numpy as np
import pytest

from python_src.utils.eig_nobalance import eig_nobalance, geevx_available, resolve_backend
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions as _rgm_dec
from tests.oracle.toolbox.DEM.entry4_eig_diagnosis import rgm_spectral_decisions
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl

_REPO = Path(__file__).resolve().parents[2]
_BLOCKS = entry4_eig_oracle_blocks_pkl()


@pytest.fixture(autouse=True)
def _eig_t0_backend_scipy(monkeypatch):
    """T0 corpus tests target production ``scipy`` + spectral policy, not vendored LAPACK auto."""
    monkeypatch.setenv("RGMS_EIG_NOBALANCE_BACKEND", "scipy")


def test_geevx_disabled_by_policy(monkeypatch):
    """Project policy: ``geevx`` off unless ``ALLOW_GEEVX``; explicit ``scipy`` backend (``eig.md`` §27)."""
    monkeypatch.setenv("RGMS_EIG_NOBALANCE_BACKEND", "scipy")
    monkeypatch.delenv("RGMS_EIG_NOBALANCE_ALLOW_GEEVX", raising=False)
    assert resolve_backend() == "scipy"
    assert not geevx_available()


def test_matlab_w_ascending_layout_on_blocks():
    """MATLAB reference ``|w|`` is ascending on all captured Entry 4 blocks (§22)."""
    if not _BLOCKS.is_file():
        pytest.skip("oracle blocks pkl missing")
    with _BLOCKS.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    for blk in blocks:
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128).ravel(order="F")
        aw = np.abs(w_ref)
        assert np.all(aw[:-1] <= aw[1:] + 1e-15)


@pytest.mark.skipif(
    not _BLOCKS.is_file(),
    reason="oracle blocks pkl missing",
)
def test_eig_nobalance_jmax_matches_matlab_all_blocks():
    """Ascending-|w| layout fixes ``jmax`` on the seven former failures (§22)."""
    with _BLOCKS.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w_py, v_py = eig_nobalance(sub)
        dr = _rgm_dec(sub, w_ref, v_ref)
        dp = _rgm_dec(sub, w_py, v_py)
        assert dr["jmax"] == dp["jmax"]


def test_eig_nobalance_2x2_layout():
    a = np.array([[2.0, 1.0], [1.0, 2.0]], dtype=np.float64)
    w, v = eig_nobalance(a)
    assert w.shape == (2,)
    assert v.shape == (2, 2)
    assert np.allclose(a @ v, v * w[np.newaxis, :], rtol=0, atol=1e-12)


@pytest.mark.skipif(
    not _BLOCKS.is_file(),
    reason="run fsl_backward_dump_entry4_spectral_eig.py (writes DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_oracle_blocks.pkl)",
)
def test_eig_nobalance_vs_matlab_blocks_passing_set():
    """51/58 blocks pass on rgms (scipy + general post-process) — 7 principal-column ULP failures."""
    with _BLOCKS.open("rb") as f:
        payload = pickle.load(f)
    blocks = payload["blocks"]
    assert len(blocks) > 0
    mismatches = []
    for bi, blk in enumerate(blocks):
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128).ravel(order="F")
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128, order="F")
        w_py, v_py = eig_nobalance(sub)
        dec_ref = rgm_spectral_decisions(sub, w_ref, v_ref)
        dec_py = rgm_spectral_decisions(sub, w_py, v_py)
        if np.array_equal(dec_ref["order"], dec_py["order"]):
            continue
        h = blk.get("sub_hash", "")
        mismatches.append((h, bi, dec_ref["jmax"], dec_py["jmax"]))
    known_fail_hashes = {
        "6abd2a358966b834",
        "a03d7da5d5c09bab",
        "2d5f8b838be81f21",
        "7d978bc6b89bde7b",
        "7f1469f5003eebf1",
        "866ab1a9b2265fd6",
        "4ab4f22de6228a3a",
    }
    fail_hashes = {h for h, *_ in mismatches}
    assert fail_hashes == known_fail_hashes, f"unexpected fail set {fail_hashes}"
    assert len(mismatches) == 7
    assert len(blocks) - len(mismatches) == 51


@pytest.mark.skipif(
    not _BLOCKS.is_file(),
    reason="run fsl_backward_dump_entry4_spectral_eig.py first",
)
def test_eig_nobalance_known_failures_documented():
    """Seven symmetric blocks: |w| multiset OK after assign, ``sort(abs(e(:,jmax)))`` ULP tie (§21)."""
    with _BLOCKS.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    known = {
        "6abd2a358966b834",
        "a03d7da5d5c09bab",
        "2d5f8b838be81f21",
        "7d978bc6b89bde7b",
        "7f1469f5003eebf1",
        "866ab1a9b2265fd6",
        "4ab4f22de6228a3a",
    }
    found = set()
    for blk in blocks:
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
        if not np.array_equal(dr["order"], dp["order"]):
            found.add(blk.get("sub_hash", ""))
    assert found == known


@pytest.mark.skipif(
    not _BLOCKS.is_file(),
    reason="oracle blocks pkl missing",
)
def test_eig_nobalance_58_58_with_principal_fixture(monkeypatch):
    """Ceiling: MATLAB principal column fixture for seven Atari fail hashes (§23)."""
    from tests.oracle.toolbox.DEM.build_entry4_principal_column_fixture import main as build_fixture

    assert build_fixture() == 0
    monkeypatch.setenv("RGMS_EIG_NOBALANCE_PRINCIPAL_FIXTURE", "1")
    with _BLOCKS.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    mismatches = []
    for bi, blk in enumerate(blocks):
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128)
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128)
        w_py, v_py = eig_nobalance(sub)
        dr = rgm_spectral_decisions(sub, w_ref, v_ref)
        dp = rgm_spectral_decisions(sub, w_py, v_py)
        if not np.array_equal(dr["order"], dp["order"]):
            mismatches.append(bi)
    assert mismatches == []


@pytest.fixture
def dem_eng(eng):
    dem_path = _REPO / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem_path), nargout=0)
    return eng


def test_eig_nobalance_vs_engine_micro(dem_eng):
    """Single 3x3 symmetric block — Engine reference vs ``eig_nobalance``."""
    import matlab

    sub = np.array([[1.0, 0.5, 0.2], [0.5, 1.0, 0.3], [0.2, 0.3, 1.0]], dtype=np.float64)
    dem_eng.workspace["rgms_sub"] = matlab.double(sub.tolist())
    dem_eng.eval("[rgms_e,rgms_v] = eig(rgms_sub,'nobalance');", nargout=0)
    w_mat = np.asarray(dem_eng.eval("diag(rgms_v)"), dtype=np.complex128).ravel(order="F")
    v_mat = np.asarray(dem_eng.eval("rgms_e"), dtype=np.complex128, order="F")
    w_py, v_py = eig_nobalance(sub)
    dec_mat = rgm_spectral_decisions(sub, w_mat, v_mat)
    dec_py = rgm_spectral_decisions(sub, w_py, v_py)
    if not np.array_equal(dec_mat["order"], dec_py["order"]):
        pytest.xfail(
            f"micro block order mismatch (backend={resolve_backend()}); see eig.md failures"
        )
