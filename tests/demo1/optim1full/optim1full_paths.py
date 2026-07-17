"""OPTIM1FULL fixture and artifact path resolution (lane-isolated)."""

from __future__ import annotations

import os
from pathlib import Path

from tests.demo1.demo1_paths import demo1_repo_root


def optim1full_repo_root() -> Path:
    return demo1_repo_root()


def optim1full_shipped_fixtures_dir() -> Path:
    return optim1full_repo_root() / "tests" / "demo1" / "optim1full" / "fixtures"


def optim1full_fixtures_dir() -> Path:
    """
    OPTIM1FULL Product B authority root.

    Resolution order:
    1. ``RGMS_OPTIM1FULL_FIXTURES_DIR``
    2. Shipped default ``tests/demo1/optim1full/fixtures``
    """
    raw = str(os.getenv("RGMS_OPTIM1FULL_FIXTURES_DIR", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim1full_shipped_fixtures_dir()


def optim1full_mdp_post_nr_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_MDP_post_nr.mat"


def optim1full_mdp_pre_mi382_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_MDP_pre_mi382.mat"


def optim1full_mdp_post_mi382_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_MDP_post_mi382.mat"


def optim1full_mdp_pre_mi429_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_MDP_pre_mi429.mat"


def optim1full_mdp_post_mi429_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_MDP_post_mi429.mat"


def optim1full_np_mi429_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_np_mi429.mat"


def optim1full_mi382_post_pkl() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_mi382_post.pkl"


def optim1full_mi429_post_pkl() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_mi429_post.pkl"


def optim1full_mi382_causal_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_mi382_causal.mat"


def optim1full_mi429_causal_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_mi429_causal.mat"


def optim1full_mdp_pre_active_inference_mat() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_MDP_pre_active_inference.mat"


def optim1full_post_nr_pkl() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_post_nr.pkl"


def optim1full_mdp_pre_pkl() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_mdp_pre.pkl"


def optim1full_rand_ledger_mat() -> Path:
    return optim1full_fixtures_dir() / "optim1full_dem_atari_rand_buf.mat"


def optim1full_rand_manifest_json() -> Path:
    return optim1full_fixtures_dir() / "optim1full_rand_manifest.json"


def optim1full_call3_rdp_pkl() -> Path:
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_call3_rdp.pkl"


def optim1full_call4_rdp_pkl() -> Path:
    """Assembled call-4 input RDP (Engine sort + ``spm_RDP_MI`` + goals/costs/mdp2rdp)."""
    return optim1full_fixtures_dir() / "DEMAtariIII_optim1full_call4_rdp.pkl"


# --- Per-game NR authority trace (OPTIM1FULL.md § "Per-game NR authority trace") ---
#
# One MATLAB ``capture_optim1full_rand_ledger`` run with
# ``RGMS_OPTIM1FULL_NR_AUTHORITY_TRACE=1`` dumps, for each of the 32 NR games, the
# MATLAB VB input ``RDP``, the MATLAB VB output ``PDP``, and the post-merge/basin
# ``MDP_post_game`` into this directory, plus a manifest. These are the genuine
# MATLAB authority for localizing the optimized ``spm_MDP_VB_XXX_optim`` game-by-game
# without ever re-running the (slow) Python fidelity NR loop.


def optim1full_nr_authority_dir() -> Path:
    return optim1full_fixtures_dir() / "optim1full_nr_authority"


def optim1full_nr_authority_manifest_json() -> Path:
    return optim1full_nr_authority_dir() / "optim1full_nr_authority_manifest.json"


def optim1full_nr_authority_rdp_mat(game: int) -> Path:
    return optim1full_nr_authority_dir() / f"DEMAtariIII_optim1full_nr_game_{int(game):02d}_rdp.mat"


def optim1full_nr_authority_pdp_mat(game: int) -> Path:
    return optim1full_nr_authority_dir() / f"DEMAtariIII_optim1full_nr_game_{int(game):02d}_pdp.mat"


def optim1full_nr_authority_mdp_mat(game: int) -> Path:
    return optim1full_nr_authority_dir() / f"DEMAtariIII_optim1full_nr_game_{int(game):02d}_mdp.mat"


# --- W1 phase 0 plot fixtures (OPTIM1FULL-pure; see OPTIM1FULL.md § W1) ---

OPTIM1FULL_PLOT_CTX_MAT_NAME = "DEMAtariIII_optim1full_plot_ctx.mat"


def optim1full_plot_ctx_mat() -> Path:
    """Shared plot inputs: ``RGB``, ``GDP``, ``Nm``, scalars (Model B session)."""
    return optim1full_fixtures_dir() / OPTIM1FULL_PLOT_CTX_MAT_NAME


def optim1full_pdp_mat_for_tag(tag: str) -> Path:
    """Entry **12** MATLAB **PDP** for plot oracles — ``DEMAtariIII_XXX_12_<tag>_pdp.mat``."""
    tag_use = str(tag).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_XXX_12_{tag_use}_pdp.mat"


def optim1full_pdp_pkl_for_tag(tag: str) -> Path:
    """Entry **12** Python **PDP** for plot Phase **B** — ``DEMAtariIII_XXX_12_<tag>_pdp.pkl``."""
    tag_use = str(tag).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_XXX_12_{tag_use}_pdp.pkl"


def optim1full_12plot_oracle_mat(tag: str) -> Path:
    """MATLAB 12PLOT numeric oracle — ``J``, ``K``, ``h`` for ``tag``."""
    tag_use = str(tag).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_entry12_{tag_use}_12PLOT.mat"


def optim1full_paths_oracle_mat(tag: str) -> Path:
    """MATLAB paths-panel oracle — ``I``, ``HID`` for ``tag`` (W1 **A2**)."""
    tag_use = str(tag).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_entry12_{tag_use}_PATHS.mat"


def optim1full_site_paths_oracle_mat(site_id: str) -> Path:
    """Spine paths oracle — ``I``, ``HID`` for one § **13** paths ``site_id``."""
    site_use = str(site_id).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_optim1full_{site_use}_paths.mat"


# --- Genuine MATLAB-owned plot-fence PDP authority (OPTIM1FULL.md § Parity-with-plots) ---
#
# One MATLAB ``capture_optim1full_rand_ledger`` run with
# ``RGMS_OPTIM1FULL_PLOT_FENCE_TRACE=1`` writes, for each DEM_AtariIII.m illustrate site,
# the INDEPENDENT MATLAB-computed VB output PDP at that fence (``metaPdp.capture ==
# 'capture_optim1full_plot_fence'``). This is the authority against which the translated
# Python plotting functions are certified. It is NOT a re-serialization of Python output;
# the Python-resaved ``…_<site>_input.mat`` (``--save-mat-from-pkl``) must NEVER stand in
# for it in the plot-parity ladder (that would be circular).
#
# Site -> MATLAB source boundary (baked into DEMAtariIII_entry12_dump_all_subentries.m):
#   dem_gameplay                 -> after spm_MDP_generate (Gameplay) → matlab_pdp
#   dem_attractors_basin         -> after Attractors basin loop → matlab_payload (NS…NH)
#   dem_attractors_mdp_post_sort -> after sort+goals → matlab_payload (b1/hid); kind post_sort_orbits
#   dem_generative_ai            -> vb_call1 → matlab_pdp
#   dem_active_inference_nr      -> final NR game (game 32) → matlab_pdp
#   dem_structure_learning       -> after NR i=NR → matlab_payload (F)
#   dem_before_compression_rgb   -> vb_call3 → matlab_pdp
#   dem_with_compression_rgb     -> vb_call4 → matlab_pdp
#   dem_orbits_before / _after   -> reuse call3/call4 matlab_pdp (spine_alias; no new dump)

OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE = "capture_optim1full_plot_fence"


def optim1full_plot_fence_matlab_pdp_mat(site_id: str) -> Path:
    """Independent MATLAB-owned plot-fence PDP for one illustrate ``site_id``."""
    site_use = str(site_id).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_optim1full_{site_use}_matlab_pdp.mat"


def optim1full_plot_fence_matlab_payload_mat(site_id: str) -> Path:
    """Independent MATLAB-owned non-PDP plot-fence payload (basin series, F, …)."""
    site_use = str(site_id).strip()
    return optim1full_fixtures_dir() / f"DEMAtariIII_optim1full_{site_use}_matlab_payload.mat"


def optim1full_visualizations_dir() -> Path:
    return optim1full_repo_root() / "visualizations"


def optim1full_plot_paths_for_site(site_id: str) -> dict[str, Path]:
    """
    Fixture / oracle / PNG path stems for one § **13** plot ``site_id``.

    Sites with ``legacy_entry12_tag`` also expose ``legacy_*`` paths for translation-milestone
    regression; normative spine inputs always use ``DEMAtariIII_optim1full_<site_id>_`` stems
    unless ``spine_alias_site_id`` remaps ``input_*`` / ``matlab_pdp`` to a sibling fence
    (``dem_orbits_*`` → call3/call4 RGB artifacts).

    Paths-only sites (legacy) load spine ``PDP`` from ``spine_pdp_site_id`` and store
    paths oracles under ``…_<site_id>_paths.mat``.

    ``authority_mat`` is the MATLAB-owned fence file (``matlab_pdp`` or ``matlab_payload``).
    For payload sites, ``matlab_pdp_mat`` aliases ``authority_mat`` so dump-once ladder helpers
    that still key on ``matlab_pdp_mat`` stamp the correct authority without a second gate.
    """
    from tests.demo1.optim1full.optim1full_plot_sites import (
        AUTHORITY_KIND_PAYLOAD,
        optim1full_paths_site_spec_optional,
        optim1full_plot_site_spec_optional,
    )

    key = str(site_id).strip()
    fix = optim1full_fixtures_dir()
    vis = optim1full_visualizations_dir()
    paths_spec = optim1full_paths_site_spec_optional(key)
    spec = optim1full_plot_site_spec_optional(key)

    if spec is not None:
        spine_id = str(spec.spine_alias_site_id).strip() if spec.spine_alias_site_id else key
        stem = f"AtariIII_optim1full_{key}"
        paths: dict[str, Path] = {
            "plot_ctx": optim1full_plot_ctx_mat(),
            "site_id": key,
            "input_mat": fix / f"DEMAtariIII_optim1full_{spine_id}_input.mat",
            "input_pkl": fix / f"DEMAtariIII_optim1full_{spine_id}_input.pkl",
            "oracle_mat": fix / f"DEMAtariIII_optim1full_{key}_oracle.mat",
            "png_python_glob": vis / f"{stem}_python_*.png",
            "png_compare_glob": vis / f"{stem}_compare_*.png",
        }
        if spine_id != key:
            paths["spine_alias_site_id"] = spine_id
        if spec.authority_kind == AUTHORITY_KIND_PAYLOAD:
            payload_mat = optim1full_plot_fence_matlab_payload_mat(key)
            paths["matlab_payload_mat"] = payload_mat
            paths["authority_mat"] = payload_mat
            paths["matlab_pdp_mat"] = payload_mat
        else:
            pdp_mat = optim1full_plot_fence_matlab_pdp_mat(spine_id)
            paths["matlab_pdp_mat"] = pdp_mat
            paths["authority_mat"] = pdp_mat
        if paths_spec is not None:
            paths["paths_oracle_mat"] = optim1full_site_paths_oracle_mat(key)
            paths["spine_pdp_site_id"] = paths_spec.spine_pdp_site_id
        if spec.legacy_entry12_tag:
            tag = spec.legacy_entry12_tag
            paths["legacy_input_mat"] = optim1full_pdp_mat_for_tag(tag)
            paths["legacy_input_pkl"] = optim1full_pdp_pkl_for_tag(tag)
            paths["legacy_oracle_mat"] = optim1full_12plot_oracle_mat(tag)
            if spec.legacy_paths_tag:
                paths["paths_oracle_mat"] = optim1full_paths_oracle_mat(spec.legacy_paths_tag)
        return paths

    if paths_spec is not None:
        spine_id = paths_spec.spine_pdp_site_id
        pdp_mat = optim1full_plot_fence_matlab_pdp_mat(spine_id)
        return {
            "plot_ctx": optim1full_plot_ctx_mat(),
            "site_id": key,
            "spine_pdp_site_id": spine_id,
            "input_mat": fix / f"DEMAtariIII_optim1full_{spine_id}_input.mat",
            "input_pkl": fix / f"DEMAtariIII_optim1full_{spine_id}_input.pkl",
            "matlab_pdp_mat": pdp_mat,
            "authority_mat": pdp_mat,
            "paths_oracle_mat": optim1full_site_paths_oracle_mat(key),
        }

    raise KeyError(f"unknown OPTIM1FULL plot/paths site_id: {key!r}")

