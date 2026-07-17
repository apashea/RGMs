"""OPTIM1FULL Product B — full-script scalar RNG ledger (Model B, § **11.7.2**).

Ledger contract
---------------
MATLAB capture logs **scalar** ``rand()`` only (``fsl_backward/rand.m``), matching FSL
backward. ``randperm`` inside MATLAB ``spm_sample`` is **not** logged as a separate API;
it advances the same twister via internal ``rand()`` calls that are **not** intercepted
by the shadow.

Python replay patches ``np.random.rand`` and ``spm_MDP_VB_XXX._spm_sample`` implements
MATLAB ``randperm(k,1)`` stream alignment by consuming one or two **buffered** scalar
draws on logical branches (see ``notes/andrew Python Matlab Translation Issues.md``,
RNG subsection). Numeric ``spm_sample`` uses one buffered draw per call.

Parity therefore requires: (1) ledger segments index the MATLAB inline capture path;
(2) Python uses the same ``_spm_sample`` branch/draw-count rules; (3) sign-off env pins
``NR=32``, ``NT=256``, ``NS=256`` (``optim1full_signoff_env``).
"""

from __future__ import annotations

import copy
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import numpy as np

_LEDGER_PROTOCOL = "optim1full_scalar_rand_log_v1"


def _entries_rand_patch_targets() -> tuple[str, ...]:
    """``entries_1_11`` — same scalar patch set as OPTIM1 Product **B** (#3)."""
    from tests.demo1.optim1full.optim1full_replay_rand_optim1full import (
        optim1full_rand_patch_targets,
    )

    return optim1full_rand_patch_targets()


def _optim1full_rand_patch_targets() -> tuple[str, ...]:
    """FSL + OPTIM1 Product B targets plus VB for post–Entries-12 segments."""
    from tests.demo1.optim1full.optim1full_replay_rand_optim1full import (
        optim1full_rand_patch_targets,
    )

    return optim1full_rand_patch_targets() + (
        "python_src.toolbox.DEM.spm_MDP_VB_XXX.np.random.rand",
    )


_RAND_PATCH_TARGETS = _optim1full_rand_patch_targets()


@dataclass(frozen=True)
class Optim1fullRandSegment:
    id: str
    start: int
    k: int

    @property
    def end(self) -> int:
        return self.start + self.k


@dataclass(frozen=True)
class Optim1fullRandManifest:
    protocol: str
    rng_seed: int
    plotting: str
    segments: tuple[Optim1fullRandSegment, ...]
    k_total: int

    def segment(self, seg_id: str) -> Optim1fullRandSegment:
        for seg in self.segments:
            if seg.id == seg_id:
                return seg
        known = ", ".join(s.id for s in self.segments)
        raise KeyError(f"manifest segment {seg_id!r} not found (known: {known})")


