"""OPTIM1FULL plot site registry — ``dem_*`` IDs per ``Atari_plotting.md`` § **13**."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
    ENTRY12_OPTIM1FULL_CALL2_TAG,
    ENTRY12_OPTIM1FULL_CALL3_TAG,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
)

DEM_GAMEPLAY = "dem_gameplay"
DEM_ATTRACTORS_BASIN = "dem_attractors_basin"
DEM_ATTRACTORS_MDP_POST_SORT = "dem_attractors_mdp_post_sort"
DEM_GENERATIVE_AI = "dem_generative_ai"
DEM_ACTIVE_INFERENCE_NR = "dem_active_inference_nr"
DEM_STRUCTURE_LEARNING = "dem_structure_learning"
DEM_BEFORE_COMPRESSION_RGB = "dem_before_compression_rgb"
DEM_ORBITS_BEFORE = "dem_orbits_before"
DEM_WITH_COMPRESSION_RGB = "dem_with_compression_rgb"
DEM_ORBITS_AFTER = "dem_orbits_after"

OPTIM1FULL_PLOT_SITE_IDS: tuple[str, ...] = (
    DEM_GAMEPLAY,
    DEM_ATTRACTORS_BASIN,
    DEM_ATTRACTORS_MDP_POST_SORT,
    DEM_GENERATIVE_AI,
    DEM_ACTIVE_INFERENCE_NR,
    DEM_STRUCTURE_LEARNING,
    DEM_BEFORE_COMPRESSION_RGB,
    DEM_ORBITS_BEFORE,
    DEM_WITH_COMPRESSION_RGB,
    DEM_ORBITS_AFTER,
)

# Site kinds — declared numerics for site-type-aware --plot-parity (Step 5+).
# Never put non-rgb_jkh sites into PLOT_PARITY_RGB_SITES.
SITE_KIND_RGB_JKH = "rgb_jkh"
SITE_KIND_GAMEPLAY_O2RGB = "gameplay_o2rgb"
SITE_KIND_BASIN_SERIES = "basin_series"
SITE_KIND_POST_SORT_ORBITS = "post_sort_orbits"
SITE_KIND_ORBITS_FIGURE = "orbits_figure"
SITE_KIND_STRUCTURE_F = "structure_f"

# Authority artifact kind: PDP fence vs non-PDP payload (NS…NH, F, …).
AUTHORITY_KIND_PDP = "matlab_pdp"
AUTHORITY_KIND_PAYLOAD = "matlab_payload"


@dataclass(frozen=True)
class Optim1fullPlotSiteSpec:
    """Fence parameters for one ``DEM_AtariIII.m`` plot site."""

    site_id: str
    figure_title: str
    kind: str
    numeric_keys: tuple[str, ...]
    nt: int = 0
    movie: int = 0
    hits_y_offset: float = 0.0
    final_t: int = 0
    authority_kind: str = AUTHORITY_KIND_PDP
    legacy_entry12_tag: Optional[str] = None
    legacy_paths_tag: Optional[str] = None
    # When set, spine ``input.pkl`` / ``matlab_pdp`` resolve to this sibling site
    # (orbits before/after reuse call3/call4 RGB fence artifacts; no duplicate export).
    spine_alias_site_id: Optional[str] = None


@dataclass(frozen=True)
class Optim1fullPathsSiteSpec:
    """Paths-to-hits panel at a § **13** site — uses paired spine ``PDP`` from ``spine_pdp_site_id``."""

    site_id: str
    panel_title: str
    nt: int
    b_threshold: float
    spine_pdp_site_id: str


def _site_specs() -> dict[str, Optim1fullPlotSiteSpec]:
    return {
        DEM_GAMEPLAY: Optim1fullPlotSiteSpec(
            site_id=DEM_GAMEPLAY,
            figure_title="Gameplay",
            kind=SITE_KIND_GAMEPLAY_O2RGB,
            numeric_keys=("frame_rgb", "control"),
            final_t=128,
        ),
        DEM_ATTRACTORS_BASIN: Optim1fullPlotSiteSpec(
            site_id=DEM_ATTRACTORS_BASIN,
            figure_title="Attractors",
            kind=SITE_KIND_BASIN_SERIES,
            numeric_keys=("NS", "NU", "NA", "NO", "NH"),
            authority_kind=AUTHORITY_KIND_PAYLOAD,
        ),
        DEM_ATTRACTORS_MDP_POST_SORT: Optim1fullPlotSiteSpec(
            site_id=DEM_ATTRACTORS_MDP_POST_SORT,
            figure_title="Attractors",
            kind=SITE_KIND_POST_SORT_ORBITS,
            numeric_keys=("u", "I", "HID"),
            authority_kind=AUTHORITY_KIND_PAYLOAD,
        ),
        DEM_STRUCTURE_LEARNING: Optim1fullPlotSiteSpec(
            site_id=DEM_STRUCTURE_LEARNING,
            figure_title="Structure learning",
            kind=SITE_KIND_STRUCTURE_F,
            numeric_keys=("F",),
            authority_kind=AUTHORITY_KIND_PAYLOAD,
        ),
        DEM_ORBITS_BEFORE: Optim1fullPlotSiteSpec(
            site_id=DEM_ORBITS_BEFORE,
            figure_title="Orbits",
            kind=SITE_KIND_ORBITS_FIGURE,
            numeric_keys=("u", "I", "HID"),
            authority_kind=AUTHORITY_KIND_PDP,
            spine_alias_site_id=DEM_BEFORE_COMPRESSION_RGB,
        ),
        DEM_ORBITS_AFTER: Optim1fullPlotSiteSpec(
            site_id=DEM_ORBITS_AFTER,
            figure_title="Orbits",
            kind=SITE_KIND_ORBITS_FIGURE,
            numeric_keys=("u", "I", "HID"),
            authority_kind=AUTHORITY_KIND_PDP,
            spine_alias_site_id=DEM_WITH_COMPRESSION_RGB,
        ),
        DEM_BEFORE_COMPRESSION_RGB: Optim1fullPlotSiteSpec(
            site_id=DEM_BEFORE_COMPRESSION_RGB,
            figure_title="Active inference (before compression)",
            kind=SITE_KIND_RGB_JKH,
            numeric_keys=("J", "K", "h"),
            nt=8,
            movie=0,
            hits_y_offset=-2.0,
            legacy_entry12_tag=ENTRY12_OPTIM1FULL_CALL3_TAG,
            legacy_paths_tag=ENTRY12_OPTIM1FULL_CALL3_TAG,
        ),
        DEM_WITH_COMPRESSION_RGB: Optim1fullPlotSiteSpec(
            site_id=DEM_WITH_COMPRESSION_RGB,
            figure_title="Active inference (with compression)",
            kind=SITE_KIND_RGB_JKH,
            numeric_keys=("J", "K", "h"),
            nt=4,
            movie=0,
            hits_y_offset=-2.0,
            legacy_entry12_tag=ENTRY12_OPTIM1FULL_CALL4_TAG,
            legacy_paths_tag=ENTRY12_OPTIM1FULL_CALL4_TAG,
        ),
        DEM_GENERATIVE_AI: Optim1fullPlotSiteSpec(
            site_id=DEM_GENERATIVE_AI,
            figure_title="Generative AI",
            kind=SITE_KIND_RGB_JKH,
            numeric_keys=("J", "K", "h"),
            nt=4,
            movie=1,
            hits_y_offset=0.0,
        ),
        DEM_ACTIVE_INFERENCE_NR: Optim1fullPlotSiteSpec(
            site_id=DEM_ACTIVE_INFERENCE_NR,
            figure_title="Active inference",
            kind=SITE_KIND_RGB_JKH,
            numeric_keys=("J", "K", "h"),
            nt=4,
            movie=0,
            hits_y_offset=-2.0,
        ),
    }


def _paths_site_specs() -> dict[str, Optim1fullPathsSiteSpec]:
    return {
        DEM_ORBITS_BEFORE: Optim1fullPathsSiteSpec(
            site_id=DEM_ORBITS_BEFORE,
            panel_title="Paths to hits (before)",
            nt=32,
            b_threshold=1.0 / 32.0,
            spine_pdp_site_id=DEM_BEFORE_COMPRESSION_RGB,
        ),
        DEM_ORBITS_AFTER: Optim1fullPathsSiteSpec(
            site_id=DEM_ORBITS_AFTER,
            panel_title="Paths to hits (after)",
            nt=32,
            b_threshold=1.0 / 32.0,
            spine_pdp_site_id=DEM_WITH_COMPRESSION_RGB,
        ),
    }


_OPTIM1FULL_PLOT_SITE_SPECS: dict[str, Optim1fullPlotSiteSpec] = _site_specs()
_OPTIM1FULL_PATHS_SITE_SPECS: dict[str, Optim1fullPathsSiteSpec] = _paths_site_specs()

# Legacy tier-3a Entry 12 tag — not ``dem_active_inference_nr`` (NR final).
LEGACY_A3_LITE_ENTRY12_TAG = ENTRY12_OPTIM1FULL_CALL2_TAG


def optim1full_plot_site_spec(site_id: str) -> Optim1fullPlotSiteSpec:
    key = str(site_id).strip()
    if key not in _OPTIM1FULL_PLOT_SITE_SPECS:
        raise KeyError(f"unknown OPTIM1FULL plot site_id: {key!r}")
    return _OPTIM1FULL_PLOT_SITE_SPECS[key]


def optim1full_plot_site_spec_optional(site_id: str) -> Optional[Optim1fullPlotSiteSpec]:
    key = str(site_id).strip()
    return _OPTIM1FULL_PLOT_SITE_SPECS.get(key)


def optim1full_spine_export_site_id(site_id: str) -> str:
    """Site id to pass to spine ``--site`` export (honors ``spine_alias_site_id``)."""
    spec = optim1full_plot_site_spec(site_id)
    alias = spec.spine_alias_site_id
    return str(alias).strip() if alias else spec.site_id


def optim1full_plot_site_kind(site_id: str) -> str:
    """Return declared site kind (``rgb_jkh``, ``gameplay_o2rgb``, …)."""
    return optim1full_plot_site_spec(site_id).kind


def optim1full_plot_authority_kind(site_id: str) -> str:
    """Return ``matlab_pdp`` or ``matlab_payload`` for the site's fence authority."""
    return optim1full_plot_site_spec(site_id).authority_kind


def optim1full_paths_site_spec(site_id: str) -> Optim1fullPathsSiteSpec:
    key = str(site_id).strip()
    if key not in _OPTIM1FULL_PATHS_SITE_SPECS:
        raise KeyError(f"unknown OPTIM1FULL paths site_id: {key!r}")
    return _OPTIM1FULL_PATHS_SITE_SPECS[key]


def optim1full_paths_site_spec_optional(site_id: str) -> Optional[Optim1fullPathsSiteSpec]:
    key = str(site_id).strip()
    return _OPTIM1FULL_PATHS_SITE_SPECS.get(key)

def optim1full_plot_site_id_for_legacy_tag(tag: str) -> Optional[str]:
    """Map legacy Entry **12** plot tag to ``site_id`` when defined."""
    tag_use = str(tag).strip()
    for spec in _OPTIM1FULL_PLOT_SITE_SPECS.values():
        if spec.legacy_entry12_tag == tag_use:
            return spec.site_id
    return None
