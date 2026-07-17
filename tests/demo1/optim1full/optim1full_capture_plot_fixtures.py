#!/usr/bin/env python3
"""OPTIM1FULL W1 — plot fixture dump orchestrator (steps **D2**, **D4**).

**2a** — Save ``DEMAtariIII_optim1full_plot_ctx.mat`` from Model **B** driver ctx
        (``run_optim1full_optim1_through_mdp_pre``, ``stop_after='entries_11'``).
**2b** — MATLAB ``DEMAtariIII_entry12_12plot_capture`` per phase-0 tag (loads **PDP** — no VB).
**2c** — Manifest log under ``logs/optim1full_plot_fixture_capture_*.log``.
**D4** — ``--visual-review-only``: Python PNG + MATLAB-vs-Python compare per tag (W1-D; no VB).

See ``OPTIM1FULL.md`` § W1 — D2 one-time dump; W1-D Lane A for D4.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _log_line(log_fp: TextIO | None, msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
    if log_fp is not None:
        log_fp.write(msg + "\n")
        log_fp.flush()


def _require_plot_pdp_mats(tags: tuple[str, ...]) -> list[Path]:
    from tests.demo1.optim1full.optim1full_paths import optim1full_pdp_mat_for_tag

    missing: list[Path] = []
    for tag in tags:
        p = optim1full_pdp_mat_for_tag(tag)
        if not p.is_file():
            missing.append(p)
    return missing


def _load_driver_ctx_for_plot(
    *,
    deadline_minutes: str,
    driver_ctx_pkl: Path | None,
) -> dict[str, Any]:
    if driver_ctx_pkl is not None:
        if not driver_ctx_pkl.is_file():
            raise FileNotFoundError(f"driver ctx pickle not found: {driver_ctx_pkl}")
        with driver_ctx_pkl.open("rb") as f:
            ctx = pickle.load(f)
        need = ("RGB", "GDP", "Nm", "Nr", "Nc", "Nd", "C", "Sc")
        missing = [k for k in need if k not in ctx]
        if missing:
            raise KeyError(f"driver ctx pickle missing keys {missing!r}: {driver_ctx_pkl}")
        return ctx

    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env
    from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim1full_parity import (
        run_optim1full_optim1_through_mdp_pre,
    )

    buf, manifest = load_validated_optim1full_ledger()
    with optim1full_signoff_env(deadline_minutes=deadline_minutes):
        return run_optim1full_optim1_through_mdp_pre(
            buf,
            manifest,
            deadline_minutes=deadline_minutes,
            stop_after="entries_11",
        )


def _save_plot_ctx_mat_via_matlab(eng: Any, out_path: Path, ctx: dict[str, Any]) -> None:
    """Write v7 ``plot_ctx`` using Engine ``spm_MDP_pong`` + Model **B** ``Nm`` / ``GDP.id``."""
    import matlab

    gdp_id = ctx["GDP"]["id"]
    for key in ("reward", "contraint", "control"):
        if key not in gdp_id:
            raise KeyError(f"driver ctx GDP.id missing {key!r}")

    eng.workspace["Nm_save"] = matlab.double([[float(ctx["Nm"])]])
    eng.workspace["reward_id"] = matlab.double([[float(gdp_id["reward"])]])
    eng.workspace["contraint_id"] = matlab.double([[float(gdp_id["contraint"])]])
    eng.workspace["control_id"] = matlab.double([[float(gdp_id["control"])]])

    nr = int(ctx["Nr"])
    nc = int(ctx["Nc"])
    nd = int(ctx["Nd"])
    sc = int(ctx["Sc"])
    c_val = int(ctx["C"])
    out_s = str(out_path.resolve()).replace("\\", "/")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    eng.eval(
        f"""
        [GDP,~,~,~,RGB] = spm_MDP_pong({nr},{nc},{nd},true,0);
        GDP.tau = 1;
        GDP.T = 10000;
        GDP.id.reward = reward_id;
        GDP.id.contraint = contraint_id;
        GDP.id.control = control_id;
        Nm = Nm_save;
        Nr = {nr};
        Nc = {nc};
        Nd = {nd};
        C = {c_val};
        Sc = {sc};
        plot_meta = struct();
        plot_meta.capture_script = 'optim1full_capture_plot_fixtures.py';
        plot_meta.purpose = 'OPTIM1FULL-pure plot inputs (Model B ledger session Nm/id)';
        plot_meta.timestamp = '{ts}';
        plot_meta.matlab_release = version;
        save('{out_s}', 'RGB', 'GDP', 'Nm', 'Nr', 'Nc', 'Nd', 'C', 'Sc', 'plot_meta', '-v7');
        """,
        nargout=0,
    )


def _capture_plot_ctx(
    eng: Any,
    *,
    out_path: Path,
    deadline_minutes: str,
    driver_ctx_pkl: Path | None,
    log_fp: TextIO | None,
) -> dict[str, Any]:
    from python_src.toolbox.DEM.entry12_plot import load_plot_ctx_from_mat

    _log_line(log_fp, "[optim1full_capture_plot] D2a: Model B driver ctx → plot_ctx.mat")
    ctx = _load_driver_ctx_for_plot(
        deadline_minutes=deadline_minutes,
        driver_ctx_pkl=driver_ctx_pkl,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_plot_ctx_mat_via_matlab(eng, out_path, ctx)
    _log_line(log_fp, f"[optim1full_capture_plot] wrote {out_path}")
    loaded = load_plot_ctx_from_mat(out_path)
    if int(loaded["Nm"]) != int(ctx["Nm"]):
        raise RuntimeError(
            f"plot_ctx round-trip Nm mismatch: saved {ctx['Nm']!r}, loaded {loaded['Nm']!r}"
        )
    return {
        "plot_ctx_mat": str(out_path.resolve()),
        "Nm": int(ctx["Nm"]),
        "Nr": int(ctx["Nr"]),
        "Nc": int(ctx["Nc"]),
        "Nd": int(ctx["Nd"]),
        "C": int(ctx["C"]),
        "Sc": int(ctx["Sc"]),
    }


def _set_matlab_12plot_env(
    eng: Any,
    *,
    fixtures: Path,
    plot_ctx_mat: Path,
    pdp_mat: Path,
    tag: str,
    vis_dir: Path,
    site: Any,
) -> None:
    fix = str(fixtures.resolve())
    eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
    eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix, nargout=0)
    eng.setenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", tag, nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_PDP_MAT", str(pdp_mat.resolve()), nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_CTX_MAT", str(plot_ctx_mat.resolve()), nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_VIS_DIR", str(vis_dir.resolve()), nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_FIGURE_TITLE", str(site.figure_title), nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_NT", str(int(site.nt)), nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_MOVIE", str(int(site.movie)), nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_HITS_Y", str(float(site.hits_y_offset)), nargout=0)


def _capture_12plot_oracles(
    eng: Any,
    *,
    tags: tuple[str, ...],
    plot_ctx_mat: Path,
    log_fp: TextIO | None,
) -> list[dict[str, str]]:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_12plot_oracle_mat,
        optim1full_fixtures_dir,
        optim1full_pdp_mat_for_tag,
        optim1full_visualizations_dir,
    )
    from tests.demo1.optim1full.optim1full_plot import DEM_PLOT_SITES

    fixtures = optim1full_fixtures_dir()
    vis_dir = optim1full_visualizations_dir()
    vis_dir.mkdir(parents=True, exist_ok=True)

    _log_line(log_fp, "[optim1full_capture_plot] D2b: MATLAB 12PLOT capture per tag")
    eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)

    manifest_rows: list[dict[str, str]] = []
    for tag in tags:
        pdp_mat = optim1full_pdp_mat_for_tag(tag)
        oracle_mat = optim1full_12plot_oracle_mat(tag)
        _set_matlab_12plot_env(
            eng,
            fixtures=fixtures,
            plot_ctx_mat=plot_ctx_mat,
            pdp_mat=pdp_mat,
            tag=tag,
            vis_dir=vis_dir,
            site=DEM_PLOT_SITES[tag],
        )
        _log_line(log_fp, f"[optim1full_capture_plot] 12PLOT tag={tag} pdp={pdp_mat.name}")
        eng.DEMAtariIII_entry12_12plot_capture(nargout=0)
        if not oracle_mat.is_file():
            raise FileNotFoundError(f"12PLOT oracle not written: {oracle_mat}")
        manifest_rows.append(
            {
                "tag": tag,
                "pdp_mat": str(pdp_mat.resolve()),
                "oracle_mat": str(oracle_mat.resolve()),
            }
        )
        _log_line(log_fp, f"[optim1full_capture_plot] wrote {oracle_mat.name}")
    return manifest_rows


def _set_matlab_paths_env(
    eng: Any,
    *,
    fixtures: Path,
    pdp_mat: Path,
    tag: str,
    site: Any,
) -> None:
    fix = str(fixtures.resolve())
    eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
    eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix, nargout=0)
    eng.setenv("RGMS_ENTRY12_CAPTURE_RUN_TAG", tag, nargout=0)
    eng.setenv("RGMS_ENTRY12_12PLOT_PDP_MAT", str(pdp_mat.resolve()), nargout=0)
    eng.setenv("RGMS_ENTRY12_PATHS_NT", str(int(site.nt)), nargout=0)
    eng.setenv("RGMS_ENTRY12_PATHS_B_THRESHOLD", str(float(site.b_threshold)), nargout=0)
    eng.setenv("RGMS_ENTRY12_PATHS_PANEL_TITLE", str(site.panel_title), nargout=0)


def _capture_paths_oracles(
    eng: Any,
    *,
    tags: tuple[str, ...],
    log_fp: TextIO | None,
) -> list[dict[str, str]]:
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_fixtures_dir,
        optim1full_paths_oracle_mat,
        optim1full_pdp_mat_for_tag,
    )
    from tests.demo1.optim1full.optim1full_plot import DEM_PATHS_SITES

    fixtures = optim1full_fixtures_dir()
    _log_line(log_fp, "[optim1full_capture_plot] A2: MATLAB paths capture per tag")
    eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)

    manifest_rows: list[dict[str, str]] = []
    for tag in tags:
        pdp_mat = optim1full_pdp_mat_for_tag(tag)
        oracle_mat = optim1full_paths_oracle_mat(tag)
        _set_matlab_paths_env(
            eng,
            fixtures=fixtures,
            pdp_mat=pdp_mat,
            tag=tag,
            site=DEM_PATHS_SITES[tag],
        )
        _log_line(log_fp, f"[optim1full_capture_plot] PATHS tag={tag} pdp={pdp_mat.name}")
        eng.DEMAtariIII_entry12_paths_capture(nargout=0)
        if not oracle_mat.is_file():
            raise FileNotFoundError(f"PATHS oracle not written: {oracle_mat}")
        manifest_rows.append(
            {
                "tag": tag,
                "pdp_mat": str(pdp_mat.resolve()),
                "oracle_mat": str(oracle_mat.resolve()),
            }
        )
        _log_line(log_fp, f"[optim1full_capture_plot] wrote {oracle_mat.name}")
    return manifest_rows


def _capture_site_paths_oracle(
    eng: Any,
    *,
    site_id: str,
    log_fp: TextIO | None,
) -> dict[str, str]:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir, optim1full_plot_paths_for_site
    from tests.demo1.optim1full.optim1full_plot import Optim1fullPathsSite
    from tests.demo1.optim1full.optim1full_plot_sites import optim1full_paths_site_spec

    site_use = str(site_id).strip()
    spec = optim1full_paths_site_spec(site_use)
    paths = optim1full_plot_paths_for_site(site_use)
    # Genuine plot-parity: paths oracle (I/HID) must run MATLAB code on the INDEPENDENT
    # MATLAB-owned fence PDP, never the Python re-save (circular). Refuse a non-MATLAB mat.
    from tests.demo1.optim1full.optim1full_compare_spine_fence_pdp_pkl_to_mat import (
        _assert_spine_mat_meta,
    )

    pdp_mat = paths["matlab_pdp_mat"]
    oracle_mat = paths["paths_oracle_mat"]
    if not pdp_mat.is_file():
        raise FileNotFoundError(
            "missing MATLAB-owned plot-fence authority PDP for paths site: "
            f"{pdp_mat}; regenerate via capture_optim1full_rand_ledger + "
            "RGMS_OPTIM1FULL_PLOT_FENCE_TRACE=1"
        )
    _assert_spine_mat_meta(pdp_mat, require_matlab_authority=True)

    fixtures = optim1full_fixtures_dir()
    paths_site = Optim1fullPathsSite(
        tag=spec.site_id,
        panel_title=spec.panel_title,
        nt=int(spec.nt),
        b_threshold=float(spec.b_threshold),
    )
    _log_line(
        log_fp,
        f"[optim1full_capture_plot] PATHS site={site_use} spine_pdp={paths['spine_pdp_site_id']} "
        f"pdp={pdp_mat.name}",
    )
    eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
    _set_matlab_paths_env(
        eng,
        fixtures=fixtures,
        pdp_mat=pdp_mat,
        tag=site_use,
        site=paths_site,
    )
    eng.setenv("RGMS_ENTRY12_PATHS_OUT_MAT", str(oracle_mat.resolve()), nargout=0)
    eng.DEMAtariIII_entry12_paths_capture(nargout=0)
    if not oracle_mat.is_file():
        raise FileNotFoundError(f"PATHS oracle not written: {oracle_mat}")
    _log_line(log_fp, f"[optim1full_capture_plot] wrote {oracle_mat.name}")
    return {
        "site_id": site_use,
        "spine_pdp_site_id": str(paths["spine_pdp_site_id"]),
        "pdp_mat": str(pdp_mat.resolve()),
        "oracle_mat": str(oracle_mat.resolve()),
    }


def _run_d4_site_visual_review(
    *,
    site_id: str,
    source: str,
    log_fp: TextIO | None,
) -> list[dict[str, Any]]:
    import matplotlib

    matplotlib.use("Agg")
    from tests.demo1.optim1full.optim1full_plot import run_optim1full_site_d4_visual_review
    from tests.demo1.optim1full.optim1full_plot_sites import optim1full_plot_site_spec

    optim1full_plot_site_spec(site_id)
    _log_line(log_fp, f"[optim1full_capture_plot] D4 site={site_id} source={source}")
    row = run_optim1full_site_d4_visual_review(site_id, source=source)  # type: ignore[arg-type]
    _log_line(log_fp, f"[optim1full_capture_plot] D4 python_png={row['python_png']}")
    if row.get("compare_png"):
        _log_line(log_fp, f"[optim1full_capture_plot] D4 compare_png={row['compare_png']}")
    return [row]


def _run_d4_visual_review(
    *,
    tags: tuple[str, ...],
    source: str,
    log_fp: TextIO | None,
) -> list[dict[str, Any]]:
    import matplotlib

    matplotlib.use("Agg")
    from tests.demo1.optim1full.optim1full_plot import (
        assert_optim1full_plot_fixtures_present,
        run_optim1full_d4_visual_review,
    )

    assert_optim1full_plot_fixtures_present()
    _log_line(log_fp, "[optim1full_capture_plot] D4: Python visual review per tag (W1-D)")
    rows: list[dict[str, Any]] = []
    for tag in tags:
        _log_line(log_fp, f"[optim1full_capture_plot] D4 tag={tag} source={source}")
        row = run_optim1full_d4_visual_review(tag, source=source)  # type: ignore[arg-type]
        rows.append(row)
        _log_line(log_fp, f"[optim1full_capture_plot] D4 python_png={row['python_png']}")
        if row.get("compare_png"):
            _log_line(log_fp, f"[optim1full_capture_plot] D4 compare_png={row['compare_png']}")
    return rows


def main(argv: list[str] | None = None) -> int:
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_plot import (
        A3_LITE_PLOT_TAGS,
        DEM_PLOT_SITES,
        OPTIM1FULL_12PLOT_TAGS,
        PHASE0_PLOT_TAGS,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_ctx_mat

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--deadline-minutes", default="240", help="Model B entries_1_11 budget")
    p.add_argument(
        "--driver-ctx-pkl",
        type=Path,
        default=None,
        help="optional pickled driver ctx (RGB/GDP/Nm/scalars) — skips entries_1_11 replay",
    )
    p.add_argument("--skip-plot-ctx", action="store_true", help="skip D2a (use existing plot_ctx.mat)")
    p.add_argument("--skip-12plot", action="store_true", help="skip D2b (12PLOT oracle capture)")
    p.add_argument("--plot-ctx-only", action="store_true", help="run D2a only")
    p.add_argument(
        "--oracle-only",
        action="store_true",
        help="run D2b only (requires existing plot_ctx.mat)",
    )
    p.add_argument(
        "--paths-only",
        action="store_true",
        help="run A2 paths oracle capture only (no plot_ctx / 12PLOT)",
    )
    p.add_argument(
        "--a3-lite-only",
        action="store_true",
        help="run A3-lite 12PLOT oracle capture for call2 only (tier 3a)",
    )
    p.add_argument(
        "--visual-review-only",
        action="store_true",
        help="W1-D D4: Python PNG + compare per tag on frozen fixtures (no VB, no Engine)",
    )
    p.add_argument(
        "--site-id",
        default=None,
        help="§13 site_id for --visual-review-only or --paths-only (spine fixtures)",
    )
    p.add_argument(
        "--tag",
        default=None,
        help="single OPTIM1FULL plot tag (for --visual-review-only); default all 12PLOT tags",
    )
    p.add_argument(
        "--pdp-source",
        choices=("pkl", "mat"),
        default="pkl",
        help="PDP source for --visual-review-only (default Phase B .pkl)",
    )
    args = p.parse_args(argv)

    exclusive_flags = (
        args.plot_ctx_only,
        args.oracle_only,
        args.paths_only,
        args.a3_lite_only,
        args.visual_review_only,
    )
    if sum(int(x) for x in exclusive_flags) > 1:
        print("[optim1full_capture_plot] only one mode flag allowed", file=sys.stderr)
        return 2
    if args.paths_only and (args.plot_ctx_only or args.oracle_only or args.a3_lite_only):
        print("[optim1full_capture_plot] --paths-only is exclusive", file=sys.stderr)
        return 2
    if args.a3_lite_only and (args.plot_ctx_only or args.oracle_only or args.paths_only):
        print("[optim1full_capture_plot] --a3-lite-only is exclusive", file=sys.stderr)
        return 2

    if args.visual_review_only:
        if args.site_id is not None and args.tag is not None:
            print(
                "[optim1full_capture_plot] use only one of --site-id or --tag",
                file=sys.stderr,
            )
            return 2
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = _REPO / "logs" / f"optim1full_plot_visual_review_{stamp}.log"
        if args.site_id is not None:
            from tests.demo1.optim1full.optim1full_plot_sites import optim1full_plot_site_spec

            site_use = str(args.site_id).strip()
            try:
                optim1full_plot_site_spec(site_use)
            except KeyError:
                print(f"[optim1full_capture_plot] unknown site_id: {site_use!r}", file=sys.stderr)
                return 2
            manifest: dict[str, Any] = {
                "capture_script": "optim1full_capture_plot_fixtures.py",
                "mode": "visual-review-only",
                "timestamp": stamp,
                "site_id": site_use,
                "pdp_source": args.pdp_source,
            }
            with log_path.open("w", encoding="utf-8") as log_fp:
                _log_line(log_fp, f"[optim1full_capture_plot] log {log_path}")
                manifest["visual_review"] = _run_d4_site_visual_review(
                    site_id=site_use,
                    source=str(args.pdp_source),
                    log_fp=log_fp,
                )
                _log_line(log_fp, f"[optim1full_capture_plot] manifest: {manifest}")
            print(f"[optim1full_capture_plot] done log={log_path}", file=sys.stderr, flush=True)
            return 0
        if args.tag is not None:
            tag_use = str(args.tag).strip()
            if tag_use not in OPTIM1FULL_12PLOT_TAGS:
                print(f"[optim1full_capture_plot] unknown tag: {tag_use!r}", file=sys.stderr)
                return 2
            tags = (tag_use,)
        else:
            tags = OPTIM1FULL_12PLOT_TAGS
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = _REPO / "logs" / f"optim1full_plot_visual_review_{stamp}.log"
        manifest: dict[str, Any] = {
            "capture_script": "optim1full_capture_plot_fixtures.py",
            "mode": "visual-review-only",
            "timestamp": stamp,
            "tags": list(tags),
            "pdp_source": args.pdp_source,
        }
        with log_path.open("w", encoding="utf-8") as log_fp:
            _log_line(log_fp, f"[optim1full_capture_plot] log {log_path}")
            manifest["visual_review"] = _run_d4_visual_review(
                tags=tags,
                source=str(args.pdp_source),
                log_fp=log_fp,
            )
            _log_line(log_fp, f"[optim1full_capture_plot] manifest: {manifest}")
        print(f"[optim1full_capture_plot] done log={log_path}", file=sys.stderr, flush=True)
        return 0

    if args.paths_only:
        if args.site_id is not None and args.tag is not None:
            print(
                "[optim1full_capture_plot] use only one of --site-id or --tag for --paths-only",
                file=sys.stderr,
            )
            return 2
        if args.site_id is not None:
            from tests.demo1.optim1full.optim1full_plot_sites import optim1full_paths_site_spec

            site_use = str(args.site_id).strip()
            try:
                optim1full_paths_site_spec(site_use)
            except KeyError:
                print(f"[optim1full_capture_plot] unknown paths site_id: {site_use!r}", file=sys.stderr)
                return 2
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = _REPO / "logs" / f"optim1full_plot_paths_capture_{stamp}.log"
            manifest: dict[str, Any] = {
                "capture_script": "optim1full_capture_plot_fixtures.py",
                "mode": "paths-only-site",
                "timestamp": stamp,
                "site_id": site_use,
            }
            import matlab.engine

            with log_path.open("w", encoding="utf-8") as log_fp:
                _log_line(log_fp, f"[optim1full_capture_plot] log {log_path}")
                eng = matlab.engine.start_matlab()
                try:
                    configure_dem_matlab_engine(eng, _REPO)
                    manifest["paths_site"] = _capture_site_paths_oracle(
                        eng,
                        site_id=site_use,
                        log_fp=log_fp,
                    )
                finally:
                    eng.quit()
                _log_line(log_fp, f"[optim1full_capture_plot] manifest: {manifest}")
            print(f"[optim1full_capture_plot] done log={log_path}", file=sys.stderr, flush=True)
            return 0

    if args.plot_ctx_only and args.oracle_only:
        print("[optim1full_capture_plot] cannot combine --plot-ctx-only and --oracle-only", file=sys.stderr)
        return 2
    if args.paths_only and (args.plot_ctx_only or args.oracle_only or args.a3_lite_only):
        print("[optim1full_capture_plot] --paths-only is exclusive", file=sys.stderr)
        return 2
    if args.a3_lite_only and (args.plot_ctx_only or args.oracle_only or args.paths_only):
        print("[optim1full_capture_plot] --a3-lite-only is exclusive", file=sys.stderr)
        return 2

    if args.a3_lite_only:
        tags = A3_LITE_PLOT_TAGS
    else:
        tags = PHASE0_PLOT_TAGS
    plot_ctx_path = optim1full_plot_ctx_mat()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _REPO / "logs" / f"optim1full_plot_fixture_capture_{stamp}.log"

    run_2a = not args.skip_plot_ctx and not args.oracle_only and not args.paths_only and not args.a3_lite_only
    run_2b = not args.skip_12plot and not args.plot_ctx_only and not args.paths_only
    run_paths = args.paths_only

    if run_2b or run_paths:
        missing = _require_plot_pdp_mats(tags)
        if missing:
            for m in missing:
                print(f"[optim1full_capture_plot] missing PDP mat: {m}", file=sys.stderr)
            return 2
        if run_2b and not plot_ctx_path.is_file() and not run_2a:
            print(
                f"[optim1full_capture_plot] plot_ctx missing: {plot_ctx_path} "
                "(run D2a first or drop --12plot-only)",
                file=sys.stderr,
            )
            return 2

    import matlab.engine

    manifest: dict[str, Any] = {
        "capture_script": "optim1full_capture_plot_fixtures.py",
        "timestamp": stamp,
        "tags": list(tags),
    }

    with log_path.open("w", encoding="utf-8") as log_fp:
        _log_line(log_fp, f"[optim1full_capture_plot] log {log_path}")
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, _REPO)
            if run_2a:
                manifest["plot_ctx"] = _capture_plot_ctx(
                    eng,
                    out_path=plot_ctx_path,
                    deadline_minutes=str(args.deadline_minutes),
                    driver_ctx_pkl=args.driver_ctx_pkl,
                    log_fp=log_fp,
                )
            if run_2b:
                manifest["12plot"] = _capture_12plot_oracles(
                    eng,
                    tags=tags,
                    plot_ctx_mat=plot_ctx_path,
                    log_fp=log_fp,
                )
            if run_paths:
                manifest["paths"] = _capture_paths_oracles(
                    eng,
                    tags=tags,
                    log_fp=log_fp,
                )
        finally:
            eng.quit()

        _log_line(log_fp, f"[optim1full_capture_plot] manifest: {manifest}")
    print(f"[optim1full_capture_plot] done log={log_path}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
