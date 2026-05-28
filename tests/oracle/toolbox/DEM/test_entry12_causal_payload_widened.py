"""Oracle: widened causal payloads include parent ``Q`` and ``MDP.F`` after align."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    ENTRY12_CAUSAL_BOUNDARY_STEPS,
    entry12_align_12D_snap_to_mat,
    entry12_align_12F_snap_to_mat,
    entry12_assert_causal_def_boundaries,
    entry12_causal_payload_12d,
    entry12_causal_payload_12f,
    entry12_mat_snap_for_value_assert,
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
    _load_subentry_pkl,
    _mat_blob_to_py,
    _normalize_lean_boundary_payload,
)

_REPO = Path(__file__).resolve().parents[4]
_FIX = _REPO / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"
_SKIP = frozenset({"OPTIONS", "meta", "per_t"})


def _load_band(code: str) -> tuple[dict, dict]:
    mat_p = entry12_subentry_mat_path(ENTRY12_CANONICAL_RUN_TAG, code, out_dir=_FIX)
    pkl_p = _FIX / f"DEMAtariIII_entry12_{ENTRY12_CANONICAL_RUN_TAG}_{code}.pkl"
    if not mat_p.is_file() or not pkl_p.is_file():
        pytest.skip(f"missing {code} fixtures")
    py_blob = _load_subentry_pkl(pkl_p)
    mat_blob = _mat_blob_to_py(load_entry12_subentry_mat(mat_p))
    py_ws = {k: v for k, v in py_blob.items() if k not in _SKIP}
    mat_ws = {k: v for k, v in mat_blob.items() if k not in _SKIP}
    return _normalize_lean_boundary_payload(py_ws, code=code), _normalize_lean_boundary_payload(
        mat_ws, code=code
    )


def test_causal_payload_12d_out_t2_includes_parent_Q_and_F() -> None:
    py_ws, mat_ws = _load_band("12D")
    sub = "out_t2"
    py_cmp = entry12_align_12D_snap_to_mat(py_ws[sub], mat_ws[sub])
    mat_cmp = entry12_mat_snap_for_value_assert("12D", mat_ws[sub])
    py_pl = entry12_causal_payload_12d(py_cmp)
    mat_pl = entry12_causal_payload_12d(mat_cmp)
    assert "MDP" in py_pl and "MDP" in mat_pl
    assert "Q" in py_pl["MDP"] and "Q" in mat_pl["MDP"]
    assert "F" in py_pl["MDP"] and "F" in mat_pl["MDP"]


def test_causal_payload_12f_out_t1_includes_mdp_F() -> None:
    py_ws, mat_ws = _load_band("12F")
    sub = "out_t1"
    py_cmp = entry12_align_12F_snap_to_mat(py_ws[sub], mat_ws[sub])
    mat_cmp = entry12_mat_snap_for_value_assert("12F", mat_ws[sub])
    py_pl, _ = entry12_causal_payload_12f(py_cmp, py_ws[sub])
    mat_pl, _ = entry12_causal_payload_12f(mat_cmp, mat_ws[sub])
    assert "MDP" in py_pl and "MDP" in mat_pl
    assert "F" in py_pl["MDP"] and "F" in mat_pl["MDP"]


def test_causal_boundaries_all_pass_with_widened_payloads() -> None:
    py_def: dict[str, dict] = {}
    mat_def: dict[str, dict] = {}
    for band in ("12D", "12E", "12F"):
        py_def[band], mat_def[band] = _load_band(band)
    failures = entry12_assert_causal_def_boundaries(py_def, mat_def)
    assert failures == [], f"causal failures ({len(failures)}): {failures[:3]}"
    assert len(ENTRY12_CAUSAL_BOUNDARY_STEPS) == 15
