"""OPTIM1FULL — causal steps inside ``spm_RDP_MI`` (OPTIM1.md § 11.5.1)."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.spm_RDP_MI import MiCausalSnap, _build_mi_causal_snap

build_mi_causal_snap = _build_mi_causal_snap


def load_mi_causal_authority(mat_path: Path, var_name: str) -> MiCausalSnap:
    """Load MATLAB ``mi382_causal`` / ``mi429_causal`` struct via Engine pull."""
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root

    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        p = str(mat_path.resolve()).replace("\\", "/")
        eng.eval(f"load('{p}');", nargout=0)
        base = var_name
        b_ambig = np.asarray(eng.eval(f"{base}.B_ambig", nargout=1), dtype=np.float64)
        b_norm = np.asarray(eng.eval(f"{base}.B_norm", nargout=1), dtype=np.float64)
        c_n = int(np.asarray(eng.eval(f"{base}.C_n", nargout=1)).reshape(-1)[0])
        c_shapes = np.asarray(eng.eval(f"{base}.C_shapes", nargout=1), dtype=np.int64)
        c_sums = np.asarray(eng.eval(f"{base}.C_sums", nargout=1), dtype=np.float64).reshape(
            -1, 1
        )
        r_mat = np.asarray(eng.eval(f"{base}.R", nargout=1), dtype=np.float64)
        return MiCausalSnap(
            B_ambig=b_ambig,
            B_norm=b_norm,
            C_n=c_n,
            C_shapes=c_shapes,
            C_sums=c_sums,
            R=r_mat,
        )
    finally:
        eng.quit()


def _assert_snap_arrays_equal(
    py: np.ndarray, mat: np.ndarray, step: str, label: str
) -> None:
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_array_equal_exact

    _assert_array_equal_exact(py, mat, f"{step}:{label}", k=0)


def compare_mi_causal_snap(py: MiCausalSnap, mat: MiCausalSnap) -> tuple[str | None, str]:
    """Return ``(first_red_step, detail)``; ``(None, '')`` if steps 1--4 green."""
    try:
        _assert_snap_arrays_equal(py.B_ambig, mat.B_ambig, "B_ambig", "trailing_B")
    except AssertionError as exc:
        return "B_ambig", str(exc)

    try:
        _assert_snap_arrays_equal(py.B_norm, mat.B_norm, "B_norm", "trailing_B")
    except AssertionError as exc:
        return "B_norm", str(exc)

    if int(py.C_n) != int(mat.C_n):
        return "C", f"C_n py={py.C_n} mat={mat.C_n}"

    try:
        _assert_snap_arrays_equal(py.C_shapes, mat.C_shapes, "C", "shapes")
    except AssertionError as exc:
        return "C", str(exc)

    try:
        _assert_snap_arrays_equal(py.C_sums, mat.C_sums, "C", "sums")
    except AssertionError as exc:
        return "C", str(exc)

    try:
        _assert_snap_arrays_equal(py.R, mat.R, "R", "full")
    except AssertionError as exc:
        return "R", str(exc)

    return None, ""


def run_causal_gate(
    *,
    pre_mat: Path,
    pre_var: str,
    causal_mat: Path,
    causal_var: str,
    site_label: str,
) -> tuple[str | None, str]:
    """Steps **1--4** only; step **5** is the final MDP compare script."""
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat

    if not causal_mat.is_file():
        return (
            "capture",
            f"missing causal authority {causal_mat} — re-run capture_optim1full_mi_boundaries",
        )

    mdp_in = load_mdp_from_mat(pre_mat, pre_var)
    py_snap = build_mi_causal_snap(copy.deepcopy(mdp_in), 1)
    mat_snap = load_mi_causal_authority(causal_mat, causal_var)
    step, detail = compare_mi_causal_snap(py_snap, mat_snap)
    if step is not None:
        return step, f"[{site_label}] first causal red: {step} — {detail}"
    return None, f"[{site_label}] causal steps B_ambig..R OK (n_C={py_snap.C_n})"
