"""OPTIM1FULL W1 — plot oracle tests (no VB re-run).

Phase **A**: Python plot on MATLAB **PDP** (``.mat``) vs ``DEMAtariIII_entry12_<tag>_12PLOT.mat``.
Phase **B**: same ``J``/``K``/``h`` on Python Entry **12** **PDP** (``.pkl``).

Fences: call3/call4 (**A1** ``spm_show_RGB``; **A2** paths ``I``/``HID``); call2 (**A3-lite** NR game **1**).
Fixtures: ``optim1full_capture_plot_fixtures.py`` (``--oracle-only`` / ``--paths-only`` / ``--a3-lite-only``).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

from python_src.toolbox.DEM.dem_atariiii_plot_active_inference_nr import (
    dem_atariiii_plot_active_inference_nr,
)
from python_src.toolbox.DEM.dem_atariiii_plot_before_compression_rgb import (
    dem_atariiii_plot_before_compression_rgb,
)
from python_src.toolbox.DEM.dem_atariiii_plot_gameplay import dem_atariiii_plot_gameplay
from python_src.toolbox.DEM.dem_atariiii_plot_attractors_basin import (
    dem_atariiii_plot_attractors_basin,
)
from python_src.toolbox.DEM.dem_atariiii_plot_structure_learning import (
    dem_atariiii_plot_structure_learning,
)
from python_src.toolbox.DEM.dem_atariiii_plot_attractors_mdp_post_sort import (
    dem_atariiii_plot_attractors_mdp_post_sort,
)
from python_src.toolbox.DEM.dem_atariiii_plot_orbits_after import dem_atariiii_plot_orbits_after
from python_src.toolbox.DEM.dem_atariiii_plot_orbits_before import dem_atariiii_plot_orbits_before
from python_src.toolbox.DEM.dem_atariiii_plot_generative_ai import (
    dem_atariiii_plot_generative_ai,
)
from python_src.toolbox.DEM.dem_atariiii_plot_with_compression_rgb import (
    dem_atariiii_plot_with_compression_rgb,
)
from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
    ENTRY12_OPTIM1FULL_CALL2_TAG,
    ENTRY12_OPTIM1FULL_CALL3_TAG,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
)
from tests.demo1.optim1full.optim1full_plot import (
    A3_LITE_PLOT_TAG,
    assert_optim1full_live_pdp_plot_oracles,
    load_optim1full_12plot_oracle,
    load_optim1full_basin_series_for_site,
    load_optim1full_structure_f_for_site,
    load_optim1full_post_sort_payload_for_site,
    load_optim1full_paths_oracle,
    load_optim1full_pdp_for_plot,
    load_optim1full_pdp_for_site,
    load_optim1full_plot_ctx,
    load_optim1full_site_oracle,
    load_optim1full_site_paths_oracle,
    run_optim1full_paths_for_site,
    run_optim1full_paths_plot,
    run_optim1full_plot,
)
from tests.demo1.optim1full.optim1full_paths import (
    optim1full_12plot_oracle_mat,
    optim1full_paths_oracle_mat,
    optim1full_pdp_mat_for_tag,
    optim1full_pdp_pkl_for_tag,
    optim1full_plot_ctx_mat,
    optim1full_plot_paths_for_site,
)
from tests.demo1.optim1full.optim1full_plot_sites import (
    DEM_ACTIVE_INFERENCE_NR,
    DEM_BEFORE_COMPRESSION_RGB,
    DEM_GAMEPLAY,
    DEM_ATTRACTORS_BASIN,
    DEM_ATTRACTORS_MDP_POST_SORT,
    DEM_STRUCTURE_LEARNING,
    DEM_GENERATIVE_AI,
    DEM_ORBITS_BEFORE,
    DEM_ORBITS_AFTER,
    DEM_WITH_COMPRESSION_RGB,
)

# Plan order: call4 then call3; Phase A (mat) before Phase B (pkl) per tag.
_TEST_ORDER: tuple[tuple[str, str], ...] = (
    (ENTRY12_OPTIM1FULL_CALL4_TAG, "mat"),
    (ENTRY12_OPTIM1FULL_CALL4_TAG, "pkl"),
    (ENTRY12_OPTIM1FULL_CALL3_TAG, "mat"),
    (ENTRY12_OPTIM1FULL_CALL3_TAG, "pkl"),
)

_A3_LITE_TEST_ORDER: tuple[tuple[str, str], ...] = (
    (A3_LITE_PLOT_TAG, "mat"),
    (A3_LITE_PLOT_TAG, "pkl"),
)

_SITE_RGB_PLOT_FN = {
    DEM_BEFORE_COMPRESSION_RGB: dem_atariiii_plot_before_compression_rgb,
    DEM_WITH_COMPRESSION_RGB: dem_atariiii_plot_with_compression_rgb,
}

_SITE_JKH_ORDER: tuple[tuple[str, str, str], ...] = (
    (DEM_WITH_COMPRESSION_RGB, ENTRY12_OPTIM1FULL_CALL4_TAG, "mat"),
    (DEM_WITH_COMPRESSION_RGB, ENTRY12_OPTIM1FULL_CALL4_TAG, "pkl"),
    (DEM_BEFORE_COMPRESSION_RGB, ENTRY12_OPTIM1FULL_CALL3_TAG, "mat"),
    (DEM_BEFORE_COMPRESSION_RGB, ENTRY12_OPTIM1FULL_CALL3_TAG, "pkl"),
)

# ``matlab_pdp`` = plot-fn parity on the INDEPENDENT MATLAB-owned fence PDP (same input the
# MATLAB oracle itself used). ``pkl`` = full-chain parity (Python fence PDP + Python plot code).
_GENERATIVE_AI_JKH_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_GENERATIVE_AI, "matlab_pdp"),
    (DEM_GENERATIVE_AI, "mat"),
    (DEM_GENERATIVE_AI, "pkl"),
)

_ACTIVE_INFERENCE_NR_JKH_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ACTIVE_INFERENCE_NR, "matlab_pdp"),
    (DEM_ACTIVE_INFERENCE_NR, "mat"),
    (DEM_ACTIVE_INFERENCE_NR, "pkl"),
)

_BEFORE_COMPRESSION_JKH_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_BEFORE_COMPRESSION_RGB, "matlab_pdp"),
    (DEM_BEFORE_COMPRESSION_RGB, "mat"),
    (DEM_BEFORE_COMPRESSION_RGB, "pkl"),
)

_WITH_COMPRESSION_JKH_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_WITH_COMPRESSION_RGB, "matlab_pdp"),
    (DEM_WITH_COMPRESSION_RGB, "mat"),
    (DEM_WITH_COMPRESSION_RGB, "pkl"),
)

_ORBITS_BEFORE_IHID_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ORBITS_BEFORE, "matlab_pdp"),
    (DEM_ORBITS_BEFORE, "mat"),
    (DEM_ORBITS_BEFORE, "pkl"),
)

_ORBITS_AFTER_IHID_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ORBITS_AFTER, "matlab_pdp"),
    (DEM_ORBITS_AFTER, "mat"),
    (DEM_ORBITS_AFTER, "pkl"),
)

# Gameplay: final-t frame_rgb + control (not J/K/h). Prefer matlab_pdp + pkl only.
_GAMEPLAY_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_GAMEPLAY, "matlab_pdp"),
    (DEM_GAMEPLAY, "pkl"),
)

# Attractors basin: final NS…NH series (not J/K/h). Prefer matlab_pdp(=payload) + pkl.
_BASIN_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ATTRACTORS_BASIN, "matlab_pdp"),
    (DEM_ATTRACTORS_BASIN, "pkl"),
)

# Structure learning: F 6×NR. Prefer matlab_pdp(=payload) + pkl.
_STRUCTURE_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_STRUCTURE_LEARNING, "matlab_pdp"),
    (DEM_STRUCTURE_LEARNING, "pkl"),
)

# Attractors post-sort: u / I / HID. Prefer matlab_pdp(=payload) + pkl.
_POST_SORT_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ATTRACTORS_MDP_POST_SORT, "matlab_pdp"),
    (DEM_ATTRACTORS_MDP_POST_SORT, "pkl"),
)

# Orbits full figures: u / I / HID on call3/call4 PDP. Prefer matlab_pdp + pkl.
_ORBITS_BEFORE_FIGURE_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ORBITS_BEFORE, "matlab_pdp"),
    (DEM_ORBITS_BEFORE, "pkl"),
)
_ORBITS_AFTER_FIGURE_ORDER: tuple[tuple[str, str], ...] = (
    (DEM_ORBITS_AFTER, "matlab_pdp"),
    (DEM_ORBITS_AFTER, "pkl"),
)


def _require(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"missing OPTIM1FULL plot fixture: {path}")
    return path


def _require_site_pdp(paths: dict, source: str) -> Path:
    """Require the site PDP for ``source`` (``matlab_pdp`` = MATLAB-owned fence authority)."""
    if source == "matlab_pdp":
        return _require(paths["matlab_pdp_mat"])
    if source == "mat":
        return _require(paths["input_mat"])
    return _require(paths["input_pkl"])


def _assert_jkh(j, k, h, oracle: dict) -> None:
    np.testing.assert_array_equal(j, oracle["J"])
    np.testing.assert_array_equal(k, oracle["K"])
    np.testing.assert_array_equal(h, oracle["h"])


def _assert_gameplay(frame_rgb, control, oracle: dict) -> None:
    np.testing.assert_array_equal(frame_rgb, oracle["frame_rgb"])
    np.testing.assert_array_equal(control, oracle["control"])


def _assert_basin(ns, nu, na, no, nh, oracle: dict) -> None:
    np.testing.assert_array_equal(ns, oracle["NS"])
    np.testing.assert_array_equal(nu, oracle["NU"])
    np.testing.assert_array_equal(na, oracle["NA"])
    np.testing.assert_array_equal(no, oracle["NO"])
    np.testing.assert_array_equal(nh, oracle["NH"])


def _assert_structure_f(f_mat, oracle: dict) -> None:
    np.testing.assert_allclose(f_mat, oracle["F"], rtol=0.0, atol=1e-10)


def _assert_post_sort(u, i_mat, hid, oracle: dict) -> None:
    np.testing.assert_allclose(u, oracle["u"], rtol=0.0, atol=1e-10)
    np.testing.assert_array_equal(i_mat, oracle["I"])
    np.testing.assert_array_equal(hid, oracle["HID"])


@pytest.fixture(scope="module")
def gameplay_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_GAMEPLAY)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_GAMEPLAY)


@pytest.mark.parametrize("site_id,source", _GAMEPLAY_ORDER)
def test_dem_atariiii_plot_gameplay_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    gameplay_oracle,
):
    """Row **1** — ``dem_gameplay`` final ``t=128`` ``frame_rgb``/``control`` vs MATLAB oracle."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    frame_rgb, control, _png = dem_atariiii_plot_gameplay(pdp, plot_ctx, save_png=False)
    _assert_gameplay(frame_rgb, control, gameplay_oracle)


