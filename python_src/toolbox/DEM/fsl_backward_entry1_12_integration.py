"""FSL backward Track A — full driver integration Entries 1–11 + Entry 12 VB.

**RNG (do not conflate):**

- Entries **1–11:** ``dem_atari_rand_buf`` replay through ``K_11`` (``fsl_backward_replay_matlab_draws``).
- Entry **12:** ``vb_rand_buf`` replay via ``spm_MDP_VB_XXX(..., reuse_matlab_draws=True)`` — **not**
  the ledger buffer.

See ``Atari_example.md`` § **Post FSL backward — optional tracks** (Track **A**).
"""

from __future__ import annotations

import copy
import os
import pickle
import shutil
import time
from pathlib import Path
from typing import Any

from python_src.toolbox.DEM.fsl_backward_entry11 import entry11_rdp_for_entry12_vb


def integration_vb_out_dir() -> Path:
    raw = str(os.getenv("RGMS_FSL_ENTRY1_12_INTEGRATION_VB_OUT_DIR", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    repo = Path(__file__).resolve().parents[3]
    return (
        repo
        / "tests"
        / "oracle"
        / "toolbox"
        / "DEM"
        / "fixtures"
        / "fsl_backward_entry1_12_integration_vb"
    )


def run_entries_1_11_with_dem_atari_replay(
    *,
    deadline_minutes: str = "90",
) -> tuple[dict[str, Any], int, int]:
    """
    ``run_dem_atariiii(entry_stop=11)`` under ``dem_atari_rand_buf[0:K_11]``.

    Returns ``(ctx, k_11, draws_used)``.
    """
    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        fsl_backward_replay_matlab_draws,
        fsl_entry11_driver_env,
        load_dem_atari_rand_buf,
    )

    buf, k_11 = load_dem_atari_rand_buf()
    with fsl_entry11_driver_env(deadline_minutes=deadline_minutes):
        with fsl_backward_replay_matlab_draws(k_11, buf) as ctr:
            ctx = run_dem_atariiii(entry_stop=11)
        used = int(ctr[0])
    if used != k_11:
        raise RuntimeError(
            f"Track A 1–11: used {used} dem_atari draws, expected K_11={k_11}"
        )
    return ctx, k_11, used


def _mirror_canonical_vb_rng(*, tag: str, out_dir: Path) -> None:
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_signoff_artifact_paths

    old_out = os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
    try:
        canon = entry12_signoff_artifact_paths(tag)
    finally:
        if old_out is not None:
            os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = old_out
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in ("rand_buf", "rand_k"):
        src = canon[key]
        dst = out_dir / src.name
        if not src.is_file():
            raise FileNotFoundError(f"missing canonical {key}: {src}")
        if not dst.is_file() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)


def run_entry12_vb_on_integration_ctx(
    ctx: dict[str, Any],
    *,
    tag: str = "rgms_canonical",
    out_dir: Path | None = None,
    deadline_minutes: str = "90",
) -> dict[str, Any]:
    """
    Entry **12** on ``ctx['RDP']`` from integrated 1–11 (VB-input prep + ``vb_rand_buf`` replay).
    """
    from python_src.toolbox.DEM.DEM_AtariIII import (
        _rgms_deadline_reset_for_run,
        _rgms_run_deadline_check,
        _rgms_run_set_last_label,
    )
    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_assert_buf_k_coherent,
        entry12_assert_signoff_chain_ready,
        entry12_vb_oracle_flags,
    )
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

    vb_dir = out_dir if out_dir is not None else integration_vb_out_dir()
    entry12_assert_signoff_chain_ready(tag, require_rand_buf=True, require_script3_pkls=False)
    rdp_vb = entry11_rdp_for_entry12_vb(copy.deepcopy(ctx["RDP"]), tag=tag)

    old_out = os.environ.get("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    old_tag = os.environ.get("RGMS_ENTRY12_CAPTURE_RUN_TAG")
    old_mins = os.environ.get("RGMS_ATARI_RUN_DEADLINE_MINUTES")
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = tag
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = str(vb_dir.resolve())
    os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = deadline_minutes
    try:
        _mirror_canonical_vb_rng(tag=tag, out_dir=vb_dir)
        entry12_assert_buf_k_coherent(tag)
        _rgms_deadline_reset_for_run()
        _rgms_run_set_last_label("Track A 1-12: spm_MDP_VB_XXX")
        _rgms_run_deadline_check()
        t0 = time.perf_counter()
        pdp = spm_MDP_VB_XXX(rdp_vb, {}, **entry12_vb_oracle_flags(reuse_matlab_draws=True))
        wall_s = time.perf_counter() - t0
        if not isinstance(pdp, dict):
            raise TypeError(f"expected dict PDP, got {type(pdp).__name__}")
        return {
            "pdp": pdp,
            "rdp_vb": rdp_vb,
            "vb_out_dir": str(vb_dir.resolve()),
            "vb_wall_s": wall_s,
            "tag": tag,
        }
    finally:
        if old_out is None:
            os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
        else:
            os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = old_out
        if old_tag is None:
            os.environ.pop("RGMS_ENTRY12_CAPTURE_RUN_TAG", None)
        else:
            os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = old_tag
        if old_mins is None:
            os.environ.pop("RGMS_ATARI_RUN_DEADLINE_MINUTES", None)
        else:
            os.environ["RGMS_ATARI_RUN_DEADLINE_MINUTES"] = old_mins


def run_track_a_integration(
    *,
    tag: str = "rgms_canonical",
    replay_dem_atari: bool = True,
    deadline_minutes: str = "90",
) -> dict[str, Any]:
    """Full Track **A**: 1–11 ``dem_atari_rand_buf`` + Entry **12** ``vb_rand_buf``."""
    if not replay_dem_atari:
        raise ValueError("Track A requires dem_atari_rand_buf replay (replay_dem_atari=True)")

    ctx, k_11, used = run_entries_1_11_with_dem_atari_replay(
        deadline_minutes=deadline_minutes
    )
    vb_out = run_entry12_vb_on_integration_ctx(
        ctx, tag=tag, deadline_minutes=deadline_minutes
    )
    ctx_out = dict(ctx)
    ctx_out["PDP"] = vb_out["pdp"]
    return {
        "ctx": ctx_out,
        "k_11": k_11,
        "dem_atari_draws_used": used,
        "entry12": vb_out,
        "validation_lane": "track_a_1_12_integration",
        "tag": tag,
    }
