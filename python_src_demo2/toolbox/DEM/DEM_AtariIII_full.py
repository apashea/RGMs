"""
ENTRY DEMO2 FULL ATARI — Python-native full ``DEM_AtariIII.m`` compute driver.

Runs ``run_dem_atariiii_full()`` from ``python_src_demo2`` (preamble via ``python_src`` DEMO1 path, or
resume from preamble PKL when ``RGMS_DEMO2_LOAD_PREAMBLE_CTX=1``).
See ``Atari_example.md`` § **ENTRY DEMO2 FULL ATARI** and § **Preamble boundary dumps**.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from python_src_demo2.toolbox.DEM.run_dem_atariiii_full import run_dem_atariiii_full


def run_dem_atariiii_full_demo() -> dict:
    """Lane A product entry — full native compute, no plotting."""
    return run_dem_atariiii_full()


def main(argv: list[str] | None = None) -> int:
    _ = argparse.ArgumentParser(
        description="ENTRY DEMO2 — full DEM_AtariIII.m compute (lane A, python_src_demo2)."
    ).parse_args(argv)
    t0 = time.perf_counter()
    ctx = run_dem_atariiii_full_demo()
    total_s = time.perf_counter() - t0
    print(
        f"[DEM_AtariIII_full] complete. demo2_np={ctx.get('demo2_np')!s} total_wall_s={total_s:.6f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