@pytest.fixture(scope="module")
def basin_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ATTRACTORS_BASIN)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_ATTRACTORS_BASIN)


@pytest.mark.parametrize("site_id,source", _BASIN_ORDER)
def test_dem_atariiii_plot_attractors_basin_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    basin_oracle,
):
    """Row **2** — ``dem_attractors_basin`` final ``NS``…``NH`` vs MATLAB oracle."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    series = load_optim1full_basin_series_for_site(site_id, source)  # type: ignore[arg-type]
    ns, nu, na, no, nh, _png = dem_atariiii_plot_attractors_basin(
        series, plot_ctx, save_png=False
    )
    _assert_basin(ns, nu, na, no, nh, basin_oracle)


@pytest.fixture(scope="module")
def structure_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_STRUCTURE_LEARNING)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_STRUCTURE_LEARNING)


@pytest.mark.parametrize("site_id,source", _STRUCTURE_ORDER)
def test_dem_atariiii_plot_structure_learning_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    structure_oracle,
):
    """Row **6** — ``dem_structure_learning`` ``F`` vs MATLAB oracle."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    series = load_optim1full_structure_f_for_site(site_id, source)  # type: ignore[arg-type]
    f_mat, _png = dem_atariiii_plot_structure_learning(series, plot_ctx, save_png=False)
    _assert_structure_f(f_mat, structure_oracle)


