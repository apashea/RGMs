"""Canonical paths for Entry 4 ``spm_rgm_group`` spectral / ``eig(...,'nobalance')`` dumps.

All Entry-4-eig artifacts use the ``DEMAtariIII_fsl_backward_entry4_rgm_spectral_*`` prefix
so they cannot collide with Entry 12 captures, snippet checkpoints
(``fsl_rgm_spectral_workload_*.pkl``), or FSL post/compare PKLs (``*_post.pkl``).

See repo-root ``eig.md`` §7.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]

# --- Inputs (existing FSL boundary; do not rename) ---
FSL_MDP_PRE_ENTRY10_MAT = "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
FSL_MDP_PRE_ENTRY4_PKL = "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"

# --- Entry 4 rgm spectral eig dumps (unique product names) ---
ENTRY4_RGM_SPECTRAL_MATLAB_EIG_RECORDS_MAT = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_matlab_eig_records.mat"
)
ENTRY4_RGM_SPECTRAL_PYTHON_ENGINE_PROBE_PKL = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_python_engine_probe.pkl"
)
ENTRY4_RGM_SPECTRAL_EIG_ORACLE_BLOCKS_PKL = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_oracle_blocks.pkl"
)
ENTRY4_RGM_SPECTRAL_EIG_DUMP_MANIFEST_JSON = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_dump_manifest.json"
)
ENTRY4_RGM_SPECTRAL_EIG_DIAGNOSIS_JSON = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_diagnosis.json"
)
ENTRY4_RGM_SPECTRAL_EIG_DIAGNOSIS_GRANULAR_JSON = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_diagnosis_granular.json"
)
ENTRY4_RGM_SPECTRAL_EIG_INSPECTION_DEEP_JSON = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_inspection_deep.json"
)
ENTRY4_RGM_SPECTRAL_EIG_FAILURE_INDEX_JSON = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_failure_index.json"
)
ENTRY4_RGM_SPECTRAL_EIG_FAILURE_REPLAY_PKL = (
    "DEMAtariIII_fsl_backward_entry4_rgm_spectral_eig_failure_replay.pkl"
)
ENTRY4_RGM_SPECTRAL_EIG_ENGINE_PRINCIPAL_PROBE_JSON = (
    "DEMAtariIII_fsl_backward_entry4_eig_engine_principal_probe.json"
)
ENTRY4_RGM_SPECTRAL_EIG_SOLVER_MATRIX_JSON = (
    "DEMAtariIII_fsl_backward_entry4_eig_solver_matrix.json"
)

# --- Report (matlab_custom; not a fixture) ---
ENTRY4_RGM_SPECTRAL_DUMP_REPORT_TXT = "fsl_backward_entry4_rgm_spectral_eig_dump_output.txt"


def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def matlab_custom_dir() -> Path:
    return _REPO / "matlab_custom"


def fsl_mdp_pre_entry10_mat() -> Path:
    return fixtures_dir() / FSL_MDP_PRE_ENTRY10_MAT


def fsl_mdp_pre_entry4_pkl() -> Path:
    return fixtures_dir() / FSL_MDP_PRE_ENTRY4_PKL


def entry4_matlab_eig_records_mat() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_MATLAB_EIG_RECORDS_MAT


def entry4_python_engine_probe_pkl() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_PYTHON_ENGINE_PROBE_PKL


def entry4_eig_oracle_blocks_pkl() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_ORACLE_BLOCKS_PKL


def entry4_dump_manifest_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_DUMP_MANIFEST_JSON


def entry4_eig_diagnosis_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_DIAGNOSIS_JSON


def entry4_eig_diagnosis_granular_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_DIAGNOSIS_GRANULAR_JSON


def entry4_eig_inspection_deep_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_INSPECTION_DEEP_JSON


def entry4_eig_failure_index_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_FAILURE_INDEX_JSON


def entry4_eig_failure_replay_pkl() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_FAILURE_REPLAY_PKL


def entry4_eig_engine_principal_probe_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_ENGINE_PRINCIPAL_PROBE_JSON


def entry4_eig_solver_matrix_json() -> Path:
    return fixtures_dir() / ENTRY4_RGM_SPECTRAL_EIG_SOLVER_MATRIX_JSON


def entry4_dump_report_txt() -> Path:
    return matlab_custom_dir() / ENTRY4_RGM_SPECTRAL_DUMP_REPORT_TXT


def dump_refresh_allowed() -> bool:
    return str(os.getenv("RGMS_ENTRY4_RGM_SPECTRAL_EIG_DUMP_REFRESH", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def assert_can_write(path: Path, *, label: str) -> None:
    """Refuse accidental overwrite unless ``RGMS_ENTRY4_RGM_SPECTRAL_EIG_DUMP_REFRESH=1``."""
    if path.is_file() and not dump_refresh_allowed():
        raise FileExistsError(
            f"{label} already exists (refusing overwrite): {path}\n"
            "Set RGMS_ENTRY4_RGM_SPECTRAL_EIG_DUMP_REFRESH=1 to replace."
        )


def write_manifest(*, extra: dict[str, Any] | None = None) -> Path:
    """Write/update JSON manifest listing all Entry 4 eig dump paths and presence."""
    manifest = {
        "purpose": "Entry 4 spm_rgm_group eig(nobalance) dump registry",
        "paths": {
            "input_mat_pre_entry10": str(fsl_mdp_pre_entry10_mat()),
            "input_pkl_pre_entry4": str(fsl_mdp_pre_entry4_pkl()),
            "matlab_eig_records_mat": str(entry4_matlab_eig_records_mat()),
            "python_engine_probe_pkl": str(entry4_python_engine_probe_pkl()),
            "eig_oracle_blocks_pkl": str(entry4_eig_oracle_blocks_pkl()),
            "eig_diagnosis_json": str(entry4_eig_diagnosis_json()),
            "eig_diagnosis_granular_json": str(entry4_eig_diagnosis_granular_json()),
            "eig_inspection_deep_json": str(entry4_eig_inspection_deep_json()),
            "eig_failure_index_json": str(entry4_eig_failure_index_json()),
            "eig_failure_replay_pkl": str(entry4_eig_failure_replay_pkl()),
        },
        "exists": {
            "input_mat_pre_entry10": fsl_mdp_pre_entry10_mat().is_file(),
            "input_pkl_pre_entry4": fsl_mdp_pre_entry4_pkl().is_file(),
            "matlab_eig_records_mat": entry4_matlab_eig_records_mat().is_file(),
            "python_engine_probe_pkl": entry4_python_engine_probe_pkl().is_file(),
            "eig_oracle_blocks_pkl": entry4_eig_oracle_blocks_pkl().is_file(),
            "eig_diagnosis_json": entry4_eig_diagnosis_json().is_file(),
            "eig_diagnosis_granular_json": entry4_eig_diagnosis_granular_json().is_file(),
            "eig_inspection_deep_json": entry4_eig_inspection_deep_json().is_file(),
            "eig_failure_index_json": entry4_eig_failure_index_json().is_file(),
            "eig_failure_replay_pkl": entry4_eig_failure_replay_pkl().is_file(),
        },
    }
    if extra:
        manifest["run"] = extra
    out = entry4_dump_manifest_json()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    return out
