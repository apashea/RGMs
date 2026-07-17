#!/usr/bin/env python3
"""FSL backward — run Entry 11 only on MATLAB-fed ``MDP`` (no ``entry_stop=11``).

Loads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry11.pkl`` (one-time materialize).
Writes ``fixtures/DEMAtariIII_fsl_backward_entry11_rdp.pkl`` (``RDP`` only).

Compare with ``fsl_backward_compare_entry11_pkl_to_mat.py``.

See ``Atari_example.md`` § **FSL backward validation (Entry 11 → 1)**.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _pre11_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_MDP_PRE11_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry11.pkl"


def _rdp_out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY11_RDP_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry11_rdp.pkl"


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry11 import run_entry11_assembly_from_mdp

    pre = _pre11_pkl()
    if not pre.is_file():
        print(
            f"[FSL backward Entry 11 isolated] missing {pre}\n"
            "Run: matlab dump_MDP_pre_entry11.m, then "
            "python fsl_backward_materialize_mdp_pre_entry11_pkl.py",
            file=sys.stderr,
        )
        return 2

    with pre.open("rb") as f:
        boundary = pickle.load(f)
    mdp = boundary["mdp"]
    c_val = float(boundary["C"])
    print(f"[FSL backward Entry 11 isolated] input {pre}", file=sys.stderr)

    from python_src.toolbox.DEM.fsl_backward_entry11 import entry11_rdp_for_entry12_vb

    rdp_asm = run_entry11_assembly_from_mdp(mdp, c_val=c_val)
    rdp_vb = entry11_rdp_for_entry12_vb(rdp_asm)
    out = _rdp_out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                "RDP": rdp_asm,
                "RDP_vb": rdp_vb,
                "C": c_val,
                "source_pre11_pkl": str(pre),
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 11 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
