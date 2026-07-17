#!/usr/bin/env python3
"""OPTIM1FULL — Entry **12** VB fixture re-capture from Python authority mats.

Runs MATLAB ``capture_optim1full_entry12_from_authority``: loads on-disk
``MDP_pre_active_inference`` / ``MDP_post_nr`` (``capture_optim1full_python_product_b``),
assembles call-2/3/4 RDP, counts ``K``, dumps script **1b** chain for tags
``rgms_atari_optim1full_call2`` / ``call3`` / ``call4``.

Does **not** overwrite authority MDP mats or the Model **B** ledger.
Prior Entry **12** sidecars for those tags are moved to ``fixtures/deprecated/``.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_CAPTURE_TAGS = (
    "rgms_atari_optim1full_call2",
    "rgms_atari_optim1full_call3",
    "rgms_atari_optim1full_call4",
)


def _entry12_sidecar_paths(fixtures: Path, tag: str) -> list[Path]:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        optim1full_entry12_signoff_artifact_paths,
    )

    paths = optim1full_entry12_signoff_artifact_paths(tag)
    out: list[Path] = [
        paths["rdp_mat"],
        paths["pdp_mat"],
        paths["rand_buf"],
        paths["rand_k"],
        paths["manifest"],
    ]
    for sub in ("12A", "12B", "12C", "12D", "12E", "12F", "12G", "12H", "12I"):
        out.append(fixtures / f"DEMAtariIII_entry12_{tag}_{sub}.mat")
        out.append(fixtures / f"DEMAtariIII_entry12_{tag}_{sub}.pkl")
    for suffix in ("rdp", "pdp"):
        out.append(fixtures / f"DEMAtariIII_XXX_12_{tag}_{suffix}.pkl")
    return out


def _backup_entry12_sidecars(fixtures: Path, backup_dir: Path) -> int:
    backup_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for tag in _CAPTURE_TAGS:
        for src in _entry12_sidecar_paths(fixtures, tag):
            if src.is_file():
                dst = backup_dir / src.name
                shutil.copy2(src, dst)
                n += 1
    return n


def _remove_stale_script3_pkls(fixtures: Path) -> None:
    for tag in _CAPTURE_TAGS:
        for p in _entry12_sidecar_paths(fixtures, tag):
            if p.suffix == ".pkl" and p.is_file():
                p.unlink()


def _set_matlab_optim1full_fixture_env(eng) -> None:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fix = str(optim1full_fixtures_dir().resolve())
    eng.setenv("RGMS_ENTRY12_CAPTURE_OUT_DIR", fix, nargout=0)
    eng.setenv("RGMS_OPTIM1FULL_FIXTURES_DIR", fix, nargout=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Do not copy prior Entry 12 sidecars to deprecated/",
    )
    args = parser.parse_args()

    from tests.demo1.optim1full.optim1full_authority import assert_optim1full_mdp_ledger_session
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    fixtures = optim1full_fixtures_dir()
    assert_optim1full_mdp_ledger_session(fixtures)

    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_mdp_post_nr_mat,
        optim1full_mdp_pre_active_inference_mat,
    )
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import atari_ns_concentration

    pre_mat = optim1full_mdp_pre_active_inference_mat()
    post_mat = optim1full_mdp_post_nr_mat()
    c_val = atari_c_value()
    ns = atari_ns_concentration()

    if not args.skip_backup:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_dir = fixtures / "deprecated" / f"entry12_pre_authority_recapture_{stamp}"
        n = _backup_entry12_sidecars(fixtures, backup_dir)
        print(
            f"[optim1full_capture_entry12_from_authority] backed up {n} files -> {backup_dir}",
            file=sys.stderr,
            flush=True,
        )

    _remove_stale_script3_pkls(fixtures)

    import matlab.engine

    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_entry12_rdp_authority import (
        save_all_entry12_rdp_mats_from_authority,
    )

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        _set_matlab_optim1full_fixture_env(eng)
        print("[optim1full_capture_entry12_from_authority] phase 1: RDP assembly", file=sys.stderr, flush=True)
        save_all_entry12_rdp_mats_from_authority(
            eng,
            fixtures=fixtures,
            pre_mat=pre_mat,
            post_mat=post_mat,
            c_val=c_val,
            ns=ns,
        )
        eng.cd(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        print("[optim1full_capture_entry12_from_authority] phase 2: MATLAB VB dump", file=sys.stderr, flush=True)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_entry12_from_authority');",
            nargout=0,
        )
        # Call4: re-dump with ``matlab_custom/optim1full`` fork (eight lean boundaries incl. t10/20/30).
        # Same authority RDP from phase 1 — not a separate RDP source.
        print(
            "[optim1full_capture_entry12_from_authority] phase 2b: call4 extended boundaries (optim1full fork)",
            file=sys.stderr,
            flush=True,
        )
        # cwd must be optim1full so ``which('spm_MDP_VB_XXX_entry12_dump')`` picks the fork
        eng.addpath(str(_REPO / "matlab_custom" / "entry12"), nargout=0)
        eng.cd(str(_REPO / "matlab_custom" / "optim1full"), nargout=0)
        eng.eval(
            "DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_call4_extended_boundaries');",
            nargout=0,
        )
        print(
            "[optim1full_capture_entry12_from_authority] phase 3: lean in sidecars (v7)",
            file=sys.stderr,
            flush=True,
        )
        from tests.demo1.optim1full.optim1full_rewrite_entry12_lean_sidecars import _rewrite_tags

        _rewrite_tags(eng, _CAPTURE_TAGS, fixtures)
        print(
            "[optim1full_capture_entry12_from_authority] phase 3b: call4 lean sidecars after extended dump",
            file=sys.stderr,
            flush=True,
        )
        _rewrite_tags(eng, ("rgms_atari_optim1full_call4",), fixtures)
    finally:
        eng.quit()

    print("[optim1full_capture_entry12_from_authority] done", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
