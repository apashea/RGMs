"""OPTIM1 path resolution smoke tests."""

from __future__ import annotations

from tests.demo1.demo1_paths import demo1_shipped_fixtures_dir
from tests.demo1.optim1.optim1_paths import (
    optim1_demo1_authority_fixtures_dir,
    optim1_fixtures_dir,
    optim1_python_native_dir,
    optim1_shipped_fixtures_dir,
    optim1_visualizations_dir,
)


def test_optim1_paths_isolated_from_demo1_native():
    assert optim1_fixtures_dir() == optim1_shipped_fixtures_dir()
    assert optim1_python_native_dir().name == "python_native"
    assert optim1_python_native_dir().parent.name == "optim1"
    assert "optim1" in str(optim1_visualizations_dir())
    assert optim1_visualizations_dir().name == "optim1"


def test_optim1_authority_points_at_demo1_fixtures_by_default():
    assert optim1_demo1_authority_fixtures_dir() == demo1_shipped_fixtures_dir()