@pytest.fixture(scope="module")
def post_sort_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ATTRACTORS_MDP_POST_SORT)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_ATTRACTORS_MDP_POST_SORT)


@pytest.fixture(scope="module")
def post_sort_matlab_injects():
    """Product B policy B: one Engine for module-scoped eig+svd injects."""
    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_repo_root
    from tests.demo1.optim1full.optim1full_dir_orbits_matlab import (
        bind_dir_orbits_matlab_injects,
    )

    eng = matlab.engine.start_matlab()
    configure_dem_matlab_engine(eng, demo1_repo_root())
    injects = bind_dir_orbits_matlab_injects(eng)
    try:
        yield {"eng": eng, **injects}
    finally:
        eng.quit()


@pytest.mark.parametrize("site_id,source", _POST_SORT_ORDER)
def test_dem_atariiii_plot_attractors_mdp_post_sort_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    post_sort_oracle,
    post_sort_matlab_injects,
):
    """Row **3** — ``dem_attractors_mdp_post_sort`` ``u``/``I``/``HID`` vs MATLAB oracle."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    payload = load_optim1full_post_sort_payload_for_site(site_id, source)  # type: ignore[arg-type]
    u, i_mat, hid, _png = dem_atariiii_plot_attractors_mdp_post_sort(
        payload,
        plot_ctx,
        save_png=False,
        eig=post_sort_matlab_injects["eig"],
        svd=post_sort_matlab_injects["svd"],
        ness_order=post_sort_matlab_injects.get("ness_order"),
        eng=post_sort_matlab_injects["eng"],
    )
    _assert_post_sort(u, i_mat, hid, post_sort_oracle)


@pytest.mark.parametrize("site_id,source", _ORBITS_BEFORE_FIGURE_ORDER)
def test_dem_atariiii_plot_orbits_before_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    orbits_before_figure_oracle,
    post_sort_matlab_injects,
):
    """Row **8** — ``dem_orbits_before`` ``u``/``I``/``HID`` vs MATLAB oracle."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    u, i_mat, hid, _png = dem_atariiii_plot_orbits_before(
        pdp,
        plot_ctx,
        save_png=False,
        eig=post_sort_matlab_injects["eig"],
        svd=post_sort_matlab_injects["svd"],
        ness_order=post_sort_matlab_injects.get("ness_order"),
        eng=post_sort_matlab_injects["eng"],
    )
    _assert_post_sort(u, i_mat, hid, orbits_before_figure_oracle)


