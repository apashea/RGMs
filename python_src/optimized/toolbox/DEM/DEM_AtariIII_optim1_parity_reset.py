"""
OPTIM1 parity reset — delete OPTIM1-owned checkpoints only.

Never touches ``tests/demo1/fixtures/`` (DEMO1 authority).

Usage::

    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1_parity_reset.py
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1_parity_reset.py --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[4]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir, optim1_python_native_dir


def _targets() -> tuple[Path, ...]:
    return (
        optim1_fixtures_dir(),
        optim1_python_native_dir(),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 checkpoint reset (never DEMO1 fixtures)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    for path in _targets():
        if not path.exists():
            print(f"[OPTIM1 reset] skip (absent): {path}", file=sys.stderr)
            continue
        if args.dry_run:
            print(f"[OPTIM1 reset] would delete: {path}", file=sys.stderr)
        else:
            shutil.rmtree(path, ignore_errors=True)
            print(f"[OPTIM1 reset] deleted: {path}", file=sys.stderr)

    print("[OPTIM1 reset] done (DEMO1 fixtures untouched)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
