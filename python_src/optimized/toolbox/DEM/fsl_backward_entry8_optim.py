"""OPTIM1 FSL backward — Entry 8 (``spm_merge_structure_learning_optim``; not Entry 12).

Ledger: ``training_window_assimilations`` from ``dem_atariiii_entry8_optim``.

Authority: DEMO1 ``MDP_post_entry8`` in ``tests/demo1/fixtures/`` (read-only).
"""

from __future__ import annotations

import copy
import pickle
import time
from pathlib import Path
from typing import Any

from python_src.optimized.toolbox.DEM.dem_atariiii_entry8_optim import (
    training_window_assimilations,
)
from python_src.toolbox.DEM.dem_atariiii_pdp_o import assert_pdp_o_columns_sufficient
from python_src.toolbox.DEM.fsl_backward_entry8 import entry8_boundary_from_driver_ctx
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir


def run_entry8_optim_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **8** optim ledger from materialized pre-Entry-9 boundary dict.

    Required keys: ``mdp``, ``pdp_o``, ``Ne``. Optional: ``NT`` (100), ``n_outer`` (128).
    """
    ne = int(boundary["Ne"])
    nt = int(boundary.get("NT", 100))
    n_outer = int(boundary.get("n_outer", 128))
    assert_pdp_o_columns_sufficient(
        boundary["pdp_o"],
        ne=ne,
        nt=nt,
        n_outer=n_outer,
    )
    mdp_out, merge_s = training_window_assimilations(
        boundary["pdp_o"],
        copy.deepcopy(boundary["mdp"]),
        ne,
        nt=nt,
        n_outer=n_outer,
    )
    return {
        "mdp": mdp_out,
        "entry8_merge_loop_s": float(merge_s),
        "NT": nt,
        "n_outer": n_outer,
    }


def run_entry8_optim_from_pre_entry9_pkl(
    *,
    pre_entry9_pkl: Path | None = None,
) -> dict[str, Any]:
    """Run Entry **8** optim from DEMO1 ``MDP_pre_entry9`` boundary PKL."""
    pkl = pre_entry9_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
    )
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 pre_entry9 PKL: {pkl}")
    with pkl.open("rb") as f:
        boundary = pickle.load(f)
    if not isinstance(boundary, dict):
        raise TypeError(f"expected dict in {pkl}")
    t0 = time.perf_counter()
    out = run_entry8_optim_from_boundary(boundary)
    wall_s = time.perf_counter() - t0
    return {
        **out,
        "C": float(boundary.get("C", 32.0)),
        "validation_lane": "optim_pre_entry9",
        "source_pre9_pkl": str(pkl),
        "entry8_wall_s": wall_s,
    }


def write_entry8_optim_post_pkl(payload: dict[str, Any], path: Path | None = None) -> Path:
    """Persist OPTIM1 Entry **8** post blob under ``tests/demo1/optim1/fixtures/``."""
    out = path or (optim1_fixtures_dir() / "DEMAtariIII_optim1_entry8_post.pkl")
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "mdp": payload["mdp"],
        "entry8_merge_loop_s": payload.get("entry8_merge_loop_s"),
        "entry8_wall_s": payload.get("entry8_wall_s"),
        "NT": payload.get("NT"),
        "n_outer": payload.get("n_outer"),
        "C": payload.get("C"),
        "validation_lane": payload.get("validation_lane"),
        "source_pre9_pkl": payload.get("source_pre9_pkl"),
        "validation": {
            "lane": "optim1_entry8",
            "authority_var": "MDP_post_entry8",
        },
    }
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def compare_entry8_optim_mdp_to_demo_authority(
    mdp: list[dict[str, Any]],
    *,
    authority_mat: Path | None = None,
) -> None:
    """Assert ``MDP`` matches DEMO1 ``MDP_post_entry8`` authority."""
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_mdp_full_equal,
        _pull_mdp_from_matlab,
    )

    mat_path = authority_mat or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    )
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing DEMO1 authority mat: {mat_path}")
    repo = demo1_repo_root()
    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, repo)
        eng.eval(f"load('{str(mat_path.resolve()).replace(chr(92), '/')}');", nargout=0)
        mat_mdp = _pull_mdp_from_matlab(eng, "MDP_post_entry8")
    finally:
        eng.quit()
    _assert_mdp_full_equal(mdp, mat_mdp, k=8)


__all__ = [
    "entry8_boundary_from_driver_ctx",
    "run_entry8_optim_from_boundary",
    "run_entry8_optim_from_pre_entry9_pkl",
    "write_entry8_optim_post_pkl",
    "compare_entry8_optim_mdp_to_demo_authority",
]
