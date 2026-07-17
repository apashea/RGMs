"""W2 Phase 4-E-1 — optim cold bands (12A–12C setup, 12G–12H teardown).

Optim-owned boundary for setup/teardown transliteration helpers. Calls fidelity
``spm_MDP_VB_XXX`` private helpers explicitly — deletion target when cold path is
fully native (post **4-E-1** / **4-X-1**).
"""
from __future__ import annotations

from typing import Any

from python_src.toolbox.DEM import spm_MDP_VB_XXX as _vb_fidelity


def vb_cold_setup_12b(
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """12B: tensors through ``H``, init ``Q/X/S/P`` / process."""
    bundle = _vb_fidelity._vb_tensors_through_H(models, nm, t_h)
    post = _vb_fidelity._vb_init_QXSP_outcomes_and_process(
        models, bundle, opts, float(hp["chi"])
    )
    bundle.update(post)
    return bundle


def vb_cold_setup_12c(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """12C: policy depth + ``M``."""
    bundle.update(_vb_fidelity._vb_policy_depth_and_get_M(models, bundle, hp))
    bundle["options_vb"] = opts
    return bundle


def vb_cold_setup_12bc(
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """12B + 12C — convenience wrapper."""
    bundle = vb_cold_setup_12b(models, nm, t_h, opts, hp)
    return vb_cold_setup_12c(models, bundle, opts, hp)


def vb_cold_teardown_12g(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """12G: backwards replay, learning, ``Y``, ``X/S`` layout, neural responses."""
    _vb_fidelity._vb_optional_backwards_replay(models, bundle, opts)
    _vb_fidelity._vb_accumulate_dirichlet_parameter_learning(models, bundle, hp)
    _vb_fidelity._vb_posterior_predictive_Y(models, bundle, opts)
    _vb_fidelity._vb_reorganize_X_S_from_QP(bundle)
    _vb_fidelity._vb_options_N_neural_simulated_responses(models, bundle, opts)


def vb_cold_assemble_12h(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> None:
    """12H: assemble final ``MDP`` result fields on ``models``."""
    _vb_fidelity._vb_assemble_mdp_results_1691(models, bundle)


def vb_cold_teardown_12gh(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """12G + 12H — convenience wrapper for nested lean child path."""
    vb_cold_teardown_12g(models, bundle, opts, hp)
    vb_cold_assemble_12h(models, bundle)


def vb_cold_setup_child_12bc_native(
    models: list[dict[str, Any]],
    nm: int,
    t_h: float,
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> dict[str, Any]:
    """**5-C-arena** — nested child 12B/C setup (optim cold bridge; no top-level re-entry)."""
    return vb_cold_setup_12bc(models, nm, t_h, opts, hp)


def vb_cold_teardown_child_partial_native(
    models: list[dict[str, Any]],
    bundle: dict[str, Any],
    opts: dict[str, Any],
    hp: dict[str, Any],
) -> None:
    """**5-C-arena** — nested child partial teardown (12G learning + 12H assemble)."""
    vb_cold_teardown_12gh(models, bundle, opts, hp)
