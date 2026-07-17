#!/usr/bin/env python3
"""One-shot reverify: Tier A MD5 vs w2_backup snapshot + XXX_comp optim import chain."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_SNAP = "notes/w2_backup/PASS2-shareQ_C4ab_pre_20260710_1125"

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

_IMPORT_MODS = [
    "python_src.optimized.toolbox.DEM.spm_MDP_VB_XXX_optim",
    "python_src.optimized.toolbox.DEM.vb_entry_optim",
    "python_src.optimized.toolbox.DEM.vb_contract_optim",
    "python_src.optimized.toolbox.DEM.vb_t_loop_optim",
    "python_src.optimized.toolbox.DEM.vb_induction_optim",
]


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest().upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--snapshot",
        default=_DEFAULT_SNAP,
        help="w2_backup folder (default: C4ab restore point)",
    )
    args = ap.parse_args()
    snap = Path(args.snapshot)
    if not snap.is_absolute():
        snap = _REPO / snap

    print(f"[REVERIFY] repo={_REPO}")
    print(f"[REVERIFY] python={sys.executable}")
    print(f"[REVERIFY] cwd={Path.cwd()}")
    print(f"[REVERIFY] snapshot={snap}")
    print("--- Tier A live vs snapshot ---")
    mismatches: list[str] = []
    for rel in _TIER_A:
        live = _REPO / rel
        bak = snap / rel
        hl = _md5(live)
        hb = _md5(bak)
        ok = hl == hb
        if not ok:
            mismatches.append(rel)
        tag = "MATCH" if ok else "MISMATCH"
        print(f"{tag} {rel}")
        print(f"  live={hl}")
        print(f"  snap={hb}")
    print("--- Hot-path deps (not snapshotted) ---")
    for rel in _DEPS:
        p = _REPO / rel
        if p.is_file():
            print(f"live={_md5(p)}  {rel}")
        else:
            print(f"MISSING  {rel}")
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    from tests.demo1.optim1full import xxx_comp_call4 as xc
    from tests.demo1.optim1full.optim1full_vb_dispatch import spm_mdp_vb_xxx_callable

    vb_fn = spm_mdp_vb_xxx_callable("optim")
    print("--- XXX_comp optim lane ---")
    print(f"TAG={xc.TAG!r}")
    print(f"OPTIM_PKL={xc.OPTIM_PKL}")
    print(f"spm_mdp_vb_xxx_callable(optim)={vb_fn}")
    print(f"callable.__module__={vb_fn.__module__}")
    print(f"callable.__qualname__={vb_fn.__qualname__}")
    print("--- Imported module files (post-import) ---")
    for name in _IMPORT_MODS:
        mod = importlib.import_module(name)
        p = Path(mod.__file__).resolve()
        print(f"module={name}")
        print(f"  file={p}")
        print(f"  md5={_md5(p)}")
    print(f"--- SUMMARY: Tier A mismatches={len(mismatches)} ---")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