@pytest.fixture(scope="module")
def orbits_before_figure_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ORBITS_BEFORE)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_ORBITS_BEFORE)


@pytest.mark.parametrize("site_id,source", _ORBITS_AFTER_FIGURE_ORDER)
def test_dem_atariiii_plot_orbits_after_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    orbits_after_figure_oracle,
    post_sort_matlab_injects,
):
    """Row **10** — ``dem_orbits_after`` ``u``/``I``/``HID`` vs MATLAB oracle."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    u, i_mat, hid, _png = dem_atariiii_plot_orbits_after(
        pdp,
        plot_ctx,
        save_png=False,
        eig=post_sort_matlab_injects["eig"],
        svd=post_sort_matlab_injects["svd"],
        ness_order=post_sort_matlab_injects.get("ness_order"),
        eng=post_sort_matlab_injects["eng"],
    )
    _assert_post_sort(u, i_mat, hid, orbits_after_figure_oracle)


@pytest.fixture(scope="module")
def orbits_after_figure_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ORBITS_AFTER)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_ORBITS_AFTER)


@pytest.fixture(scope="module")
def plot_ctx():
    _require(optim1full_plot_ctx_mat())
    return load_optim1full_plot_ctx()


@pytest.fixture(scope="module")
def plot_oracles() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for tag in (ENTRY12_OPTIM1FULL_CALL4_TAG, ENTRY12_OPTIM1FULL_CALL3_TAG):
        _require(optim1full_12plot_oracle_mat(tag))
        out[tag] = load_optim1full_12plot_oracle(tag)
    return out


@pytest.mark.parametrize("tag,source", _TEST_ORDER)
def test_optim1full_plot_jkh_oracle(tag: str, source: str, plot_ctx, plot_oracles):
    """``J``/``K``/``h`` vs MATLAB 12PLOT capture for call3/call4 tier **3e/3f** PDP."""
    if source == "mat":
        _require(optim1full_pdp_mat_for_tag(tag))
    else:
        _require(optim1full_pdp_pkl_for_tag(tag))
    pdp = load_optim1full_pdp_for_plot(tag, source)  # type: ignore[arg-type]
    save_png = source == "mat" and tag == ENTRY12_OPTIM1FULL_CALL4_TAG
    j, k, h, png = run_optim1full_plot(tag, pdp, plot_ctx, save_png=save_png)
    if save_png:
        assert png is not None and png.is_file()
        assert "optim1full_plot" in png.name
    _assert_jkh(j, k, h, plot_oracles[tag])


@pytest.mark.parametrize("site_id,tag,source", _SITE_JKH_ORDER)
def test_dem_atariiii_plot_site_jkh_oracle(
    site_id: str,
    tag: str,
    source: str,
    plot_ctx,
    plot_oracles,
):
    """Top-level ``dem_atariiii_plot_*`` vs same MATLAB oracle as legacy tag path."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_plot(tag, source)  # type: ignore[arg-type]
    plot_fn = _SITE_RGB_PLOT_FN[site_id]
    j, k, h, _png = plot_fn(pdp, plot_ctx, save_png=False)
    _assert_jkh(j, k, h, plot_oracles[tag])


