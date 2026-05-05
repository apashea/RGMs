"""Entry 12 — MATLAB `spm_MDP_VB_XXX(RDP)` boundary capture for DEM_AtariIII isolation.

``run_dem_atariiii(entry_stop=12)`` now calls Python ``spm_MDP_VB_XXX`` (partial mode); this module
builds **artifact-first** MATLAB checkpoints so Entry 12 validation can replay a
persisted MATLAB ``PDP`` (``rgms_pdp12`` pull) against Python when ready.

Uses the same MATLAB preamble as Entry 10 sort capture through ``rgms_rdp11`` (costs,
``spm_mdp2rdp``, ``T = 64``), then runs::

    rgms_pdp12 = spm_MDP_VB_XXX(rgms_rdp11);

RNG note: MATLAB executes VB with its own PRNG state during capture; Python parity tests
should replay MATLAB ``rand()`` where sampling paths mirror ``spm_MDP_generate`` / branch
notes when comparing stochastic internals.

Environment:

- ``RGMS_ATARI_ENTRY12_VB_CAPTURE_REFRESH`` — ``1`` / ``true`` / ``yes`` / ``on`` to rebuild.
- ``RGMS_ATARI_ENTRY12_VB_CAPTURE_TAG`` — filename suffix (sanitized), default ``default``.

Capture versions:

- ``entry12_capture_v == 1`` — nested ``rdp11`` / ``pdp12`` pulls only.
- ``entry12_capture_v == 2`` — adds ``pdp12_l0_X_shapes`` / ``pdp12_l0_P_shapes`` for partial-mode geometry checks vs MATLAB.
- ``entry12_capture_v == 3`` — adds ``pdp12_l0_Q_shapes``, ``pdp12_l0_o_shape``, ``pdp12_l0_s_shape``, ``pdp12_l0_u_shape``, ``pdp12_l0_R_shape``, ``pdp12_l0_v_shape``, ``pdp12_l0_w_shape`` (MATLAB ~1691 assembly) for driver-relevant parity.

Artifact path::

    tests/oracle/toolbox/DEM/_checkpoint_data/atari_entry/
      dem_atari_entry12_vb_capture_t<training_t>_outer<n_outer>_<tag>.pkl
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import matlab.engine

from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    _matlab_build_entry10_training_end_boundary,
    _matlab_run_entry10_sort_goals_and_P,
    _pull_nested_rdp_from_matlab,
    dem_eng_entry10,
)
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
    _mat_int,
    _pull_mdp_from_matlab,
)


def entry12_vb_capture_refresh_enabled() -> bool:
    return str(os.getenv("RGMS_ATARI_ENTRY12_VB_CAPTURE_REFRESH", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def entry12_vb_capture_tag() -> str:
    raw = str(os.getenv("RGMS_ATARI_ENTRY12_VB_CAPTURE_TAG", "default")).strip()
    safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in raw)
    return safe or "default"


def entry12_vb_capture_path(training_t: int, n_outer: int) -> Path:
    repo = Path(__file__).resolve().parents[4]
    ckpt_dir = repo / "tests" / "oracle" / "toolbox" / "DEM" / "_checkpoint_data" / "atari_entry"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    tag = entry12_vb_capture_tag()
    return (
        ckpt_dir
        / f"dem_atari_entry12_vb_capture_t{int(training_t)}_outer{int(n_outer)}_{tag}.pkl"
    )


def _normalize_pdp_to_cell_for_pull(dem_eng, expr: str = "rgms_pdp12") -> None:
    """Brace-index pulls expect a cell array of per-level MDP structs."""
    dem_eng.eval(
        f"if ~iscell({expr}), {expr} = num2cell({expr}(:)); end;",
        nargout=0,
    )


def _capture_entry12_vb_artifact(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    """MATLAB lane through Entry 11 RDP, then ``spm_MDP_VB_XXX``; pull checkpoint fields."""
    _matlab_build_entry10_training_end_boundary(dem_eng, training_t, n_outer)
    _matlab_run_entry10_sort_goals_and_P(dem_eng)
    dem_eng.eval(
        "rgms_mdp11_costs = spm_set_costs(rgms_mdp10_goals,[2,3],[C,-C]); "
        "rgms_rdp11 = spm_mdp2rdp(rgms_mdp11_costs); rgms_rdp11.T = 64; "
        "rgms_pdp12 = spm_MDP_VB_XXX(rgms_rdp11);",
        nargout=0,
    )
    _normalize_pdp_to_cell_for_pull(dem_eng, "rgms_pdp12")
    rdp11 = _pull_nested_rdp_from_matlab(dem_eng, "rgms_rdp11")
    pdp12_mdp = _pull_mdp_from_matlab(dem_eng, "rgms_pdp12")
    pdp12_F: np.ndarray | None = None
    if _mat_int(dem_eng, "isfield(rgms_pdp12{1},'F')"):
        pdp12_F = np.asarray(dem_eng.eval("double(rgms_pdp12{1}.F)"), dtype=np.float64).ravel(
            order="F"
        )
    # Geometry checkpoint for partial Python vs full MATLAB on the same RDP (factor × time layouts).
    pdp12_l0_X_shapes: list[tuple[int, int]] = []
    pdp12_l0_P_shapes: list[tuple[int, int]] = []
    if _mat_int(dem_eng, "isfield(rgms_pdp12{1},'X')"):
        nf_x = _mat_int(dem_eng, "numel(rgms_pdp12{1}.X)")
        for f in range(1, nf_x + 1):
            nr = _mat_int(dem_eng, f"size(rgms_pdp12{{1}}.X{{{f}}},1)")
            nc = _mat_int(dem_eng, f"size(rgms_pdp12{{1}}.X{{{f}}},2)")
            pdp12_l0_X_shapes.append((nr, nc))
    if _mat_int(dem_eng, "isfield(rgms_pdp12{1},'P')"):
        nf_p = _mat_int(dem_eng, "numel(rgms_pdp12{1}.P)")
        for f in range(1, nf_p + 1):
            nr = _mat_int(dem_eng, f"size(rgms_pdp12{{1}}.P{{{f}}},1)")
            nc = _mat_int(dem_eng, f"size(rgms_pdp12{{1}}.P{{{f}}},2)")
            pdp12_l0_P_shapes.append((nr, nc))

    pdp12_l0_Q_shapes: list[tuple[int, int]] = []
    if _mat_int(dem_eng, "isfield(rgms_pdp12{1},'Q')"):
        nf_q = _mat_int(dem_eng, "numel(rgms_pdp12{1}.Q)")
        for f in range(1, nf_q + 1):
            nr = _mat_int(dem_eng, f"size(rgms_pdp12{{1}}.Q{{{f}}},1)")
            nc = _mat_int(dem_eng, f"size(rgms_pdp12{{1}}.Q{{{f}}},2)")
            pdp12_l0_Q_shapes.append((nr, nc))

    assembly_shapes: dict[str, tuple[int, int]] = {}
    for fld in ("o", "s", "u", "R", "v", "w"):
        if _mat_int(dem_eng, f"isfield(rgms_pdp12{{1}},'{fld}')"):
            ex = f"rgms_pdp12{{1}}.{fld}"
            nr = _mat_int(dem_eng, f"size({ex},1)")
            nc = _mat_int(dem_eng, f"size({ex},2)")
            assembly_shapes[f"pdp12_l0_{fld}_shape"] = (nr, nc)

    return {
        "entry12_capture_v": 3,
        "training_t": int(training_t),
        "n_outer": int(n_outer),
        "tag": entry12_vb_capture_tag(),
        "rdp11_nested_mat": rdp11,
        "pdp12_mdp_mat": pdp12_mdp,
        "pdp12_F_mat": pdp12_F,
        "pdp12_l0_X_shapes": pdp12_l0_X_shapes,
        "pdp12_l0_P_shapes": pdp12_l0_P_shapes,
        "pdp12_l0_Q_shapes": pdp12_l0_Q_shapes,
        **assembly_shapes,
    }


def load_or_build_entry12_vb_artifact(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    capture_path = entry12_vb_capture_path(training_t, n_outer)
    refresh = entry12_vb_capture_refresh_enabled()
    if capture_path.exists() and not refresh:
        with capture_path.open("rb") as f:
            old = pickle.load(f)
        if (
            isinstance(old, dict)
            and int(old.get("entry12_capture_v", 0)) in (1, 2, 3)
            and "pdp12_mdp_mat" in old
            and "rdp11_nested_mat" in old
        ):
            return old
        refresh = True
    if capture_path.exists() and refresh:
        capture_path.unlink(missing_ok=True)
    artifact = _capture_entry12_vb_artifact(dem_eng, training_t, n_outer)
    with capture_path.open("wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)
    return artifact


@pytest.mark.slow
def test_entry12_vb_capture_artifact_build_or_reuse(dem_eng_entry10):
    """Build or reuse Entry 12 MATLAB-VB checkpoint (heavy: runs ``spm_MDP_VB_XXX`` once per refresh)."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    try:
        artifact = load_or_build_entry12_vb_artifact(dem_eng_entry10, training_t, n_outer)
    except matlab.engine.MatlabExecutionError as e:
        pytest.skip(f"entry12 MATLAB capture unavailable in this env: {e}")
    assert int(artifact["entry12_capture_v"]) in (1, 2, 3)
    assert isinstance(artifact.get("pdp12_mdp_mat"), list)
    assert isinstance(artifact.get("rdp11_nested_mat"), dict)
    p = entry12_vb_capture_path(training_t, n_outer)
    assert p.is_file(), f"expected capture at {p}"


