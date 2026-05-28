#!/usr/bin/env python3
"""Entry 12 quad-tag process sign-off: script **3** → draw audit → full coerced script **4**.

Does **not** run MATLAB **1a**/**1b**. Requires paired fixtures on disk for each tag.

Per tag (``ENTRY12_ATARI_VB_TAGS``):

1. ``pytest`` ``test_DEM_AtariIII_XXX_12.py::test_xxx_12_fsl_rdp_to_pdp_pkl`` (``RGMS_ATARI_RUN_XXX_12=1``)
2. Refresh manifest **script 3** pickle checksums (``entry12_refresh_manifest_script3_checksums``)
3. ``matlab_custom/entry12_draw_index_audit.py`` (``unused_draws=0``, ``sample_calls_match``)
4. ``XXX_12_compare_pdp_pkl_to_mat.py`` with ``--coerce-sparse-to-dense-for-compare`` (full Validation **12**)

Set ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` per tag. Exit **0** only if all tags pass.

See ``Atari_example.md`` § Entry 12 workflow.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_src.toolbox.DEM.entry12_atari_calls import (  # noqa: E402
    ENTRY12_ATARI_VB_TAGS,
    ENTRY12_SIGNOFF_MANIFEST_SCHEMA,
    entry12_assert_draw_audit_summary,
    entry12_assert_signoff_chain_ready,
    entry12_load_signoff_manifest,
    entry12_refresh_manifest_script3_checksums,
    entry12_upgrade_manifest_schema2_mat_only,
)


def _repo_root() -> Path:
    return _ROOT


def _run(cmd: list[str], *, env: dict[str, str], label: str) -> None:
    print(f"[entry12 quad] {label}: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=str(_repo_root()), env=env, check=True)


def _env_for_tag(tag: str, base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    env["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = tag
    return env


def _prepare_manifest(tag: str, *, upgrade_mat: bool) -> None:
    try:
        m = entry12_load_signoff_manifest(tag)
    except FileNotFoundError:
        raise SystemExit(
            f"[entry12 quad] tag={tag!r}: missing manifest. Run script 1b on this tag first."
        ) from None
    schema = int(m.get("manifest_schema", 1))
    if schema < ENTRY12_SIGNOFF_MANIFEST_SCHEMA:
        if not upgrade_mat:
            raise SystemExit(
                f"[entry12 quad] tag={tag!r}: manifest schema {schema} "
                f"(need {ENTRY12_SIGNOFF_MANIFEST_SCHEMA}). "
                "Re-run 1b or pass --upgrade-manifest-mat."
            )
        entry12_upgrade_manifest_schema2_mat_only(tag)


def _run_tag(tag: str, *, base_env: dict[str, str], skip_draw_audit: bool) -> None:
    env = _env_for_tag(tag, base_env)
    py = sys.executable
    repo = _repo_root()

    entry12_assert_signoff_chain_ready(tag, require_script3_pkls=False)

    _run(
        [
            py,
            "-m",
            "pytest",
            "tests/oracle/toolbox/DEM/test_DEM_AtariIII_XXX_12.py::test_xxx_12_fsl_rdp_to_pdp_pkl",
            "-q",
        ],
        env={**env, "RGMS_ATARI_RUN_XXX_12": "1"},
        label=f"script 3 tag={tag}",
    )

    entry12_refresh_manifest_script3_checksums(tag)
    entry12_assert_signoff_chain_ready(tag, require_script3_pkls=True)

    if not skip_draw_audit:
        _run(
            [py, str(repo / "matlab_custom" / "entry12_draw_index_audit.py")],
            env=env,
            label=f"draw audit tag={tag}",
        )
        entry12_assert_draw_audit_summary()

    _run(
        [
            py,
            str(repo / "tests" / "oracle" / "toolbox" / "DEM" / "XXX_12_compare_pdp_pkl_to_mat.py"),
            "--coerce-sparse-to-dense-for-compare",
        ],
        env=env,
        label=f"script 4 tag={tag}",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Entry 12 quad-tag 3→audit→4 sign-off runner")
    p.add_argument(
        "--tags",
        nargs="*",
        default=list(ENTRY12_ATARI_VB_TAGS),
        help=f"Tags to run (default: all {ENTRY12_ATARI_VB_TAGS})",
    )
    p.add_argument(
        "--skip-draw-audit",
        action="store_true",
        help="Skip draw-index audit (not recommended for sign-off)",
    )
    p.add_argument(
        "--upgrade-manifest-mat",
        action="store_true",
        help=(
            "Upgrade schema-1 manifests: hash 12A–12I .mat from disk without MATLAB 1b "
            "(use when .mat fixtures are current but manifest predates schema 2)"
        ),
    )
    args = p.parse_args(argv)
    base_env = dict(os.environ)
    tags = [str(t).strip() for t in args.tags if str(t).strip()]
    failed: list[str] = []
    for tag in tags:
        print(f"\n[entry12 quad] ===== tag {tag!r} =====\n", flush=True)
        try:
            _prepare_manifest(tag, upgrade_mat=bool(args.upgrade_manifest_mat))
            _run_tag(tag, base_env=base_env, skip_draw_audit=bool(args.skip_draw_audit))
            print(f"[entry12 quad] PASS tag={tag!r}", flush=True)
        except (subprocess.CalledProcessError, SystemExit, FileNotFoundError, ValueError) as exc:
            print(f"[entry12 quad] FAIL tag={tag!r}: {exc}", file=sys.stderr, flush=True)
            failed.append(tag)
    if failed:
        print(f"[entry12 quad] failed tags: {failed}", file=sys.stderr, flush=True)
        return 1
    print("[entry12 quad] all tags PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
