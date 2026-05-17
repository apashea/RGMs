"""Entry 12 global gates — MATLAB `spm_MDP_VB_XXX(RDP)` boundary capture for DEM_AtariIII.

``run_dem_atariiii(entry_stop=12)`` calls Python ``spm_MDP_VB_XXX`` in **full mode** (no
``_rgms_partial_ok``). This module builds **artifact-first** MATLAB checkpoints so Entry 12
validation can replay a persisted MATLAB ``PDP`` (``rgms_pdp12`` pull) against Python.

Uses the same MATLAB preamble as Entry 10 sort capture through ``rgms_rdp11`` (costs,
``spm_mdp2rdp``, ``T = 64``), then runs::

    rgms_pdp12 = spm_MDP_VB_XXX(rgms_rdp11);

This file is intentionally **global** (artifact + structural + numeric + driver-contract gates), not
an Entry 12A/12B/... isolate test module.

**RNG / ``spm_sample`` (mandatory for ``F`` parity):** MATLAB’s file-local ``spm_sample`` consumes only
scalar ``rand()`` (same pattern as ``test_spm_MDP_generate.py``).

Capture **v5** matches parity **from the first line of** ``spm_MDP_VB_XXX`` **as actually invoked** after the
ledger preamble: MATLAB does **not** re-seed before VB. Immediately before the call we save
``rgms_entry12_s_pre = rng`` (the live twister state after ``spm_mdp2rdp`` / ``T=64``). We run
``rgms_pdp12 = spm_MDP_VB_XXX(rgms_rdp11)``, then ``rng(rgms_entry12_s_pre)`` and ``rand(K,1)`` where ``K`` is
the count of scalar ``numpy.random.rand()`` calls from a Python VB dry-run on the same pulled ``rdp11``. That
buffer is **exactly** the VB draw sequence under the preamble’s RNG continuation. Python tests patch
``numpy.random.rand`` to replay it. **Never** use a VB-local ``rng(arbitrary_seed)`` for this oracle: that would
misalign the workflow relative to ``DEM_AtariIII`` / capture preamble.

Environment:

- ``RGMS_ATARI_ENTRY12_VB_CAPTURE_REFRESH`` — ``1`` / ``true`` / ``yes`` / ``on`` to rebuild.
- ``RGMS_ATARI_ENTRY12_VB_CAPTURE_TAG`` — filename suffix (sanitized), default ``default``.

Capture versions:

- ``entry12_capture_v == 1`` — nested ``rdp11`` / ``pdp12`` pulls only.
- ``entry12_capture_v == 2`` — adds ``pdp12_l0_X_shapes`` / ``pdp12_l0_P_shapes`` for partial-mode geometry checks vs MATLAB.
- ``entry12_capture_v == 3`` — adds ``pdp12_l0_Q_shapes``, ``pdp12_l0_o_shape``, ``pdp12_l0_s_shape``, ``pdp12_l0_u_shape``, ``pdp12_l0_R_shape``, ``pdp12_l0_v_shape``, ``pdp12_l0_w_shape`` (MATLAB ~1691 assembly) for driver-relevant parity.
- ``entry12_capture_v == 4`` — (superseded) VB-local seed + buffer; **invalid** for current tests — pickles refresh to v5.
- ``entry12_capture_v == 5`` — preamble-true RNG: ``entry12_vb_matlab_rand_buf``, ``entry12_vb_numpy_rand_calls``, ``entry12_vb_rng_at_vb_entry`` (required for strict ``F`` parity tests).

Artifact path::

    tests/oracle/toolbox/DEM/_checkpoint_data/atari_entry/
      dem_atari_entry12_vb_capture_t<training_t>_outer<n_outer>_<tag>.pkl
"""

from __future__ import annotations

import copy
import os
import pickle
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest
import matlab.engine

from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    _matlab_build_entry10_training_end_boundary,
    _matlab_run_entry10_sort_goals_and_P,
    _pull_nested_rdp_from_matlab,
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


def count_numpy_rand_calls_for_vb_on_rdp11(rdp11: dict[str, Any]) -> int:
    """
    Dry-run Python ``spm_MDP_VB_XXX`` on a copy of ``rdp11`` and count scalar ``numpy.random.rand()`` calls.

    Used to size the MATLAB ``rand(K,1)`` buffer so Engine capture and Python replay share the same draw
    sequence (``spm_sample`` / branch notes).
    """
    ctr = [0]
    real_rand = np.random.rand

    def shim(*args: Any, **kwargs: Any) -> Any:
        if args or kwargs:
            raise RuntimeError(
                "entry12 VB rand counting: only scalar np.random.rand() is supported in this lane"
            )
        ctr[0] += 1
        return float(real_rand())

    with patch("numpy.random.rand", side_effect=shim):
        spm_MDP_VB_XXX(
            copy.deepcopy(rdp11),
            {},
            monitoring=False,
            dump_subentries=True,
            reuse_matlab_draws=False,
        )
    return int(ctr[0])


