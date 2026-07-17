#!/usr/bin/env python3
"""OPTIM1 Product A — full-driver wall-time benchmark (timing only, not parity).

Runs ``run_dem_atariiii_optim(entry_stop=12)`` and reports wall time vs a static
fidelity reference from ``logs/demo1_thorough_run_step3_python_native.log`` (2026-06-14).

Parity sign-off is ``optim1_native_gate.py --tier3`` (strict ``NS``/``PDP.o`` compare).
This script does **not** assert optim ≡ fidelity.

Usage (repo root)::

    python tests/demo1/optim1/optim1_benchmark_native_full.py
    python tests/demo1/optim1/optim1_benchmark_native_full.py --live-fidelity
    python tests/demo1/optim1/optim1_benchmark_native_full.py --repeats 2
"""
from __future__ import annotations

import argparse
import io
import re
import statistics
import sys
import time
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_ENTRY_RE = re.compile(
    r"\[DEM_AtariIII entry timing\] ENTRY(\d+) total_s=([0-9.]+)"
)
_SECTION_RE = re.compile(
    r"\[DEM_AtariIII timing\] ([^:]+): section_s=([0-9.]+) total_elapsed_s=([0-9.]+)"
)

# DEMO1 Product A native reference (logs/demo1_thorough_run_step3_python_native.log)
_FIDELITY_REF_WALL = 1929.612
_FIDELITY_REF_ENTRIES = {
    1: 0.005,
    2: 0.113,
    3: 1119.303,
    4: 9.818,
    5: 0.012,
    6: 0.002,
    7: 22.245,
    8: 259.022,
    9: 449.205,
    10: 39.530,
    11: 0.348,
    12: 30.009,
}


def _parse_stderr(stderr: str) -> tuple[dict[int, float], dict[str, float]]:
    entries: dict[int, float] = {}
    sections: dict[str, float] = {}
    for line in stderr.splitlines():
        m = _ENTRY_RE.search(line)
        if m:
            entries[int(m.group(1))] = float(m.group(2))
            continue
        m = _SECTION_RE.search(line)
        if m:
            sections[m.group(1).strip()] = float(m.group(2))
    return entries, sections


def _run_optim_driver() -> tuple[dict[str, Any], float, dict[int, float], dict[str, float]]:
    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim

    buf = io.StringIO()
    t0 = time.perf_counter()
    with redirect_stderr(buf):
        ctx = run_dem_atariiii_optim(entry_stop=12)
    wall_s = time.perf_counter() - t0
    stderr = buf.getvalue()
    if stderr:
        print(stderr, file=sys.stderr, end="")
    entries, sections = _parse_stderr(stderr)
    return ctx, wall_s, entries, sections


def _run_fidelity_driver() -> tuple[dict[str, Any], float, dict[int, float], dict[str, float]]:
    from python_src.toolbox.DEM.DEM_AtariIII import run_dem_atariiii

    buf = io.StringIO()
    t0 = time.perf_counter()
    with redirect_stderr(buf):
        ctx = run_dem_atariiii(entry_stop=12)
    wall_s = time.perf_counter() - t0
    stderr = buf.getvalue()
    if stderr:
        print(stderr, file=sys.stderr, end="")
    entries, sections = _parse_stderr(stderr)
    return ctx, wall_s, entries, sections


def _format_md(
    *,
    optim_rows: list[dict[str, Any]],
    fidelity_wall: float,
    fidelity_source: str,
    out_path: Path,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    med_wall = float(statistics.median([r["wall_s"] for r in optim_rows]))
    speedup = 100.0 * (fidelity_wall - med_wall) / fidelity_wall if fidelity_wall > 0 else 0.0
    lines = [
        f"# OPTIM1 Product A native full-driver benchmark ({ts} UTC)",
        "",
        "**Timing only** — parity is ``optim1_native_gate.py --tier3`` (not this script).",
        "",
        f"- fidelity wall_s: **{fidelity_wall:.3f}** ({fidelity_source})",
        f"- optim repeats: **{len(optim_rows)}**",
        f"- optim median wall_s: **{med_wall:.3f}**",
        f"- median speedup vs fidelity: **{speedup:.1f}%** faster",
        f"- log: `{out_path}`",
        "",
        "## Optim repeats",
        "",
        "| Repeat | wall_s |",
        "|--------|--------|",
    ]
    for row in optim_rows:
        lines.append(f"| {row['repeat']} | {row['wall_s']:.3f} |")
    if optim_rows and optim_rows[-1].get("entries"):
        lines.extend(["", "## Optim per-entry (last repeat)", ""])
        lines.append("| Entry | Optim (s) | Fidelity ref (s) |")
        lines.append("|-------|-----------|------------------|")
        entries = optim_rows[-1]["entries"]
        for n in sorted(set(entries) | set(_FIDELITY_REF_ENTRIES)):
            o = entries.get(n)
            f = _FIDELITY_REF_ENTRIES.get(n)
            if o is None and f is None:
                continue
            o_s = f"{o:.3f}" if o is not None else "—"
            f_s = f"{f:.3f}" if f is not None else "—"
            lines.append(f"| {n} | {o_s} | {f_s} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 Product A native full-driver benchmark (timing only)")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument(
        "--live-fidelity",
        action="store_true",
        help="Re-run fidelity native driver for wall time (slow, ~32 min)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Markdown report (default logs/optim1_native_full_benchmark.md)",
    )
    args = p.parse_args(argv)
    repeats = max(1, int(args.repeats))

    fidelity_source = "static ref (demo1_thorough_run_step3_python_native.log)"
    fidelity_wall = _FIDELITY_REF_WALL

    if args.live_fidelity:
        print("[OPTIM1 native benchmark] running live fidelity driver (slow)", file=sys.stderr)
        _, fidelity_wall, _, _ = _run_fidelity_driver()
        fidelity_source = "live run"

    optim_rows: list[dict[str, Any]] = []
    for i in range(repeats):
        print(f"[OPTIM1 native benchmark] optim repeat {i + 1}/{repeats}", file=sys.stderr)
        _, wall_s, entries, sections = _run_optim_driver()
        optim_rows.append(
            {
                "repeat": i + 1,
                "wall_s": wall_s,
                "entries": entries,
                "sections": sections,
            }
        )

    out_path = args.out or (_REPO / "logs" / "optim1_native_full_benchmark.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        _format_md(
            optim_rows=optim_rows,
            fidelity_wall=fidelity_wall,
            fidelity_source=fidelity_source,
            out_path=out_path,
        ),
        encoding="utf-8",
    )
    med = float(statistics.median([r["wall_s"] for r in optim_rows]))
    print(
        f"[OPTIM1 native benchmark] optim median wall_s={med:.3f} "
        f"fidelity={fidelity_wall:.3f} wrote {out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
