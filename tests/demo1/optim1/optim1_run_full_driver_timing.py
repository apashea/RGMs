#!/usr/bin/env python3
"""OPTIM1 full-driver timing — ``run_dem_atariiii_optim(entry_stop=12)`` section breakdown.

Runs the holistic OPTIM1 driver and parses ``[DEM_AtariIII entry timing]`` / section lines
from stderr. Writes ``logs/optim1_full_driver_timing.md``.

Includes static fidelity reference from ``logs/demo1_thorough_run_step3_python_native.log``
(DEMO1 Product A native, pre-OPTIM1) for section comparison — not a live re-run.

Usage (repo root)::

    python tests/demo1/optim1/optim1_run_full_driver_timing.py
    python tests/demo1/optim1/optim1_run_full_driver_timing.py --entry-stop 9
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_ENTRY_RE = re.compile(
    r"\[DEM_AtariIII entry timing\] ENTRY(\d+) total_s=([0-9.]+)"
)
_SECTION_RE = re.compile(
    r"\[DEM_AtariIII timing\] ([^:]+): section_s=([0-9.]+) total_elapsed_s=([0-9.]+)"
)

# DEMO1 fidelity native reference (logs/demo1_thorough_run_step3_python_native.log, 2026-06-14)
_FIDELITY_REF = {
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
_FIDELITY_SECTIONS = {
    "Data Generation": 1119.303,
    "Merge Structure Learning": 708.258,
}


def _parse_stderr(stderr: str) -> tuple[dict[int, float], dict[str, tuple[float, float]]]:
    entries: dict[int, float] = {}
    sections: dict[str, tuple[float, float]] = {}
    for line in stderr.splitlines():
        m = _ENTRY_RE.search(line)
        if m:
            entries[int(m.group(1))] = float(m.group(2))
            continue
        m = _SECTION_RE.search(line)
        if m:
            sections[m.group(1).strip()] = (float(m.group(2)), float(m.group(3)))
    return entries, sections


def _format_md(
    *,
    entry_stop: int,
    wall_s: float,
    entries: dict[int, float],
    sections: dict[str, tuple[float, float]],
    out_path: Path,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# OPTIM1 full driver timing ({ts} UTC)",
        "",
        f"- driver: `run_dem_atariiii_optim(entry_stop={entry_stop})`",
        f"- wall_s: **{wall_s:.3f}**",
        f"- log: `{out_path}`",
        "",
        "## Per-entry wall time (optim vs fidelity reference)",
        "",
        "| Entry | Optim (s) | Fidelity ref (s) | Δ vs ref |",
        "|-------|-----------|------------------|----------|",
    ]
    for n in sorted(set(entries) | set(_FIDELITY_REF)):
        o = entries.get(n)
        f = _FIDELITY_REF.get(n)
        if o is None and f is None:
            continue
        o_s = f"{o:.3f}" if o is not None else "—"
        f_s = f"{f:.3f}" if f is not None else "—"
        if o is not None and f is not None and f > 0:
            pct = 100.0 * (f - o) / f
            delta = f"{pct:+.1f}%"
        else:
            delta = "—"
        lines.append(f"| {n} | {o_s} | {f_s} | {delta} |")
    lines.extend(["", "## Named sections", ""])
    if sections:
        lines.append("| Section | section_s | total_elapsed_s | Fidelity ref section_s |")
        lines.append("|---------|-----------|-----------------|------------------------|")
        for name, (sec_s, tot_s) in sections.items():
            ref = _FIDELITY_SECTIONS.get(name)
            ref_s = f"{ref:.3f}" if ref is not None else "—"
            lines.append(f"| {name} | {sec_s:.3f} | {tot_s:.3f} | {ref_s} |")
    else:
        lines.append("(no section timing lines — run did not reach Entry 3 or 9)")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **Fidelity ref** = DEMO1 Product A native run (`demo1_thorough_run_step3_python_native.log`); "
            "not re-run here — Entries **11** / **12** deltas are not optim regressions.",
            "- **Optim entries:** **3**, **4**, **7**, **8**, **9**, **10** in `run_dem_atariiii_optim`; "
            "all others fidelity.",
            "- **Fair per-entry speed:** use isolated scale runners (§8.0); holistic wall varies with load (8+9).",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1 full driver timing report")
    p.add_argument("--entry-stop", type=int, default=12)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Markdown report (default logs/optim1_full_driver_timing.md)",
    )
    args = p.parse_args(argv)
    entry_stop = int(args.entry_stop)
    if entry_stop < 1 or entry_stop > 12:
        print("[OPTIM1 full driver timing] --entry-stop must be 1..12", file=sys.stderr)
        return 2

    from python_src.optimized.toolbox.DEM.DEM_AtariIII_optim import run_dem_atariiii_optim

    import io
    from contextlib import redirect_stderr

    print(
        f"[OPTIM1 full driver timing] run_dem_atariiii_optim(entry_stop={entry_stop})",
        file=sys.stderr,
    )
    buf = io.StringIO()
    t0 = time.perf_counter()
    with redirect_stderr(buf):
        run_dem_atariiii_optim(entry_stop=entry_stop)
    wall_s = time.perf_counter() - t0
    stderr = buf.getvalue()
    if stderr:
        print(stderr, file=sys.stderr, end="")

    entries, sections = _parse_stderr(stderr)
    out_path = args.out or (_REPO / "logs" / "optim1_full_driver_timing.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        _format_md(
            entry_stop=entry_stop,
            wall_s=wall_s,
            entries=entries,
            sections=sections,
            out_path=out_path,
        ),
        encoding="utf-8",
    )
    print(f"[OPTIM1 full driver timing] wall_s={wall_s:.3f} wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