def spm_MDP_VB_XXX_with_matlab_rand_buf(rdp11: dict[str, Any], buf: np.ndarray | None) -> Any:
    """Run Python VB replaying ``buf`` via ``spm_MDP_VB_XXX(..., reuse_matlab_draws=True)``."""
    if buf is None or int(np.asarray(buf).size) == 0:
        return spm_MDP_VB_XXX(copy.deepcopy(rdp11), {}, reuse_matlab_draws=False)
    import os
    import tempfile

    from scipy.io import savemat

    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tf:
        tmp = Path(tf.name)
    savemat(
        str(tmp),
        {"vb_rand_buf": np.asarray(buf, dtype=np.float64).ravel(order="F")},
    )
    old = os.environ.get("RGMS_ENTRY12_VB_MATLAB_RAND_MAT")
    try:
        os.environ["RGMS_ENTRY12_VB_MATLAB_RAND_MAT"] = str(tmp)
        return spm_MDP_VB_XXX(copy.deepcopy(rdp11), {}, reuse_matlab_draws=True)
    finally:
        if old is None:
            os.environ.pop("RGMS_ENTRY12_VB_MATLAB_RAND_MAT", None)
        else:
            os.environ["RGMS_ENTRY12_VB_MATLAB_RAND_MAT"] = old
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _normalize_pdp_to_cell_for_pull(dem_eng, expr: str = "rgms_pdp12") -> None:
    """Brace-index pulls expect a cell array of per-level MDP structs."""
    dem_eng.eval(
        f"if ~iscell({expr}), {expr} = num2cell({expr}(:)); end;",
        nargout=0,
    )


def _capture_entry12_vb_artifact(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    """MATLAB lane through Entry 11 RDP, then ``spm_MDP_VB_XXX``; pull checkpoint fields (capture v5+)."""
    dem_eng.eval(
        "addpath('c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM','-begin');",
        nargout=0,
    )
    _matlab_build_entry10_training_end_boundary(dem_eng, training_t, n_outer, rng_seed=2)
    _matlab_run_entry10_sort_goals_and_P(dem_eng)
    dem_eng.eval(
        "rgms_mdp11_costs = spm_set_costs(rgms_mdp10_goals,[2,3],[C,-C]); "
        "rgms_rdp11 = spm_mdp2rdp(rgms_mdp11_costs); rgms_rdp11.T = 64; ",
        nargout=0,
    )
    dem_eng.eval(
        "rgms_entry12_e_repaired = 0; "
        "for rgms_m = 1:numel(rgms_rdp11), "
        "if ~isfield(rgms_rdp11(rgms_m),'E') || isempty(rgms_rdp11(rgms_m).E), "
        "rgms_rdp11(rgms_m).E = cell(1,numel(rgms_rdp11(rgms_m).B)); "
        "end; "
        "for rgms_f = 1:numel(rgms_rdp11(rgms_m).B), "
        "rgms_nu = size(rgms_rdp11(rgms_m).B{rgms_f},3); "
        "if rgms_nu < 1, rgms_nu = 1; end; "
        "if numel(rgms_rdp11(rgms_m).E) < rgms_f || isempty(rgms_rdp11(rgms_m).E{rgms_f}), "
        "rgms_rdp11(rgms_m).E{rgms_f} = ones(rgms_nu,1)/rgms_nu; "
        "rgms_entry12_e_repaired = rgms_entry12_e_repaired + 1; "
        "end; "
        "end; "
        "end; ",
        nargout=0,
    )
    rdp11 = _pull_nested_rdp_from_matlab(dem_eng, "rgms_rdp11")
    try:
        K = count_numpy_rand_calls_for_vb_on_rdp11(rdp11)
    except Exception as e:
        raise RuntimeError(
            "entry12 capture: Python VB dry-run failed while counting numpy.random.rand draws "
            f"(fix before MATLAB capture): {e}"
        ) from e
    dem_eng.eval(f"rgms_entry12_k = {int(K)};", nargout=0)
    # True entry parity: no rng() before VB — save live stream, run VB, rewind, extract exactly K scalars.
    dem_eng.eval(
        "rgms_entry12_s_pre = rng; "
        "rgms_pdp12 = spm_MDP_VB_XXX(rgms_rdp11); "
        "rng(rgms_entry12_s_pre); "
        "if rgms_entry12_k > 0, rgms_entry12_vb_rand_buf = rand(rgms_entry12_k, 1); "
        "else, rgms_entry12_vb_rand_buf = zeros(0,1); end; ",
        nargout=0,
    )
    _normalize_pdp_to_cell_for_pull(dem_eng, "rgms_pdp12")
    vb_buf = np.asarray(
        dem_eng.eval("double(rgms_entry12_vb_rand_buf)"), dtype=np.float64
    ).ravel(order="F")
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
        "entry12_capture_v": 5,
        "training_t": int(training_t),
        "n_outer": int(n_outer),
        "tag": entry12_vb_capture_tag(),
        "entry12_vb_rng_at_vb_entry": "preamble_continuation",
        "entry12_rdp11_empty_e_repair_count": int(_mat_int(dem_eng, "rgms_entry12_e_repaired")),
        "entry12_vb_numpy_rand_calls": int(K),
        "entry12_vb_matlab_rand_buf": vb_buf,
        "rdp11_nested_mat": rdp11,
        "pdp12_mdp_mat": pdp12_mdp,
        "pdp12_F_mat": pdp12_F,
        "pdp12_l0_X_shapes": pdp12_l0_X_shapes,
        "pdp12_l0_P_shapes": pdp12_l0_P_shapes,
        "pdp12_l0_Q_shapes": pdp12_l0_Q_shapes,
        **assembly_shapes,
    }