@pytest.fixture(scope="module")
def generative_ai_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_GENERATIVE_AI)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_GENERATIVE_AI)


@pytest.mark.parametrize("site_id,source", _GENERATIVE_AI_JKH_ORDER)
def test_dem_atariiii_plot_generative_ai_jkh_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    generative_ai_oracle,
):
    """Row **4** — ``dem_generative_ai`` ``J``/``K``/``h`` vs MATLAB oracle (hits **y=0**)."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    j, k, h, _png = dem_atariiii_plot_generative_ai(pdp, plot_ctx, save_png=False)
    _assert_jkh(j, k, h, generative_ai_oracle)


@pytest.fixture(scope="module")
def active_inference_nr_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ACTIVE_INFERENCE_NR)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_ACTIVE_INFERENCE_NR)


@pytest.mark.parametrize("site_id,source", _ACTIVE_INFERENCE_NR_JKH_ORDER)
def test_dem_atariiii_plot_active_inference_nr_jkh_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    active_inference_nr_oracle,
):
    """Row **5** — ``dem_active_inference_nr`` ``J``/``K``/``h`` vs spine MATLAB oracle (hits **y=-2**)."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    j, k, h, _png = dem_atariiii_plot_active_inference_nr(pdp, plot_ctx, save_png=False)
    _assert_jkh(j, k, h, active_inference_nr_oracle)


@pytest.fixture(scope="module")
def before_compression_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_BEFORE_COMPRESSION_RGB)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_BEFORE_COMPRESSION_RGB)


