"""DEMO1 shipped fixture environment — greenfield user contract."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from tests.demo1.demo1_paths import demo1_shipped_fixtures_dir

_FIXTURE_ENV_KEYS = ("RGMS_DEMO1_FIXTURES_DIR", "RGMS_ENTRY12_CAPTURE_OUT_DIR")


def apply_shipped_fixture_env(*, repo_fixtures: Path | None = None) -> Path:
    """
    Set env vars so all DEMO1 parity code uses the shipped fixture root.

    Default: ``<repo>/tests/demo1/fixtures`` (gitignored; empty on fresh clone).
    """
    fix = (repo_fixtures or demo1_shipped_fixtures_dir()).resolve()
    fix.mkdir(parents=True, exist_ok=True)
    os.environ["RGMS_DEMO1_FIXTURES_DIR"] = str(fix)
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = str(fix)
    return fix


def clear_fixture_env() -> None:
    for key in _FIXTURE_ENV_KEYS:
        os.environ.pop(key, None)


@contextmanager
def shipped_fixture_env(fixtures_dir: Path | None = None) -> Iterator[Path]:
    """Temporarily apply shipped fixture env (restores prior env on exit)."""
    saved = {k: os.environ.get(k) for k in _FIXTURE_ENV_KEYS}
    try:
        fix = apply_shipped_fixture_env(repo_fixtures=fixtures_dir)
        yield fix
    finally:
        for key, val in saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


def assert_under_fixture_root(path: Path, fixture_root: Path) -> None:
    """Fail fast if ``path`` resolves outside the active DEMO1 fixture root."""
    root = fixture_root.resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise AssertionError(f"path {path} is outside DEMO1 fixture root {root}") from exc
