"""OPTIM1FULL Product B — MATLAB replay helpers (``rng(2)`` / ``vb_rand_buf`` / Engine ``eig``)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Callable, Iterator

import numpy as np


@contextmanager
def optim1full_entry12_fixture_env() -> Iterator[None]:
    """Point Entry **12** artifact resolution at ``tests/demo1/optim1/fixtures/``."""
    from tests.demo1.optim1full.optim1full_rng_authority import optim1full_entry12_fixture_root

    fix = str(optim1full_entry12_fixture_root().resolve())
    old = os.environ.get("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = fix
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("RGMS_ENTRY12_CAPTURE_OUT_DIR", None)
        else:
            os.environ["RGMS_ENTRY12_CAPTURE_OUT_DIR"] = old


@contextmanager
def entry12_vb_tag_env(tag: str) -> Iterator[None]:
    """Set ``RGMS_ENTRY12_CAPTURE_RUN_TAG`` for ``entry12_load_vb_rand_buf_for_tag``."""
    old = os.environ.get("RGMS_ENTRY12_CAPTURE_RUN_TAG")
    os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = str(tag).strip()
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("RGMS_ENTRY12_CAPTURE_RUN_TAG", None)
        else:
            os.environ["RGMS_ENTRY12_CAPTURE_RUN_TAG"] = old


def vb_replay_kwargs_for_tag(tag: str, *, dump_subentries: bool = True) -> dict[str, Any]:
    """``spm_MDP_VB_XXX`` kwargs with MATLAB ``vb_rand_buf`` replay for ``tag``."""
    from python_src.toolbox.DEM.entry12_atari_calls import (
        entry12_assert_buf_k_coherent,
        entry12_assert_signoff_chain_ready,
        entry12_vb_oracle_flags,
    )

    entry12_assert_signoff_chain_ready(tag, require_rand_buf=True, require_script3_pkls=False)
    with entry12_vb_tag_env(tag):
        entry12_assert_buf_k_coherent(tag)
        kw = entry12_vb_oracle_flags(reuse_matlab_draws=True)
        kw["dump_subentries"] = bool(dump_subentries)
        return kw


def optim1full_vb_replay_kwargs_for_tag(
    tag: str,
    *,
    dump_subentries: bool = True,
) -> dict[str, Any]:
    """``vb_replay_kwargs_for_tag`` with OPTIM1FULL fixture root (§ **11.7.1**)."""
    with optim1full_entry12_fixture_env():
        return vb_replay_kwargs_for_tag(tag, dump_subentries=dump_subentries)


def optim1full_vb_replay_kwargs_for_call2_game(
    game: int,
    *,
    dump_subentries: bool = True,
) -> dict[str, Any] | None:
    """
    Replay kwargs for NR-loop game ``1..32``, or ``None`` if sign-off chain incomplete.

    Used by tier **3g** / full-replay when per-game ``vb_rand_buf`` exists.
    """
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call2_game_tag
    from tests.demo1.optim1full.optim1full_rng_authority import missing_entry12_vb_paths

    tag = entry12_atari_call2_game_tag(game)
    if missing_entry12_vb_paths(tag):
        return None
    return optim1full_vb_replay_kwargs_for_tag(tag, dump_subentries=dump_subentries)


def optim1full_vb_kwargs_provider_for_nr_loop(
    *,
    dump_subentries: bool = False,
) -> Callable[[int], dict[str, Any] | None]:
    """
    *(Retired for full-script replay.)* Per-game Model **A** tag provider.

    ``run_dem_atariiii_optim1full_parity`` uses Model **B** ledger replay (§ **11.7.2**).
    """

    def _provider(game: int) -> dict[str, Any] | None:
        return optim1full_vb_replay_kwargs_for_call2_game(
            game,
            dump_subentries=dump_subentries,
        )

    return _provider


def matlab_eig_callable(eng: Any) -> Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]:
    """Diagnostic-only ``eig`` inject for sort-split probes — not OPTIM1FULL Product B sign-off.

    Product B tier **2** / full parity driver use Engine ``spm_RDP_sort`` via
    ``optim1full_matlab_sort.py`` (``RGMS_OPTIM1FULL_SPM_RDP_SORT_MATLAB=1``).
    """
    from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig

    return _make_matlab_spm_RDP_sort_eig(eng)


def run_preamble_optim_12_replay(*, deadline_minutes: str = "120") -> dict[str, Any]:
    """
    OPTIM1FULL Product B preamble — ``run_dem_atariiii_optim`` through Entry **12**
    with ``dem_atari_rand_buf`` (Entries **1–11**) and ``vb_rand_buf`` (call **1**).
    """
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim
    from python_src.toolbox.DEM.entry12_atari_calls import ENTRY12_ATARI_CALL1_TAG
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
    from tests.oracle.toolbox.DEM.fsl_backward_rand import (
        fsl_backward_replay_matlab_draws,
        fsl_entry11_driver_env,
        load_dem_atari_rand_buf,
    )

    buf, k_11 = load_dem_atari_rand_buf()
    with fsl_entry11_driver_env(deadline_minutes=deadline_minutes):
        with fsl_backward_replay_matlab_draws(k_11, buf) as ctr:
            ctx = run_dem_atariiii_optim(entry_stop=11)
        used = int(ctr[0])
    if used != k_11:
        raise RuntimeError(
            f"OPTIM1FULL preamble: used {used} dem_atari draws, expected K_11={k_11}"
        )

    vb_kw = optim1full_vb_replay_kwargs_for_tag(ENTRY12_ATARI_CALL1_TAG)
    with entry12_vb_tag_env(ENTRY12_ATARI_CALL1_TAG):
        ctx["PDP"] = spm_MDP_VB_XXX(ctx["RDP"], {}, **vb_kw)
    ctx["_optim1full_preamble_replay"] = {
        "k_11": k_11,
        "dem_atari_draws_used": used,
        "entry12_tag": ENTRY12_ATARI_CALL1_TAG,
    }
    return ctx


def atari_c_value() -> float:
    raw = str(os.getenv("RGMS_ATARI_C", "32")).strip()
    return float(raw)
