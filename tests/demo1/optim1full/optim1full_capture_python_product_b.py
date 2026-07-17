#!/usr/bin/env python3
"""OPTIM1FULL Product B — re-capture authority ``.mat`` from Python parity driver.

Writes ``MDP_pre_active_inference`` and ``MDP_post_nr`` under ``optim1full/fixtures/``
using ``run_optim1full_optim1_through_mdp_pre`` (Entries **1–11**) and
``run_dem_atariiii_optim1full_parity(stop_after_nr=True)`` (NR boundary).

Does **not** re-capture the Model **B** scalar ledger (``optim1full_dem_atari_rand_buf.mat`` /
``optim1full_rand_manifest.json``) — those bytes stay the RNG authority.

Prior MATLAB-inline mats are moved to ``fixtures/deprecated/`` before overwrite.
"""
from __future__ import annotations

import argparse
import pickle
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _backup_authority_mats(fixtures: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "DEMAtariIII_optim1full_MDP_pre_active_inference.mat",
        "DEMAtariIII_optim1full_MDP_post_nr.mat",
    ):
        src = fixtures / name
        if src.is_file():
            shutil.copy2(src, backup_dir / name)


def _write_authority_mats(
    eng: Any,
    *,
    mdp_pre: list,
    mdp_post: list | None,
    nm: int,
    ne: int,
    template_pre: Path,
    fixtures: Path,
) -> None:
    from tests.demo1.optim1full.optim1full_mdp_engine_io import (
        CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
        save_mdp_authority_v7_mat,
    )
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mdp_post_nr_mat,
        optim1full_mdp_pre_active_inference_mat,
        optim1full_mdp_pre_pkl,
        optim1full_post_nr_pkl,
    )

    pre_out = optim1full_mdp_pre_active_inference_mat()
    save_mdp_authority_v7_mat(
        eng,
        mdp_pre,
        out_path=pre_out,
        var_name="MDP_pre_active_inference",
        meta_field="metaPre",
        capture_mode=CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
        nm=nm,
        ne=ne,
        template_mat=template_pre,
        template_var="MDP_pre_active_inference",
    )
    print(f"[optim1full_capture_python] wrote {pre_out}", file=sys.stderr)

    with optim1full_mdp_pre_pkl().open("wb") as f:
        pickle.dump(
            {
                "mdp": mdp_pre,
                "nm": nm,
                "ne": ne,
                "capture": CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
                "boundary": "optim1full_entries_mdp_pre",
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    if mdp_post is None:
        return

    post_out = optim1full_mdp_post_nr_mat()
    template_post = post_out if post_out.is_file() else template_pre
    post_var = "MDP_post_nr" if template_post == post_out else "MDP_pre_active_inference"
    save_mdp_authority_v7_mat(
        eng,
        mdp_post,
        out_path=post_out,
        var_name="MDP_post_nr",
        meta_field="metaPost",
        capture_mode=CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
        nm=nm,
        ne=ne,
        template_mat=template_post,
        template_var=post_var,
    )
    print(f"[optim1full_capture_python] wrote {post_out}", file=sys.stderr)

    with optim1full_post_nr_pkl().open("wb") as f:
        pickle.dump(
            {
                "mdp": mdp_post,
                "nm": nm,
                "ne": ne,
                "capture": CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
                "boundary": "optim1full_entries_post_nr",
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


def _write_staging(
    staging_path: Path,
    *,
    mdp_pre: list,
    mdp_post: list | None,
    nm: int,
    ne: int,
    phase: str,
) -> None:
    from tests.demo1.optim1full.optim1full_mdp_engine_io import CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B

    staging_path.parent.mkdir(parents=True, exist_ok=True)
    with staging_path.open("wb") as f:
        pickle.dump(
            {
                "mdp_pre": mdp_pre,
                "mdp_post": mdp_post,
                "nm": nm,
                "ne": ne,
                "phase": phase,
                "capture": CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[optim1full_capture_python] staged {staging_path} phase={phase}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    import matlab.engine

    from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim1full_parity import (
        run_optim1full_nr_on_ctx,
        run_optim1full_optim1_through_mdp_pre,
    )
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_mdp_engine_io import (
        CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
        save_mdp_authority_v7_mat,
    )
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_fixtures_dir,
        optim1full_mdp_post_nr_mat,
        optim1full_mdp_pre_active_inference_mat,
        optim1full_mdp_pre_pkl,
        optim1full_post_nr_pkl,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import load_validated_optim1full_ledger
    from tests.demo1.optim1full.optim1full_signoff_env import optim1full_signoff_env

    p = argparse.ArgumentParser(description="OPTIM1FULL Python Product B authority capture")
    p.add_argument("--deadline-minutes", default="240")
    p.add_argument("--skip-post-nr", action="store_true", help="only capture MDP_pre")
    p.add_argument("--skip-backup", action="store_true")
    p.add_argument(
        "--save-from-staging",
        action="store_true",
        help="write .mat authority from deprecated/_optim1full_capture_staging.pkl only",
    )
    p.add_argument(
        "--resume-from-staging",
        action="store_true",
        help="NR-only from B1 staging (skip Entries 1–11 recompute)",
    )
    args = p.parse_args(argv)

    fixtures = optim1full_fixtures_dir()
    staging_path = fixtures / "deprecated" / "_optim1full_capture_staging.pkl"

    if args.resume_from_staging:
        if not staging_path.is_file():
            print(f"[optim1full_capture_python] missing staging {staging_path}", file=sys.stderr)
            return 2
        with staging_path.open("rb") as f:
            staged = pickle.load(f)
        mdp_pre = staged["mdp_pre"]
        nm = int(staged["nm"])
        ne = int(staged["ne"])
        template_pre = optim1full_mdp_pre_active_inference_mat()
        buf, manifest = load_validated_optim1full_ledger()
        t0 = time.perf_counter()
        import copy

        ctx = {
            "MDP": copy.deepcopy(mdp_pre),
            "Ne": ne,
            "MDP_pre_active_inference": mdp_pre,
        }
        with optim1full_signoff_env(deadline_minutes=str(args.deadline_minutes)):
            print(
                "[optim1full_capture_python] resume B3: NR-only from staging mdp_pre",
                file=sys.stderr,
                flush=True,
            )
            ctx = run_optim1full_nr_on_ctx(ctx, buf, manifest)
        mdp_post = ctx["MDP_post_nr"]
        _write_staging(
            staging_path,
            mdp_pre=mdp_pre,
            mdp_post=mdp_post,
            nm=nm,
            ne=ne,
            phase="mdp_post_nr",
        )
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, _REPO)
            _write_authority_mats(
                eng,
                mdp_pre=mdp_pre,
                mdp_post=mdp_post,
                nm=nm,
                ne=ne,
                template_pre=template_pre,
                fixtures=fixtures,
            )
        finally:
            eng.quit()
        wall_s = time.perf_counter() - t0
        print(
            f"[optim1full_capture_python] done resume capture={CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B} "
            f"wall_s={wall_s:.1f}",
            file=sys.stderr,
        )
        return 0

    if args.save_from_staging:
        if not staging_path.is_file():
            print(f"[optim1full_capture_python] missing staging {staging_path}", file=sys.stderr)
            return 2
        with staging_path.open("rb") as f:
            staged = pickle.load(f)
        mdp_pre = staged["mdp_pre"]
        mdp_post = staged.get("mdp_post")
        nm = int(staged["nm"])
        ne = int(staged["ne"])
        template_pre = optim1full_mdp_pre_active_inference_mat()
        if not template_pre.is_file():
            print(f"[optim1full_capture_python] missing template {template_pre}", file=sys.stderr)
            return 2
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, _REPO)
            _write_authority_mats(
                eng,
                mdp_pre=mdp_pre,
                mdp_post=mdp_post,
                nm=nm,
                ne=ne,
                template_pre=template_pre,
                fixtures=fixtures,
            )
        finally:
            eng.quit()
        print("[optim1full_capture_python] save-from-staging done", file=sys.stderr)
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = fixtures / "deprecated" / f"matlab_inline_capture_{stamp}"
    if not args.skip_backup:
        _backup_authority_mats(fixtures, backup_dir)
        print(f"[optim1full_capture_python] backed up prior mats -> {backup_dir}", file=sys.stderr)

    buf, manifest = load_validated_optim1full_ledger()
    template_pre = optim1full_mdp_pre_active_inference_mat()
    if not template_pre.is_file():
        print(f"[optim1full_capture_python] missing template {template_pre}", file=sys.stderr)
        return 2

    t0 = time.perf_counter()
    with optim1full_signoff_env(deadline_minutes=str(args.deadline_minutes)):
        if args.skip_post_nr:
            print(
                "[optim1full_capture_python] Entries 1–11 -> MDP_pre only",
                file=sys.stderr,
                flush=True,
            )
            ctx = run_optim1full_optim1_through_mdp_pre(
                buf,
                manifest,
                deadline_minutes=str(args.deadline_minutes),
            )
            mdp_pre = ctx["MDP_pre_active_inference"]
            mdp_post = None
        else:
            print(
                "[optim1full_capture_python] B1 Entries 1–11 -> MDP_pre; then B3 NR -> MDP_post_nr",
                file=sys.stderr,
                flush=True,
            )
            ctx = run_optim1full_optim1_through_mdp_pre(
                buf,
                manifest,
                deadline_minutes=str(args.deadline_minutes),
            )
            mdp_pre = ctx["MDP_pre_active_inference"]
            nm = len(mdp_pre)
            ne = int(ctx["Ne"])
            _write_staging(
                staging_path,
                mdp_pre=mdp_pre,
                mdp_post=None,
                nm=nm,
                ne=ne,
                phase="mdp_pre",
            )
            eng_b2 = matlab.engine.start_matlab()
            try:
                configure_dem_matlab_engine(eng_b2, _REPO)
                _write_authority_mats(
                    eng_b2,
                    mdp_pre=mdp_pre,
                    mdp_post=None,
                    nm=nm,
                    ne=ne,
                    template_pre=template_pre,
                    fixtures=fixtures,
                )
            finally:
                eng_b2.quit()
            print(
                "[optim1full_capture_python] B1/B2 done — run persistence-audit before NR on failure",
                file=sys.stderr,
                flush=True,
            )
            ctx = run_optim1full_nr_on_ctx(ctx, buf, manifest)
            mdp_post = ctx["MDP_post_nr"]
        nm = len(mdp_pre)
        ne = int(ctx["Ne"])

    if args.skip_post_nr:
        _write_staging(
            staging_path,
            mdp_pre=mdp_pre,
            mdp_post=mdp_post,
            nm=nm,
            ne=ne,
            phase="mdp_pre",
        )
    else:
        _write_staging(
            staging_path,
            mdp_pre=mdp_pre,
            mdp_post=mdp_post,
            nm=nm,
            ne=ne,
            phase="mdp_post_nr",
        )

    if args.skip_post_nr:
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, _REPO)
            _write_authority_mats(
                eng,
                mdp_pre=mdp_pre,
                mdp_post=mdp_post,
                nm=nm,
                ne=ne,
                template_pre=template_pre,
                fixtures=fixtures,
            )
        finally:
            eng.quit()
    elif mdp_post is not None:
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, _REPO)
            _write_authority_mats(
                eng,
                mdp_pre=mdp_pre,
                mdp_post=mdp_post,
                nm=nm,
                ne=ne,
                template_pre=template_pre,
                fixtures=fixtures,
            )
        finally:
            eng.quit()

    wall_s = time.perf_counter() - t0
    print(
        f"[optim1full_capture_python] done capture={CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B} "
        f"wall_s={wall_s:.1f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
