#!/usr/bin/env python3
"""OPTIM1FULL — spine ``PDP`` export at illustrate fence (Python driver lineage).

Normative capture for § **13** plot inputs: one process on Model **B** ledger,
stopping at the fence boundary:

- ``dem_gameplay`` / ``generate`` (``entry_stop=3`` after ``spm_MDP_generate``)
- ``dem_attractors_basin`` / ``after_basin`` (``entry_stop=9``; series ``NS``…``NH``)
- ``dem_attractors_mdp_post_sort`` / ``after_post_sort`` (Entry **10**; ``b1``/``hid``)
- ``dem_generative_ai`` / ``vb_call1``
- ``dem_active_inference_nr`` / ``nr_game_32``
- ``dem_before_compression_rgb`` / ``vb_call3``
- ``dem_with_compression_rgb`` / ``vb_call4``

Writes ``DEMAtariIII_optim1full_<site_id>_input.pkl`` from the Python driver.

**Resume (default ``--resume-from auto``):** post-NR fences resume from authority
``MDP_post_nr``; ``nr_game_32`` resumes from ``MDP_pre``; ``generate``, ``after_basin``,
``after_post_sort``, and ``vb_call1`` cold-start. See ``OPTIM1FULL.md`` § **Checkpoint + pairing imperative**.

Use ``--save-mat-from-pkl`` to write paired ``input.mat`` from an existing spine
``.pkl`` (Engine overlay; no VB re-run). No plot oracle refresh; no VB edits.

Replaces the asymmetric ``optim1full_capture_dem_generative_ai`` Python phase.
See ``OPTIM1FULL.md`` spine fence plan.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP = "optim1full_export_spine_fence_pdp"

SPINE_RESUME_AUTO = "auto"
SPINE_RESUME_COLD = "cold"
SPINE_RESUME_MDP_PRE = "mdp_pre"
SPINE_RESUME_MDP_POST_NR = "mdp_post_nr"
SPINE_RESUME_CHOICES = (
    SPINE_RESUME_AUTO,
    SPINE_RESUME_COLD,
    SPINE_RESUME_MDP_PRE,
    SPINE_RESUME_MDP_POST_NR,
)

# site_id -> driver stop_after boundary
_SITE_STOP_AFTER: dict[str, str] = {
    "dem_gameplay": "generate",
    "dem_attractors_basin": "after_basin",
    "dem_attractors_mdp_post_sort": "after_post_sort",
    "dem_structure_learning": "nr_game_32",
    "dem_generative_ai": "vb_call1",
    "dem_active_inference_nr": "nr_game_32",
    "dem_before_compression_rgb": "vb_call3",
    "dem_with_compression_rgb": "vb_call4",
}

# Orbits full figures reuse call3/call4 spine; oracle refresh only (no stop_after export).
_ORBITS_FIGURE_SITES: tuple[str, ...] = (
    "dem_orbits_before",
    "dem_orbits_after",
)
_EXPORT_CLI_SITES: tuple[str, ...] = tuple(_SITE_STOP_AFTER) + _ORBITS_FIGURE_SITES

_BASIN_SERIES_KEYS = ("NS", "NU", "NA", "NO", "NH")
_POST_SORT_PAYLOAD_KEYS = ("b1", "hid")


def _log_line(log_fp: TextIO | None, msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
    if log_fp is not None:
        log_fp.write(msg + "\n")
        log_fp.flush()


def _relocate_prior_asymmetric_mat(mat_path: Path, *, log_fp: TextIO | None) -> str | None:
    """Move non-spine ``input.mat`` aside so it is not mistaken for paired authority."""
    if not mat_path.is_file():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    deprecated_dir = mat_path.parent / "deprecated" / f"asymmetric_capture_{stamp}"
    deprecated_dir.mkdir(parents=True, exist_ok=True)
    dest = deprecated_dir / mat_path.name
    shutil.move(str(mat_path), str(dest))
    _log_line(
        log_fp,
        f"[optim1full_export_spine_fence_pdp] relocated asymmetric {mat_path.name} -> {dest}",
    )
    return str(dest.resolve())


def _assert_ledger_segment_audit(
    ctx: dict[str, Any],
    manifest: Any,
    *,
    stop_after: str,
) -> dict[str, int]:
    ledger = ctx.get("_optim1full_optim1_segment_ledger")
    if not isinstance(ledger, dict):
        raise RuntimeError("driver did not record _optim1full_optim1_segment_ledger")

    seg11 = manifest.segment("entries_1_11")
    k11_manifest = int(seg11.k)
    k11_ctx = int(ledger.get("entries_1_11_k", -1))
    if k11_ctx != k11_manifest:
        raise RuntimeError(
            f"entries_1_11 ledger audit: ctx k={k11_ctx} manifest k={k11_manifest}"
        )

    out: dict[str, int] = {"entries_1_11_k": k11_manifest}

    if stop_after == "generate":
        # Prefix of entries_1_11 only — do not require full-segment draw exhaustion.
        if ledger.get("stop_after") != "generate":
            raise RuntimeError(f"expected stop_after=generate, got {ledger.get('stop_after')!r}")
        draws = int(ledger.get("generate_draws", -1))
        if draws < 1:
            raise RuntimeError(f"generate fence expected generate_draws>=1, got {draws!r}")
        if draws > k11_manifest:
            raise RuntimeError(
                f"generate_draws={draws} exceeds entries_1_11.k={k11_manifest}"
            )
        out["generate_draws"] = draws
    elif stop_after == "after_basin":
        if ledger.get("stop_after") != "after_basin":
            raise RuntimeError(f"expected stop_after=after_basin, got {ledger.get('stop_after')!r}")
        draws = int(ledger.get("after_basin_draws", -1))
        if draws != k11_manifest:
            raise RuntimeError(
                f"after_basin_draws={draws} expected entries_1_11.k={k11_manifest}"
            )
        out["after_basin_draws"] = draws
    elif stop_after == "after_post_sort":
        if ledger.get("stop_after") != "after_post_sort":
            raise RuntimeError(
                f"expected stop_after=after_post_sort, got {ledger.get('stop_after')!r}"
            )
        draws = int(ledger.get("after_post_sort_draws", ledger.get("entries_1_11_draws", -1)))
        if draws != k11_manifest:
            raise RuntimeError(
                f"after_post_sort_draws={draws} expected entries_1_11.k={k11_manifest}"
            )
        out["after_post_sort_draws"] = draws
    elif stop_after == "vb_call1":
        seg1 = manifest.segment("vb_call1")
        k1_manifest = int(seg1.k)
        k1_ctx = int(ledger.get("vb_call1_k", -1))
        if k1_ctx != k1_manifest:
            raise RuntimeError(
                f"vb_call1 ledger audit: ctx k={k1_ctx} manifest k={k1_manifest}"
            )
        if ledger.get("stop_after") != "vb_call1":
            raise RuntimeError(f"expected stop_after=vb_call1, got {ledger.get('stop_after')!r}")
        out["vb_call1_k"] = k1_manifest
    elif stop_after == "vb_call3":
        seg3 = manifest.segment("vb_call3")
        k3_manifest = int(seg3.k)
        k3_ctx = int(ledger.get("vb_call3_k", -1))
        if k3_ctx != k3_manifest:
            raise RuntimeError(
                f"vb_call3 ledger audit: ctx k={k3_ctx} manifest k={k3_manifest}"
            )
        if ledger.get("stop_after") != "vb_call3":
            raise RuntimeError(f"expected stop_after=vb_call3, got {ledger.get('stop_after')!r}")
        out["vb_call3_k"] = k3_manifest
    elif stop_after == "vb_call4":
        seg4 = manifest.segment("vb_call4")
        k4_manifest = int(seg4.k)
        k4_ctx = int(ledger.get("vb_call4_k", -1))
        if k4_ctx != k4_manifest:
            raise RuntimeError(
                f"vb_call4 ledger audit: ctx k={k4_ctx} manifest k={k4_manifest}"
            )
        if ledger.get("stop_after") != "vb_call4":
            raise RuntimeError(f"expected stop_after=vb_call4, got {ledger.get('stop_after')!r}")
        out["vb_call4_k"] = k4_manifest
    elif stop_after == "nr_game_32":
        seg1 = manifest.segment("vb_call1")
        k1_manifest = int(seg1.k)
        k1_ctx = int(ledger.get("vb_call1_k", -1))
        if k1_ctx != k1_manifest:
            raise RuntimeError(
                f"vb_call1 ledger audit: ctx k={k1_ctx} manifest k={k1_manifest}"
            )
        seg_nr = manifest.segment("nr_game_32")
        k_nr_manifest = int(seg_nr.k)
        k_nr_ctx = int(ledger.get("nr_game_32_k", -1))
        if k_nr_ctx != k_nr_manifest:
            raise RuntimeError(
                f"nr_game_32 ledger audit: ctx k={k_nr_ctx} manifest k={k_nr_manifest}"
            )
        if ledger.get("stop_after") != "nr_game_32":
            raise RuntimeError(f"expected stop_after=nr_game_32, got {ledger.get('stop_after')!r}")
        if int(ledger.get("nr_game_i", -1)) != 32:
            raise RuntimeError(f"expected nr_game_i=32, got {ledger.get('nr_game_i')!r}")
        out["vb_call1_k"] = k1_manifest
        out["nr_game_32_k"] = k_nr_manifest

    return out


def resolve_spine_export_resume_mode(site_id: str, resume_from: str) -> str:
    """Map ``--resume-from`` to concrete spine export lane (see ``OPTIM1FULL.md`` checkpoint discipline)."""
    mode = str(resume_from).strip().lower()
    if mode not in SPINE_RESUME_CHOICES:
        raise ValueError(f"resume_from must be one of {SPINE_RESUME_CHOICES}, got {resume_from!r}")
    if mode != SPINE_RESUME_AUTO:
        return mode
    stop_after = _SITE_STOP_AFTER[str(site_id).strip()]
    if stop_after == "generate":
        return SPINE_RESUME_COLD
    if stop_after == "after_basin":
        return SPINE_RESUME_COLD
    if stop_after == "after_post_sort":
        return SPINE_RESUME_COLD
    if stop_after == "vb_call1":
        return SPINE_RESUME_COLD
    if stop_after == "nr_game_32":
        return SPINE_RESUME_MDP_PRE
    if stop_after in ("vb_call3", "vb_call4"):
        return SPINE_RESUME_MDP_POST_NR
    return SPINE_RESUME_COLD


def export_spine_fence_pdp(
    site_id: str,
    *,
    deadline_minutes: str = "240",
    resume_from: str = SPINE_RESUME_AUTO,
    output_pkl: Path | None = None,
    log_fp: TextIO | None = None,
) -> dict[str, Any]:
    from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim1full_parity import (
        run_optim1full_optim1_through_mdp_pre,
        run_optim1full_through_after_basin,
        run_optim1full_through_after_post_sort,
        run_optim1full_through_generate,
        run_optim1full_through_nr_game32,
        run_optim1full_through_nr_game32_from_authority,
        run_optim1full_through_vb_call3,
        run_optim1full_through_vb_call4,
        run_optim1full_through_vb_call3_from_authority,
        run_optim1full_through_vb_call4_from_authority,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        optim1full_vb_dev_optim_enabled,
        optim1full_vb_dispatch_status,
    )

    site = str(site_id).strip()
    if site not in _SITE_STOP_AFTER:
        raise KeyError(f"unsupported site_id for spine export: {site!r}")

    stop_after = _SITE_STOP_AFTER[site]
    resume_mode = resolve_spine_export_resume_mode(site, resume_from)
    paths = optim1full_plot_paths_for_site(site)
    pkl_out = Path(output_pkl).resolve() if output_pkl is not None else paths["input_pkl"]
    mat_path = paths["input_mat"]

    relocated = None
    if output_pkl is None:
        relocated = _relocate_prior_asymmetric_mat(mat_path, log_fp=log_fp)

    buf, manifest = load_validated_optim1full_ledger()
    seg11 = manifest.segment("entries_1_11")
    seg1 = manifest.segment("vb_call1") if stop_after in ("vb_call1", "vb_call3", "vb_call4", "nr_game_32") else None
    seg3 = manifest.segment("vb_call3") if stop_after in ("vb_call3", "vb_call4") else None
    seg4 = manifest.segment("vb_call4") if stop_after == "vb_call4" else None
    seg_nr = manifest.segment("nr_game_32") if stop_after == "nr_game_32" else None

    _log_line(
        log_fp,
        f"[optim1full_export_spine_fence_pdp] site={site} stop_after={stop_after} "
        f"resume_from={resume_from} resume_mode={resume_mode} "
        f"entries_1_11.k={seg11.k} vb_call1.k={seg1.k if seg1 else 'n/a'} "
        f"vb_call3.k={seg3.k if seg3 else 'n/a'} "
        f"vb_call4.k={seg4.k if seg4 else 'n/a'} "
        f"nr_game_32.k={seg_nr.k if seg_nr else 'n/a'} "
        f"deadline_minutes={deadline_minutes} "
        f"vb_dispatch={optim1full_vb_dispatch_status()}",
    )

    os.environ.setdefault("RGMS_ATARI_RUN_SEGMENT_TIMING", "1")
    t0 = time.perf_counter()
    with optim1full_signoff_env(deadline_minutes=str(deadline_minutes)):
        if stop_after == "generate":
            if resume_mode != SPINE_RESUME_COLD:
                raise RuntimeError(
                    f"resume_mode={resume_mode!r} incompatible with stop_after=generate "
                    "(generate fence is cold entry_stop=3 only)"
                )
            ctx = run_optim1full_through_generate(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
            )
        elif stop_after == "after_basin":
            if resume_mode != SPINE_RESUME_COLD:
                raise RuntimeError(
                    f"resume_mode={resume_mode!r} incompatible with stop_after=after_basin "
                    "(basin fence is cold entry_stop=9 only)"
                )
            ctx = run_optim1full_through_after_basin(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
            )
        elif stop_after == "after_post_sort":
            if resume_mode != SPINE_RESUME_COLD:
                raise RuntimeError(
                    f"resume_mode={resume_mode!r} incompatible with stop_after=after_post_sort "
                    "(post_sort fence is cold Entry 10 only)"
                )
            ctx = run_optim1full_through_after_post_sort(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
            )
        elif resume_mode == SPINE_RESUME_MDP_POST_NR:
            if stop_after == "vb_call3":
                ctx = run_optim1full_through_vb_call3_from_authority(
                    buf,
                    manifest,
                    deadline_minutes=str(deadline_minutes),
                )
            elif stop_after == "vb_call4":
                ctx = run_optim1full_through_vb_call4_from_authority(
                    buf,
                    manifest,
                    deadline_minutes=str(deadline_minutes),
                )
            else:
                raise RuntimeError(
                    f"resume_mode=mdp_post_nr incompatible with stop_after={stop_after!r}"
                )
        elif resume_mode == SPINE_RESUME_MDP_PRE:
            if stop_after == "nr_game_32":
                ctx = run_optim1full_through_nr_game32_from_authority(
                    buf,
                    manifest,
                    deadline_minutes=str(deadline_minutes),
                )
            else:
                raise RuntimeError(
                    f"resume_mode=mdp_pre incompatible with stop_after={stop_after!r}"
                )
        elif stop_after == "vb_call4":
            ctx = run_optim1full_through_vb_call4(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
            )
        elif stop_after == "vb_call3":
            ctx = run_optim1full_through_vb_call3(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
            )
        elif stop_after == "nr_game_32":
            ctx = run_optim1full_through_nr_game32(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
            )
        else:
            ctx = run_optim1full_optim1_through_mdp_pre(
                buf,
                manifest,
                deadline_minutes=str(deadline_minutes),
                stop_after=stop_after,
            )
    wall_s = time.perf_counter() - t0

    audit = _assert_ledger_segment_audit(ctx, manifest, stop_after=stop_after)

    if site == "dem_structure_learning":
        import numpy as np

        if "F" not in ctx:
            raise RuntimeError("dem_structure_learning export missing ctx['F']")
        payload: dict[str, Any] = {
            "F": np.asarray(ctx["F"], dtype=np.float64),
            "boundary": stop_after,
            "site_id": site,
            "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
            "kind": "structure_f",
            "ledger_protocol": manifest.protocol,
            "entries_1_11_k": audit["entries_1_11_k"],
            "nr_game_32_k": audit.get("nr_game_32_k"),
            "wall_s": wall_s,
            "resume_from": resume_from,
            "resume_mode": resume_mode,
            "vb_dev_optim": bool(optim1full_vb_dev_optim_enabled()),
        }
    elif stop_after == "after_basin":
        import numpy as np

        series: dict[str, Any] = {}
        for key in _BASIN_SERIES_KEYS:
            if key not in ctx:
                raise RuntimeError(f"stop_after=after_basin missing ctx[{key!r}]")
            series[key] = np.asarray(ctx[key], dtype=np.float64).reshape(-1)
        payload = {
            **series,
            "boundary": stop_after,
            "site_id": site,
            "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
            "kind": "basin_series",
            "ledger_protocol": manifest.protocol,
            "entries_1_11_k": audit["entries_1_11_k"],
            "after_basin_draws": audit.get("after_basin_draws"),
            "wall_s": wall_s,
            "resume_from": resume_from,
            "resume_mode": resume_mode,
            "vb_dev_optim": bool(optim1full_vb_dev_optim_enabled()),
        }
    elif stop_after == "after_post_sort":
        import numpy as np

        if "b1" not in ctx or "hid" not in ctx:
            raise RuntimeError("stop_after=after_post_sort missing ctx['b1']/'hid'")
        payload = {
            "b1": np.asarray(ctx["b1"], dtype=np.float64),
            "hid": np.asarray(ctx["hid"], dtype=np.int64).ravel(order="F"),
            "boundary": stop_after,
            "site_id": site,
            "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
            "kind": "post_sort_orbits",
            "ledger_protocol": manifest.protocol,
            "entries_1_11_k": audit["entries_1_11_k"],
            "after_post_sort_draws": audit.get("after_post_sort_draws"),
            "wall_s": wall_s,
            "resume_from": resume_from,
            "resume_mode": resume_mode,
            "vb_dev_optim": bool(optim1full_vb_dev_optim_enabled()),
        }
    else:
        if "PDP" not in ctx:
            raise RuntimeError(f"stop_after={stop_after} did not produce ctx['PDP']")
        payload = {
            "PDP": ctx["PDP"],
            "boundary": stop_after,
            "site_id": site,
            "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
            "ledger_protocol": manifest.protocol,
            "entries_1_11_k": audit["entries_1_11_k"],
            "vb_call1_k": audit.get("vb_call1_k"),
            "vb_call3_k": audit.get("vb_call3_k"),
            "vb_call4_k": audit.get("vb_call4_k"),
            "nr_game_32_k": audit.get("nr_game_32_k"),
            "generate_draws": audit.get("generate_draws"),
            "wall_s": wall_s,
            "resume_from": resume_from,
            "resume_mode": resume_mode,
            "vb_dev_optim": bool(optim1full_vb_dev_optim_enabled()),
        }

    pkl_out.parent.mkdir(parents=True, exist_ok=True)
    with pkl_out.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    from tests.demo1.optim1full.optim1full_plot_parity_fingerprints import write_spine_pkl_meta

    authority = paths.get("authority_mat") or paths.get("matlab_pdp_mat")
    if authority is not None and Path(authority).is_file():
        meta_path = write_spine_pkl_meta(
            pkl_out,
            site_id=site,
            boundary=stop_after,
            matlab_pdp_mat=Path(authority),
            ledger_protocol=manifest.protocol,
            vb_dev_optim=bool(optim1full_vb_dev_optim_enabled()),
            repo=_REPO,
        )
        _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] wrote fingerprint {meta_path.name}")

    _log_line(
        log_fp,
        f"[optim1full_export_spine_fence_pdp] wrote {pkl_out} capture={CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP} "
        f"wall_s={wall_s:.3f}",
    )

    return {
        "site_id": site,
        "boundary": stop_after,
        "input_pkl": str(pkl_out.resolve()),
        "relocated_asymmetric_mat": relocated,
        "ledger_audit": audit,
        "wall_s": wall_s,
        "resume_from": resume_from,
        "resume_mode": resume_mode,
        "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
    }


def save_spine_fence_mat_from_pkl(
    site_id: str,
    *,
    log_fp: TextIO | None = None,
) -> dict[str, Any]:
    """Write spine ``input.mat`` from existing normative ``input.pkl`` (no VB re-run)."""
    import pickle

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_pdp_engine_io import (
        _align_spine_pdp_for_engine,
        save_pdp_authority_v7_mat,
    )
    # Plot/mat loaders before ``matlab.engine`` (DLL import order on Windows).
    from python_src.toolbox.DEM.entry12_plot import load_pdp_mat_for_plot  # noqa: F401

    site = str(site_id).strip()
    if site not in _SITE_STOP_AFTER:
        raise KeyError(f"unsupported site_id for spine mat save: {site!r}")

    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site

    paths = optim1full_plot_paths_for_site(site)
    pkl_path = paths["input_pkl"]
    mat_path = paths["input_mat"]
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing spine pkl: {pkl_path}")

    with pkl_path.open("rb") as f:
        payload = pickle.load(f)
    if payload.get("capture") != CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP:
        raise RuntimeError(
            f"refusing mat save from non-spine pkl capture={payload.get('capture')!r}"
        )
    if "PDP" not in payload:
        raise RuntimeError(f"spine pkl missing PDP: {pkl_path}")

    _log_line(
        log_fp,
        f"[optim1full_export_spine_fence_pdp] mat-from-pkl site={site} pkl={pkl_path.name}",
    )

    py_aligned = _align_spine_pdp_for_engine(payload["PDP"])

    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        eng.addpath(str(_REPO / "matlab_custom" / "optim1full"), nargout=0)
        save_pdp_authority_v7_mat(
            eng,
            payload["PDP"],
            out_path=mat_path,
            py_aligned=py_aligned,
        )
    finally:
        eng.quit()

    _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] wrote {mat_path}")
    return {
        "site_id": site,
        "input_pkl": str(pkl_path.resolve()),
        "input_mat": str(mat_path.resolve()),
        "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
    }


def capture_spine_fence_oracle_from_python(
    site_id: str,
    *,
    log_fp: TextIO | None = None,
) -> dict[str, Any]:
    """Python ``J``/``K``/``h`` oracle from spine ``input.pkl`` (paired lineage witness)."""
    from scipy.io import savemat

    from python_src.toolbox.DEM.dem_atariiii_plot_generative_ai import (
        dem_atariiii_plot_generative_ai,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site
    from tests.demo1.optim1full.optim1full_plot import (
        load_optim1full_pdp_for_site,
        load_optim1full_plot_ctx,
    )

    site = str(site_id).strip()
    if site not in _SITE_STOP_AFTER:
        raise KeyError(f"unsupported site_id for spine python oracle: {site!r}")

    paths = optim1full_plot_paths_for_site(site)
    pkl_path = paths["input_pkl"]
    oracle_path = paths["oracle_mat"]
    if not pkl_path.is_file():
        raise FileNotFoundError(f"missing spine pkl: {pkl_path}")

    _log_line(
        log_fp,
        f"[optim1full_export_spine_fence_pdp] python-oracle site={site} pkl={pkl_path.name}",
    )

    pdp = load_optim1full_pdp_for_site(site, "pkl")
    plot_ctx = load_optim1full_plot_ctx()
    j, k, h, _png = dem_atariiii_plot_generative_ai(pdp, plot_ctx, save_png=False)

    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    savemat(
        str(oracle_path),
        {
            "J": j,
            "K": k,
            "h": h,
            "Nm": int(plot_ctx["Nm"]),
        },
        do_compression=False,
    )

    _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] wrote {oracle_path}")
    return {
        "site_id": site,
        "input_pkl": str(pkl_path.resolve()),
        "oracle_mat": str(oracle_path.resolve()),
        "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
        "oracle_source": "python_spine_pkl",
    }


def refresh_spine_fence_oracle_mat(
    site_id: str,
    *,
    require_matlab_authority: bool = True,
    log_fp: TextIO | None = None,
) -> dict[str, Any]:
    """MATLAB plot oracle for one spine site (paired lineage; no VB).

    Site-kind dispatch (do **not** run 12PLOT ``J``/``K``/``h`` for non-RGB sites):

    - ``rgb_jkh`` → ``DEMAtariIII_entry12_12plot_capture`` (``J``/``K``/``h``)
    - ``gameplay_o2rgb`` → ``DEMAtariIII_optim1full_gameplay_oracle_capture``
      (final-``t`` ``frame_rgb`` + ``control``)
    - ``basin_series`` → ``DEMAtariIII_optim1full_basin_oracle_capture``
      (final ``NS``…``NH`` + MATLAB PNG from ``matlab_payload``)
    - ``post_sort_orbits`` → ``DEMAtariIII_optim1full_post_sort_oracle_capture``
      (``u``/``I``/``HID`` + MATLAB PNG from ``matlab_payload`` ``b1``/``hid``)
    - ``orbits_figure`` → ``DEMAtariIII_optim1full_orbits_oracle_capture``
      (``u``/``I``/``HID`` + MATLAB PNG from call3/call4 ``matlab_pdp``; threshold ``1/32``)
    - ``structure_f`` → ``DEMAtariIII_optim1full_structure_learning_oracle_capture``
      (``F`` 6×NR + MATLAB PNG from ``matlab_payload``)

    Genuine plot-parity (``require_matlab_authority=True``, default): run MATLAB plot code
    on the INDEPENDENT MATLAB-owned fence authority (``matlab_pdp_mat`` or
    ``matlab_payload_mat``, ``capture=capture_optim1full_plot_fence``). A Python-resaved
    ``input.mat`` is REFUSED here — using it would make the oracle a re-render of Python's
    own output (circular).
    Set ``require_matlab_authority=False`` only for the historical (circular) diagnostic.
    """
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_fixtures_dir,
        optim1full_plot_paths_for_site,
        optim1full_visualizations_dir,
    )
    from tests.demo1.optim1full.optim1full_plot_sites import (
        AUTHORITY_KIND_PAYLOAD,
        SITE_KIND_BASIN_SERIES,
        SITE_KIND_GAMEPLAY_O2RGB,
        SITE_KIND_ORBITS_FIGURE,
        SITE_KIND_POST_SORT_ORBITS,
        SITE_KIND_RGB_JKH,
        SITE_KIND_STRUCTURE_F,
        optim1full_plot_authority_kind,
        optim1full_plot_site_spec,
    )
    # Plot loaders before Engine (matplotlib vs Engine DLL order on Windows).
    from python_src.toolbox.DEM.entry12_plot import load_pdp_mat_for_plot  # noqa: F401

    site = str(site_id).strip()
    if site not in _SITE_STOP_AFTER and site not in _ORBITS_FIGURE_SITES:
        raise KeyError(f"unsupported site_id for spine oracle refresh: {site!r}")

    paths = optim1full_plot_paths_for_site(site)
    auth_kind = optim1full_plot_authority_kind(site)
    if require_matlab_authority:
        from tests.demo1.optim1full.optim1full_compare_spine_fence_pdp_pkl_to_mat import (
            _assert_spine_authority_mat_meta,
        )

        mat_path = paths["authority_mat"]
        if not mat_path.is_file():
            raise FileNotFoundError(
                "missing MATLAB-owned plot-fence authority "
                f"{mat_path}; regenerate via capture_optim1full_rand_ledger + "
                "RGMS_OPTIM1FULL_PLOT_FENCE_TRACE=1"
            )
        _assert_spine_authority_mat_meta(mat_path, authority_kind=auth_kind)
    else:
        mat_path = paths["input_mat"]
    oracle_path = paths["oracle_mat"]
    ctx_path = paths["plot_ctx"]
    if not mat_path.is_file():
        raise FileNotFoundError(f"missing spine oracle input authority mat: {mat_path}")
    # Basin series oracle does not need plot_ctx; RGB/gameplay/orbits do.
    if auth_kind != AUTHORITY_KIND_PAYLOAD and not ctx_path.is_file():
        raise FileNotFoundError(f"missing plot_ctx: {ctx_path}")

    spec = optim1full_plot_site_spec(site)
    fixtures = optim1full_fixtures_dir()
    vis_dir = optim1full_visualizations_dir()
    vis_dir.mkdir(parents=True, exist_ok=True)

    kind = str(spec.kind)
    _log_line(
        log_fp,
        f"[optim1full_export_spine_fence_pdp] refresh-oracle site={site} kind={kind} "
        f"authority={mat_path.name} oracle={oracle_path.name}",
    )

    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        fix = str(fixtures.resolve())
        eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
        eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix, nargout=0)
        eng.setenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", f"optim1full_{site}", nargout=0)
        eng.setenv("RGMS_ENTRY12_12PLOT_PDP_MAT", str(mat_path.resolve()), nargout=0)
        if ctx_path.is_file():
            eng.setenv("RGMS_ENTRY12_12PLOT_CTX_MAT", str(ctx_path.resolve()), nargout=0)
        eng.setenv("RGMS_ENTRY12_12PLOT_VIS_DIR", str(vis_dir.resolve()), nargout=0)
        eng.setenv("RGMS_ENTRY12_12PLOT_ORACLE_MAT", str(oracle_path.resolve()), nargout=0)
        eng.setenv("RGMS_ENTRY12_12PLOT_FIGURE_TITLE", str(spec.figure_title), nargout=0)
        eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        if kind == SITE_KIND_GAMEPLAY_O2RGB:
            final_t = int(spec.final_t) if int(spec.final_t) > 0 else 128
            eng.setenv("RGMS_OPTIM1FULL_GAMEPLAY_FINAL_T", str(final_t), nargout=0)
            eng.DEMAtariIII_optim1full_gameplay_oracle_capture(nargout=0)
        elif kind == SITE_KIND_BASIN_SERIES:
            eng.DEMAtariIII_optim1full_basin_oracle_capture(nargout=0)
        elif kind == SITE_KIND_POST_SORT_ORBITS:
            eng.DEMAtariIII_optim1full_post_sort_oracle_capture(nargout=0)
        elif kind == SITE_KIND_ORBITS_FIGURE:
            eng.setenv("RGMS_OPTIM1FULL_ORBITS_SITE_ID", site, nargout=0)
            eng.DEMAtariIII_optim1full_orbits_oracle_capture(nargout=0)
        elif kind == SITE_KIND_STRUCTURE_F:
            eng.setenv("RGMS_OPTIM1FULL_STRUCTURE_NT", "256", nargout=0)
            eng.DEMAtariIII_optim1full_structure_learning_oracle_capture(nargout=0)
        elif kind == SITE_KIND_RGB_JKH:
            eng.setenv("RGMS_ENTRY12_12PLOT_NT", str(int(spec.nt)), nargout=0)
            eng.setenv("RGMS_ENTRY12_12PLOT_MOVIE", str(int(spec.movie)), nargout=0)
            eng.setenv("RGMS_ENTRY12_12PLOT_HITS_Y", str(float(spec.hits_y_offset)), nargout=0)
            eng.DEMAtariIII_entry12_12plot_capture(nargout=0)
        else:
            raise KeyError(
                f"unsupported plot site kind for oracle refresh: {kind!r} (site={site!r})"
            )
    finally:
        eng.quit()

    if not oracle_path.is_file():
        raise FileNotFoundError(f"oracle mat not written: {oracle_path}")

    _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] wrote {oracle_path}")
    from tests.demo1.optim1full.optim1full_paths import (
        OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE,
    )
    from tests.demo1.optim1full.optim1full_plot_parity_fingerprints import write_oracle_mat_meta

    oracle_source = (
        OPTIM1FULL_PLOT_FENCE_AUTHORITY_CAPTURE
        if require_matlab_authority
        else "python_resave_input_mat"
    )
    if require_matlab_authority and mat_path.is_file():
        meta_path = write_oracle_mat_meta(
            oracle_path,
            site_id=site,
            matlab_pdp_mat=mat_path,
            oracle_source=oracle_source,
            repo=_REPO,
        )
        _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] wrote fingerprint {meta_path.name}")

    return {
        "site_id": site,
        "input_mat": str(mat_path.resolve()),
        "oracle_mat": str(oracle_path.resolve()),
        "oracle_source": oracle_source,
        "capture": CAPTURE_OPTIM1FULL_EXPORT_SPINE_FENCE_PDP,
        "kind": kind,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--site",
        default="dem_generative_ai",
        choices=_EXPORT_CLI_SITES,
        help="§13 plot site (default: dem_generative_ai); orbits_* = refresh-oracle only",
    )
    p.add_argument("--deadline-minutes", default="240", help="driver segment budget")
    p.add_argument(
        "--resume-from",
        default=SPINE_RESUME_COLD,
        choices=SPINE_RESUME_CHOICES,
        help="checkpoint resume for spine export (default cold until resume path proved; auto=mdp_post_nr/call3/4, mdp_pre/nr_game_32)",
    )
    p.add_argument(
        "--output-pkl",
        type=Path,
        default=None,
        help="write spine .pkl here instead of normative input.pkl (sidecar resume proof)",
    )
    p.add_argument(
        "--save-mat-from-pkl",
        action="store_true",
        help="write input.mat from existing spine input.pkl via Engine (no VB re-run)",
    )
    p.add_argument(
        "--refresh-oracle",
        action="store_true",
        help=(
            "MATLAB plot oracle from the MATLAB-owned fence authority "
            "(matlab_pdp_mat or matlab_payload_mat; no VB). "
            "rgb_jkh → 12PLOT J/K/h; gameplay_o2rgb → final-t frame_rgb+control; "
            "basin_series → NS…NH + PNG; post_sort_orbits → u/I/HID + PNG; "
            "orbits_figure → u/I/HID + PNG (call3/call4 PDP); "
            "structure_f → F 6×NR + PNG. "
            "Genuine plot-parity authority."
        ),
    )
    p.add_argument(
        "--oracle-from-python-resave",
        action="store_true",
        help=(
            "DIAGNOSTIC ONLY (circular): refresh oracle from the Python-resaved input.mat "
            "instead of the MATLAB-owned fence PDP. Not valid for plot-parity sign-off."
        ),
    )
    p.add_argument(
        "--capture-python-oracle",
        action="store_true",
        help="Python J/K/h oracle from spine input.pkl (paired lineage witness)",
    )
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        add_vb_dev_optim_cli_argument,
        apply_vb_dev_optim_cli,
        optim1full_vb_dev_optim_enabled,
    )

    add_vb_dev_optim_cli_argument(p)
    args = p.parse_args(argv)
    apply_vb_dev_optim_cli(args)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.capture_python_oracle:
        log_suffix = "python_oracle"
    elif args.refresh_oracle:
        log_suffix = "refresh_oracle"
    elif args.save_mat_from_pkl:
        log_suffix = "mat_from_pkl"
    else:
        log_suffix = _SITE_STOP_AFTER.get(str(args.site).strip(), "export")
    log_path = _REPO / "logs" / f"optim1full_export_spine_{log_suffix}_{stamp}.log"

    manifest_out: dict[str, Any] = {
        "capture_script": "optim1full_export_spine_fence_pdp.py",
        "timestamp": stamp,
        "mode": (
            "capture_python_oracle"
            if args.capture_python_oracle
            else (
                "refresh_oracle"
                if args.refresh_oracle
                else ("save_mat_from_pkl" if args.save_mat_from_pkl else "export_pkl")
            )
        ),
    }
    if not args.save_mat_from_pkl and not args.refresh_oracle and not args.capture_python_oracle:
        manifest_out["deadline_minutes"] = str(args.deadline_minutes)
        manifest_out["resume_from"] = str(args.resume_from)
        manifest_out["vb_dev_optim"] = bool(optim1full_vb_dev_optim_enabled())

    with log_path.open("w", encoding="utf-8") as log_fp:
        _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] log {log_path}")
        try:
            site = str(args.site).strip()
            if args.capture_python_oracle:
                if site in _ORBITS_FIGURE_SITES:
                    raise KeyError(
                        f"orbits site {site!r} has no Python J/K/h oracle path; "
                        "use --refresh-oracle"
                    )
                manifest_out["python_oracle"] = capture_spine_fence_oracle_from_python(
                    site,
                    log_fp=log_fp,
                )
            elif args.refresh_oracle:
                manifest_out["oracle_refresh"] = refresh_spine_fence_oracle_mat(
                    site,
                    require_matlab_authority=not bool(args.oracle_from_python_resave),
                    log_fp=log_fp,
                )
            elif args.save_mat_from_pkl:
                if site in _ORBITS_FIGURE_SITES:
                    from tests.demo1.optim1full.optim1full_plot_sites import (
                        optim1full_spine_export_site_id,
                    )

                    site = optim1full_spine_export_site_id(site)
                    _log_line(
                        log_fp,
                        f"[optim1full_export_spine_fence_pdp] orbits alias → save-mat site={site}",
                    )
                manifest_out["mat_save"] = save_spine_fence_mat_from_pkl(
                    site,
                    log_fp=log_fp,
                )
            else:
                if site in _ORBITS_FIGURE_SITES:
                    from tests.demo1.optim1full.optim1full_plot_sites import (
                        optim1full_spine_export_site_id,
                    )

                    site = optim1full_spine_export_site_id(site)
                    _log_line(
                        log_fp,
                        f"[optim1full_export_spine_fence_pdp] orbits alias → export site={site}",
                    )
                manifest_out["export"] = export_spine_fence_pdp(
                    site,
                    deadline_minutes=str(args.deadline_minutes),
                    resume_from=str(args.resume_from),
                    output_pkl=args.output_pkl,
                    log_fp=log_fp,
                )
        except Exception as exc:
            _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] FAILED: {exc!r}")
            raise
        _log_line(log_fp, f"[optim1full_export_spine_fence_pdp] manifest: {json.dumps(manifest_out, indent=2)}")

    print(f"[optim1full_export_spine_fence_pdp] done log={log_path}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
