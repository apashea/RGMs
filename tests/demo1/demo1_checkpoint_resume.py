"""DEMO1 checkpoint resume — skip parity steps when registry dumps already exist.

See ``DEMO1.md`` §6. ``rng(2)`` / ``dem_atari_rand_buf`` /
``vb_rand_buf`` stay authoritative; skipping only elides recompute when the checkpoint file
is already on disk under ``tests/demo1/fixtures/``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from tests.demo1.fixture_registry import artifact_by_id

# Phase B script blocks (must match ``demo1_parity_phases._PHASE_B_SCRIPTS`` order).
_PHASE_B_ENTRY_SCRIPTS: dict[str, tuple[str, ...]] = {
    "1": (
        "fsl_backward_preflight_rand_k_entry1.py",
        "fsl_backward_materialize_mdp_pre_entry1_pkl.py",
        "fsl_backward_run_entry1_isolated.py",
        "fsl_backward_compare_entry1_pkl_to_mat.py",
    ),
    "2": (
        "fsl_backward_preflight_rand_k_entry2.py",
        "fsl_backward_materialize_mdp_pre_entry2_pkl.py",
        "fsl_backward_run_entry2_isolated.py",
        "fsl_backward_compare_entry2_pkl_to_mat.py",
    ),
    "3": (
        "fsl_backward_preflight_rand_k_entry3.py",
        "fsl_backward_materialize_mdp_pre_entry3_pkl.py",
        "fsl_backward_run_entry3_isolated.py",
        "fsl_backward_compare_entry3_pkl_to_mat.py",
    ),
    "4": (
        "fsl_backward_materialize_mdp_pre_entry4_pkl.py",
        "fsl_backward_run_entry4_isolated.py",
        "fsl_backward_compare_entry4_pkl_to_mat.py",
    ),
    "5": (
        "fsl_backward_materialize_mdp_pre_entry5_pkl.py",
        "fsl_backward_run_entry5_isolated.py",
        "fsl_backward_compare_entry5_pkl_to_mat.py",
    ),
    "6": (
        "fsl_backward_materialize_mdp_pre_entry6_pkl.py",
        "fsl_backward_run_entry6_isolated.py",
        "fsl_backward_compare_entry6_pkl_to_mat.py",
    ),
    "7": (
        "fsl_backward_materialize_mdp_pre_entry7_pkl.py",
        "fsl_backward_run_entry7_isolated.py",
        "fsl_backward_compare_entry7_pkl_to_mat.py",
    ),
    "8+9": (
        "fsl_backward_materialize_mdp_pre_entry9_pkl.py",
        "fsl_backward_run_entry9_isolated.py",
        "fsl_backward_compare_entry9_pkl_to_mat.py",
    ),
    "10": (
        "fsl_backward_materialize_mdp_pre_entry10_pkl.py",
        "fsl_backward_run_entry10_isolated.py",
        "fsl_backward_compare_entry10_pkl_to_mat.py",
    ),
    "11": (
        "fsl_backward_materialize_mdp_pre_entry11_pkl.py",
        "fsl_backward_run_entry11_isolated.py",
        "fsl_backward_compare_entry11_pkl_to_mat.py",
    ),
}

_PHASE_B_GATE_SCRIPTS: tuple[str, ...] = ("fsl_backward_validate_entry11_through_entry12.py",)

_ENTRY_POST_ARTIFACT: dict[str, str] = {
    **{str(n): f"B{n}_post" for n in range(1, 8)},
    "8+9": "B89_post",
    **{str(n): f"B{n}_post" for n in range(10, 12)},
}


@dataclass(frozen=True)
class CheckpointUnit:
    """One skippable parity block."""

    label: str
    artifact_id: str
    scripts: tuple[str, ...]


def _artifact_present(artifact_id: str, fixtures: Path) -> bool:
    art = artifact_by_id(artifact_id)
    if not art.skip_if_present:
        return False
    p = art.path(fixtures)
    if art.relative_path.endswith("/"):
        return p.is_dir()
    return p.is_file()


def entry_gate_checkpoint_present(fixtures: Path) -> bool:
    """Entry 11→12 ``--vb-only`` gate: gate-dir PDP dump (not empty dir alone)."""
    p = fixtures / "fsl_backward_entry11_entry12_vb" / "DEMAtariIII_fsl_backward_entry11_entry12_pdp.pkl"
    return p.is_file()


def checkpoint_present(artifact_id: str, fixtures: Path) -> bool:
    if artifact_id == "B11_gate":
        return entry_gate_checkpoint_present(fixtures)
    return _artifact_present(artifact_id, fixtures)


def phase_b_units() -> tuple[CheckpointUnit, ...]:
    units: list[CheckpointUnit] = []
    for key in [str(n) for n in range(1, 8)]:
        units.append(
            CheckpointUnit(
                label=f"entry {key}",
                artifact_id=_ENTRY_POST_ARTIFACT[key],
                scripts=_PHASE_B_ENTRY_SCRIPTS[key],
            )
        )
    units.append(
        CheckpointUnit(
            label="entry 8+9",
            artifact_id=_ENTRY_POST_ARTIFACT["8+9"],
            scripts=_PHASE_B_ENTRY_SCRIPTS["8+9"],
        )
    )
    for key in ("10", "11"):
        units.append(
            CheckpointUnit(
                label=f"entry {key}",
                artifact_id=_ENTRY_POST_ARTIFACT[key],
                scripts=_PHASE_B_ENTRY_SCRIPTS[key],
            )
        )
    units.append(
        CheckpointUnit(
            label="entry 11→12 gate",
            artifact_id="B11_gate",
            scripts=_PHASE_B_GATE_SCRIPTS,
        )
    )
    return tuple(units)


def phase_b_scripts_in_order() -> tuple[str, ...]:
    out: list[str] = []
    for unit in phase_b_units():
        out.extend(unit.scripts)
    return tuple(out)


def plan_phase_b(fixtures: Path) -> list[tuple[CheckpointUnit, bool]]:
    """Return each Phase B unit and whether it will be skipped (``True`` = skip)."""
    return [(u, checkpoint_present(u.artifact_id, fixtures)) for u in phase_b_units()]


def log_checkpoint_skip(label: str, *, artifact_id: str) -> None:
    print(
        f"[checkpoint resume] skip {label} ({artifact_id} present)",
        file=sys.stderr,
    )


def phase_c_skip_script3(fixtures: Path) -> bool:
    return checkpoint_present("C3_pdp", fixtures)


def phase_c_skip_script4(fixtures: Path) -> bool:
    return checkpoint_present("C4_compare", fixtures)


def phase_d_skip(fixtures: Path) -> bool:
    return checkpoint_present("D3_png", fixtures)
