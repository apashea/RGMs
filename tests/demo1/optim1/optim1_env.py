"""OPTIM1 environment — DEMO1 authority read-only; OPTIM1 checkpoints writable."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from tests.demo1.demo1_env import apply_shipped_fixture_env
from tests.demo1.optim1.optim1_paths import optim1_shipped_fixtures_dir

_OPTIM1_FIXTURE_ENV = "RGMS_OPTIM1_FIXTURES_DIR"


def apply_optim1_env(
    *,
    demo1_fixtures: Path | None = None,
    optim1_fixtures: Path | None = None,
) -> tuple[Path, Path]:
    """
    Set env for OPTIM1 parity:

    - ``RGMS_DEMO1_FIXTURES_DIR`` / ``RGMS_ENTRY12_CAPTURE_OUT_DIR`` → DEMO1 authority
    - ``RGMS_OPTIM1_FIXTURES_DIR`` → OPTIM1-owned checkpoints
    """
    demo = apply_shipped_fixture_env(repo_fixtures=demo1_fixtures)
    opt = (optim1_fixtures or optim1_shipped_fixtures_dir()).resolve()
    opt.mkdir(parents=True, exist_ok=True)
    os.environ[_OPTIM1_FIXTURE_ENV] = str(opt)
    os.environ["RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS"] = "1"
    return demo, opt


@contextmanager
def optim1_env(
    *,
    demo1_fixtures: Path | None = None,
    optim1_fixtures: Path | None = None,
) -> Iterator[tuple[Path, Path]]:
    saved_demo = {
        k: os.environ.get(k)
        for k in (
            "RGMS_DEMO1_FIXTURES_DIR",
            "RGMS_ENTRY12_CAPTURE_OUT_DIR",
            "RGMS_FSL_BACKWARD_REPLAY_MATLAB_DRAWS",
            _OPTIM1_FIXTURE_ENV,
        )
    }
    try:
        paths = apply_optim1_env(
            demo1_fixtures=demo1_fixtures,
            optim1_fixtures=optim1_fixtures,
        )
        yield paths
    finally:
        for key, val in saved_demo.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
