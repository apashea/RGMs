"""OPTIM1FULL W1 — fixture-first plot orchestration (no VB re-run).

Each ``DEM_AtariIII.m`` plot fence is implemented as **one** top-level function
``dem_atariiii_plot_<site_id>`` in ``python_src/toolbox/DEM/`` (see
``Atari_plotting.md`` § **13**). This module loads frozen fixtures, dispatches
to those functions, and runs D3/D4 visual review.

**Legacy:** ``run_optim1full_plot(tag=…)`` dispatches rows **7**/**9** to ``dem_atariiii_plot_*``.

See ``OPTIM1FULL.md`` § W1 and ``Atari_plotting.md`` § **13**.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

from python_src.toolbox.DEM.dem_atariiii_paths import dem_atariiii_paths_to_hits_P
from python_src.toolbox.DEM.entry12_plot import (
    _unwrap_matlab_scalar,
    compose_entry12plot_matlab_vs_pklpdp_png,
    entry12plot_timestamp,
    load_12plot_oracle_from_mat,
    load_pdp_mat_for_plot,
    load_pdp_pkl_for_plot,
    load_plot_ctx_from_mat,
)
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
from python_src.toolbox.DEM.dem_atariiii_plot_rgb_fence import dem_atariiii_plot_rgb_with_hits
from python_src.toolbox.DEM.dem_atariiii_plot_generative_ai import (
    dem_atariiii_plot_generative_ai,
)
from python_src.toolbox.DEM.dem_atariiii_plot_with_compression_rgb import (
    dem_atariiii_plot_with_compression_rgb,
)
from tests.demo1.optim1full.optim1full_plot_sites import (
    DEM_ACTIVE_INFERENCE_NR,
    DEM_ATTRACTORS_BASIN,
    DEM_ATTRACTORS_MDP_POST_SORT,
    DEM_BEFORE_COMPRESSION_RGB,
    DEM_GAMEPLAY,
    DEM_GENERATIVE_AI,
    DEM_ORBITS_AFTER,
    DEM_ORBITS_BEFORE,
    DEM_STRUCTURE_LEARNING,
    DEM_WITH_COMPRESSION_RGB,
    SITE_KIND_BASIN_SERIES,
    SITE_KIND_GAMEPLAY_O2RGB,
    SITE_KIND_ORBITS_FIGURE,
    SITE_KIND_POST_SORT_ORBITS,
    SITE_KIND_RGB_JKH,
    SITE_KIND_STRUCTURE_F,
    optim1full_plot_site_kind,
    optim1full_plot_site_spec,
)
from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site
from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
    ENTRY12_OPTIM1FULL_CALL2_TAG,
    ENTRY12_OPTIM1FULL_CALL3_TAG,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
)
from tests.demo1.optim1full.optim1full_paths import (
    optim1full_12plot_oracle_mat,
    optim1full_paths_oracle_mat,
    optim1full_pdp_mat_for_tag,
    optim1full_pdp_pkl_for_tag,
    optim1full_plot_ctx_mat,
    optim1full_repo_root,
    optim1full_visualizations_dir,
)

# ``matlab_pdp`` = the INDEPENDENT MATLAB-owned plot-fence PDP (matlab_pdp_mat). Loading the
# plotting-function parity input from here (identical to MATLAB's own oracle input) certifies
# the translated Python plot code against MATLAB plot code on the SAME input. ``mat`` (the
# Python-resaved input.mat) is retained only for legacy diagnostics, not plot-fn parity.
# For ``basin_series`` / ``post_sort_orbits``, the same source names load the payload / spine pkl.
PdpSource = Literal["mat", "pkl", "matlab_pdp"]
_BASIN_SERIES_KEYS = ("NS", "NU", "NA", "NO", "NH")
_POST_SORT_PAYLOAD_KEYS = ("b1", "hid")
_POST_SORT_ORACLE_KEYS = ("u", "I", "HID")

# Phase 0 non-loop plot tags (tier 3e / 3f).
PHASE0_PLOT_TAGS: tuple[str, ...] = (
    ENTRY12_OPTIM1FULL_CALL3_TAG,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
)

# Legacy Entry 12 plot tags (rows 7/9 + tier 3a call2 — not dem_active_inference_nr).
A3_LITE_PLOT_TAG = ENTRY12_OPTIM1FULL_CALL2_TAG
A3_LITE_PLOT_TAGS: tuple[str, ...] = (A3_LITE_PLOT_TAG,)

# All fixture-first plot tags with 12PLOT oracles.
OPTIM1FULL_12PLOT_TAGS: tuple[str, ...] = PHASE0_PLOT_TAGS + A3_LITE_PLOT_TAGS

# ``DEM_AtariIII.m`` lines ~342–350 (call3) and ~394–401 (call4).
_DEM_CALL2_TITLE = "Active inference"
_DEM_CALL3_TITLE = "Active inference (before compression)"
_DEM_CALL4_TITLE = "Active inference (with compression)"
_DEM_HITS_Y = -2.0
_PATHS_NT = 32
_PATHS_B_THRESHOLD = 1.0 / 32.0

_OPTIM1FULL_PLOT_ENV = "RGMS_OPTIM1FULL_PLOT"
_OPTIM1FULL_MATLAB_PNG_ENV = "RGMS_OPTIM1FULL_12PLOT_MATLAB_PNG"


def optim1full_plot_enabled() -> bool:
    """True when full-flow plot witness is active (W1-B). Default off for gate sign-off."""
    return os.getenv(_OPTIM1FULL_PLOT_ENV, "").strip().lower() in ("1", "true", "yes")


def build_optim1full_plot_ctx_from_driver(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build plot inputs from a live ``run_dem_atariiii_optim1full_parity`` driver ctx."""
    for key in ("RGB", "GDP", "Nm"):
        if key not in ctx:
            raise KeyError(f"driver ctx missing {key!r} required for plot witness")
    return {
        "RGB": ctx["RGB"],
        "GDP": ctx["GDP"],
        "Nm": int(ctx["Nm"]),
    }


def assert_optim1full_plot_jkh_matches_oracle(
    tag: str,
    j: Any,
    k: Any,
    h: Any,
    *,
    site_label: str = "",
) -> None:
    oracle = load_optim1full_12plot_oracle(tag)
    prefix = f"{site_label}: " if site_label else ""
    np.testing.assert_array_equal(j, oracle["J"], err_msg=f"{prefix}{tag} J mismatch")
    np.testing.assert_array_equal(k, oracle["K"], err_msg=f"{prefix}{tag} K mismatch")
    np.testing.assert_array_equal(h, oracle["h"], err_msg=f"{prefix}{tag} h mismatch")