@pytest.mark.parametrize("site_id,source", _BEFORE_COMPRESSION_JKH_ORDER)
def test_dem_atariiii_plot_before_compression_jkh_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    before_compression_oracle,
):
    """Row **7** — ``dem_before_compression_rgb`` ``J``/``K``/``h`` vs spine MATLAB oracle (hits **y=-2**)."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    j, k, h, _png = dem_atariiii_plot_before_compression_rgb(pdp, plot_ctx, save_png=False)
    _assert_jkh(j, k, h, before_compression_oracle)


@pytest.fixture(scope="module")
def with_compression_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_WITH_COMPRESSION_RGB)
    _require(paths["oracle_mat"])
    return load_optim1full_site_oracle(DEM_WITH_COMPRESSION_RGB)


@pytest.mark.parametrize("site_id,source", _WITH_COMPRESSION_JKH_ORDER)
def test_dem_atariiii_plot_with_compression_jkh_oracle(
    site_id: str,
    source: str,
    plot_ctx,
    with_compression_oracle,
):
    """Row **9** — ``dem_with_compression_rgb`` ``J``/``K``/``h`` vs spine MATLAB oracle (hits **y=-2**)."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    j, k, h, _png = dem_atariiii_plot_with_compression_rgb(pdp, plot_ctx, save_png=False)
    _assert_jkh(j, k, h, with_compression_oracle)


@pytest.fixture(scope="module")
def orbits_before_paths_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ORBITS_BEFORE)
    _require(paths["paths_oracle_mat"])
    return load_optim1full_site_paths_oracle(DEM_ORBITS_BEFORE)


