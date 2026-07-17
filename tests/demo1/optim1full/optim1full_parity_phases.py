"""OPTIM1FULL Product B parity phases — Entry 12 replay gates (§ **11.0.3**).

Mirrors OPTIM1 ``optim1_parity_phases.py`` + DEMO1 Phase C discipline for post–12 VB tags.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_ORACLE_DEM = _REPO / "tests" / "oracle" / "toolbox" / "DEM"
_DRAW_AUDIT = _REPO / "matlab_custom" / "entry12_draw_index_audit.py"


def _env_for_tag(tag: str) -> dict[str, str]:
    from tests.demo1.optim1full.optim1full_rng_authority import optim1full_entry12_subprocess_env

    return optim1full_entry12_subprocess_env(tag)


def _run_pytest_xxx12(tag: str) -> None:
    env = _env_for_tag(tag)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(_ORACLE_DEM / "test_DEM_AtariIII_XXX_12.py::test_xxx_12_fsl_rdp_to_pdp_pkl"),
        "-q",
    ]
    print(f"[optim1full parity] XXX 12 script 3 tag={tag!r}", file=sys.stderr, flush=True)
    subprocess.run(cmd, cwd=str(_REPO), env=env, check=True)


def _run_draw_audit(tag: str) -> None:
    env = _env_for_tag(tag)
    print(f"[optim1full parity] draw audit tag={tag!r}", file=sys.stderr, flush=True)
    subprocess.run([sys.executable, str(_DRAW_AUDIT)], cwd=str(_REPO), env=env, check=True)


def _run_xxx12_compare(tag: str) -> None:
    env = _env_for_tag(tag)
    cmd = [
        sys.executable,
        str(_ORACLE_DEM / "XXX_12_compare_pdp_pkl_to_mat.py"),
        "--coerce-sparse-to-dense-for-compare",
    ]
    print(f"[optim1full parity] XXX 12 script 4 tag={tag!r}", file=sys.stderr, flush=True)
    subprocess.run(cmd, cwd=str(_REPO), env=env, check=True)


def run_entry12_vb_gate(tag: str, *, label: str) -> float:
    """Full Entry 12 sign-off chain for one VB tag: script **3** → audit → script **4**."""
    from tests.demo1.optim1full.optim1full_rng_authority import assert_entry12_vb_tag_ready

    t0 = time.perf_counter()
    assert_entry12_vb_tag_ready(tag, require_script3_pkls=False)
    print(f"[optim1full parity] {label} — authority OK tag={tag!r}", file=sys.stderr, flush=True)
    _run_pytest_xxx12(tag)
    _run_draw_audit(tag)
    _run_xxx12_compare(tag)
    wall = time.perf_counter() - t0
    print(f"[optim1full parity] {label} PASS wall_s={wall:.3f}", file=sys.stderr, flush=True)
    return wall


def run_tier_3a_call2_game1() -> float:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL2_TAG,
    )

    return run_entry12_vb_gate(ENTRY12_OPTIM1FULL_CALL2_TAG, label="tier 3a call-2 game 1")


def run_tier_3e_call3() -> float:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL3_TAG,
    )

    return run_entry12_vb_gate(ENTRY12_OPTIM1FULL_CALL3_TAG, label="tier 3e call-3")


def run_tier_3f_call4() -> float:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL4_TAG,
    )

    return run_entry12_vb_gate(ENTRY12_OPTIM1FULL_CALL4_TAG, label="tier 3f call-4")


def run_phase_c_nr_g01_ledger() -> float:
    """OPTIM1FULL Phase C — ``rgms_atari_optim1full_nr_g01`` (ledger ``MDP_pre`` NR game 1)."""
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_NR_G01_TAG,
    )

    return run_entry12_vb_gate(
        ENTRY12_OPTIM1FULL_NR_G01_TAG,
        label="Phase C NR g01 ledger",
    )


def run_entry12_vb_gates_for_games(
    games: range,
    *,
    label: str,
) -> float:
    """Entry **12** sign-off chain for each NR call-2 game in ``games``."""
    from python_src.toolbox.DEM.entry12_atari_calls import entry12_atari_call2_game_tag

    t0 = time.perf_counter()
    for g in games:
        tag = entry12_atari_call2_game_tag(int(g))
        run_entry12_vb_gate(tag, label=f"{label} game {g}")
    wall = time.perf_counter() - t0
    print(f"[optim1full parity] {label} PASS wall_s={wall:.3f}", file=sys.stderr, flush=True)
    return wall


def run_tier_3b_call2_games_2_16() -> float:
    return run_entry12_vb_gates_for_games(range(2, 17), label="tier 3b")


def run_tier_3c_call2_games_17_32() -> float:
    return run_entry12_vb_gates_for_games(range(17, 33), label="tier 3c")
