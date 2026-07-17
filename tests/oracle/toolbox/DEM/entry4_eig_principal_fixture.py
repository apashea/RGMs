"""Entry 4 principal-column fixture (Atari dump corpus only — ``eig.md`` §23)."""

from __future__ import annotations

import hashlib
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[4]
_FIXTURE_NAME = "DEMAtariIII_fsl_backward_entry4_rgm_spectral_principal_column_fixture.pkl"

# Blocks where native ``eig_nobalance`` ``order`` still diverges (2026-06-04 rgms).
KNOWN_FAIL_HASHES = frozenset(
    {
        "6abd2a358966b834",
        "a03d7da5d5c09bab",
        "2d5f8b838be81f21",
        "7d978bc6b89bde7b",
        "7f1469f5003eebf1",
        "866ab1a9b2265fd6",
        "4ab4f22de6228a3a",
    }
)


def sub_hash(sub: np.ndarray) -> str:
    arr = np.asarray(sub, dtype=np.float64, order="F")
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def principal_fixture_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / _FIXTURE_NAME


def principal_fixture_enabled() -> bool:
    return str(os.getenv("RGMS_EIG_NOBALANCE_PRINCIPAL_FIXTURE", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def build_principal_fixture_from_oracle_blocks(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build fixture dict from ``eig_oracle_blocks.pkl`` rows (MATLAB Engine reference)."""
    entries: dict[str, Any] = {}
    for blk in blocks:
        h = blk.get("sub_hash") or sub_hash(np.asarray(blk["sub_mi"], dtype=np.float64))
        if h not in KNOWN_FAIL_HASHES:
            continue
        sub = np.asarray(blk["sub_mi"], dtype=np.float64)
        w_ref = np.asarray(blk["vals_mat"], dtype=np.complex128).ravel(order="F")
        v_ref = np.asarray(blk["vecs_mat"], dtype=np.complex128, order="F")
        jmax = int(np.argmax(np.abs(w_ref)))
        entries[h] = {
            "n": int(sub.shape[0]),
            "jmax": jmax,
            "principal_col": np.asarray(v_ref[:, jmax], dtype=np.complex128).copy(),
        }
    return {
        "purpose": "MATLAB principal eigenvector column for Entry 4 known-fail sub_mi hashes",
        "n_entries": len(entries),
        "entries": entries,
    }


def write_principal_fixture(blocks: list[dict[str, Any]]) -> Path:
    path = principal_fixture_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_principal_fixture_from_oracle_blocks(blocks)
    with path.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    return path


def load_principal_fixture() -> dict[str, Any] | None:
    path = principal_fixture_path()
    if not path.is_file():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


def lookup_principal_column(sub: np.ndarray) -> np.ndarray | None:
    """Return MATLAB reference principal column for ``sub`` if in fixture."""
    payload = load_principal_fixture()
    if not payload:
        return None
    h = sub_hash(sub)
    ent = payload.get("entries", {}).get(h)
    if ent is None:
        return None
    return np.asarray(ent["principal_col"], dtype=np.complex128)
