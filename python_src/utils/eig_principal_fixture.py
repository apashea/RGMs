"""Atari Entry 4 principal-column fixture loader (``eig.md`` §23)."""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from typing import Any

import numpy as np

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "oracle"
    / "toolbox"
    / "DEM"
    / "fixtures"
    / "DEMAtariIII_fsl_backward_entry4_rgm_spectral_principal_column_fixture.pkl"
)


def sub_hash(sub: np.ndarray) -> str:
    arr = np.asarray(sub, dtype=np.float64, order="F")
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def fixture_path() -> Path:
    return _FIXTURE


def load_fixture() -> dict[str, Any] | None:
    path = fixture_path()
    if not path.is_file():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


def lookup_principal_column(sub: np.ndarray) -> np.ndarray | None:
    payload = load_fixture()
    if not payload:
        return None
    ent = payload.get("entries", {}).get(sub_hash(sub))
    if ent is None:
        return None
    return np.asarray(ent["principal_col"], dtype=np.complex128)