def assert_optim1full_plot_paths_matches_oracle(
    tag: str,
    i_mat: Any,
    hid: Any,
    *,
    site_label: str = "",
) -> None:
    oracle = load_optim1full_paths_oracle(tag)
    prefix = f"{site_label}: " if site_label else ""
    np.testing.assert_array_equal(i_mat, oracle["I"], err_msg=f"{prefix}{tag} I mismatch")
    np.testing.assert_array_equal(hid, oracle["HID"], err_msg=f"{prefix}{tag} HID mismatch")


def assert_optim1full_live_pdp_plot_oracles(
    tag: str,
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    include_paths: bool | None = None,
    site_label: str = "",
) -> None:
    """
    Legacy W1-B — live PDP vs Entry-12 **tag** oracles (12PLOT / PATHS).

    Prefer ``assert_optim1full_live_site_plot_oracles`` for W1-E full-driver witness
    (§13 ``site_id`` + spine oracles). Kept for fixture regression tests.
    """
    j, k, h, _png = run_optim1full_plot(tag, pdp, plot_ctx, save_png=False)
    assert_optim1full_plot_jkh_matches_oracle(tag, j, k, h, site_label=site_label)
    use_paths = include_paths if include_paths is not None else tag in PHASE0_PLOT_TAGS
    if use_paths:
        i_mat, hid = run_optim1full_paths_plot(tag, pdp)
        assert_optim1full_plot_paths_matches_oracle(tag, i_mat, hid, site_label=site_label)


def assert_optim1full_live_site_plot_oracles(
    site_id: str,
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    include_paths_site_id: str | None = None,
    site_label: str = "",
) -> None:
    """
    W1-E — run §13 ``dem_atariiii_plot_*`` on a **live** PDP vs spine site oracle.

    RGB sites: ``J``/``K``/``h`` from ``…_<site>_oracle.mat``. Optional paths hitch
    (``dem_orbits_before`` / ``dem_orbits_after``): ``I``/``HID`` from ``…_<paths>_paths.mat``.
    Does not invoke VB; does not save PNGs (fixture visual lane stays ``--visual-review-only``).
    """
    from tests.demo1.optim1full.optim1full_plot_sites import (
        SITE_KIND_RGB_JKH,
        optim1full_plot_site_kind,
    )

    kind = optim1full_plot_site_kind(site_id)
    if kind != SITE_KIND_RGB_JKH:
        raise ValueError(
            f"assert_optim1full_live_site_plot_oracles supports rgb_jkh only "
            f"(got kind={kind!r} for site_id={site_id!r})"
        )

    out = run_optim1full_plot_for_site(site_id, pdp, plot_ctx, save_png=False)
    if len(out) < 3:
        raise RuntimeError(
            f"live site plot expected (J, K, h, …) for {site_id!r}, got len={len(out)}"
        )
    j, k, h = out[0], out[1], out[2]
    oracle = load_optim1full_site_oracle(site_id)
    prefix = f"{site_label}: " if site_label else ""
    np.testing.assert_array_equal(
        j, oracle["J"], err_msg=f"{prefix}{site_id} J mismatch"
    )
    np.testing.assert_array_equal(
        k, oracle["K"], err_msg=f"{prefix}{site_id} K mismatch"
    )
    np.testing.assert_array_equal(
        h, oracle["h"], err_msg=f"{prefix}{site_id} h mismatch"
    )

    if include_paths_site_id:
        # Paths panel hitch — compare to §13 orbits site oracle I/HID (COVERED Step 9),
        # not legacy ``…_paths.mat`` (stale threshold / width vs current 1/32 paths).
        i_mat, hid = run_optim1full_paths_for_site(include_paths_site_id, pdp)
        paths_oracle = load_optim1full_site_oracle(include_paths_site_id)
        np.testing.assert_array_equal(
            i_mat,
            paths_oracle["I"],
            err_msg=f"{prefix}{include_paths_site_id} I mismatch",
        )
        np.testing.assert_array_equal(
            hid,
            paths_oracle["HID"],
            err_msg=f"{prefix}{include_paths_site_id} HID mismatch",
        )


def assert_optim1full_w1e_plot_oracles_present() -> None:
    """Require spine RGB + orbits oracles used by the W1-E live witness."""
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site

    required: list[tuple[str, Path]] = []
    for sid in (
        DEM_GENERATIVE_AI,
        DEM_ACTIVE_INFERENCE_NR,
        DEM_BEFORE_COMPRESSION_RGB,
        DEM_WITH_COMPRESSION_RGB,
        DEM_ORBITS_BEFORE,
        DEM_ORBITS_AFTER,
    ):
        required.append((f"oracle[{sid}]", optim1full_plot_paths_for_site(sid)["oracle_mat"]))
    missing = [f"{label}: {path}" for label, path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "missing OPTIM1FULL W1-E spine plot oracles "
            "(land §13 sites via --plot-parity before full-driver plot witness):\n"
            + "\n".join(missing)
        )


@dataclass(frozen=True)
class Optim1fullPlotSite:
    """Per-tag plot fence — ``DEM_AtariIII.m`` post-VB illustrate blocks."""

    tag: str
    figure_title: str
    hits_y_offset: float
    nt: int
    movie: int


def _dem_site(tag: str) -> Optim1fullPlotSite:
    """``DEM_AtariIII.m`` fence per OPTIM1FULL plot tag."""
    if tag == ENTRY12_OPTIM1FULL_CALL2_TAG:
        return Optim1fullPlotSite(
            tag=tag,
            figure_title=_DEM_CALL2_TITLE,
            hits_y_offset=_DEM_HITS_Y,
            nt=4,
            movie=0,
        )
    if tag == ENTRY12_OPTIM1FULL_CALL3_TAG:
        return Optim1fullPlotSite(
            tag=tag,
            figure_title=_DEM_CALL3_TITLE,
            hits_y_offset=_DEM_HITS_Y,
            nt=8,
            movie=0,
        )
    if tag == ENTRY12_OPTIM1FULL_CALL4_TAG:
        return Optim1fullPlotSite(
            tag=tag,
            figure_title=_DEM_CALL4_TITLE,
            hits_y_offset=_DEM_HITS_Y,
            nt=4,
            movie=0,
        )
    raise KeyError(f"unknown OPTIM1FULL plot tag: {tag!r}")


DEM_PLOT_SITES: dict[str, Optim1fullPlotSite] = {
    tag: _dem_site(tag) for tag in OPTIM1FULL_12PLOT_TAGS
}