def test_entry12_capture_helpers_tag_and_path_roundtrip():
    """Sanity: path composition does not raise (no MATLAB)."""
    p = entry12_vb_capture_path(1000, 1)
    assert "dem_atari_entry12_vb_capture_t1000_outer1_" in str(p)


@pytest.mark.slow
def test_entry12_python_partial_structural_checkpoint_from_artifact(dem_eng_entry10):
    """
    Artifact-based Entry-12 checkpoint (Python partial mode).

    Runs ``spm_MDP_VB_XXX`` on MATLAB-captured ``rdp11`` with ``_rgms_partial_ok`` and
    compares structural parity against MATLAB ``pdp12`` capture: level count, ``T``, ``id``
    keys (``A``/``D``/``E``), ``a``/``b`` counts, per-factor ``X``/``P``/``Q`` shapes (artifact
    v2+), ``|F|`` vs MATLAB ``F`` vector (when stored), and ``o``/``s``/``u``/``R``/``v``/``w``
    shapes when capture **v3** includes MATLAB ``size()`` snapshots (~1691 assembly).
    """
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    try:
        artifact = load_or_build_entry12_vb_artifact(dem_eng_entry10, training_t, n_outer)
    except matlab.engine.MatlabExecutionError as e:
        pytest.skip(f"entry12 MATLAB capture unavailable in this env: {e}")
    rdp11 = artifact["rdp11_nested_mat"]
    mat_pdp = artifact["pdp12_mdp_mat"]

    py_out = spm_MDP_VB_XXX(rdp11, {"_rgms_partial_ok": 1})
    py_levels = py_out if isinstance(py_out, list) else [py_out]
    assert isinstance(mat_pdp, list) and len(mat_pdp) > 0
    assert len(py_levels) == len(mat_pdp), f"level count py={len(py_levels)} mat={len(mat_pdp)}"

    p0 = py_levels[0]
    m0 = mat_pdp[0]
    assert "id" in p0 and isinstance(p0["id"], dict)
    assert "id" in m0 and isinstance(m0["id"], dict)
    for k in ("A", "D", "E"):
        assert k in p0["id"], f"python missing id.{k}"
        assert k in m0["id"], f"matlab missing id.{k}"

    assert "a" in p0 and "a" in m0
    assert "b" in p0 and "b" in m0
    assert len(p0["a"]) == len(m0["a"]), f"a-count py={len(p0['a'])} mat={len(m0['a'])}"
    assert len(p0["b"]) == len(m0["b"]), f"b-count py={len(p0['b'])} mat={len(m0['b'])}"
    assert float(p0["T"]) == float(m0["T"]), f"T py={p0['T']} matlab_pull={m0['T']}"

    # Numeric geometry: factor × time layouts for posteriors (must match full MATLAB run on same RDP).
    x_shapes = artifact.get("pdp12_l0_X_shapes")
    if x_shapes:
        assert "X" in p0 and isinstance(p0["X"], list)
        assert len(p0["X"]) == len(x_shapes), (
            f"X factor count py={len(p0['X'])} mat_shapes={len(x_shapes)}"
        )
        for f, sh in enumerate(x_shapes):
            assert np.asarray(p0["X"][f]).shape == tuple(sh), (
                f"X[{f}] shape py={np.asarray(p0['X'][f]).shape} mat={sh}"
            )
    p_shapes = artifact.get("pdp12_l0_P_shapes")
    if p_shapes:
        assert "P" in p0 and isinstance(p0["P"], list)
        assert len(p0["P"]) == len(p_shapes), (
            f"P factor count py={len(p0['P'])} mat_shapes={len(p_shapes)}"
        )
        for f, sh in enumerate(p_shapes):
            assert np.asarray(p0["P"][f]).shape == tuple(sh), (
                f"P[{f}] shape py={np.asarray(p0['P'][f]).shape} mat={sh}"
            )

    q_shapes = artifact.get("pdp12_l0_Q_shapes")
    if q_shapes:
        assert "Q" in p0 and isinstance(p0["Q"], list)
        assert len(p0["Q"]) == len(q_shapes), (
            f"Q factor count py={len(p0['Q'])} mat_shapes={len(q_shapes)}"
        )
        for f, sh in enumerate(q_shapes):
            assert np.asarray(p0["Q"][f]).shape == tuple(sh), (
                f"Q[{f}] shape py={np.asarray(p0['Q'][f]).shape} mat={sh}"
            )

    F_mat = artifact.get("pdp12_F_mat")
    if F_mat is not None and "F" in p0:
        py_F = np.asarray(p0["F"], dtype=np.float64).ravel()
        assert py_F.size == np.asarray(F_mat).size, (
            f"|F| py={py_F.size} mat_capture={np.asarray(F_mat).size}"
        )

    for fld_key in (
        ("pdp12_l0_o_shape", "o"),
        ("pdp12_l0_s_shape", "s"),
        ("pdp12_l0_u_shape", "u"),
        ("pdp12_l0_R_shape", "R"),
        ("pdp12_l0_v_shape", "v"),
        ("pdp12_l0_w_shape", "w"),
    ):
        ak, pk = fld_key
        sh = artifact.get(ak)
        if sh is not None and pk in p0:
            assert np.asarray(p0[pk]).shape == tuple(sh), (
                f"{pk} shape py={np.asarray(p0[pk]).shape} mat={sh}"
            )

    # Partial mode guarantee for staged recursion continuity.
    assert int(np.asarray(p0.get("_rgms_partial_v", 0)).reshape(-1)[0]) == 1


