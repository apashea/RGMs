#!/usr/bin/env python3
"""DEMO1 Product A — dump native authority fixtures (one fidelity run).

Runs ``run_dem_atariiii(entry_stop=12)`` once with seed **2**, captures ``ctx`` after
entries **3, 7, 9, 12**, and installs them under ``tests/demo1/python_native/fixtures/``
for OPTIM1 Product A pairing.

Usage (repo root)::

    conda activate rgms
    python tests/demo1/demo1_native_dump.py
    python tests/demo1/demo1_native_dump.py --check-only

OPTIM1 gate then compares optim-only runs to these fixtures (no live fidelity re-run).
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from contextlib import redirect_stderr
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_native_fixtures import (
    DEMO1_NATIVE_LADDER_ENTRY_STOPS,
    assert_demo1_native_fixtures_present,
    capture_env_for_native_dump,
    collect_driver_captures_to_fixtures,
    missing_demo1_native_entry_stops,
    write_demo1_native_manifest,
)
from tests.demo1.demo1_native_rng import seed_native_driver_rng


def dump_demo1_native_authority_fixtures() -> dict[int, Path]:
    """One seeded fidelity run → ladder fixtures on disk."""
    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii

    seed = seed_native_driver_rng()
    print(
        f"[DEMO1 native dump] seed={seed} entry_stop=12 capture posts={DEMO1_NATIVE_LADDER_ENTRY_STOPS}",
        file=sys.stderr,
    )
    cap_env = capture_env_for_native_dump()
    old = os.environ.copy()
    buf = io.StringIO()
    with redirect_stderr(buf):
        try:
            os.environ.update(cap_env)
            run_dem_atariiii(entry_stop=12)
        finally:
            os.environ.clear()
            os.environ.update(old)
    stderr = buf.getvalue()
    if stderr:
        print(stderr, file=sys.stderr, end="")

    written = collect_driver_captures_to_fixtures()
    write_demo1_native_manifest(rng_seed=seed, entry_stops=DEMO1_NATIVE_LADDER_ENTRY_STOPS)
    for n, path in sorted(written.items()):
        print(f"[DEMO1 native dump] wrote entry {n:02d} authority {path}", file=sys.stderr)
    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="DEMO1 Product A native authority dump (one run)")
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Verify all ladder fixtures present; do not run fidelity driver",
    )
    args = p.parse_args(argv)

    if args.check_only:
        missing = missing_demo1_native_entry_stops()
        if missing:
            print(f"[DEMO1 native dump] missing entry stops: {missing}", file=sys.stderr)
            return 2
        assert_demo1_native_fixtures_present()
        print("[DEMO1 native dump] authority fixtures OK", file=sys.stderr)
        return 0

    dump_demo1_native_authority_fixtures()
    print("[DEMO1 native dump] done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