# --- Level-0 `F` vector: single authoritative parity gate (Entry 12) -----------------


def _entry12_level0_F_diagnostics(py_F: np.ndarray, fm: np.ndarray) -> dict[str, Any]:
    """Finite-element diagnostics for assertion messages (both inputs 1-D float64)."""
    py_F = np.asarray(py_F, dtype=np.float64).ravel()
    fm = np.asarray(fm, dtype=np.float64).ravel()
    if py_F.size != fm.size or py_F.size == 0:
        return {"n_py": int(py_F.size), "n_mat": int(fm.size)}
    nan_py = ~np.isfinite(py_F)
    nan_fm = ~np.isfinite(fm)
    fin = (~nan_py) & (~nan_fm)
    out: dict[str, Any] = {
        "n": int(py_F.size),
        "n_nonfinite_py": int(nan_py.sum()),
        "n_nonfinite_mat": int(nan_fm.sum()),
    }
    if not np.array_equal(nan_py, nan_fm):
        out["nonfinite_pattern_match"] = False
        return out
    out["nonfinite_pattern_match"] = True
    if not fin.any():
        return out
    d = np.abs(py_F[fin] - fm[fin])
    s_py = np.sign(py_F[fin])
    s_m = np.sign(fm[fin])
    nz = (s_py != 0) & (s_m != 0)
    sign_mismatch = int((nz & (s_py != s_m)).sum())
    out.update(
        {
            "max_abs_diff": float(np.max(d)),
            "mean_abs_diff": float(np.mean(d)),
            "p50_abs_diff": float(np.percentile(d, 50)),
            "p90_abs_diff": float(np.percentile(d, 90)),
            "p99_abs_diff": float(np.percentile(d, 99)),
            "sign_mismatch_count": sign_mismatch,
            "sum_py": float(np.sum(py_F[fin])),
            "sum_mat": float(np.sum(fm[fin])),
        }
    )
    return out


def assert_entry12_level0_F_full_vector_parity(py_F: np.ndarray, fm: np.ndarray) -> None:
    """
    Authoritative Entry-12 gate: full level-0 ``F`` vs MATLAB artifact ``pdp12_F_mat``.

    **Strict float parity** on mutually finite elements (``numpy.array_equal``). Do not add ``rtol``/``atol``
    acceptance here unless a residual inequality is documented in branch notes after proving true parity is
    unattainable for a stated reason. Oracle tests must replay MATLAB ``rand`` (capture v5 buffer) so trajectories
    match; mismatches then indicate a translation bug, not “tolerance tuning”.
    """
    py_F = np.asarray(py_F, dtype=np.float64).ravel()
    fm = np.asarray(fm, dtype=np.float64).ravel()
    assert py_F.size == fm.size, (
        f"|F| mismatch: python={py_F.size} matlab_artifact={fm.size}; "
        f"diag={_entry12_level0_F_diagnostics(py_F, fm)}"
    )
    nan_py = ~np.isfinite(py_F)
    nan_fm = ~np.isfinite(fm)
    assert np.array_equal(nan_py, nan_fm), (
        "non-finite pattern mismatch for F; "
        f"diag={_entry12_level0_F_diagnostics(py_F, fm)}"
    )
    fin = ~nan_py
    if not fin.any():
        return
    if not np.array_equal(py_F[fin], fm[fin]):
        raise AssertionError(
            "full-vector F strict parity failed; "
            f"diag={_entry12_level0_F_diagnostics(py_F, fm)}"
        )


