"""DEMO1 fresh-user contract — greenfield fixture root, no oracle reuse."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.demo1.demo1_env import apply_shipped_fixture_env, assert_under_fixture_root, clear_fixture_env, shipped_fixture_env
from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root, demo1_shipped_fixtures_dir
from tests.demo1.fixture_registry import all_artifacts, artifact_by_id, missing_artifacts


@pytest.fixture(autouse=True)
def _clear_demo1_fixture_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts without inherited fixture env (fresh-user isolation)."""
    for key in ("RGMS_DEMO1_FIXTURES_DIR", "RGMS_ENTRY12_CAPTURE_OUT_DIR"):
        monkeypatch.delenv(key, raising=False)


def test_default_fixture_root_is_shipped_greenfield() -> None:
    """Fresh clone: unset env → ``tests/demo1/fixtures``, not oracle."""
    fix = demo1_fixtures_dir()
    assert fix == demo1_shipped_fixtures_dir()
    assert "demo1" in fix.parts
    assert "oracle" not in fix.parts


def test_shipped_env_unifies_hub_modules(tmp_path: Path) -> None:
    """Orchestrator env: all hub resolvers point at the same empty root."""
    greenfield = tmp_path / "demo1_fixtures"
    with shipped_fixture_env(greenfield):
        from python_src.toolbox.DEM import entry12_atari_calls, entry12_plot
        from tests.oracle.toolbox.DEM import fsl_backward_rand

        roots = {
            demo1_fixtures_dir(),
            entry12_atari_calls.entry12_fixtures_dir(),
            entry12_plot.fixtures_dir(),
            fsl_backward_rand.fixtures_dir(),
        }
        assert len(roots) == 1
        assert next(iter(roots)) == greenfield.resolve()
        assert not any(greenfield.iterdir())


def test_missing_artifacts_on_empty_greenfield(tmp_path: Path) -> None:
    """Empty fixture dir: registry reports Phase A authority mat missing first."""
    greenfield = tmp_path / "fixtures"
    greenfield.mkdir()
    missing = missing_artifacts(greenfield)
    assert len(missing) > 0
    assert missing[0].artifact_id == "A1_pre_entry10"
    assert artifact_by_id("A1_pre_entry10").path(greenfield) == greenfield / (
        "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    )


def test_artifact_paths_stay_under_greenfield_root(tmp_path: Path) -> None:
    with shipped_fixture_env(tmp_path / "fixtures"):
        root = demo1_fixtures_dir()
        for art in all_artifacts():
            if art.relative_path.endswith("/"):
                continue
            if art.phase == "D" and art.artifact_id == "D3_png":
                continue
            if "matlab_custom/" in art.relative_path:
                continue
            assert_under_fixture_root(art.path(root), root)


def test_apply_shipped_fixture_env_uses_repo_demo1_dir() -> None:
    try:
        fix = apply_shipped_fixture_env()
        assert fix == demo1_shipped_fixtures_dir()
        assert fix.name == "fixtures"
        assert fix.parent.name == "demo1"
    finally:
        clear_fixture_env()


def test_oracle_fixtures_not_default_for_parity() -> None:
    oracle = demo1_repo_root() / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"
    assert demo1_fixtures_dir() != oracle


def test_parity_reset_clears_fixture_artifacts(tmp_path: Path) -> None:
    """Reset removes .mat/.pkl/.json under fixture root and empty gate subdirs."""
    greenfield = tmp_path / "fixtures"
    greenfield.mkdir()
    (greenfield / "a.mat").write_bytes(b"mat")
    (greenfield / "b.pkl").write_bytes(b"pkl")
    (greenfield / "entry12_signoff_manifest_rgms_canonical.json").write_text("{}", encoding="utf-8")
    gate = greenfield / "fsl_backward_entry11_entry12_vb"
    gate.mkdir()
    (gate / "gate.pkl").write_bytes(b"pkl")

    with shipped_fixture_env(greenfield):
        from python_src.toolbox.DEM.DEM_AtariIII_demo1_parity_reset import reset_fixtures

        assert reset_fixtures(dry_run=True) == 0
        assert (greenfield / "a.mat").is_file()
        assert reset_fixtures(dry_run=False) == 0
        assert not list(greenfield.rglob("*.mat"))
        assert not list(greenfield.rglob("*.pkl"))
        assert not list(greenfield.rglob("*.json"))
        assert not gate.exists()
