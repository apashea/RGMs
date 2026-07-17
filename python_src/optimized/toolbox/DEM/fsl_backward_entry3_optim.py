"""OPTIM1 FSL backward — Entry 3 (``spm_MDP_generate_optim``; not Entry 12).

Ledger: ``prepare_gdp_for_generate`` → ``generate_mdp_rollout`` (optim).

Authority: DEMO1 ``PDP_o`` / ``PDP_O`` in ``tests/demo1/fixtures/`` (read-only).
"""

from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any

from python_src.optimized.toolbox.DEM.dem_atariiii_entry3_optim import (
    ATARI_TRAINING_T_LEDGER,
    generate_mdp_rollout,
    prepare_gdp_for_generate,
)
from python_src.toolbox.DEM.dem_atariiii_entry4 import ENTRY4_O_COLS
from tests.demo1.demo1_paths import demo1_fixtures_dir
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir


def run_entry3_optim_from_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    """
    Run Entry **3** optim ledger from materialized boundary.

    Required keys: ``gdp``. Optional: ``training_t`` (default ``10000``).
    """
    tt = int(boundary.get("training_t", ATARI_TRAINING_T_LEDGER))
    gdp = prepare_gdp_for_generate(boundary["gdp"], training_t=tt)
    t0 = time.perf_counter()
    pdp = generate_mdp_rollout(gdp)
    elapsed_s = time.perf_counter() - t0
    return {
        "gdp": gdp,
        "pdp": pdp,
        "training_t": tt,
        "entry3_generate_s": elapsed_s,
    }


def run_entry3_optim_from_entry2_post_pkl(
    *,
    entry2_post_pkl: Path | None = None,
    k_use: int | None = None,
    deadline_minutes: str = "60",
) -> dict[str, Any]:
    """
    Run Entry **3** at ``T=10000`` from DEMO1 Entry **2** post ``gdp`` with ``dem_atari_rand_buf`` replay.

    Requires DEMO1 fixtures: ``DEMAtariIII_fsl_backward_entry2_post.pkl``,
    ``dem_atari_rand_buf_through_entry11.mat``, ``fsl_backward_entry3_K_py.mat``.
    """
    from tests.demo1.optim1.optim1_replay_rand import (
        optim1_entry3_driver_env,
        optim1_replay_matlab_draws,
    )
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        load_dem_atari_rand_buf,
        load_entry3_k_py,
    )

    pkl = entry2_post_pkl or (demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_entry2_post.pkl")
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 Entry 2 post PKL: {pkl}")
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "gdp" not in blob:
        raise KeyError(f"expected dict with gdp in {pkl}")
    k_3 = int(k_use) if k_use is not None else load_entry3_k_py()
    buf, _k_11 = load_dem_atari_rand_buf()
    boundary = {"gdp": blob["gdp"], "training_t": ATARI_TRAINING_T_LEDGER}
    with optim1_entry3_driver_env(deadline_minutes=deadline_minutes):
        with optim1_replay_matlab_draws(k_3, buf) as ctr:
            out = run_entry3_optim_from_boundary(boundary)
        used = int(ctr[0])
    if used != k_3:
        raise RuntimeError(
            f"OPTIM1 Entry 3 replay: used {used} draws, expected K_3={k_3} "
            f"(unused_draws={k_3 - used})"
        )
    pdp = dict(out["pdp"])
    pdp["O_cols_pulled"] = ENTRY4_O_COLS
    return {
        "gdp": out["gdp"],
        "pdp": pdp,
        "training_t": ATARI_TRAINING_T_LEDGER,
        "validation_lane": "optim_entry2_post_replay",
        "k_3": k_3,
        "draws_used": used,
        "entry3_generate_s": out["entry3_generate_s"],
        "entry2_post_pkl": str(pkl),
    }


def write_entry3_optim_post_pkl(payload: dict[str, Any], path: Path | None = None) -> Path:
    """Persist OPTIM1 Entry **3** post blob under ``tests/demo1/optim1/fixtures/``."""
    out = path or (optim1_fixtures_dir() / "DEMAtariIII_optim1_entry3_post.pkl")
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "pdp": payload["pdp"],
        "gdp": payload.get("gdp"),
        "training_t": payload.get("training_t"),
        "validation_lane": payload.get("validation_lane"),
        "k_3": payload.get("k_3"),
        "draws_used": payload.get("draws_used"),
        "entry3_generate_s": payload.get("entry3_generate_s"),
    }
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def compare_entry3_optim_pdp_to_demo1_authority(
    pdp: dict[str, Any],
    *,
    authority_mat: Path | None = None,
) -> None:
    """Assert ``PDP.o`` and ``PDP.O(:,1:1000)`` match DEMO1 MATLAB authority."""
    from scipy.io import loadmat

    from tests.oracle.toolbox.DEM.fsl_backward_compare_entry3_pkl_to_mat import (
        _assert_pdp_O_equal,
        _assert_pdp_o_equal,
        _pdp_o_from_loadmat,
    )

    mat_path = authority_mat or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    )
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing DEMO1 authority mat: {mat_path}")
    raw = loadmat(str(mat_path), simplify_cells=True)
    for key in ("PDP_o", "PDP_O"):
        if key not in raw:
            raise KeyError(f"{mat_path} missing {key}")
    _assert_pdp_o_equal(pdp["o"], raw["PDP_o"])
    mat_O = _pdp_o_from_loadmat(raw["PDP_O"])
    o_cols = int(pdp.get("O_cols_pulled", ENTRY4_O_COLS))
    _assert_pdp_O_equal(pdp["O"], mat_O, max_cols=o_cols)