# Back-compat alias (phase 0 module name).
PHASE0_PLOT_SITES = DEM_PLOT_SITES


@dataclass(frozen=True)
class Optim1fullPathsSite:
    """Paths-to-hits panel — ``DEM_AtariIII.m`` ``imagesc(I)`` block on ``PDP.B{1}``."""

    tag: str
    panel_title: str
    nt: int = _PATHS_NT
    b_threshold: float = _PATHS_B_THRESHOLD


def _dem_paths_site(tag: str) -> Optim1fullPathsSite:
    if tag == ENTRY12_OPTIM1FULL_CALL3_TAG:
        return Optim1fullPathsSite(tag=tag, panel_title="Paths to hits (before)")
    if tag == ENTRY12_OPTIM1FULL_CALL4_TAG:
        return Optim1fullPathsSite(tag=tag, panel_title="Paths to hits (after)")
    raise KeyError(f"unknown OPTIM1FULL paths tag: {tag!r}")


DEM_PATHS_SITES: dict[str, Optim1fullPathsSite] = {
    tag: _dem_paths_site(tag) for tag in PHASE0_PLOT_TAGS
}


def _pdp_B1_transition_mask(pdp: Any, *, threshold: float) -> np.ndarray:
    b_field = pdp["B"]
    b1 = b_field[0] if isinstance(b_field, list) else b_field
    arr = np.asarray(b1, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(f"PDP.B{{1}} expected 3-D array, got shape {arr.shape!r}")
    return np.sum(arr, axis=2) > float(threshold)


def _pdp_hid_1based(pdp: Any) -> np.ndarray:
    id_rec = pdp["id"]
    if not isinstance(id_rec, dict) or "hid" not in id_rec:
        raise KeyError("PDP.id.hid required for paths-to-hits panel")
    return np.asarray(id_rec["hid"], dtype=np.int64).ravel(order="F")


def compute_optim1full_paths_to_hits(
    pdp: Any,
    *,
    site: Optim1fullPathsSite | None = None,
    tag: str | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Reachability matrix ``I`` and ``HID`` indices — mirrors ``DEM_AtariIII.m`` post-VB block.

    Returns ``(I, HID)`` with ``I`` shape ``(nt, Ns)`` and ``HID`` 1-based state indices.
    """
    tag_use = tag or (site.tag if site is not None else None)
    site_use = site or (DEM_PATHS_SITES[tag_use] if tag_use is not None else None)
    if site_use is None:
        raise ValueError("compute_optim1full_paths_to_hits requires site or tag")
    b_mask = _pdp_B1_transition_mask(pdp, threshold=site_use.b_threshold)
    hid = _pdp_hid_1based(pdp)
    i_mat = dem_atariiii_paths_to_hits_P(b_mask, hid, int(site_use.nt))
    return i_mat, hid


def load_optim1full_paths_oracle_from_mat(path: Path) -> dict[str, Any]:
    from scipy.io import loadmat

    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    hid = np.asarray(raw["HID"], dtype=np.int64).ravel(order="F")
    return {
        "I": np.asarray(raw["I"], dtype=np.float64),
        "HID": hid,
    }


def load_optim1full_paths_oracle(tag: str) -> dict[str, Any]:
    if tag not in PHASE0_PLOT_TAGS:
        raise KeyError(f"unknown OPTIM1FULL paths tag: {tag!r}")
    return load_optim1full_paths_oracle_from_mat(optim1full_paths_oracle_mat(tag))


def load_optim1full_site_paths_oracle(site_id: str) -> dict[str, Any]:
    """Load spine paths oracle ``I``/``HID`` for one § **13** paths site."""
    from tests.demo1.optim1full.optim1full_paths import optim1full_site_paths_oracle_mat

    return load_optim1full_paths_oracle_from_mat(optim1full_site_paths_oracle_mat(site_id))


def _paths_site_from_spec(site_id: str) -> Optim1fullPathsSite:
    from tests.demo1.optim1full.optim1full_plot_sites import optim1full_paths_site_spec

    spec = optim1full_paths_site_spec(site_id)
    return Optim1fullPathsSite(
        tag=spec.site_id,
        panel_title=spec.panel_title,
        nt=int(spec.nt),
        b_threshold=float(spec.b_threshold),
    )


def run_optim1full_paths_for_site(site_id: str, pdp: Any) -> tuple[np.ndarray, np.ndarray]:
    """Compute paths oracle targets for one § **13** paths ``site_id``."""
    return compute_optim1full_paths_to_hits(pdp, site=_paths_site_from_spec(site_id))


def run_optim1full_paths_plot(
    tag: str,
    pdp: Any,
    *,
    site: Optim1fullPathsSite | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute paths oracle targets for ``tag`` — no figure export (numeric sign-off only)."""
    return compute_optim1full_paths_to_hits(pdp, site=site, tag=tag)


def optim1full_plot_png_path(tag: str, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    safe = tag.replace(" ", "_")
    return optim1full_visualizations_dir() / f"AtariIII_optim1full_plot_{safe}_{ts}.png"


def optim1full_plot_compare_png_path(tag: str, ts: str | None = None) -> Path:
    """Side-by-side MATLAB (left) vs Python PDP plot (right) for ``tag``."""
    ts = ts or entry12plot_timestamp()
    safe = tag.replace(" ", "_")
    return (
        optim1full_visualizations_dir()
        / f"AtariIII_optim1full_plot_compare_{safe}_{ts}.png"
    )


def resolve_optim1full_12plot_reference_png(
    tag: str,
    *,
    repo_root: Path | None = None,
) -> Optional[Path]:
    """
    MATLAB capture PNG for OPTIM1FULL Phase **4** compare.

    Resolution order: env ``RGMS_OPTIM1FULL_12PLOT_MATLAB_PNG`` (manual override),
    then ``meta.png_path`` in ``DEMAtariIII_entry12_<tag>_12PLOT.mat``.
    """
    if tag not in OPTIM1FULL_12PLOT_TAGS:
        raise KeyError(f"unknown OPTIM1FULL plot tag: {tag!r}")
    env = str(os.getenv(_OPTIM1FULL_MATLAB_PNG_ENV, "")).strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
    oracle_path = optim1full_12plot_oracle_mat(tag)
    if oracle_path.is_file():
        raw = loadmat(str(oracle_path), squeeze_me=True, struct_as_record=False)
        meta = raw.get("meta")
        if meta is not None:
            meta = _unwrap_matlab_scalar(meta)
            if hasattr(meta, "_fieldnames") and "png_path" in meta._fieldnames:
                p = Path(str(getattr(meta, "png_path")))
                if p.is_file():
                    return p.resolve()
    root = repo_root or optim1full_repo_root()
    vis = root / "visualizations"
    if vis.is_dir():
        skip = ("python", "compare", "matpdp", "pklpdp", "optim1full")
        candidates = [
            p
            for p in vis.glob("AtariIII_12plot_*.png")
            if not any(s in p.name.lower() for s in skip)
        ]
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_mtime).resolve()
    return None


def run_optim1full_plot_phase_b_visual_review(
    tag: str,
    *,
    ts: str | None = None,
    source: PdpSource = "pkl",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, Path, Optional[Path]]:
    """
    W1-D — Phase **B** plot PNG + MATLAB-vs-Python side-by-side compare (no VB re-run).

    Primary sign-off remains numeric ``J``/``K``/``h``; PNG output is secondary
    (``Atari_plotting.md`` § **7.2** / § **8.3.1**).
    """
    if tag not in OPTIM1FULL_12PLOT_TAGS:
        raise KeyError(f"unknown OPTIM1FULL plot tag: {tag!r}")
    ts = ts or entry12plot_timestamp()
    ctx = load_optim1full_plot_ctx()
    pdp = load_optim1full_pdp_for_plot(tag, source)
    python_png = optim1full_plot_png_path(tag, ts)
    j, k, h, saved = run_optim1full_plot(
        tag,
        pdp,
        ctx,
        save_png=True,
        png_path=python_png,
    )
    if saved is None:
        raise RuntimeError(f"run_optim1full_plot did not save PNG for tag {tag!r}")
    matlab_ref = resolve_optim1full_12plot_reference_png(tag)
    compare: Optional[Path] = None
    if matlab_ref is not None:
        compare = compose_entry12plot_matlab_vs_pklpdp_png(
            matlab_ref,
            saved,
            optim1full_plot_compare_png_path(tag, ts),
        )
    return j, k, h, saved, compare


def run_optim1full_d4_visual_review(
    tag: str,
    *,
    source: PdpSource = "pkl",
    ts: str | None = None,
) -> dict[str, Any]:
    """
    W1-D step **D4** — one tag; manifest row for ``optim1full_capture_plot_fixtures.py``.

    Loads frozen fixtures only (no VB, no MATLAB Engine).
    """
    j, k, h, py_png, cmp_png = run_optim1full_plot_phase_b_visual_review(
        tag, ts=ts, source=source
    )
    return {
        "tag": tag,
        "source": source,
        "python_png": str(py_png.resolve()),
        "compare_png": str(cmp_png.resolve()) if cmp_png is not None else None,
        "J_shape": list(j.shape),
        "K_shape": list(k.shape),
        "h_len": int(len(h)),
    }


def optim1full_site_python_png_path(site_id: str, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return optim1full_visualizations_dir() / f"AtariIII_optim1full_{site_id}_python_{ts}.png"


def optim1full_site_compare_png_path(site_id: str, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return optim1full_visualizations_dir() / f"AtariIII_optim1full_{site_id}_compare_{ts}.png"


def resolve_optim1full_site_reference_png(site_id: str) -> Optional[Path]:
    """MATLAB reference PNG from spine ``…_<site_id>_oracle.mat`` ``meta.png_path``."""
    paths = optim1full_plot_paths_for_site(site_id)
    oracle_path = paths["oracle_mat"]
    if not oracle_path.is_file():
        return None
    raw = loadmat(str(oracle_path), squeeze_me=True, struct_as_record=False)
    meta = raw.get("meta")
    if meta is not None:
        meta = _unwrap_matlab_scalar(meta)
        if hasattr(meta, "_fieldnames") and "png_path" in meta._fieldnames:
            p = Path(str(getattr(meta, "png_path")))
            if p.is_file():
                return p.resolve()
    return None


def run_optim1full_site_phase_b_visual_review(
    site_id: str,
    *,
    ts: str | None = None,
    source: PdpSource = "pkl",
) -> tuple[tuple[Any, ...], Path, Optional[Path]]:
    """
    W1-D — § **13** spine fixtures: Python PNG + MATLAB-vs-Python compare (no VB).

    Kind-aware: ``run_optim1full_plot_for_site`` returns ``(..., png_path)``;
    only the **last** element is the PNG (``rgb_jkh`` → ``(J,K,h,png)``;
    ``gameplay_o2rgb`` → ``(frame_rgb, control, png)``;
    ``basin_series`` → ``(NS,NU,NA,NO,NH,png)``). Numerics are
    ``out[:-1]``. Compose helper and naming globs are unchanged.
    """
    paths = optim1full_plot_paths_for_site(site_id)
    kind = optim1full_plot_site_kind(site_id)
    if not paths["plot_ctx"].is_file() and kind not in (
        SITE_KIND_BASIN_SERIES,
        SITE_KIND_POST_SORT_ORBITS,
        SITE_KIND_STRUCTURE_F,
    ):
        raise FileNotFoundError(f"missing plot_ctx: {paths['plot_ctx']}")
    if kind == SITE_KIND_BASIN_SERIES:
        fence = load_optim1full_basin_series_for_site(site_id, source)
        if not paths["oracle_mat"].is_file():
            raise FileNotFoundError(f"missing site oracle: {paths['oracle_mat']}")
        ts = ts or entry12plot_timestamp()
        ctx = load_optim1full_plot_ctx() if paths["plot_ctx"].is_file() else {}
        python_png = optim1full_site_python_png_path(site_id, ts)
        out = run_optim1full_plot_for_site(
            site_id,
            fence,
            ctx,
            save_png=True,
            png_path=python_png,
        )
    elif kind == SITE_KIND_STRUCTURE_F:
        fence = load_optim1full_structure_f_for_site(site_id, source)
        if not paths["oracle_mat"].is_file():
            raise FileNotFoundError(f"missing site oracle: {paths['oracle_mat']}")
        ts = ts or entry12plot_timestamp()
        ctx = load_optim1full_plot_ctx() if paths["plot_ctx"].is_file() else {}
        python_png = optim1full_site_python_png_path(site_id, ts)
        out = run_optim1full_plot_for_site(
            site_id,
            fence,
            ctx,
            save_png=True,
            png_path=python_png,
        )
    elif kind == SITE_KIND_POST_SORT_ORBITS:
        fence = load_optim1full_post_sort_payload_for_site(site_id, source)
        if not paths["oracle_mat"].is_file():
            raise FileNotFoundError(f"missing site oracle: {paths['oracle_mat']}")
        ts = ts or entry12plot_timestamp()
        ctx = load_optim1full_plot_ctx() if paths["plot_ctx"].is_file() else {}
        python_png = optim1full_site_python_png_path(site_id, ts)
        out = run_optim1full_plot_for_site(
            site_id,
            fence,
            ctx,
            save_png=True,
            png_path=python_png,
        )
    else:
        pdp_key = "input_mat" if source == "mat" else "input_pkl"
        if source == "matlab_pdp":
            pdp_key = "matlab_pdp_mat"
        if not paths[pdp_key].is_file():
            raise FileNotFoundError(f"missing spine PDP: {paths[pdp_key]}")
        if not paths["oracle_mat"].is_file():
            raise FileNotFoundError(f"missing site oracle: {paths['oracle_mat']}")

        ts = ts or entry12plot_timestamp()
        ctx = load_optim1full_plot_ctx()
        pdp = load_optim1full_pdp_for_site(site_id, source)
        python_png = optim1full_site_python_png_path(site_id, ts)
        out = run_optim1full_plot_for_site(
            site_id,
            pdp,
            ctx,
            save_png=True,
            png_path=python_png,
        )
    if not out:
        raise RuntimeError(
            f"run_optim1full_plot_for_site returned empty for site {site_id!r}"
        )
    saved = out[-1]
    if saved is None:
        raise RuntimeError(f"run_optim1full_plot_for_site did not save PNG for site {site_id!r}")
    values = tuple(out[:-1])
    matlab_ref = resolve_optim1full_site_reference_png(site_id)
    compare: Optional[Path] = None
    if matlab_ref is not None:
        compare = compose_entry12plot_matlab_vs_pklpdp_png(
            matlab_ref,
            saved,
            optim1full_site_compare_png_path(site_id, ts),
        )
    return values, saved, compare


def run_optim1full_site_d4_visual_review(
    site_id: str,
    *,
    source: PdpSource = "pkl",
    ts: str | None = None,
) -> dict[str, Any]:
    """W1-D step **D4** — one § **13** ``site_id`` on spine-paired fixtures.

    Manifest shape fields are kind-aware (``rgb_jkh`` → ``J``/``K``/``h``;
    ``gameplay_o2rgb`` → ``frame_rgb``/``control`` shapes;
    ``basin_series`` → ``NS``…``NH`` lengths; no assumed JKH).
    """
    values, py_png, cmp_png = run_optim1full_site_phase_b_visual_review(
        site_id, ts=ts, source=source
    )
    kind = optim1full_plot_site_kind(site_id)
    row: dict[str, Any] = {
        "site_id": site_id,
        "source": source,
        "kind": kind,
        "python_png": str(py_png.resolve()),
        "compare_png": str(cmp_png.resolve()) if cmp_png is not None else None,
    }
    if kind == SITE_KIND_RGB_JKH:
        if len(values) != 3:
            raise RuntimeError(
                f"rgb_jkh visual review expected (J,K,h); got {len(values)} values "
                f"for site {site_id!r}"
            )
        j, k, h = values
        row["J_shape"] = list(np.asarray(j).shape)
        row["K_shape"] = list(np.asarray(k).shape)
        row["h_len"] = int(len(np.asarray(h).ravel()))
    elif kind == SITE_KIND_GAMEPLAY_O2RGB:
        if len(values) != 2:
            raise RuntimeError(
                f"gameplay_o2rgb visual review expected (frame_rgb, control); "
                f"got {len(values)} values for site {site_id!r}"
            )
        frame_rgb, control = values
        row["frame_rgb_shape"] = list(np.asarray(frame_rgb).shape)
        row["control_shape"] = list(np.asarray(control).shape)
    elif kind == SITE_KIND_BASIN_SERIES:
        if len(values) != 5:
            raise RuntimeError(
                f"basin_series visual review expected (NS,NU,NA,NO,NH); "
                f"got {len(values)} values for site {site_id!r}"
            )
        for key, arr in zip(_BASIN_SERIES_KEYS, values):
            row[f"{key}_len"] = int(np.asarray(arr).ravel().size)
    elif kind == SITE_KIND_POST_SORT_ORBITS:
        if len(values) != 3:
            raise RuntimeError(
                f"post_sort_orbits visual review expected (u,I,HID); "
                f"got {len(values)} values for site {site_id!r}"
            )
        u, i_mat, hid = values
        row["u_shape"] = list(np.asarray(u).shape)
        row["I_shape"] = list(np.asarray(i_mat).shape)
        row["HID_len"] = int(np.asarray(hid).ravel().size)
    elif kind == SITE_KIND_ORBITS_FIGURE:
        if len(values) != 3:
            raise RuntimeError(
                f"orbits_figure visual review expected (u,I,HID); "
                f"got {len(values)} values for site {site_id!r}"
            )
        u, i_mat, hid = values
        row["u_shape"] = list(np.asarray(u).shape)
        row["I_shape"] = list(np.asarray(i_mat).shape)
        row["HID_len"] = int(np.asarray(hid).ravel().size)
    elif kind == SITE_KIND_STRUCTURE_F:
        if len(values) != 1:
            raise RuntimeError(
                f"structure_f visual review expected (F,); "
                f"got {len(values)} values for site {site_id!r}"
            )
        row["F_shape"] = list(np.asarray(values[0]).shape)
    return row


def load_optim1full_plot_ctx() -> dict[str, Any]:
    """Load OPTIM1FULL-pure ``plot_ctx`` (``RGB``, ``GDP``, ``Nm``)."""
    return load_plot_ctx_from_mat(optim1full_plot_ctx_mat())


def load_optim1full_pdp_for_plot(tag: str, source: PdpSource) -> dict[str, Any]:
    """Load **PDP** for plot code from gate-green Entry **12** fixtures."""
    if tag not in OPTIM1FULL_12PLOT_TAGS:
        raise KeyError(f"unknown OPTIM1FULL plot tag: {tag!r}")
    mat_path = optim1full_pdp_mat_for_tag(tag)
    if source == "mat":
        return load_pdp_mat_for_plot(mat_path)
    pkl_path = optim1full_pdp_pkl_for_tag(tag)
    return load_pdp_pkl_for_plot(pkl_path, mat_template_path=mat_path)


def load_optim1full_pdp_for_site(site_id: str, source: PdpSource) -> dict[str, Any]:
    """Load site **PDP** for plotting.

    ``matlab_pdp`` loads the INDEPENDENT MATLAB-owned fence PDP (plot-fn parity input,
    identical to the oracle's own input); ``mat`` loads the legacy Python-resaved
    ``input.mat``; ``pkl`` loads the Python spine export.
    """
    paths = optim1full_plot_paths_for_site(site_id)
    if source == "matlab_pdp":
        return load_pdp_mat_for_plot(paths["matlab_pdp_mat"])
    mat_path = paths["input_mat"]
    if source == "mat":
        return load_pdp_mat_for_plot(mat_path)
    return load_pdp_pkl_for_plot(paths["input_pkl"], mat_template_path=mat_path)


def load_basin_series_from_payload_mat(path: Path) -> dict[str, np.ndarray]:
    """Load Attractors basin series ``NS``…``NH`` from ``…_matlab_payload.mat``."""
    raw = loadmat(str(path), squeeze_me=True, struct_as_record=False)
    out: dict[str, np.ndarray] = {}
    for key in _BASIN_SERIES_KEYS:
        if key not in raw:
            raise KeyError(f"basin payload missing {key!r}: {path}")
        out[key] = np.asarray(raw[key], dtype=np.float64).reshape(-1)
    return out


def load_basin_series_from_pkl(path: Path) -> dict[str, np.ndarray]:
    """Load Attractors basin series from spine ``input.pkl``."""
    import pickle

    with Path(path).open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"basin spine pkl must be dict: {path}")
    out: dict[str, np.ndarray] = {}
    for key in _BASIN_SERIES_KEYS:
        if key not in blob:
            raise KeyError(f"basin spine pkl missing {key!r}: {path}")
        out[key] = np.asarray(blob[key], dtype=np.float64).reshape(-1)
    return out


def load_optim1full_basin_series_for_site(site_id: str, source: PdpSource) -> dict[str, np.ndarray]:
    """Load basin series for plot-fn parity (``matlab_pdp`` → payload authority)."""
    paths = optim1full_plot_paths_for_site(site_id)
    if source == "matlab_pdp":
        return load_basin_series_from_payload_mat(paths["authority_mat"])
    if source == "mat":
        # No Python-resaved basin input.mat in the normative ladder.
        return load_basin_series_from_payload_mat(paths["authority_mat"])
    return load_basin_series_from_pkl(paths["input_pkl"])


def load_structure_f_from_payload_mat(path: Path) -> dict[str, np.ndarray]:
    """Load structure ``F`` from MATLAB-owned ``matlab_payload``."""
    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    if "F" not in raw:
        raise KeyError(f"structure payload missing F: {path}")
    return {"F": np.asarray(raw["F"], dtype=np.float64)}


def load_structure_f_from_pkl(path: Path) -> dict[str, np.ndarray]:
    """Load structure ``F`` from spine ``input.pkl``."""
    import pickle

    with path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict) or "F" not in blob:
        raise KeyError(f"structure spine pkl missing F: {path}")
    return {"F": np.asarray(blob["F"], dtype=np.float64)}


def load_optim1full_structure_f_for_site(site_id: str, source: PdpSource) -> dict[str, np.ndarray]:
    paths = optim1full_plot_paths_for_site(site_id)
    if source in ("matlab_pdp", "mat"):
        return load_structure_f_from_payload_mat(paths["authority_mat"])
    return load_structure_f_from_pkl(paths["input_pkl"])


def load_structure_oracle_from_mat(path: Path) -> dict[str, np.ndarray]:
    """Load structure oracle ``F`` from ``…_oracle.mat``."""
    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    if "F" not in raw:
        raise KeyError(f"structure oracle missing F: {path}")
    return {"F": np.asarray(raw["F"], dtype=np.float64)}


def load_gameplay_oracle_from_mat(path: Path) -> dict[str, Any]:
    """Load Gameplay oracle ``frame_rgb`` / ``control`` from ``…_oracle.mat``."""
    from scipy.io import loadmat as _loadmat

    raw = _loadmat(str(path), squeeze_me=False, struct_as_record=False)
    if "frame_rgb" not in raw or "control" not in raw:
        raise KeyError(
            f"gameplay oracle missing frame_rgb/control: {path} "
            "(keys=%s)" % sorted(k for k in raw if not str(k).startswith("__"))
        )
    control = np.asarray(raw["control"], dtype=np.float64)
    if control.ndim == 1:
        control = control.reshape(1, -1)
    return {
        "frame_rgb": np.asarray(raw["frame_rgb"], dtype=np.uint8),
        "control": control,
    }


def load_basin_oracle_from_mat(path: Path) -> dict[str, np.ndarray]:
    """Load Attractors basin oracle ``NS``…``NH`` from ``…_oracle.mat``."""
    raw = loadmat(str(path), squeeze_me=True, struct_as_record=False)
    out: dict[str, np.ndarray] = {}
    for key in _BASIN_SERIES_KEYS:
        if key not in raw:
            raise KeyError(f"basin oracle missing {key!r}: {path}")
        out[key] = np.asarray(raw[key], dtype=np.float64).reshape(-1)
    return out


def load_post_sort_payload_from_mat(path: Path) -> dict[str, np.ndarray]:
    """Load post-sort fence ``b1``/``hid`` from MATLAB-owned ``matlab_payload``."""
    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    if "b1" not in raw or "hid" not in raw:
        raise KeyError(f"post_sort payload missing b1/hid: {path}")
    return {
        "b1": np.asarray(raw["b1"], dtype=np.float64),
        "hid": np.asarray(raw["hid"], dtype=np.int64).ravel(order="F"),
    }


def load_post_sort_payload_from_pkl(path: Path) -> dict[str, np.ndarray]:
    """Load post-sort fence ``b1``/``hid`` from spine ``input.pkl``."""
    import pickle

    with path.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"post_sort spine pkl must be dict: {path}")
    for key in _POST_SORT_PAYLOAD_KEYS:
        if key not in blob:
            raise KeyError(f"post_sort spine pkl missing {key!r}: {path}")
    return {
        "b1": np.asarray(blob["b1"], dtype=np.float64),
        "hid": np.asarray(blob["hid"], dtype=np.int64).ravel(order="F"),
    }


def load_optim1full_post_sort_payload_for_site(
    site_id: str, source: PdpSource
) -> dict[str, np.ndarray]:
    paths = optim1full_plot_paths_for_site(site_id)
    if source == "matlab_pdp":
        return load_post_sort_payload_from_mat(paths["authority_mat"])
    if source == "mat":
        return load_post_sort_payload_from_mat(paths["authority_mat"])
    return load_post_sort_payload_from_pkl(paths["input_pkl"])


def load_post_sort_oracle_from_mat(path: Path) -> dict[str, np.ndarray]:
    """Load post-sort oracle ``u``/``I``/``HID`` from ``…_oracle.mat``."""
    from scipy import sparse

    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    out: dict[str, np.ndarray] = {}
    for key in _POST_SORT_ORACLE_KEYS:
        if key not in raw:
            raise KeyError(f"post_sort oracle missing {key!r}: {path}")
        val = raw[key]
        if sparse.issparse(val):
            val = val.toarray()
        # Engine/scipy may wrap a lone sparse in a 1x1 object array.
        if isinstance(val, np.ndarray) and val.dtype == object and val.size == 1:
            inner = val.flat[0]
            if sparse.issparse(inner):
                val = inner.toarray()
            else:
                val = np.asarray(inner)
        if key == "HID":
            out[key] = np.asarray(val, dtype=np.int64).ravel(order="F")
        else:
            out[key] = np.asarray(val, dtype=np.float64)
    return out


def load_optim1full_site_oracle(site_id: str) -> dict[str, Any]:
    """Load numeric oracle for one § **13** plot site (kind-aware).

    - ``rgb_jkh`` → ``J``/``K``/``h``
    - ``gameplay_o2rgb`` → ``frame_rgb``/``control``
    - ``basin_series`` → ``NS``…``NH``
    - ``post_sort_orbits`` → ``u``/``I``/``HID``
    - ``orbits_figure`` → ``u``/``I``/``HID``
    - ``structure_f`` → ``F``
    """
    from tests.demo1.optim1full.optim1full_plot_sites import (
        SITE_KIND_BASIN_SERIES,
        SITE_KIND_GAMEPLAY_O2RGB,
        SITE_KIND_ORBITS_FIGURE,
        SITE_KIND_POST_SORT_ORBITS,
        SITE_KIND_STRUCTURE_F,
        optim1full_plot_site_kind,
    )

    paths = optim1full_plot_paths_for_site(site_id)
    kind = optim1full_plot_site_kind(site_id)
    if kind == SITE_KIND_GAMEPLAY_O2RGB:
        return load_gameplay_oracle_from_mat(paths["oracle_mat"])
    if kind == SITE_KIND_BASIN_SERIES:
        return load_basin_oracle_from_mat(paths["oracle_mat"])
    if kind in (SITE_KIND_POST_SORT_ORBITS, SITE_KIND_ORBITS_FIGURE):
        return load_post_sort_oracle_from_mat(paths["oracle_mat"])
    if kind == SITE_KIND_STRUCTURE_F:
        return load_structure_oracle_from_mat(paths["oracle_mat"])
    return load_12plot_oracle_from_mat(paths["oracle_mat"])


def load_optim1full_12plot_oracle(tag: str) -> dict[str, Any]:
    """Load MATLAB numeric oracle (``J``, ``K``, ``h``) for ``tag``."""
    if tag not in OPTIM1FULL_12PLOT_TAGS:
        raise KeyError(f"unknown OPTIM1FULL plot tag: {tag!r}")
    return load_12plot_oracle_from_mat(optim1full_12plot_oracle_mat(tag))


def run_optim1full_plot(
    tag: str,
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    site: Optim1fullPlotSite | None = None,
    save_png: bool = False,
    png_path: Path | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, Path | None]:
    """
    Run DEM-faithful fence on a loaded **PDP** — does not invoke VB.

    Returns ``(J, K, h, png_path)``. Delegates rows **7**/**9** to ``dem_atariiii_plot_*``.
    """
    site_use = site or DEM_PLOT_SITES[tag]
    out_png_path = png_path or (optim1full_plot_png_path(tag) if save_png else None)

    if tag == ENTRY12_OPTIM1FULL_CALL3_TAG:
        return dem_atariiii_plot_before_compression_rgb(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if tag == ENTRY12_OPTIM1FULL_CALL4_TAG:
        return dem_atariiii_plot_with_compression_rgb(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )

    return dem_atariiii_plot_rgb_with_hits(
        pdp,
        plot_ctx,
        figure_title=site_use.figure_title,
        nt=int(site_use.nt),
        movie=int(site_use.movie),
        hits_y_offset=float(site_use.hits_y_offset),
        save_png=save_png,
        png_path=out_png_path,
    )


def run_optim1full_plot_for_site(
    site_id: str,
    pdp: Any,
    plot_ctx: dict[str, Any],
    *,
    save_png: bool = False,
    png_path: Path | None = None,
) -> tuple[Any, ...]:
    """Run one § **13** top-level ``dem_atariiii_plot_*`` on loaded **PDP``.

    Return shape is kind-aware:
    - ``rgb_jkh`` → ``(J, K, h, png_path)``
    - ``gameplay_o2rgb`` → ``(frame_rgb, control, png_path)``
    """
    spec = optim1full_plot_site_spec(site_id)
    out_png_path = png_path
    if spec.kind == SITE_KIND_GAMEPLAY_O2RGB or site_id == DEM_GAMEPLAY:
        t_final = int(spec.final_t) if int(spec.final_t) > 0 else 128
        return dem_atariiii_plot_gameplay(
            pdp,
            plot_ctx,
            t=t_final,
            save_png=save_png,
            png_path=out_png_path,
        )
    if spec.kind == SITE_KIND_BASIN_SERIES or site_id == DEM_ATTRACTORS_BASIN:
        return dem_atariiii_plot_attractors_basin(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if spec.kind == SITE_KIND_STRUCTURE_F or site_id == DEM_STRUCTURE_LEARNING:
        return dem_atariiii_plot_structure_learning(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if spec.kind == SITE_KIND_POST_SORT_ORBITS or site_id == DEM_ATTRACTORS_MDP_POST_SORT:
        # Product B spectral injects for plot-fn parity / visual review.
        import matlab.engine

        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
        from tests.demo1.demo1_paths import demo1_repo_root
        from tests.demo1.optim1full.optim1full_dir_orbits_matlab import (
            bind_dir_orbits_matlab_injects,
            optim1full_dir_orbits_matlab_eig_enabled,
            optim1full_dir_orbits_matlab_svd_enabled,
        )

        need_eng = (
            optim1full_dir_orbits_matlab_eig_enabled()
            or optim1full_dir_orbits_matlab_svd_enabled()
        )
        if need_eng:
            eng = matlab.engine.start_matlab()
            try:
                configure_dem_matlab_engine(eng, demo1_repo_root())
                injects = bind_dir_orbits_matlab_injects(eng)
                return dem_atariiii_plot_attractors_mdp_post_sort(
                    pdp,
                    plot_ctx,
                    save_png=save_png,
                    png_path=out_png_path,
                    eig=injects["eig"],
                    svd=injects["svd"],
                    ness_order=injects.get("ness_order"),
                    eng=eng,
                )
            finally:
                eng.quit()
        return dem_atariiii_plot_attractors_mdp_post_sort(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if spec.kind == SITE_KIND_ORBITS_FIGURE or site_id in (DEM_ORBITS_BEFORE, DEM_ORBITS_AFTER):
        import matlab.engine

        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
        from tests.demo1.demo1_paths import demo1_repo_root
        from tests.demo1.optim1full.optim1full_dir_orbits_matlab import (
            bind_dir_orbits_matlab_injects,
            optim1full_dir_orbits_matlab_eig_enabled,
            optim1full_dir_orbits_matlab_svd_enabled,
        )

        plot_fn = (
            dem_atariiii_plot_orbits_before
            if site_id == DEM_ORBITS_BEFORE
            else dem_atariiii_plot_orbits_after
        )
        need_eng = (
            optim1full_dir_orbits_matlab_eig_enabled()
            or optim1full_dir_orbits_matlab_svd_enabled()
        )
        if need_eng:
            eng = matlab.engine.start_matlab()
            try:
                configure_dem_matlab_engine(eng, demo1_repo_root())
                injects = bind_dir_orbits_matlab_injects(eng)
                return plot_fn(
                    pdp,
                    plot_ctx,
                    save_png=save_png,
                    png_path=out_png_path,
                    eig=injects["eig"],
                    svd=injects["svd"],
                    ness_order=injects.get("ness_order"),
                    eng=eng,
                )
            finally:
                eng.quit()
        return plot_fn(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if site_id == DEM_GENERATIVE_AI:
        return dem_atariiii_plot_generative_ai(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if site_id == DEM_ACTIVE_INFERENCE_NR:
        return dem_atariiii_plot_active_inference_nr(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if site_id == DEM_BEFORE_COMPRESSION_RGB:
        return dem_atariiii_plot_before_compression_rgb(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if site_id == DEM_WITH_COMPRESSION_RGB:
        return dem_atariiii_plot_with_compression_rgb(
            pdp,
            plot_ctx,
            save_png=save_png,
            png_path=out_png_path,
        )
    if spec.kind != SITE_KIND_RGB_JKH:
        raise KeyError(
            f"run_optim1full_plot_for_site: unhandled kind={spec.kind!r} for {site_id!r}"
        )
    raise KeyError(f"run_optim1full_plot_for_site: no plot fn wired for {site_id!r} ({spec.figure_title})")


def run_optim1full_plot_from_fixtures(
    tag: str,
    source: PdpSource,
    *,
    save_png: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, Path | None]:
    """Convenience: load ``plot_ctx`` + **PDP** from OPTIM1FULL fixtures, then plot."""
    ctx = load_optim1full_plot_ctx()
    pdp = load_optim1full_pdp_for_plot(tag, source)
    return run_optim1full_plot(tag, pdp, ctx, save_png=save_png)


def iter_optim1full_plot_fixture_paths() -> tuple[tuple[str, Path], ...]:
    """(label, path) pairs required for ``--plot-oracle`` gate (W1-C)."""
    rows: list[tuple[str, Path]] = [("plot_ctx", optim1full_plot_ctx_mat())]
    for tag in OPTIM1FULL_12PLOT_TAGS:
        rows.append((f"pdp_mat[{tag}]", optim1full_pdp_mat_for_tag(tag)))
        rows.append((f"pdp_pkl[{tag}]", optim1full_pdp_pkl_for_tag(tag)))
        rows.append((f"12plot[{tag}]", optim1full_12plot_oracle_mat(tag)))
    for tag in PHASE0_PLOT_TAGS:
        rows.append((f"paths[{tag}]", optim1full_paths_oracle_mat(tag)))
    return tuple(rows)


def assert_optim1full_plot_fixtures_present() -> None:
    """Raise ``FileNotFoundError`` when plot-oracle fixtures are incomplete."""
    missing = [
        f"{label}: {path}"
        for label, path in iter_optim1full_plot_fixture_paths()
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "missing OPTIM1FULL plot fixtures "
            "(run optim1full_capture_plot_fixtures.py D2 / --oracle-only / --paths-only / --a3-lite-only):\n"
            + "\n".join(missing)
        )


__all__ = [
    "Optim1fullPlotSite",
    "Optim1fullPathsSite",
    "A3_LITE_PLOT_TAG",
    "A3_LITE_PLOT_TAGS",
    "DEM_PLOT_SITES",
    "DEM_PATHS_SITES",
    "OPTIM1FULL_12PLOT_TAGS",
    "PHASE0_PLOT_SITES",
    "PHASE0_PLOT_TAGS",
    "PdpSource",
    "compute_optim1full_paths_to_hits",
    "assert_optim1full_live_pdp_plot_oracles",
    "assert_optim1full_live_site_plot_oracles",
    "assert_optim1full_w1e_plot_oracles_present",
    "assert_optim1full_plot_fixtures_present",
    "assert_optim1full_plot_jkh_matches_oracle",
    "assert_optim1full_plot_paths_matches_oracle",
    "build_optim1full_plot_ctx_from_driver",
    "iter_optim1full_plot_fixture_paths",
    "load_optim1full_12plot_oracle",
    "load_optim1full_paths_oracle",
    "load_optim1full_paths_oracle_from_mat",
    "load_optim1full_site_paths_oracle",
    "load_optim1full_pdp_for_plot",
    "load_optim1full_pdp_for_site",
    "load_optim1full_plot_ctx",
    "load_gameplay_oracle_from_mat",
    "load_basin_oracle_from_mat",
    "load_optim1full_basin_series_for_site",
    "load_basin_series_from_payload_mat",
    "load_basin_series_from_pkl",
    "load_post_sort_oracle_from_mat",
    "load_optim1full_post_sort_payload_for_site",
    "load_post_sort_payload_from_mat",
    "load_post_sort_payload_from_pkl",
    "load_optim1full_site_oracle",
    "optim1full_plot_enabled",
    "optim1full_plot_compare_png_path",
    "optim1full_plot_png_path",
    "resolve_optim1full_12plot_reference_png",
    "resolve_optim1full_site_reference_png",
    "run_optim1full_d4_visual_review",
    "run_optim1full_site_d4_visual_review",
    "run_optim1full_paths_plot",
    "run_optim1full_paths_for_site",
    "run_optim1full_plot",
    "run_optim1full_plot_for_site",
    "run_optim1full_plot_from_fixtures",
    "run_optim1full_plot_phase_b_visual_review",
]
