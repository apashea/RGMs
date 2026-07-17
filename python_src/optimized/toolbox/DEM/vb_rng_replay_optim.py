"""W2 Phase 5-S-1 — optim-owned ``vb_rand_buf`` replay."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM import vb_instrumentation_optim as _inst


def vb_load_matlab_rand_buf(path: Path | None = None) -> np.ndarray:
    if path is not None:
        from scipy.io import loadmat

        if not path.is_file():
            raise FileNotFoundError(
                f"MATLAB VB rand buffer not found: {path}\n"
                "Run Entry 12 MATLAB dump (after entry12_preflight_vb_rand_k.py) to create it."
            )
        raw = loadmat(str(path))
        if "vb_rand_buf" not in raw:
            keys = sorted(k for k in raw if not k.startswith("__"))
            raise KeyError(f"expected vb_rand_buf in {path}, got keys={keys}")
        return np.asarray(raw["vb_rand_buf"], dtype=np.float64).ravel(order="F")
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_load_vb_rand_buf_for_tag

    return entry12_load_vb_rand_buf_for_tag()


class VbMatlabRandReplay:
    """Replay MATLAB ``rand(K,1)`` scalars through ``numpy.random.rand`` for ``_spm_sample``."""

    __slots__ = ("_it", "_orig")

    def __init__(self, buf: np.ndarray) -> None:
        data = np.asarray(buf, dtype=np.float64).ravel(order="F").tolist()
        self._it = iter(data)
        self._orig = np.random.rand

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError(
                "spm_MDP_VB_XXX reuse_matlab_draws: only scalar np.random.rand() is supported"
            )
        try:
            return float(next(self._it))
        except StopIteration as e:
            raise RuntimeError(
                "spm_MDP_VB_XXX reuse_matlab_draws: exhausted MATLAB vb_rand_buf "
                "(Python drew more scalars than MATLAB; refresh K preflight and dump)"
            ) from e

    def __enter__(self) -> _VbMatlabRandReplay:
        global _VB_RAND_REPLAY_ITER, _VB_RAND_REPLAY_ORIG_RAND
        _VB_RAND_REPLAY_ITER = self._it
        _VB_RAND_REPLAY_ORIG_RAND = self._orig
        np.random.rand = self._shim  # type: ignore[method-assign]
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        global _VB_RAND_REPLAY_ITER, _VB_RAND_REPLAY_ORIG_RAND
        np.random.rand = self._orig  # type: ignore[method-assign]
        _VB_RAND_REPLAY_ITER = None
        _VB_RAND_REPLAY_ORIG_RAND = None
        if exc_type is not None:
            return
        try:
            next(self._it)
        except StopIteration:
            return
        raise RuntimeError(
            "spm_MDP_VB_XXX reuse_matlab_draws: unused draws remain in vb_rand_buf "
            "(Python drew fewer scalars than MATLAB; K preflight / OPTIONS mismatch)"
        )
