"""OPTIM1 FSL backward — Entry 10 (``spm_RDP_sort_optim`` + ``spm_set_goals_optim``)."""

from __future__ import annotations

import copy
import pickle
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from python_src.optimized.toolbox.DEM.spm_RDP_sort_optim import spm_RDP_sort_optim
from python_src.optimized.toolbox.DEM.spm_set_goals_optim import spm_set_goals_optim
from python_src.toolbox.DEM.dem_atariiii_paths import dem_atariiii_paths_to_hits_P


def run_entry10_optim_from_mdp(
    mdp: list[dict[str, Any]],
    *,
    c_val: float = 32.0,
    nt_p: int = 32,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> dict[str, Any]:
    """Entry **10** optim ledger — native ``eig`` default (holistic OPTIM1 / W3 native)."""
    mdp_in = copy.deepcopy(mdp)
    mdp10, j10 = spm_RDP_sort_optim(mdp_in, eig=eig)
    mdp10 = spm_set_goals_optim(
        mdp10,
        np.array([2, 3], dtype=np.int64),
        np.array([c_val, -c_val], dtype=np.float64),
    )
    nm = len(mdp10)
    b1 = np.asarray(mdp10[nm - 1]["b"][0][0], dtype=np.float64)
    bp = (np.sum(b1, axis=2) > 0).astype(np.float64)
    hid_list = mdp10[nm - 1]["id"].get("hid", [])
    hid_arr = (
        np.asarray(hid_list, dtype=np.int64).ravel()
        if hid_list
        else np.zeros(0, dtype=np.int64)
    )
    p_mat = dem_atariiii_paths_to_hits_P(bp, hid_arr, nt_p)
    return {
        "mdp": mdp10,
        "P": p_mat,
        "hid": hid_arr,
        "entry10_j": j10,
        "entry10_Nt": nt_p,
    }


def run_entry10_optim_from_pre_entry10_pkl(
    *,
    pre_entry10_pkl: Path | None = None,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> dict[str, Any]:
    """Run Entry **10** optim from DEMO1 ``MDP_pre_entry10`` boundary PKL."""
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    pkl = pre_entry10_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    )
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 pre_entry10 PKL: {pkl}")
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "mdp" not in blob:
        raise TypeError(f"expected dict with mdp in {pkl}")
    c_val = float(blob.get("C", 32.0))
    t0 = time.perf_counter()
    out = run_entry10_optim_from_mdp(blob["mdp"], c_val=c_val, eig=eig)
    wall_s = time.perf_counter() - t0
    return {
        **out,
        "C": c_val,
        "validation_lane": "optim_pre_entry10",
        "source_pre10_pkl": str(pkl),
        "entry10_wall_s": wall_s,
    }


def write_entry10_optim_post_pkl(
    payload: dict[str, Any],
    path: Path | None = None,
    *,
    eig_source: str = "native",
) -> Path:
    from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir

    out = path or (optim1_fixtures_dir() / "DEMAtariIII_optim1_entry10_post.pkl")
    if eig_source == "matlab_engine":
        out = path or (
            optim1_fixtures_dir() / "DEMAtariIII_optim1_entry10_matlab_eig_post.pkl"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "mdp": payload["mdp"],
        "P": payload.get("P"),
        "hid": payload.get("hid"),
        "entry10_j": payload.get("entry10_j"),
        "entry10_Nt": payload.get("entry10_Nt"),
        "entry10_wall_s": payload.get("entry10_wall_s"),
        "C": payload.get("C"),
        "validation_lane": payload.get("validation_lane"),
        "source_pre10_pkl": payload.get("source_pre10_pkl"),
        "validation": {
            "lane": "optim1_entry10",
            "eig_source": eig_source,
            "matlab_eig_injected": eig_source == "matlab_engine",
            "authority_var": (
                "MDP_pre_entry11" if eig_source == "matlab_engine" else None
            ),
        },
    }
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def compare_entry10_optim_mdp_to_demo_matlab_authority(
    mdp: list[dict[str, Any]],
    *,
    authority_mat: Path | None = None,
) -> None:
    """Assert optim Entry **10** ``MDP`` matches DEMO1 ``MDP_pre_entry11`` (MATLAB FSL)."""
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_mdp_full_equal,
        _pull_mdp_from_matlab,
    )

    mat_path = authority_mat or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat"
    )
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing DEMO1 authority mat: {mat_path}")
    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        eng.eval(f"load('{str(mat_path.resolve()).replace(chr(92), '/')}');", nargout=0)
        mat_mdp = _pull_mdp_from_matlab(eng, "MDP_pre_entry11")
    finally:
        eng.quit()
    _assert_mdp_full_equal(mdp, mat_mdp, k=10)


def compare_entry10_optim_to_fidelity_native(
    optim_out: dict[str, Any],
    *,
    pre_entry10_pkl: Path | None = None,
    eig: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
) -> None:
    """Assert optim Entry **10** ≡ fidelity Entry **10** on same input (native ``eig``)."""
    from python_src.toolbox.DEM.fsl_backward_entry10 import run_entry10_from_mdp
    from tests.demo1.demo1_paths import demo1_fixtures_dir
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pkl = pre_entry10_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"
    )
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    c_val = float(blob.get("C", 32.0))
    fid = run_entry10_from_mdp(blob["mdp"], c_val=c_val, eig=eig)
    _assert_mdp_full_equal(optim_out["mdp"], fid["mdp"], k=10)
    np.testing.assert_array_equal(
        np.asarray(optim_out["entry10_j"], dtype=np.int64).ravel(order="F"),
        np.asarray(fid["entry10_j"], dtype=np.int64).ravel(order="F"),
    )
    np.testing.assert_allclose(
        np.asarray(optim_out["P"], dtype=np.float64),
        np.asarray(fid["P"], dtype=np.float64),
        rtol=0.0,
        atol=1e-12,
    )


__all__ = [
    "run_entry10_optim_from_mdp",
    "run_entry10_optim_from_pre_entry10_pkl",
    "write_entry10_optim_post_pkl",
    "compare_entry10_optim_to_fidelity_native",
    "compare_entry10_optim_mdp_to_demo_matlab_authority",
]