def load_or_build_entry12_vb_artifact(dem_eng, training_t: int, n_outer: int) -> dict[str, Any]:
    capture_path = entry12_vb_capture_path(training_t, n_outer)
    refresh = entry12_vb_capture_refresh_enabled()
    if capture_path.exists() and not refresh:
        with capture_path.open("rb") as f:
            old = pickle.load(f)
        if (
            isinstance(old, dict)
            and int(old.get("entry12_capture_v", 0)) in (1, 2, 3, 4, 5)
            and "pdp12_mdp_mat" in old
            and "rdp11_nested_mat" in old
        ):
            if int(old.get("entry12_capture_v", 0)) < 5 or "entry12_vb_matlab_rand_buf" not in old:
                refresh = True
            else:
                return old
        else:
            refresh = True
    if capture_path.exists() and refresh:
        capture_path.unlink(missing_ok=True)
    artifact = _capture_entry12_vb_artifact(dem_eng, training_t, n_outer)
    with capture_path.open("wb") as f:
        pickle.dump(artifact, f, protocol=pickle.HIGHEST_PROTOCOL)
    return artifact


@pytest.mark.slow
def test_entry12_vb_capture_artifact_build_or_reuse(dem_eng_entry12):
    """Build or reuse Entry 12 MATLAB-VB checkpoint (heavy: runs ``spm_MDP_VB_XXX`` once per refresh)."""
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    try:
        artifact = load_or_build_entry12_vb_artifact(dem_eng_entry12, training_t, n_outer)
    except matlab.engine.MatlabExecutionError as e:
        pytest.skip(f"entry12 MATLAB capture unavailable in this env: {e}")
    except RuntimeError as e:
        pytest.fail(f"entry12 capture precondition failed (Python VB dry-run / buffer sizing): {e}")
    assert int(artifact["entry12_capture_v"]) == 5
    assert artifact.get("entry12_vb_rng_at_vb_entry") == "preamble_continuation"
    assert isinstance(artifact.get("entry12_vb_matlab_rand_buf"), np.ndarray)
    assert isinstance(artifact.get("pdp12_mdp_mat"), list)
    assert isinstance(artifact.get("rdp11_nested_mat"), dict)
    p = entry12_vb_capture_path(training_t, n_outer)
    assert p.is_file(), f"expected capture at {p}"


def test_entry12_capture_helpers_tag_and_path_roundtrip():
    """Sanity: path composition does not raise (no MATLAB)."""
    p = entry12_vb_capture_path(1000, 1)
    assert "dem_atari_entry12_vb_capture_t1000_outer1_" in str(p)


def test_entry12_count_numpy_rand_for_vb_shim():
    """``count_numpy_rand_calls_for_vb_on_rdp11`` increments once per scalar ``numpy.random.rand()``."""
    n_calls = 11

    def _consume() -> None:
        for _ in range(n_calls):
            float(np.random.rand())

    ctr = [0]
    real_rand = np.random.rand

    def shim(*args: Any, **kwargs: Any) -> Any:
        if args or kwargs:
            raise RuntimeError("expected scalar rand")
        ctr[0] += 1
        return float(real_rand())

    with patch("numpy.random.rand", side_effect=shim):
        _consume()
    assert ctr[0] == n_calls


def test_entry12_level0_F_gate_helper_synthetic():
    """No MATLAB: exercise full-vector ``F`` gate and diagnostics."""
    x = np.array([1.0, -2.0, 3.0, 1e4], dtype=np.float64)
    assert_entry12_level0_F_full_vector_parity(x, x.copy())
    y = x.copy()
    y[1] += 1.0
    with pytest.raises(AssertionError):
        assert_entry12_level0_F_full_vector_parity(x, y)
    d = _entry12_level0_F_diagnostics(x, y)
    assert d["max_abs_diff"] == 1.0
    z = x.copy()
    z[0] = np.nan
    with pytest.raises(AssertionError):
        assert_entry12_level0_F_full_vector_parity(x, z)


