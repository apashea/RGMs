"""
DEMO2 — dump full preamble ``ctx`` after ``run_dem_atariiii(entry_stop=12)``.

Use once after a verified DEMO1-scale run to avoid re-running Entries **1–12**
during DEMO2 dev. See ``Atari_example.md`` § **ENTRY DEMO2 FULL ATARI** — **Preamble boundary dumps**.

Example::

    conda activate rgms
    cd C:\\Users\\andre\\.cursor\\RGMs
    $env:PYTHONPATH="C:\\Users\\andre\\.cursor\\RGMs"
    $env:RGMS_ATARI_TRAINING_T="10000"
    $env:RGMS_ATARI_ENTRY8_OUTER="128"
    python python_src_demo2/toolbox/DEM/DEM_AtariIII_dump_preamble.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii
from python_src_demo2.toolbox.DEM.demo2_preamble_ctx import (
    DEMO2_PREAMBLE_ENTRY_STOP,
    capture_native_scalar_rand,
    dump_demo2_preamble_bundle,
    resolve_demo2_preamble_ctx_pkl_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dump DEMO2 preamble bundle: ctx PKL + native rand mat + companion manifest "
            "(run_dem_atariiii entry_stop=12)."
        )
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output PKL (default: fixtures/DEMAtariIII_demo2_preamble_ctx.pkl or RGMS_DEMO2_PREAMBLE_CTX_PKL)",
    )
    args = parser.parse_args(argv)

    t0 = time.perf_counter()
    with capture_native_scalar_rand() as native_buf:
        ctx = run_dem_atariiii(entry_stop=DEMO2_PREAMBLE_ENTRY_STOP)
    wall_s = time.perf_counter() - t0
    out_path = args.out.resolve() if args.out is not None else resolve_demo2_preamble_ctx_pkl_path()
    bundle = dump_demo2_preamble_bundle(
        ctx,
        source="DEM_AtariIII_dump_preamble.py",
        native_rand_buf=list(native_buf),
        ctx_path=out_path,
    )
    print(
        f"[DEMO2 preamble] bundle dump complete wall_s={wall_s:.6f} "
        f"ctx={bundle['ctx_pkl']} native_rand={bundle['native_rand_mat']} "
        f"manifest={bundle['manifest_json']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
