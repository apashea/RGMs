"""Tests for DEMO1 Product A native authority fixture layout."""

from __future__ import annotations

import pytest

from tests.demo1.demo1_native_fixtures import (
    DEMO1_NATIVE_LADDER_ENTRY_STOPS,
    demo1_native_entry_ctx_path,
    demo1_native_fixtures_dir,
    missing_demo1_native_entry_stops,
)


def test_native_fixture_paths_under_python_native():
    base = demo1_native_fixtures_dir()
    assert "python_native" in str(base)
    assert base.name == "fixtures"
    for n in DEMO1_NATIVE_LADDER_ENTRY_STOPS:
        p = demo1_native_entry_ctx_path(n)
        assert p.parent == base
        assert p.name == f"DEMO1_native_entry{n:02d}_ctx.pkl"


def test_missing_fixtures_reports_ladder_stops():
    missing = missing_demo1_native_entry_stops()
    assert missing == list(DEMO1_NATIVE_LADDER_ENTRY_STOPS) or missing == []


def test_load_missing_fixture_raises(tmp_path, monkeypatch):
    from tests.demo1 import demo1_native_fixtures as mod

    monkeypatch.setattr(mod, "demo1_native_fixtures_dir", lambda: tmp_path)
    with pytest.raises(FileNotFoundError, match="demo1_native_dump"):
        mod.load_demo1_native_entry_ctx(3)
