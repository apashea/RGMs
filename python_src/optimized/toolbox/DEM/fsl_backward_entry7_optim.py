"""OPTIM1 FSL backward — Entry 7 (``spm_merge_structure_learning_optim``; not Entry 12).

Ledger: ``assimilate_hit_miss_sequences_optim`` from ``dem_atariiii_entry7_optim``.

Authority: DEMO1 ``MDP_pre_entry9`` in ``tests/demo1/fixtures/`` (read-only).
"""

from __future__ import annotations

import copy
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np

from python_src.toolbox.DEM.dem_atariiii_entry6 import find_events_and_windows
from python_src.optimized.toolbox.DEM.dem_atariiii_entry7_optim import (
    assimilate_hit_miss_sequences_optim,
)
from python_src.toolbox.DEM.dem_atariiii_pdp_o import assert_pdp_o_columns_sufficient
from python_src.toolbox.DEM.fsl_backward_entry7 import entry7_boundary_from_driver_ctx
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir


def run_entry7_optim_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """Run Entry **7** optim ledger from materialized pre-Entry-7 boundary dict."""
    ne = int(boundary["Ne"])
    t0 = time.perf_counter()
    _r, _c, windows = find_events_and_windows(
        np.asarray(boundary["pdp_o_obs"], dtype=np.float64),
        boundary["gdp_id"],
        ne,
    )
    assert_pdp_o_columns_sufficient(
        boundary["pdp_o"],
        ne=ne,
        entry6_windows=windows,
    )
    mdp_out = assimilate_hit_miss_sequences_optim(
        boundary["pdp_o"],
        copy.deepcopy(boundary["mdp"]),
        windows,
        ne,
    )
    entry7_loop_s = time.perf_counter() - t0
    return {
        "mdp": mdp_out,
        "entry6_windows": windows,
        "n_windows": len(windows),
        "entry7_loop_s": float(entry7_loop_s),
    }


def run_entry7_optim_from_pre_entry7_pkl(
    *,
    pre_entry7_pkl: Path | None = None,
) -> dict[str, Any]:
    """Run Entry **7** optim from DEMO1 ``MDP_pre_entry7`` boundary PKL."""
    pkl = pre_entry7_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry7.pkl"
    )
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 pre_entry7 PKL: {pkl}")
    with pkl.open("rb") as f:
        boundary = pickle.load(f)
    if not isinstance(boundary, dict):
        raise TypeError(f"expected dict in {pkl}")
    t0 = time.perf_counter()
    out = run_entry7_optim_from_boundary(boundary)
    wall_s = time.perf_counter() - t0
    return {
        **out,
        "C": float(boundary.get("C", 32.0)),
        "validation_lane": "optim_pre_entry7",
        "source_pre7_pkl": str(pkl),
        "entry7_wall_s": wall_s,
    }


def write_entry7_optim_post_pkl(payload: dict[str, Any], path: Path | None = None) -> Path:
    """Persist OPTIM1 Entry **7** post blob under ``tests/demo1/optim1/fixtures/``."""
    out = path or (optim1_fixtures_dir() / "DEMAtariIII_optim1_entry7_post.pkl")
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "mdp": payload["mdp"],
        "entry6_windows": payload.get("entry6_windows"),
        "n_windows": payload.get("n_windows"),
        "entry7_loop_s": payload.get("entry7_loop_s"),
        "entry7_wall_s": payload.get("entry7_wall_s"),
        "C": payload.get("C"),
        "validation_lane": payload.get("validation_lane"),
        "source_pre7_pkl": payload.get("source_pre7_pkl"),
        "validation": {
            "lane": "optim1_entry7",
            "authority_var": "MDP_pre_entry9",
        },
    }
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def compare_entry7_optim_mdp_to_demo_authority(
    mdp: list[dict[str, Any]],
    *,
    authority_mat: Path | None = None,
) -> None:
    """Assert ``MDP`` matches DEMO1 ``MDP_pre_entry9`` authority."""
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
        mat_mdp = _pull_mdp_from_matlab(eng, "MDP_pre_entry9")
    finally:
        eng.quit()
    _assert_mdp_full_equal(mdp, mat_mdp, k=7)


__all__ = [
    "entry7_boundary_from_driver_ctx",
    "run_entry7_optim_from_boundary",
    "run_entry7_optim_from_pre_entry7_pkl",
    "write_entry7_optim_post_pkl",
    "compare_entry7_optim_mdp_to_demo_authority",
]