def optim1full_rand_ledger_mat() -> Path:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    raw = str(os.getenv("RGMS_OPTIM1FULL_RAND_LEDGER_MAT", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim1full_fixtures_dir() / "optim1full_dem_atari_rand_buf.mat"


def optim1full_rand_manifest_json() -> Path:
    from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

    raw = str(os.getenv("RGMS_OPTIM1FULL_RAND_MANIFEST_JSON", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim1full_fixtures_dir() / "optim1full_rand_manifest.json"


def ledger_artifacts_present() -> bool:
    return optim1full_rand_ledger_mat().is_file() and optim1full_rand_manifest_json().is_file()


def load_optim1full_rand_buf() -> tuple[np.ndarray, int]:
    from scipy.io import loadmat

    p = optim1full_rand_ledger_mat()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing OPTIM1FULL ledger: {p} — run optim1full_capture_rand_ledger.py once (OPTIM1.md § 11.7.2)"
        )
    raw = loadmat(str(p))
    if "dem_atari_rand_buf" not in raw:
        keys = sorted(k for k in raw if not str(k).startswith("__"))
        raise KeyError(f"expected dem_atari_rand_buf in {p}, keys={keys}")
    buf = np.asarray(raw["dem_atari_rand_buf"], dtype=np.float64).ravel()
    k_total = int(np.asarray(raw.get("K_total", [[buf.size]]), dtype=np.float64).reshape(-1)[0])
    return buf, k_total


def _parse_segment(raw: dict[str, Any]) -> Optim1fullRandSegment:
    return Optim1fullRandSegment(
        id=str(raw["id"]),
        start=int(raw["start"]),
        k=int(raw["k"]),
    )


def load_optim1full_rand_manifest() -> Optim1fullRandManifest:
    p = optim1full_rand_manifest_json()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing OPTIM1FULL manifest: {p} — run optim1full_capture_rand_ledger.py once (OPTIM1.md § 11.7.2)"
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    segs = tuple(_parse_segment(s) for s in data["segments"])
    k_total = int(data.get("k_total", sum(s.k for s in segs)))
    return Optim1fullRandManifest(
        protocol=str(data.get("protocol", _LEDGER_PROTOCOL)),
        rng_seed=int(data.get("rng_seed", 2)),
        plotting=str(data.get("plotting", "omitted")),
        segments=segs,
        k_total=k_total,
    )


def validate_ledger_manifest(buf: np.ndarray, manifest: Optim1fullRandManifest) -> None:
    if manifest.protocol != _LEDGER_PROTOCOL:
        raise ValueError(
            f"unsupported ledger protocol {manifest.protocol!r} (expected {_LEDGER_PROTOCOL})"
        )
    if manifest.k_total != int(buf.size):
        raise ValueError(
            f"ledger K_total={manifest.k_total} but buffer has {int(buf.size)} draws"
        )
    seg_sum = sum(s.k for s in manifest.segments)
    if seg_sum != manifest.k_total:
        raise ValueError(
            f"manifest segment k sum={seg_sum} != K_total={manifest.k_total}"
        )
    cursor = 0
    for seg in manifest.segments:
        if seg.start != cursor:
            raise ValueError(
                f"manifest segment {seg.id!r} start={seg.start} != expected cursor {cursor}"
            )
        cursor = seg.end
    if cursor != manifest.k_total:
        raise ValueError(f"manifest segments end at {cursor}, K_total={manifest.k_total}")


def load_validated_optim1full_ledger() -> tuple[np.ndarray, Optim1fullRandManifest]:
    buf, k_total = load_optim1full_rand_buf()
    manifest = load_optim1full_rand_manifest()
    if manifest.k_total != k_total:
        raise ValueError(f"mat K_total={k_total} != manifest.k_total={manifest.k_total}")
    validate_ledger_manifest(buf, manifest)
    return buf, manifest


@contextmanager
def optim1full_replay_matlab_draws(
    buf: np.ndarray,
    *,
    k_use: int | None = None,
    start_index: int = 0,
    entries_11: bool = False,
) -> Iterator[list[int]]:
    """
    Replay ``buf[start_index : start_index + k_use]`` through scalar ``np.random.rand``.

    ``entries_11=True``: OPTIM1 Product **B** patch targets only (``entries_1_11`` segment).
    Default ``k_use`` replays through end of buffer from ``start_index``.
  """
    from unittest.mock import patch

    targets = _entries_rand_patch_targets() if entries_11 else _RAND_PATCH_TARGETS

    seq = np.asarray(buf, dtype=np.float64).ravel()
    i0 = int(start_index)
    if k_use is None:
        k_use = int(seq.size) - i0
    k_use = int(k_use)
    if i0 < 0 or k_use < 0 or i0 + k_use > seq.size:
        raise ValueError(
            f"replay slice [{i0}, {i0 + k_use}) invalid for buffer length {seq.size}"
        )
    ctr = [0]

    def shim(*args: Any, **kwargs: Any) -> float:
        if args or kwargs:
            raise RuntimeError("OPTIM1FULL ledger replay: only scalar np.random.rand() supported")
        if ctr[0] >= k_use:
            raise RuntimeError(
                f"OPTIM1FULL ledger replay: exhausted {k_use} draws at index {ctr[0]} "
                f"(global index {i0 + ctr[0]})"
            )
        v = float(seq[i0 + ctr[0]])
        ctr[0] += 1
        return v

    patches = [patch(t, side_effect=shim) for t in targets]
    try:
        for p in patches:
            p.start()
        yield ctr
    finally:
        for p in reversed(patches):
            p.stop()


@contextmanager
def optim1full_full_script_replay() -> Iterator[list[int]]:
    """
    Model **B** — replay the full OPTIM1FULL ledger from index **0** through ``K_total``.

    Raises if ``draws_consumed != K_total`` on exit.
    """
    buf, manifest = load_validated_optim1full_ledger()
    with optim1full_replay_matlab_draws(buf, k_use=manifest.k_total, start_index=0) as ctr:
        yield ctr
    draws = int(ctr[0])
    if draws != manifest.k_total:
        raise RuntimeError(
            f"OPTIM1FULL ledger audit: consumed {draws} draws, expected K_total={manifest.k_total}"
        )


def assert_optim1full_ledger_ready() -> tuple[np.ndarray, Optim1fullRandManifest]:
    """Fail fast when Model **B** artifacts are missing or inconsistent."""
    return load_validated_optim1full_ledger()


def optim1full_nr_game_segment_id(game: int) -> str:
    g = int(game)
    if g < 1 or g > 32:
        raise ValueError(f"NR game index must be 1..32, got {g}")
    return f"nr_game_{g:02d}"


def optim1full_vb_kwargs_for_ledger_segment(
    buf: np.ndarray,
    *,
    start: int,
    k: int,
) -> dict[str, Any]:
    """VB kwargs marker: replay ``buf[start:start+k]`` via ``reuse_matlab_draws`` (Phase C lane)."""
    return {
        "_optim1full_ledger_segment": {
            "buf": np.asarray(buf, dtype=np.float64).ravel(),
            "start": int(start),
            "k": int(k),
        }
    }


def optim1full_rdp_for_vb_from_ledger_assembly(rdp: dict[str, Any]) -> dict[str, Any]:
    """
    Script **3**-style VB input for Model **B** live NR assembly.

    Mirrors ``load_entry12_rdp_mat_nested_for_tag``: ``restore_entry12_call2_gp_dtypes``
  then ``entry12_rdp_for_vb_from_mat_nested`` (``uint8``→``logical`` on ``RDP.MDP.GA``…).
    """
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import restore_entry12_call2_gp_dtypes

    rdp_work = copy.deepcopy(rdp)
    if isinstance(rdp_work, dict) and isinstance(rdp_work.get("MDP"), dict):
        restore_entry12_call2_gp_dtypes(rdp_work)
    return entry12_rdp_for_vb_from_mat_nested(rdp_work)


def optim1full_vb_kwargs_provider_for_ledger_nr_loop(
    buf: np.ndarray,
    manifest: Optim1fullRandManifest,
) -> Any:
    """Per-game provider for ``active_inference_nr_loop`` (tier **3g** / full-replay NR)."""

    def _provider(game: int) -> dict[str, Any]:
        seg = manifest.segment(optim1full_nr_game_segment_id(game))
        return optim1full_vb_kwargs_for_ledger_segment(buf, start=seg.start, k=seg.k)

    return _provider


def spm_mdp_vb_xxx_with_ledger_segment_reuse(
    rdp: object,
    buf: np.ndarray,
    *,
    start: int,
    k: int,
    options: Any | None = None,
    extra_vb_kwargs: dict[str, Any] | None = None,
    vb_lane: str = "dispatch",
) -> Any:
    """
    ``spm_MDP_VB_XXX`` with ledger segment replay through Entry **12** ``reuse_matlab_draws``.

    Matches Phase C / MATLAB FSL shadow scalar count (``k`` draws), not external
    ``optim1full_replay_matlab_draws`` (which patches every ``np.random.rand`` call).

    ``vb_lane``: ``dispatch`` (env ``RGMS_OPTIM1FULL_VB_DEV_OPTIM``), ``fidelity``, or ``optim``.
    """
    from unittest.mock import patch

    from python_src.toolbox.DEM.entry12_atari_calls import entry12_vb_oracle_flags
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        spm_mdp_vb_xxx_callable,
        spm_mdp_vb_xxx_rand_buf_patch_target,
        spm_mdp_vb_xxx_timing_module,
    )

    segment = np.asarray(buf, dtype=np.float64).ravel()[int(start) : int(start) + int(k)].copy()
    flags = entry12_vb_oracle_flags(reuse_matlab_draws=True)
    flags["dump_subentries"] = False
    if extra_vb_kwargs:
        flags.update(extra_vb_kwargs)
    if not isinstance(rdp, dict):
        raise TypeError(f"ledger segment VB expects dict RDP, got {type(rdp).__name__}")
    rdp_vb = optim1full_rdp_for_vb_from_ledger_assembly(rdp)
    vb_fn = spm_mdp_vb_xxx_callable(vb_lane)  # type: ignore[arg-type]
    _spm_vb_mod = spm_mdp_vb_xxx_timing_module(vb_lane)  # type: ignore[arg-type]
    patch_target = spm_mdp_vb_xxx_rand_buf_patch_target(vb_lane)  # type: ignore[arg-type]
    # Stale depth after a prior unused-draw exit skips rand_replay setup (§ Phase B).
    _spm_vb_mod._VB_TIMING_DEPTH = 0

    # Both lanes assert exact segment consumption (consumed == k): drawing fewer
    # scalars than MATLAB is a genuine parity divergence, not something to relax.
    with patch(patch_target, return_value=segment):
        return vb_fn(rdp_vb, options or {}, **flags)
