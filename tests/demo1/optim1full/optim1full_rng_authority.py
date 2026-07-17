"""OPTIM1FULL Product B — Entry 12 VB sign-off fixture checks."""

from __future__ import annotations

import os
from pathlib import Path

from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
    ENTRY12_OPTIM1FULL_CALL2_TAG,
    ENTRY12_OPTIM1FULL_CALL3_TAG,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
    ENTRY12_OPTIM1FULL_NR_G01_TAG,
    optim1full_entry12_signoff_artifact_paths,
)
from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir


def optim1full_entry12_fixture_root() -> Path:
    """OPTIM1FULL Entry **12** VB authority root."""
    return optim1full_fixtures_dir()


def _with_optim1full_fixture_root(root: Path, fn):
    old_full = os.environ.get("RGMS_OPTIM1FULL_FIXTURES_DIR")
    old_out = os.environ.get("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    root_s = str(root.resolve())
    os.environ["RGMS_OPTIM1FULL_FIXTURES_DIR"] = root_s
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = root_s
    try:
        return fn()
    finally:
        if old_full is None:
            os.environ.pop("RGMS_OPTIM1FULL_FIXTURES_DIR", None)
        else:
            os.environ["RGMS_OPTIM1FULL_FIXTURES_DIR"] = old_full
        if old_out is None:
            os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
        else:
            os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = old_out


def optim1full_entry12_subprocess_env(tag: str) -> dict[str, str]:
    """Subprocess env for OPTIM1FULL Entry **12** script **3** / audit / **4** on ``tag``."""
    fix = optim1full_entry12_fixture_root().resolve()
    env = os.environ.copy()
    env["RGMS_OPTIM1FULL_FIXTURES_DIR"] = str(fix)
    env["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = str(fix)
    env["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = str(tag).strip()

    def _paths() -> dict[str, Path]:
        return optim1full_entry12_signoff_artifact_paths(tag)

    paths = _with_optim1full_fixture_root(fix, _paths)
    env["RGMS_XXX_12_RDP_PKL_PATH"] = str(paths["rdp_pkl"].resolve())
    env["RGMS_XXX_12_PDP_PKL_PATH"] = str(paths["pdp_pkl"].resolve())
    env["RGMS_XXX_12_PDP_MAT_PATH"] = str(paths["pdp_mat"].resolve())
    env["RGMS_ATARI_RUN_XXX_12"] = "1"
    env["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = env.get("RGMS_ATARI_RUN_DEADLINE_MINUTES", "120")
    return env


def assert_entry12_vb_tag_ready(
    tag: str,
    *,
    require_script3_pkls: bool = False,
    fixtures_dir: Path | None = None,
) -> dict[str, Path]:
    """Fail fast if script **1b** chain incomplete for ``tag`` (lane paths only)."""
    root = fixtures_dir or optim1full_entry12_fixture_root()

    def _check() -> dict[str, Path]:
        paths = optim1full_entry12_signoff_artifact_paths(tag)
        need: list[Path] = [
            paths["rdp_mat"],
            paths["pdp_mat"],
            paths["rand_k"],
            paths["rand_buf"],
        ]
        if require_script3_pkls:
            need.extend([paths["rdp_pkl"], paths["pdp_pkl"]])
        missing = [p for p in need if not p.is_file()]
        if missing:
            names = "\n  ".join(str(p) for p in missing)
            raise FileNotFoundError(
                f"Entry 12 sign-off chain incomplete for tag {tag!r}.\nMissing:\n  {names}"
            )
        return paths

    return _with_optim1full_fixture_root(root, _check)


def assert_call2_game1_vb_authority() -> dict[str, Path]:
    return assert_entry12_vb_tag_ready(ENTRY12_OPTIM1FULL_CALL2_TAG)


def assert_call3_vb_authority() -> dict[str, Path]:
    return assert_entry12_vb_tag_ready(ENTRY12_OPTIM1FULL_CALL3_TAG)


def assert_call4_vb_authority() -> dict[str, Path]:
    return assert_entry12_vb_tag_ready(ENTRY12_OPTIM1FULL_CALL4_TAG)


def assert_nr_g01_vb_authority() -> dict[str, Path]:
    return assert_entry12_vb_tag_ready(ENTRY12_OPTIM1FULL_NR_G01_TAG)


def missing_entry12_vb_paths(tag: str) -> list[Path]:
    root = optim1full_entry12_fixture_root()

    def _paths() -> dict[str, Path]:
        return optim1full_entry12_signoff_artifact_paths(tag)

    paths = _with_optim1full_fixture_root(root, _paths)
    need = (paths["rdp_mat"], paths["pdp_mat"], paths["rand_k"], paths["rand_buf"])
    return [p for p in need if not p.is_file()]
