"""OPTIM1FULL Product B — MATLAB authority fixture presence checks."""

from __future__ import annotations

from pathlib import Path

from tests.demo1.optim1full.optim1full_paths import optim1full_fixtures_dir


def optim1full_required_mi_mats() -> tuple[str, ...]:
    return (
        "DEMAtariIII_optim1full_MDP_pre_mi382.mat",
        "DEMAtariIII_optim1full_MDP_post_mi382.mat",
        "DEMAtariIII_optim1full_MDP_pre_mi429.mat",
        "DEMAtariIII_optim1full_MDP_post_mi429.mat",
        "DEMAtariIII_optim1full_np_mi429.mat",
        "DEMAtariIII_optim1full_mi382_causal.mat",
        "DEMAtariIII_optim1full_mi429_causal.mat",
    )


def optim1full_post_nr_mat_name() -> str:
    return "DEMAtariIII_optim1full_MDP_post_nr.mat"


def optim1full_required_ledger_artifacts() -> tuple[str, ...]:
    return (
        "optim1full_dem_atari_rand_buf.mat",
        "optim1full_rand_manifest.json",
    )


def missing_optim1full_ledger(fixtures_dir: Path | None = None) -> list[str]:
    root = fixtures_dir or optim1full_fixtures_dir()
    missing: list[str] = []
    for name in optim1full_required_ledger_artifacts():
        p = root / name
        if not p.is_file():
            missing.append(str(p))
    return missing


def missing_optim1full_authority(fixtures_dir: Path | None = None) -> list[str]:
    root = fixtures_dir or optim1full_fixtures_dir()
    missing: list[str] = []
    for name in (*optim1full_required_mi_mats(), optim1full_post_nr_mat_name()):
        if not (root / name).is_file():
            missing.append(str(root / name))
    return missing


def assert_optim1full_authority_present(fixtures_dir: Path | None = None) -> None:
    missing = missing_optim1full_authority(fixtures_dir)
    if missing:
        raise FileNotFoundError(
            "OPTIM1FULL Product B authority missing:\n"
            + "\n".join(f"  - {p}" for p in missing)
            + "\nRun MATLAB: DEMAtariIII_entry12_dump_all_subentries('capture_optim1full_mi_boundaries')"
        )


from tests.demo1.optim1full.optim1full_mdp_engine_io import CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B

_LEDGER_CAPTURE_MODE = "capture_optim1full_rand_ledger"
_MDP_CAPTURE_MODES = frozenset(
    {
        _LEDGER_CAPTURE_MODE,
        CAPTURE_OPTIM1FULL_PYTHON_PRODUCT_B,
    }
)


def _mat_capture_meta(path: Path, meta_field: str) -> str:
    from scipy.io import loadmat

    raw = loadmat(str(path), squeeze_me=True, struct_as_record=False)
    if meta_field not in raw:
        raise ValueError(f"{path.name}: missing {meta_field!r}")
    meta = raw[meta_field]
    capture = str(getattr(meta, "capture", "")).strip()
    if not capture:
        raise ValueError(f"{path.name}: {meta_field}.capture empty")
    return capture


def assert_optim1full_mdp_ledger_session(fixtures_dir: Path | None = None) -> None:
    """Tier **3g** requires ``MDP_pre`` + ``MDP_post_nr`` from one ledger capture."""
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_pre_active_inference_mat

    root = fixtures_dir or optim1full_fixtures_dir()
    pre = optim1full_mdp_pre_active_inference_mat()
    post = root / optim1full_post_nr_mat_name()
    if not pre.is_file():
        raise FileNotFoundError(
            f"missing {pre.name} — run capture_optim1full_rand_ledger (co-located MDP_pre)"
        )
    pre_cap = _mat_capture_meta(pre, "metaPre")
    post_cap = _mat_capture_meta(post, "metaPost")
    if pre_cap not in _MDP_CAPTURE_MODES or post_cap not in _MDP_CAPTURE_MODES:
        raise RuntimeError(
            "OPTIM1FULL tier 3g fixture session mismatch:\n"
            f"  {pre.name} metaPre.capture={pre_cap!r}\n"
            f"  {post.name} metaPost.capture={post_cap!r}\n"
            f"  expected one of {sorted(_MDP_CAPTURE_MODES)!r}"
        )
    if pre_cap != post_cap:
        raise RuntimeError(
            "OPTIM1FULL tier 3g fixture session mismatch:\n"
            f"  {pre.name} metaPre.capture={pre_cap!r}\n"
            f"  {post.name} metaPost.capture={post_cap!r}\n"
            "  expected matching capture mode — re-run optim1full_capture_python_product_b.py"
        )
