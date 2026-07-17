"""
OPTIM1FULL Product B — MATLAB-paired parity orchestrator.

**Not** Product A native (`DEM_AtariIII_optim1full_python.py`). See ``OPTIM1.md`` § **11.0.2**.

Usage (repo root)::

    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1full_parity.py --check-authority
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1full_parity.py --tier1
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1full_parity.py --tier2
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1full_parity.py --gate --tier1 --tier2
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1full_parity.py --full-replay            # optim (default)
    python python_src/optimized/toolbox/DEM/DEM_AtariIII_optim1full_parity.py --full-replay --vb-fidelity  # fidelity diagnostic
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[4]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))


def _gate_argv(ns: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if ns.check_authority:
        argv.append("--check-authority")
    if ns.tier1:
        argv.append("--tier1")
    if ns.tier2:
        argv.append("--tier2")
    if ns.tier3a:
        argv.append("--tier3a")
    if ns.tier3e:
        argv.append("--tier3e")
    if ns.tier3f:
        argv.append("--tier3f")
    if ns.tier3g or ns.tier3:
        argv.append("--tier3g")
    if ns.plot_oracle:
        argv.append("--plot-oracle")
    # Forward the fidelity diagnostic override so it survives gate delegation (optim is the
    # default; --vb-dev-optim is a no-op and need not be forwarded).
    if getattr(ns, "vb_fidelity", False):
        argv.append("--vb-fidelity")
    return argv


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OPTIM1FULL Product B parity orchestrator")
    p.add_argument("--check-authority", action="store_true")
    p.add_argument("--tier1", action="store_true", help="MI boundaries")
    p.add_argument("--tier2", action="store_true", help="call-3 assembly")
    p.add_argument("--tier3a", action="store_true", help="call-2 game 1 VB (Entry 12)")
    p.add_argument("--tier3e", action="store_true", help="call-3 VB (Entry 12)")
    p.add_argument("--tier3f", action="store_true", help="call-4 VB (Entry 12)")
    p.add_argument("--tier3g", action="store_true", help="full MDP_post_nr (blocked)")
    p.add_argument("--tier3", action="store_true", help="alias for --tier3g")
    p.add_argument(
        "--plot-oracle",
        action="store_true",
        help="fixture-first plot pytest via optim1full_parity_gate (W1-C)",
    )
    p.add_argument("--gate", action="store_true", help="delegate to optim1full_parity_gate.py")
    p.add_argument(
        "--full-replay",
        action="store_true",
        help="run run_dem_atariiii_optim1full_parity() (long; no compare yet)",
    )
    p.add_argument("--deadline-minutes", default="120")
    from tests.demo1.optim1full.optim1full_vb_dispatch import (
        add_vb_dev_optim_cli_argument,
        apply_vb_dev_optim_cli,
        optim1full_vb_dev_optim_enabled,
    )

    add_vb_dev_optim_cli_argument(p)
    ns = p.parse_args(argv)
    apply_vb_dev_optim_cli(ns)

    if (
        ns.gate
        or ns.check_authority
        or ns.tier1
        or ns.tier2
        or ns.tier3a
        or ns.tier3e
        or ns.tier3f
        or ns.tier3g
        or ns.tier3
        or ns.plot_oracle
    ):
        gate_argv = _gate_argv(ns)
        if not gate_argv:
            gate_argv = ["--check-authority"]
        cmd = [sys.executable, str(_repo / "tests/demo1/optim1full/optim1full_parity_gate.py"), *gate_argv]
        rc = subprocess.call(cmd, cwd=str(_repo))
        if rc != 0:
            return rc
        if ns.full_replay:
            pass
        elif not (
            ns.tier1
            or ns.tier2
            or ns.tier3a
            or ns.tier3e
            or ns.tier3f
            or ns.tier3g
            or ns.tier3
            or ns.plot_oracle
        ):
            return 0

    if ns.full_replay:
        from python_src.optimized.toolbox.DEM.run_dem_atariiii_optim1full_parity import (
            run_dem_atariiii_optim1full_parity,
        )

        print("[OPTIM1FULL Product B] full replay run starting", file=sys.stderr)
        if optim1full_vb_dev_optim_enabled():
            print(
                "[OPTIM1FULL Product B] vb_lane=optim (default go-forward — spm_MDP_VB_XXX_optim)",
                file=sys.stderr,
            )
        else:
            print(
                "[OPTIM1FULL Product B] vb_lane=fidelity (--vb-fidelity diagnostic — spm_MDP_VB_XXX)",
                file=sys.stderr,
            )
        ctx = run_dem_atariiii_optim1full_parity(deadline_minutes=str(ns.deadline_minutes))
        np_val = ctx.get("optim1full_np")
        print(f"[OPTIM1FULL Product B] full replay complete optim1full_np={np_val}", file=sys.stderr)
        return 0

    if not (
        ns.gate
        or ns.check_authority
        or ns.tier1
        or ns.tier2
        or ns.tier3a
        or ns.tier3e
        or ns.tier3f
        or ns.tier3g
        or ns.tier3
        or ns.plot_oracle
        or ns.full_replay
    ):
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