@pytest.mark.parametrize("site_id,source", _ORBITS_BEFORE_IHID_ORDER)
@pytest.mark.skip(
    reason=(
        "PARTIAL paths.mat superseded by full orbits_figure oracle "
        "(test_dem_atariiii_plot_orbits_before_oracle); stale Ns≠current PDP"
    )
)
def test_dem_orbits_before_paths_ihid_oracle(
    site_id: str,
    source: str,
    orbits_before_paths_oracle,
):
    """Row **8** — legacy paths-only ``I``/``HID`` (superseded by full figure oracle)."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    i_mat, hid = run_optim1full_paths_for_site(site_id, pdp)
    _assert_paths_i_hid(i_mat, hid, orbits_before_paths_oracle)


@pytest.fixture(scope="module")
def orbits_after_paths_oracle() -> dict:
    paths = optim1full_plot_paths_for_site(DEM_ORBITS_AFTER)
    _require(paths["paths_oracle_mat"])
    return load_optim1full_site_paths_oracle(DEM_ORBITS_AFTER)


@pytest.mark.parametrize("site_id,source", _ORBITS_AFTER_IHID_ORDER)
@pytest.mark.skip(
    reason=(
        "PARTIAL paths.mat superseded by full orbits_figure oracle "
        "(test_dem_atariiii_plot_orbits_after_oracle); stale Ns≠current PDP"
    )
)
def test_dem_orbits_after_paths_ihid_oracle(
    site_id: str,
    source: str,
    orbits_after_paths_oracle,
):
    """Row **10** — legacy paths-only ``I``/``HID`` (superseded by full figure oracle)."""
    paths = optim1full_plot_paths_for_site(site_id)
    _require_site_pdp(paths, source)
    pdp = load_optim1full_pdp_for_site(site_id, source)  # type: ignore[arg-type]
    i_mat, hid = run_optim1full_paths_for_site(site_id, pdp)
    _assert_paths_i_hid(i_mat, hid, orbits_after_paths_oracle)


@pytest.fixture(scope="module")
def paths_oracles() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for tag in (ENTRY12_OPTIM1FULL_CALL4_TAG, ENTRY12_OPTIM1FULL_CALL3_TAG):
        _require(optim1full_paths_oracle_mat(tag))
        out[tag] = load_optim1full_paths_oracle(tag)
    return out


def _assert_paths_i_hid(i_mat, hid, oracle: dict) -> None:
    np.testing.assert_array_equal(i_mat, oracle["I"])
    np.testing.assert_array_equal(hid, oracle["HID"])


@pytest.mark.parametrize("tag,source", _TEST_ORDER)
def test_optim1full_paths_ihid_oracle(tag: str, source: str, paths_oracles):
    """``I``/``HID`` vs MATLAB paths capture for call3/call4 tier **3e/3f** PDP."""
    if source == "mat":
        _require(optim1full_pdp_mat_for_tag(tag))
    else:
        _require(optim1full_pdp_pkl_for_tag(tag))
    pdp = load_optim1full_pdp_for_plot(tag, source)  # type: ignore[arg-type]
    i_mat, hid = run_optim1full_paths_plot(tag, pdp)
    _assert_paths_i_hid(i_mat, hid, paths_oracles[tag])


@pytest.fixture(scope="module")
def a3_lite_plot_oracle() -> dict:
    _require(optim1full_12plot_oracle_mat(A3_LITE_PLOT_TAG))
    return load_optim1full_12plot_oracle(A3_LITE_PLOT_TAG)


@pytest.mark.parametrize("tag,source", _A3_LITE_TEST_ORDER)
def test_optim1full_a3_lite_plot_jkh_oracle(
    tag: str,
    source: str,
    plot_ctx,
    a3_lite_plot_oracle,
):
    """``J``/``K``/``h`` vs MATLAB 12PLOT capture for call2 tier **3a** (NR game **1**)."""
    if source == "mat":
        _require(optim1full_pdp_mat_for_tag(tag))
    else:
        _require(optim1full_pdp_pkl_for_tag(tag))
    pdp = load_optim1full_pdp_for_plot(tag, source)  # type: ignore[arg-type]
    j, k, h, _png = run_optim1full_plot(tag, pdp, plot_ctx, save_png=False)
    _assert_jkh(j, k, h, a3_lite_plot_oracle)


_LIVE_ASSERT_ORDER: tuple[tuple[str, str, bool], ...] = (
    (ENTRY12_OPTIM1FULL_CALL4_TAG, "pkl", True),
    (ENTRY12_OPTIM1FULL_CALL3_TAG, "pkl", True),
    (A3_LITE_PLOT_TAG, "pkl", False),
)


@pytest.mark.parametrize("tag,source,include_paths", _LIVE_ASSERT_ORDER)
def test_optim1full_live_pdp_plot_oracles_wrapper(
    tag: str,
    source: str,
    include_paths: bool,
    plot_ctx,
):
    """Legacy W1-B assert path — tag oracles (driver hook contract regression)."""
    if source == "mat":
        _require(optim1full_pdp_mat_for_tag(tag))
    else:
        _require(optim1full_pdp_pkl_for_tag(tag))
    pdp = load_optim1full_pdp_for_plot(tag, source)  # type: ignore[arg-type]
    assert_optim1full_live_pdp_plot_oracles(
        tag,
        pdp,
        plot_ctx,
        include_paths=include_paths,
    )


_W1E_LIVE_SITE_ORDER: tuple[tuple[str, str | None], ...] = (
    (DEM_GENERATIVE_AI, None),
    (DEM_ACTIVE_INFERENCE_NR, None),
    (DEM_BEFORE_COMPRESSION_RGB, DEM_ORBITS_BEFORE),
    (DEM_WITH_COMPRESSION_RGB, DEM_ORBITS_AFTER),
)


@pytest.mark.parametrize("site_id,paths_site_id", _W1E_LIVE_SITE_ORDER)
def test_optim1full_live_site_plot_oracles_wrapper(
    site_id: str,
    paths_site_id: str | None,
    plot_ctx,
):
    """W1-E assert path — §13 site_id + spine oracles on frozen fence pkl (no full-replay)."""
    from tests.demo1.optim1full.optim1full_plot import assert_optim1full_live_site_plot_oracles

    paths = optim1full_plot_paths_for_site(site_id)
    _require(paths["input_pkl"])
    _require(paths["oracle_mat"])
    if paths_site_id is not None:
        _require(optim1full_plot_paths_for_site(paths_site_id)["oracle_mat"])
    pdp = load_optim1full_pdp_for_site(site_id, "pkl")
    assert_optim1full_live_site_plot_oracles(
        site_id,
        pdp,
        plot_ctx,
        include_paths_site_id=paths_site_id,
        site_label=f"fixture {site_id}",
    )
