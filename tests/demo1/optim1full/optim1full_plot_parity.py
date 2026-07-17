#!/usr/bin/env python3
"""OPTIM1FULL — genuine plot-parity orchestration (translated plot code vs MATLAB plot code).

GOAL / FRAMEWORK (see ``OPTIM1FULL.md`` § *Parity-with-plots* and ``Atari_plotting.md`` § 0):
certify the **translated Python plotting functions** against **MATLAB's plotting functions**
on the *same* verified input. This is NOT the input-parity check (that the PDP feeding the
plot matches MATLAB) — that is proved separately on the spine fence pkl↔mat compare. Here we
prove that, given an identical fence PDP, ``spm_show_RGB`` / paths panel produce the same
``J``/``K``/``h`` (and ``I``/``HID``) numbers in Python as in MATLAB.

Honest ladder, per illustrate site (optim lineage throughout) — **dump-once / skip-if-present**:

  1. **MATLAB authority present** — the INDEPENDENT MATLAB-owned fence PDP
     ``DEMAtariIII_optim1full_<site>_matlab_pdp.mat`` (``capture=capture_optim1full_plot_fence``)
     produced by ``capture_optim1full_rand_ledger`` + ``RGMS_OPTIM1FULL_PLOT_FENCE_TRACE=1``.
     A Python-resaved ``input.mat`` (``--save-mat-from-pkl``) is REFUSED as authority here.
  2. **Export Python fence pkl** — only if missing, **fingerprint miss**, **or** ``--force-export``.
     Otherwise reuse the frozen spine ``input.pkl`` (checkpoint / dump-once).
     Sidecar: ``…_input.pkl.meta.json``.
  3. **Input parity** — Python fence pkl vs the MATLAB-owned authority
     (``--require-matlab-authority``): the plotting input matches MATLAB.
  4. **MATLAB oracle on MATLAB authority** — only if missing, **fingerprint miss**, **or**
     ``--force-refresh-oracle``. Otherwise reuse frozen ``oracle.mat`` (no Engine).
     Sidecar: ``…_oracle.mat.meta.json``.
  5. **Plot-fn parity** — run the Python plot code on the identical MATLAB-owned fence PDP
     (``source=matlab_pdp``) and on the Python pkl (``source=pkl``); assert both equal the
     MATLAB oracle.

``--save-mat-from-pkl`` is forbidden anywhere in this path (it would make the oracle a
re-render of Python's own output — circular).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# RGB J/K/h fence sites with an INDEPENDENT MATLAB-owned plot-fence PDP authority.
PLOT_PARITY_RGB_SITES: tuple[str, ...] = (
    "dem_generative_ai",
    "dem_active_inference_nr",
    "dem_before_compression_rgb",
    "dem_with_compression_rgb",
)

# Non-RGB sites registered for site-type-aware wire (Step 5 oracle+pytest+parity).
# Do NOT merge into PLOT_PARITY_RGB_SITES — declared numerics are not J/K/h.
PLOT_PARITY_NON_RGB_SITES: tuple[str, ...] = (
    "dem_gameplay",
    "dem_attractors_basin",
    "dem_attractors_mdp_post_sort",
    "dem_orbits_before",
    "dem_orbits_after",
    "dem_structure_learning",
)

_EXPORT_SCRIPT = "tests/demo1/optim1full/optim1full_export_spine_fence_pdp.py"
_COMPARE_SCRIPT = "tests/demo1/optim1full/optim1full_compare_spine_fence_pdp_pkl_to_mat.py"
_PLOT_TEST = "tests/demo1/optim1full/test_optim1full_plot.py"


def _pytest_k_for_plot_parity_site(site_id: str) -> str:
    """Pytest ``-k`` expression for one plot-parity site.

    Prefer the thin ``dem_atariiii_plot_*`` oracle tests. Orbits sites must not
    match legacy PARTIAL ``test_dem_orbits_*_paths_ihid_oracle`` (stale paths.mat).
    """
    key = str(site_id).strip()
    if key == "dem_orbits_before":
        return "test_dem_atariiii_plot_orbits_before_oracle"
    if key == "dem_orbits_after":
        return "test_dem_atariiii_plot_orbits_after_oracle"
    if key == "dem_structure_learning":
        return "test_dem_atariiii_plot_structure_learning_oracle"
    return key


def decide_plot_parity_heavy_steps(
    *,
    pkl_exists: bool,
    oracle_exists: bool,
    force_export: bool,
    force_refresh_oracle: bool,
    pkl_meta_ok: bool = True,
    oracle_meta_ok: bool = True,
) -> tuple[bool, bool]:
    """Return ``(do_export, do_refresh_oracle)`` under dump-once + fingerprint policy.

    Missing or mismatched sidecars invalidate reuse (``*_meta_ok=False``).
    """
    return (
        bool(force_export) or not bool(pkl_exists) or not bool(pkl_meta_ok),
        bool(force_refresh_oracle) or not bool(oracle_exists) or not bool(oracle_meta_ok),
    )

def _run(cmd: list[str]) -> int:
    print(f"[optim1full_plot_parity] $ {' '.join(cmd)}", file=sys.stderr, flush=True)
    return subprocess.call(cmd, cwd=str(_REPO))


def assert_plot_parity_authority_present(site_id: str) -> Path:
    """Return the MATLAB-owned fence authority for ``site_id``; raise if missing."""
    from tests.demo1.optim1full.optim1full_compare_spine_fence_pdp_pkl_to_mat import (
        _assert_spine_authority_mat_meta,
    )
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site
    from tests.demo1.optim1full.optim1full_plot_sites import (
        AUTHORITY_KIND_PAYLOAD,
        optim1full_plot_authority_kind,
    )

    paths = optim1full_plot_paths_for_site(site_id)
    mat_path = paths.get("authority_mat", paths["matlab_pdp_mat"])
    ctx_path = paths["plot_ctx"]
    auth_kind = optim1full_plot_authority_kind(site_id)
    # Payload sites (basin series) do not require plot_ctx for authority presence.
    if auth_kind != AUTHORITY_KIND_PAYLOAD and not ctx_path.is_file():
        raise FileNotFoundError(f"missing plot_ctx: {ctx_path}")
    if not mat_path.is_file():
        raise FileNotFoundError(
            "missing MATLAB-owned plot-fence authority "
            f"{mat_path}; regenerate via capture_optim1full_rand_ledger + "
            "RGMS_OPTIM1FULL_PLOT_FENCE_TRACE=1 (see OPTIM1FULL.md § Parity-with-plots)"
        )
    _assert_spine_authority_mat_meta(mat_path, authority_kind=auth_kind)
    return mat_path


def run_plot_parity_for_site(
    site_id: str,
    *,
    check_only: bool = False,
    force_export: bool = False,
    force_refresh_oracle: bool = False,
    resume_from: str = "auto",
    deadline_minutes: str = "240",
) -> int:
    """Honest plot-parity ladder for one fence ``site_id`` (RGB or registered non-RGB).

    Returns a process rc.
    """
    from tests.demo1.optim1full.optim1full_paths import optim1full_plot_paths_for_site

    site_id = str(site_id).strip()
    allowed = set(PLOT_PARITY_RGB_SITES) | set(PLOT_PARITY_NON_RGB_SITES)
    if site_id not in allowed:
        print(
            f"[optim1full_plot_parity] unsupported plot-parity site={site_id!r}; "
            f"allowed={sorted(allowed)}",
            file=sys.stderr,
        )
        return 2

    print(f"[optim1full_plot_parity] === site={site_id} ===", file=sys.stderr, flush=True)

    # 1. MATLAB authority present (and genuinely MATLAB-owned).
    try:
        mat_path = assert_plot_parity_authority_present(site_id)
    except FileNotFoundError as exc:
        print(f"[optim1full_plot_parity] {exc}", file=sys.stderr)
        return 2
    print(f"[optim1full_plot_parity] MATLAB authority OK: {mat_path.name}", file=sys.stderr)

    paths = optim1full_plot_paths_for_site(site_id)
    pkl_path = paths["input_pkl"]
    oracle_path = paths["oracle_mat"]
    matlab_pdp = paths["matlab_pdp_mat"]

    if check_only:
        print(
            "[optim1full_plot_parity] check-only: wiring verified "
            f"(authority={mat_path.name}, pkl_target={pkl_path.name}, "
            f"oracle_target={oracle_path.name}); heavy steps not run.",
            file=sys.stderr,
            flush=True,
        )
        return 0

    from tests.demo1.optim1full.optim1full_plot_parity_fingerprints import (
        oracle_mat_meta_ok,
        spine_pkl_meta_ok,
    )
    from tests.demo1.optim1full.optim1full_vb_dispatch import optim1full_vb_dev_optim_enabled

    vb_optim = bool(optim1full_vb_dev_optim_enabled())
    pkl_ok = spine_pkl_meta_ok(pkl_path, matlab_pdp, vb_dev_optim=vb_optim) if pkl_path.is_file() else False
    oracle_ok = oracle_mat_meta_ok(oracle_path, matlab_pdp) if oracle_path.is_file() else False

    do_export, do_refresh = decide_plot_parity_heavy_steps(
        pkl_exists=pkl_path.is_file(),
        oracle_exists=oracle_path.is_file(),
        force_export=force_export,
        force_refresh_oracle=force_refresh_oracle,
        pkl_meta_ok=pkl_ok,
        oracle_meta_ok=oracle_ok,
    )

    # 2. Export Python fence pkl — dump-once: skip if present + fingerprint OK unless forced.
    from tests.demo1.optim1full.optim1full_plot_sites import optim1full_spine_export_site_id

    export_site = optim1full_spine_export_site_id(site_id)
    if do_export:
        reason = (
            "force-export"
            if force_export
            else ("missing pkl" if not pkl_path.is_file() else "fingerprint miss")
        )
        print(
            f"[optim1full_plot_parity] export required ({reason}); "
            f"export_site={export_site}",
            file=sys.stderr,
        )
        rc = _run(
            [
                sys.executable,
                _EXPORT_SCRIPT,
                "--site",
                export_site,
                "--resume-from",
                resume_from,
                "--deadline-minutes",
                deadline_minutes,
            ]
        )
        if rc != 0:
            return rc
        if not pkl_path.is_file():
            print(
                f"[optim1full_plot_parity] export finished but missing pkl: {pkl_path}",
                file=sys.stderr,
            )
            return 2
    else:
        print(f"[optim1full_plot_parity] reuse existing pkl: {pkl_path.name}", file=sys.stderr)

    # 3. Input parity — Python fence pkl vs MATLAB-owned authority (refuse circular .mat).
    rc = _run([sys.executable, _COMPARE_SCRIPT, "--site", site_id, "--require-matlab-authority"])
    if rc != 0:
        return rc

    # 4. MATLAB oracle — dump-once: skip if present + fingerprint OK unless forced.
    if do_refresh:
        reason = (
            "force-refresh-oracle"
            if force_refresh_oracle
            else ("missing oracle" if not oracle_path.is_file() else "fingerprint miss")
        )
        print(f"[optim1full_plot_parity] refresh-oracle required ({reason})", file=sys.stderr)
        rc = _run([sys.executable, _EXPORT_SCRIPT, "--site", site_id, "--refresh-oracle"])
        if rc != 0:
            return rc
        if not oracle_path.is_file():
            print(
                f"[optim1full_plot_parity] refresh-oracle finished but missing oracle: {oracle_path}",
                file=sys.stderr,
            )
            return 2
    else:
        print(
            f"[optim1full_plot_parity] reuse existing oracle: {oracle_path.name}",
            file=sys.stderr,
        )

    # 5. Plot-fn parity — Python plot code on {matlab_pdp, pkl} vs the MATLAB oracle.
    k_expr = _pytest_k_for_plot_parity_site(site_id)
    node = f"{_PLOT_TEST} -k {k_expr}"
    rc = _run([sys.executable, "-m", "pytest", "-q", _PLOT_TEST, "-k", k_expr])
    if rc != 0:
        print(f"[optim1full_plot_parity] plot-fn parity FAILED ({node})", file=sys.stderr)
        return rc

    print(f"[optim1full_plot_parity] site={site_id} PASS", file=sys.stderr, flush=True)
    return 0


def run_plot_parity(
    sites: tuple[str, ...] | list[str] | None = None,
    *,
    check_only: bool = False,
    force_export: bool = False,
    force_refresh_oracle: bool = False,
    resume_from: str = "auto",
    deadline_minutes: str = "240",
) -> int:
    site_list = list(sites) if sites else list(PLOT_PARITY_RGB_SITES)
    for site_id in site_list:
        rc = run_plot_parity_for_site(
            site_id,
            check_only=check_only,
            force_export=force_export,
            force_refresh_oracle=force_refresh_oracle,
            resume_from=resume_from,
            deadline_minutes=deadline_minutes,
        )
        if rc != 0:
            return rc
    label = "check-only" if check_only else "full"
    print(f"[optim1full_plot_parity] ALL SITES PASS ({label}): {site_list}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--site",
        default=None,
        help=(
            "single plot-parity site_id (RGB or registered non-RGB e.g. dem_gameplay; "
            "default: all four RGB fence sites)"
        ),
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="verify wiring + MATLAB-owned authority presence only; no heavy VB/Engine runs",
    )
    p.add_argument(
        "--force-export",
        action="store_true",
        help="re-export spine input.pkl even when it already exists (after compute change)",
    )
    p.add_argument(
        "--force-refresh-oracle",
        action="store_true",
        help="re-run MATLAB 12PLOT oracle even when oracle.mat already exists",
    )
    p.add_argument("--resume-from", default="auto", help="spine export checkpoint (default auto)")
    p.add_argument("--deadline-minutes", default="240", help="export segment budget")
    args = p.parse_args(argv)

    sites = [str(args.site).strip()] if args.site else None
    return run_plot_parity(
        sites,
        check_only=bool(args.check_only),
        force_export=bool(args.force_export),
        force_refresh_oracle=bool(args.force_refresh_oracle),
        resume_from=str(args.resume_from),
        deadline_minutes=str(args.deadline_minutes),
    )


if __name__ == "__main__":
    raise SystemExit(main())