@pytest.mark.slow
def test_entry12_driver_full_pdp_contract_matches_ledger():
    """
    Ledger integration (Python path): ``run_dem_atariiii(12)`` returns full-mode ``PDP`` with the
    structural contract documented in ``Atari_example.md`` (no MATLAB comparison — use
    ``test_entry12_python_partial_structural_checkpoint_from_artifact`` for artifact parity).
    """
    old_outer = os.environ.get("RGMS_ATARI_ENTRY8_OUTER")
    old_t = os.environ.get("RGMS_ATARI_TRAINING_T")
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "1"
    os.environ["RGMS_ATARI_TRAINING_T"] = "1000"
    try:
        from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii

        ctx = run_dem_atariiii(12)
    finally:
        if old_outer is None:
            os.environ.pop("RGMS_ATARI_ENTRY8_OUTER", None)
        else:
            os.environ["RGMS_ATARI_ENTRY8_OUTER"] = old_outer
        if old_t is None:
            os.environ.pop("RGMS_ATARI_TRAINING_T", None)
        else:
            os.environ["RGMS_ATARI_TRAINING_T"] = old_t

    assert ctx.get("_entry12_use_partial_vb") is False
    pdp = ctx["PDP"]
    assert isinstance(pdp, dict)
    assert "_rgms_partial_v" not in pdp
    assert float(pdp["T"]) == 64.0
    assert "X" in pdp and "P" in pdp and isinstance(pdp["X"], list) and isinstance(pdp["P"], list)
    assert len(pdp["X"]) == len(pdp["P"]) and len(pdp["X"]) > 0
    assert "id" in pdp and isinstance(pdp["id"], dict)
    # Full assembled output follows MATLAB post-loop fields (~1693+): X/P/O are guaranteed; Q may be absent.
    if "Q" in pdp:
        assert isinstance(pdp["Q"], list)
