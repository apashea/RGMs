#!/usr/bin/env python3
"""Write Tier A + dep MD5 manifest vs a w2_backup snapshot folder."""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]

_TIER_A = [
    "python_src/optimized/toolbox/DEM/vb_run_arena_optim.py",
    "python_src/optimized/toolbox/DEM/vb_workspace_optim.py",
    "python_src/optimized/toolbox/DEM/vb_orchestrator_optim.py",
    "python_src/optimized/toolbox/DEM/vb_forwards_optim.py",
    "python_src/optimized/toolbox/DEM/vb_induction_optim.py",
    "python_src/optimized/toolbox/DEM/vb_hierarchical_optim.py",
    "python_src/optimized/toolbox/DEM/vb_hierarchical_field_optim.py",
    "python_src/optimized/toolbox/DEM/vb_entry_optim.py",
    "python_src/optimized/toolbox/DEM/vb_cold_optim.py",
    "python_src/optimized/toolbox/DEM/spm_MDP_VB_XXX_optim.py",
    "python_src/optimized/toolbox/DEM/vb_optim_deepcopy.py",
    "python_src/optimized/toolbox/DEM/vb_policy_engine_optim.py",
    "python_src/optimized/toolbox/DEM/vb_VBX_optim.py",
    "python_src/optimized/toolbox/DEM/vb_contract_optim.py",
    "python_src/optimized/toolbox/DEM/vb_t_loop_optim.py",
    "python_src/optimized/toolbox/DEM/vb_child_kernel_optim.py",
    "python_src/optimized/toolbox/DEM/vb_lifecycle_optim.py",
]

_DEPS = [
    "python_src/optimized/toolbox/DEM/vb_primitives_optim.py",
    "matlab_compat.py",
    "python_src/spm_dot.py",
]


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest().upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="Folder under notes/w2_backup/")
    ap.add_argument("--label", default="MD5 manifest")
    ap.add_argument("--out", required=True, help="Log path under logs/")
    args = ap.parse_args()
    snap = Path(args.snapshot)
    if not snap.is_absolute():
        snap = _REPO / snap
    out = Path(args.out)
    if not out.is_absolute():
        out = _REPO / out
    lines = [
        f"{args.label} {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Restore source: {snap.relative_to(_REPO)}",
        "",
        "--- Tier A (17) ---",
    ]
    ok = True
    for rel in _TIER_A:
        live = _REPO / rel
        bak = snap / rel
        hl = _md5(live)
        hb = _md5(bak)
        match = hl == hb
        ok = ok and match
        tag = "MATCH" if match else "MISMATCH"
        lines.append(f"{tag}  {rel}  live={hl}  snap={hb}")
    lines += ["", "--- Hot-path deps (not in snapshot) ---"]
    for rel in _DEPS:
        p = _REPO / rel
        lines.append(f"live={_md5(p)}  {rel}")
    lines += ["", f"Tier A snap match: {ok}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
