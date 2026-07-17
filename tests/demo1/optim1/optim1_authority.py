"""DEMO1 fixture authority checks for OPTIM1 parity (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.demo1.demo1_paths import demo1_fixtures_dir


@dataclass(frozen=True)
class AuthorityRequirement:
    artifact_id: str
    relative_path: str
    used_by: str


# Minimum DEMO1 authority required before OPTIM1 parity (reuse DEMO1 Product B mats).
OPTIM1_DEMO1_AUTHORITY: tuple[AuthorityRequirement, ...] = (
    AuthorityRequirement(
        "demo1_pre_entry10",
        "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat",
        "Entry 3/8/9 scale compare authority",
    ),
    AuthorityRequirement(
        "demo1_pre_entry11",
        "DEMAtariIII_fsl_backward_MDP_pre_entry11.mat",
        "Entry 10 optim MATLAB-eig scale authority",
    ),
    AuthorityRequirement(
        "demo1_pre_entry10_pkl",
        "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl",
        "Entry 10 optim boundary PKL",
    ),
    AuthorityRequirement(
        "demo1_pre_entry9",
        "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl",
        "Entry 8/9 optim boundary",
    ),
    AuthorityRequirement(
        "demo1_entry2_post",
        "DEMAtariIII_fsl_backward_entry2_post.pkl",
        "Entry 3 optim boundary",
    ),
    AuthorityRequirement(
        "demo1_rand_buf",
        "dem_atari_rand_buf_through_entry11.mat",
        "Entry 3 RNG replay",
    ),
    AuthorityRequirement(
        "demo1_entry3_k",
        "fsl_backward_entry3_K_py.mat",
        "Entry 3 draw-count preflight",
    ),
    AuthorityRequirement(
        "demo1_12_rdp",
        "DEMAtariIII_XXX_12_rdp.mat",
        "Phase C Entry 12 lane",
    ),
    AuthorityRequirement(
        "demo1_12_pdp_mat",
        "DEMAtariIII_XXX_12_pdp.mat",
        "Phase C script 4 authority",
    ),
    AuthorityRequirement(
        "demo1_vb_k",
        "entry12_vb_rand_K.mat",
        "Phase C vb_rand preflight",
    ),
    AuthorityRequirement(
        "demo1_12_12a",
        "DEMAtariIII_entry12_rgms_canonical_12A.mat",
        "Phase C capture authority",
    ),
)


def missing_demo1_authority(fixtures: Path | None = None) -> list[AuthorityRequirement]:
    root = fixtures or demo1_fixtures_dir()
    return [req for req in OPTIM1_DEMO1_AUTHORITY if not (root / req.relative_path).is_file()]


def assert_demo1_authority_present(fixtures: Path | None = None) -> Path:
    root = fixtures or demo1_fixtures_dir()
    missing = missing_demo1_authority(root)
    if missing:
        lines = "\n".join(
            f"  - [{m.artifact_id}] {m.relative_path} ({m.used_by})" for m in missing
        )
        raise FileNotFoundError(
            "OPTIM1 parity requires green DEMO1 fixtures under "
            f"{root}.\n"
            "Run: python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity.py\n"
            f"Missing ({len(missing)}):\n{lines}"
        )
    return root
