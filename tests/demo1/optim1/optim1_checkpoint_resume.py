"""OPTIM1 checkpoint resume — skip recomputation when OPTIM1 checkpoints exist.

Fidelity entries **1–2, 4–6, 11** reuse DEMO1 Phase B scripts; checkpoints may
live in DEMO1 ``fixtures/`` (already proven by DEMO1 parity). Entry **4** stays
fidelity FSL (MATLAB structure-learning authority). Optim entries **3, 7, 8+9, 10**
write under ``tests/demo1/optim1/fixtures/`` (Entry **10** = MATLAB-eig scale).

Entry **8+9** uses ``optim1_run_entry89_scale.py`` only (merge+basin vs
``MDP_pre_entry10``). Merge-only ``optim1_run_entry8_scale.py`` is diagnostic/manual.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from tests.demo1.demo1_checkpoint_resume import (
    checkpoint_present as demo1_checkpoint_present,
    entry_gate_checkpoint_present,
    phase_b_units as demo1_phase_b_units,
)
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir


@dataclass(frozen=True)
class _OptimSpec:
    artifact_id: str
    scripts: tuple[str, ...]
    checkpoint_name: str


# Optim scale runners (repo-relative under tests/demo1/optim1/).
_OPTIM_BY_DEMO_ENTRY: dict[str, _OptimSpec] = {
    "3": _OptimSpec(
        "B3_optim",
        ("optim1_run_entry3_scale.py",),
        "DEMAtariIII_optim1_entry3_post.pkl",
    ),
    "7": _OptimSpec(
        "B7_optim",
        ("optim1_run_entry7_scale.py",),
        "DEMAtariIII_optim1_entry7_post.pkl",
    ),
    "8+9": _OptimSpec(
        "B89_optim",
        ("optim1_run_entry89_scale.py",),
        "DEMAtariIII_optim1_entry9_post.pkl",
    ),
    "10": _OptimSpec(
        "B10_optim",
        ("optim1_run_entry10_matlab_eig_scale.py",),
        "DEMAtariIII_optim1_entry10_matlab_eig_post.pkl",
    ),
}


@dataclass(frozen=True)
class Optim1CheckpointUnit:
    label: str
    artifact_id: str
    scripts: tuple[str, ...]
    optim_lane: bool
    checkpoint_path: Path | None = None


def _demo_entry_key(label: str) -> str:
    return label.replace("entry ", "").split("→")[0].strip()


def _optim_checkpoint_present(artifact_id: str, optim_fix: Path) -> bool:
    for spec in _OPTIM_BY_DEMO_ENTRY.values():
        if spec.artifact_id == artifact_id:
            return (optim_fix / spec.checkpoint_name).is_file()
    return False


def optim1_phase_b_units() -> tuple[Optim1CheckpointUnit, ...]:
    units: list[Optim1CheckpointUnit] = []
    for demo_unit in demo1_phase_b_units():
        entry_key = _demo_entry_key(demo_unit.label)
        spec = _OPTIM_BY_DEMO_ENTRY.get(entry_key)
        if spec is not None:
            units.append(
                Optim1CheckpointUnit(
                    label=f"entry {entry_key} (optim)",
                    artifact_id=spec.artifact_id,
                    scripts=spec.scripts,
                    optim_lane=True,
                    checkpoint_path=optim1_fixtures_dir() / spec.checkpoint_name,
                )
            )
        elif demo_unit.artifact_id == "B11_gate":
            units.append(
                Optim1CheckpointUnit(
                    label=demo_unit.label,
                    artifact_id=demo_unit.artifact_id,
                    scripts=demo_unit.scripts,
                    optim_lane=False,
                )
            )
        else:
            units.append(
                Optim1CheckpointUnit(
                    label=demo_unit.label,
                    artifact_id=demo_unit.artifact_id,
                    scripts=demo_unit.scripts,
                    optim_lane=False,
                )
            )
    return tuple(units)


def optim1_checkpoint_present(
    unit: Optim1CheckpointUnit,
    *,
    demo_fixtures: Path,
    optim_fixtures: Path,
) -> bool:
    if unit.artifact_id == "B11_gate":
        return entry_gate_checkpoint_present(demo_fixtures)
    if unit.optim_lane:
        return _optim_checkpoint_present(unit.artifact_id, optim_fixtures)
    return demo1_checkpoint_present(unit.artifact_id, demo_fixtures)


def log_optim1_checkpoint_skip(label: str, *, artifact_id: str) -> None:
    print(
        f"[OPTIM1 checkpoint resume] skip {label} ({artifact_id} present)",
        file=sys.stderr,
    )
