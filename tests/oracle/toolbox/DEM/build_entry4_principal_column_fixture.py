#!/usr/bin/env python3
"""Build Entry 4 principal-column fixture from oracle blocks PKL."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO))

from python_src.utils.eig_principal_fixture import fixture_path
from tests.oracle.toolbox.DEM.entry4_eig_principal_fixture import (
    KNOWN_FAIL_HASHES,
    build_principal_fixture_from_oracle_blocks,
)
from tests.oracle.toolbox.DEM.entry4_eig_dump_paths import entry4_eig_oracle_blocks_pkl


def main() -> int:
    blocks_path = entry4_eig_oracle_blocks_pkl()
    if not blocks_path.is_file():
        print(f"missing {blocks_path}", file=sys.stderr)
        return 2
    with blocks_path.open("rb") as f:
        blocks = pickle.load(f)["blocks"]
    payload = build_principal_fixture_from_oracle_blocks(blocks)
    if payload["n_entries"] != len(KNOWN_FAIL_HASHES):
        print(
            f"expected {len(KNOWN_FAIL_HASHES)} entries, got {payload['n_entries']}",
            file=sys.stderr,
        )
        return 1
    out = fixture_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"wrote {out} n_entries={payload['n_entries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