@pytest.mark.slow
def test_entry12_python_full_structural_checkpoint_from_artifact(dem_eng_entry12):
    """
    Artifact-based Entry-12 checkpoint (Python full mode).

    Runs ``spm_MDP_VB_XXX`` on MATLAB-captured ``rdp11`` (full mode) and
    compares structural parity against MATLAB ``pdp12`` capture: level count, ``T``, ``id``
    keys (``A``/``D``/``E``), ``a``/``b`` counts, per-factor ``X``/``P``/``Q`` shapes (artifact
    v2+), and ``o``/``s``/``u``/``R``/``v``/``w`` shapes when capture **v3** includes MATLAB
    ``size()`` snapshots (~1691 assembly).

    **Numeric full-vector ``F`` parity** is gated only by
    ``test_entry12_python_full_F_vector_parity_from_artifact`` (not here).
    """
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    try:
        artifact = load_or_build_entry12_vb_artifact(dem_eng_entry12, training_t, n_outer)
    except matlab.engine.MatlabExecutionError as e:
        pytest.skip(f"entry12 MATLAB capture unavailable in this env: {e}")
    except RuntimeError as e:
        pytest.fail(f"entry12 artifact build failed (Python VB dry-run / capture chain): {e}")
    rdp11 = artifact["rdp11_nested_mat"]
    mat_pdp = artifact["pdp12_mdp_mat"]
    vb_buf = artifact.get("entry12_vb_matlab_rand_buf")
    py_out = spm_MDP_VB_XXX_with_matlab_rand_buf(rdp11, vb_buf)
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
    if F_mat is not None:
        assert "F" in p0, "artifact has MATLAB F but Python PDP lacks F"
        py_F = np.asarray(p0["F"], dtype=np.float64).ravel()
        fm = np.asarray(F_mat, dtype=np.float64).ravel()
        assert py_F.size == fm.size, f"|F| py={py_F.size} mat_capture={fm.size} (full parity: F vector test)"

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

    assert "_rgms_partial_v" not in p0


@pytest.mark.slow
def test_entry12_python_full_F_vector_parity_from_artifact(dem_eng_entry12):
    """
    **Authoritative** Entry-12 numeric gate: full level-0 ``F`` vs MATLAB ``rgms_pdp12{1}.F``.

    Requires capture **v5** (preamble-true RNG: no ``rng`` before ``spm_MDP_VB_XXX``; MATLAB
    ``rng(s_pre); rand(K,1)`` after VB). Strict ``numpy.array_equal`` on finite ``F`` with
    ``spm_MDP_VB_XXX_with_matlab_rand_buf``.
    """
    raw_t = str(os.getenv("RGMS_ATARI_TRAINING_T", "10000")).strip()
    training_t = max(int(raw_t), 1000)
    raw = str(os.getenv("RGMS_ATARI_ENTRY8_OUTER", "2")).strip()
    n_outer = int(np.clip(int(raw), 1, 128))

    try:
        artifact = load_or_build_entry12_vb_artifact(dem_eng_entry12, training_t, n_outer)
    except matlab.engine.MatlabExecutionError as e:
        pytest.skip(f"entry12 MATLAB capture unavailable in this env: {e}")
    except RuntimeError as e:
        pytest.fail(f"entry12 artifact build failed (Python VB dry-run / capture chain): {e}")

    F_mat = artifact.get("pdp12_F_mat")
    if F_mat is None:
        pytest.skip("artifact has no pdp12_F_mat (MATLAB PDP lacked F)")
    vb_buf = artifact.get("entry12_vb_matlab_rand_buf")
    if vb_buf is None:
        pytest.skip("capture v5 required: entry12_vb_matlab_rand_buf missing (refresh capture)")

    rdp11 = artifact["rdp11_nested_mat"]
    py_out = spm_MDP_VB_XXX_with_matlab_rand_buf(rdp11, vb_buf)
    p0 = py_out[0] if isinstance(py_out, list) else py_out
    assert "F" in p0, "Python PDP missing F while artifact has MATLAB F"
    assert_entry12_level0_F_full_vector_parity(p0["F"], F_mat)


@pytest.mark.slow
def test_entry12_driver_full_pdp_contract_matches_ledger():
    """
    Ledger integration (Python path): ``run_dem_atariiii(12)`` returns full-mode ``PDP`` with the
    structural contract documented in ``Atari_example.md`` (no MATLAB comparison — use
    ``test_entry12_python_full_structural_checkpoint_from_artifact`` for artifact parity).
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
