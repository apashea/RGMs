#!/usr/bin/env python3
"""OPTIM1 Entry 8+9 timing benchmark — repeated fidelity vs optim combined loop.

Fair speed comparison on the **same** ``pre_entry9.pkl`` boundary and ``n_outer``.
Writes summary to ``logs/optim1_entry89_benchmark.md`` (does not mutate DEMO1 fixtures).

Usage (repo root)::

    python tests/demo1/optim1/optim1_benchmark_entry89.py --repeats 2
    python tests/demo1/optim1/optim1_benchmark_entry89.py --lane fidelity --repeats 1
    python tests/demo1/optim1/optim1_benchmark_entry89.py --lane optim --repeats 2
"""
from __future__ import annotations

import argparse
import copy
import pickle
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.demo1.demo1_paths import demo1_fixtures_dir


def _load_boundary(pre9: Path) -> dict[str, Any]:
    with pre9.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {pre9}")
    return blob


def _run_fidelity_combined(boundary: dict[str, Any]) -> dict[str, float]:
    from python_src.toolbox.DEM.fsl_backward_entry9 import run_entry9_from_boundary

    t0 = time.perf_counter()
    out = run_entry9_from_boundary(copy.deepcopy(boundary))
    wall_s = time.perf_counter() - t0
    return {
        "entry8_loop_s": float(out["entry8_loop_s"]),
        "entry9_loop_s": float(out["entry9_loop_s"]),
        "wall_s": wall_s,
    }


def _run_optim_combined(boundary: dict[str, Any]) -> dict[str, float]:
    from python_src.optimized.toolbox.DEM.fsl_backward_entry9_optim import (
        run_entry9_optim_from_boundary,
    )

    t0 = time.perf_counter()
    out = run_entry9_optim_from_boundary(copy.deepcopy(boundary))
    wall_s = time.perf_counter() - t0
    return {
        "entry8_loop_s": float(out["entry8_loop_s"]),
        "entry9_loop_s": float(out["entry9_loop_s"]),
        "wall_s": wall_s,
    }


def _median_row(rows: list[dict[str, float]], key: str) -> float:
    return float(statistics.median([r[key] for r in rows]))


def _format_md_table(rows: list[tuple[str, dict[str, float]]]) -> str:
    lines = [
        "| Lane | Repeat | entry8_loop_s | entry9_loop_s | wall_s |",
        "|------|--------|---------------|---------------|--------|",
    ]
    for label, row in rows:
        lines.append(
            f"| {label} | {row.get('repeat', '-')} | "
            f"{row['entry8_loop_s']:.3f} | {row['entry9_loop_s']:.3f} | {row['wall_s']:.3f} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Entry 8+9 repeated timing benchmark")
    p.add_argument("--pre-entry9", type=Path, default=None)
    p.add_argument("--repeats", type=int, default=2, help="Repeats per lane (default 2)")
    p.add_argument(
        "--lane",
        choices=("fidelity", "optim", "both"),
        default="both",
        help="Which lane(s) to benchmark",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Markdown summary (default logs/optim1_entry89_benchmark.md)",
    )
    args = p.parse_args(argv)

    if args.repeats < 1:
        print("[OPTIM1 benchmark] --repeats must be >= 1", file=sys.stderr)
        return 2

    pre9 = args.pre_entry9 or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
    )
    if not pre9.is_file():
        print(f"[OPTIM1 benchmark] missing {pre9}", file=sys.stderr)
        return 2

    boundary = _load_boundary(pre9)
    n_outer = int(boundary.get("n_outer", 128))
    out_path = args.out or (_REPO / "logs" / "optim1_entry89_benchmark.md")

    fidelity_rows: list[dict[str, float]] = []
    optim_rows: list[dict[str, float]] = []
    table_rows: list[tuple[str, dict[str, float]]] = []

    for rep in range(1, int(args.repeats) + 1):
        if args.lane in ("fidelity", "both"):
            print(f"[OPTIM1 benchmark] fidelity combined repeat {rep}/{args.repeats}", file=sys.stderr)
            row = _run_fidelity_combined(boundary)
            row["repeat"] = rep
            fidelity_rows.append(row)
            table_rows.append(("fidelity", row))
            print(
                f"[OPTIM1 benchmark] fidelity rep={rep} "
                f"entry8={row['entry8_loop_s']:.3f} entry9={row['entry9_loop_s']:.3f} "
                f"wall={row['wall_s']:.3f}",
                file=sys.stderr,
            )
        if args.lane in ("optim", "both"):
            print(f"[OPTIM1 benchmark] optim combined repeat {rep}/{args.repeats}", file=sys.stderr)
            row = _run_optim_combined(boundary)
            row["repeat"] = rep
            optim_rows.append(row)
            table_rows.append(("optim (current)", row))
            print(
                f"[OPTIM1 benchmark] optim rep={rep} "
                f"entry8={row['entry8_loop_s']:.3f} entry9={row['entry9_loop_s']:.3f} "
                f"wall={row['wall_s']:.3f}",
                file=sys.stderr,
            )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        f"# OPTIM1 Entry 8+9 benchmark ({ts} UTC)",
        "",
        f"- pre_entry9: `{pre9}`",
        f"- Ne={boundary.get('Ne')} NT={boundary.get('NT')} n_outer={n_outer}",
        f"- repeats per lane: {args.repeats}",
        f"- lane: {args.lane}",
        "",
        _format_md_table(table_rows),
        "",
    ]

    if fidelity_rows:
        parts.extend(
            [
                "## Fidelity isolated median",
                "",
                f"- entry8_loop_s: **{_median_row(fidelity_rows, 'entry8_loop_s'):.3f}**",
                f"- entry9_loop_s: **{_median_row(fidelity_rows, 'entry9_loop_s'):.3f}**",
                f"- wall_s: **{_median_row(fidelity_rows, 'wall_s'):.3f}**",
                "",
            ]
        )
    if optim_rows:
        parts.extend(
            [
                "## Optim (current) median",
                "",
                f"- entry8_loop_s: **{_median_row(optim_rows, 'entry8_loop_s'):.3f}**",
                f"- entry9_loop_s: **{_median_row(optim_rows, 'entry9_loop_s'):.3f}**",
                f"- wall_s: **{_median_row(optim_rows, 'wall_s'):.3f}**",
                "",
            ]
        )
    if fidelity_rows and optim_rows:
        fw = _median_row(fidelity_rows, "wall_s")
        ow = _median_row(optim_rows, "wall_s")
        pct = 100.0 * (fw - ow) / fw if fw > 0 else 0.0
        parts.extend(
            [
                "## Median comparison (optim vs fidelity wall_s)",
                "",
                f"- optim median wall_s is **{pct:.1f}%** {'faster' if pct >= 0 else 'slower'} than fidelity",
                "",
                "Historical single-run reference (low-risk, pre-B1): optim wall **1006 s** — see §6.4.",
                "",
            ]
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"[OPTIM1 benchmark] wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
