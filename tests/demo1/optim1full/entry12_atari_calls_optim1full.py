"""OPTIM1FULL lane Entry 12 VB tags and fixture paths (do not edit shared ``entry12_atari_calls.py``)."""

from __future__ import annotations

from pathlib import Path

from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir

ENTRY12_OPTIM1FULL_CALL2_TAG = "rgms_atari_optim1full_call2"
ENTRY12_OPTIM1FULL_CALL3_TAG = "rgms_atari_optim1full_call3"
ENTRY12_OPTIM1FULL_CALL4_TAG = "rgms_atari_optim1full_call4"
ENTRY12_OPTIM1FULL_NR_G01_TAG = "rgms_atari_optim1full_nr_g01"

ENTRY12_OPTIM1FULL_VB_TAGS: tuple[str, ...] = (
    ENTRY12_OPTIM1FULL_CALL2_TAG,
    ENTRY12_OPTIM1FULL_CALL3_TAG,
    ENTRY12_OPTIM1FULL_CALL4_TAG,
    ENTRY12_OPTIM1FULL_NR_G01_TAG,
)

_TAG_RDP_MAT: dict[str, str] = {
    ENTRY12_OPTIM1FULL_CALL2_TAG: "DEMAtariIII_XXX_12_rgms_atari_optim1full_call2_rdp.mat",
    ENTRY12_OPTIM1FULL_CALL3_TAG: "DEMAtariIII_XXX_12_rgms_atari_optim1full_call3_rdp.mat",
    ENTRY12_OPTIM1FULL_CALL4_TAG: "DEMAtariIII_XXX_12_rgms_atari_optim1full_call4_rdp.mat",
    ENTRY12_OPTIM1FULL_NR_G01_TAG: "DEMAtariIII_XXX_12_rgms_atari_optim1full_nr_g01_rdp.mat",
}


def optim1full_entry12_atari_call_rdp_mat_path(tag: str) -> Path:
    name = _TAG_RDP_MAT.get(tag)
    if name is None:
        raise KeyError(f"unknown OPTIM1FULL Entry 12 tag: {tag!r}")
    return optim1full_fixtures_dir() / name


def optim1full_entry12_call_pdp_artifact_paths(tag: str) -> dict[str, Path]:
    fix = optim1full_fixtures_dir()
    if tag not in _TAG_RDP_MAT:
        raise KeyError(f"unknown OPTIM1FULL Entry 12 tag: {tag!r}")
    return {
        "rdp_mat": fix / optim1full_entry12_atari_call_rdp_mat_path(tag).name,
        "rdp_pkl": fix / f"DEMAtariIII_XXX_12_{tag}_rdp.pkl",
        "pdp_mat": fix / f"DEMAtariIII_XXX_12_{tag}_pdp.mat",
        "pdp_pkl": fix / f"DEMAtariIII_XXX_12_{tag}_pdp.pkl",
        "rand_buf": fix / f"DEMAtariIII_entry12_vb_matlab_rand_buf_{tag}.mat",
    }


def optim1full_entry12_signoff_manifest_path(tag: str) -> Path:
    return optim1full_fixtures_dir() / f"entry12_signoff_manifest_{tag}.json"


def optim1full_entry12_signoff_artifact_paths(tag: str) -> dict[str, Path]:
    tag_use = str(tag).strip()
    base = optim1full_entry12_call_pdp_artifact_paths(tag_use)
    fix = optim1full_fixtures_dir()
    base["rand_k"] = fix / f"entry12_vb_rand_K_{tag_use}.mat"
    base["manifest"] = optim1full_entry12_signoff_manifest_path(tag_use)
    base["_tag"] = tag_use
    return base
