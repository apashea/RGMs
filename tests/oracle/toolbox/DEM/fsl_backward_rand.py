"""FSL backward ledger RNG helpers (not Entry 12 ``vb_rand_buf``)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np

_RAND_PATCH_TARGETS = (
    "numpy.random.rand",
    "python_src.toolbox.DEM.spm_MDP_generate.np.random.rand",
    "python_src.toolbox.DEM.spm_MDP_pong.np.random.rand",
)


def fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def default_rand_buf_mat() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_RAND_BUF_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return fixtures_dir() / "dem_atari_rand_buf_through_entry11.mat"


def load_dem_atari_rand_buf() -> tuple[np.ndarray, int]:
    from scipy.io import loadmat

    p = default_rand_buf_mat()
    if not p.is_file():
        raise FileNotFoundError(f"missing FSL backward 1b fixture: {p}")
    raw = loadmat(str(p))
    if "dem_atari_rand_buf" not in raw:
        keys = sorted(k for k in raw if not str(k).startswith("__"))
        raise KeyError(f"expected dem_atari_rand_buf in {p}, keys={keys}")
    buf = np.asarray(raw["dem_atari_rand_buf"], dtype=np.float64).ravel()
    k_11 = int(np.asarray(raw.get("K_11", [[buf.size]]), dtype=np.float64).reshape(-1)[0])
    return buf, k_11


def entry1_k_py_mat() -> Path:
    return fixtures_dir() / "fsl_backward_entry1_K_py.mat"


def load_entry1_k_py() -> int:
    from scipy.io import loadmat

    p = entry1_k_py_mat()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing Entry 1 preflight K fixture: {p} — run fsl_backward_preflight_rand_k_entry1.py"
        )
    raw = loadmat(str(p))
    return int(np.asarray(raw["K_py"], dtype=np.float64).reshape(-1)[0])


@contextmanager
def fsl_entry1_driver_env(*, deadline_minutes: str = "5") -> Iterator[None]:
    """Entry 1 ledger env (deadline only)."""
    old: dict[str, str | None] = {}
    keys = (
        "RGMS_ATARI_RUN_DEADLINE_MINUTES",
        "RGMS_ATARI_RUN_DEADLINE_MONO",
    )
    for k in keys:
        old[k] = os.environ.get(k)
    os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = deadline_minutes
    os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MONO", None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def entry2_k_py_mat() -> Path:
    return fixtures_dir() / "fsl_backward_entry2_K_py.mat"


def load_entry2_k_py() -> int:
    from scipy.io import loadmat

    p = entry2_k_py_mat()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing Entry 2 preflight K fixture: {p} — run fsl_backward_preflight_rand_k_entry2.py"
        )
    raw = loadmat(str(p))
    return int(np.asarray(raw["K_py"], dtype=np.float64).reshape(-1)[0])


@contextmanager
def fsl_entry2_driver_env(*, deadline_minutes: str = "15") -> Iterator[None]:
    """Entry 1–2 ledger env (deadline only; no ``training_t`` / ``outer``)."""
    old: dict[str, str | None] = {}
    keys = (
        "RGMS_ATARI_RUN_DEADLINE_MINUTES",
        "RGMS_ATARI_RUN_DEADLINE_MONO",
    )
    for k in keys:
        old[k] = os.environ.get(k)
    os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = deadline_minutes
    os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MONO", None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def entry3_k_py_mat() -> Path:
    return fixtures_dir() / "fsl_backward_entry3_K_py.mat"


def load_entry3_k_py() -> int:
    from scipy.io import loadmat

    p = entry3_k_py_mat()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing Entry 3 preflight K fixture: {p} — run fsl_backward_preflight_rand_k_entry3.py"
        )
    raw = loadmat(str(p))
    return int(np.asarray(raw["K_py"], dtype=np.float64).reshape(-1)[0])


@contextmanager
def fsl_entry3_driver_env(*, deadline_minutes: str = "45") -> Iterator[None]:
    """Entry 1–3 ledger env (``training_t=10000`` only; no Entry 8 ``outer``)."""
    old: dict[str, str | None] = {}
    keys = (
        "RGMS_ATARI_TRAINING_T",
        "RGMS_ATARI_RUN_DEADLINE_MINUTES",
        "RGMS_ATARI_RUN_DEADLINE_MONO",
    )
    for k in keys:
        old[k] = os.environ.get(k)
    os.environ["RGMS_ATARI_TRAINING_T"] = "10000"
    os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = deadline_minutes
    os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MONO", None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextmanager
def fsl_entry11_driver_env(*, deadline_minutes: str = "60") -> Iterator[None]:
    """Full-scale FSL driver env (``outer=128``, ``training_t=10000``) + wall limit."""
    old: dict[str, str | None] = {}
    keys = (
        "RGMS_ATARI_ENTRY8_OUTER",
        "RGMS_ATARI_TRAINING_T",
        "RGMS_ATARI_RUN_DEADLINE_MINUTES",
        "RGMS_ATARI_RUN_DEADLINE_MONO",
    )
    for k in keys:
        old[k] = os.environ.get(k)
    os.environ["RGMS_ATARI_ENTRY8_OUTER"] = "128"
    os.environ["RGMS_ATARI_TRAINING_T"] = "10000"
    os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = deadline_minutes
    os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MONO", None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextmanager
def fsl_backward_replay_matlab_draws(k_use: int, buf: np.ndarray) -> Iterator[list[int]]:
    """Replay ``buf[:k_use]`` through scalar ``np.random.rand`` on the FSL ledger path."""
    from unittest.mock import patch

    seq = np.asarray(buf, dtype=np.float64).ravel()
    if k_use > seq.size:
        raise ValueError(f"replay needs K_11={k_use} draws but buffer has {seq.size}")
    ctr = [0]

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("FSL backward replay: only scalar np.random.rand() supported")
        if ctr[0] >= k_use:
            raise RuntimeError(
                f"FSL backward replay: exhausted {k_use} draws at index {ctr[0]}"
            )
        v = float(seq[ctr[0]])
        ctr[0] += 1
        return v

    patches = [patch(t, side_effect=shim) for t in _RAND_PATCH_TARGETS]
    try:
        for p in patches:
            p.start()
        yield ctr
    finally:
        for p in reversed(patches):
            p.stop()


@contextmanager
def fsl_backward_count_native_draws() -> Iterator[list[int]]:
    """Count scalar ``np.random.rand()`` during the wrapped block (FSL backward 1a)."""
    from unittest.mock import patch

    ctr = [0]
    real_rand = np.random.rand

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("FSL backward 1a: only scalar np.random.rand() supported")
        ctr[0] += 1
        return float(real_rand())

    patches = [patch(t, side_effect=shim) for t in _RAND_PATCH_TARGETS]
    try:
        for p in patches:
            p.start()
        yield ctr
    finally:
        for p in reversed(patches):
            p.stop()
