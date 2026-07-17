#!/usr/bin/env python3
"""Call-4 ledger VB vs MATLAB fence — causal field order (not alphabetical F-first).

Reuses the NR-localizer field-order helpers so the first reported red is the earliest
VB output, not the free-energy aggregate. Optim lane only (fidelity ≡ optim on F).

Report: ``matlab_custom/optim1full_call4_pdp_causal_fields_diag.txt``.
"""
from __future__ import annotations

import copy
import pickle
import sys
import traceback
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from python_src.toolbox.DEM.entry12_matlab_capture import (
        entry12_align_mdp_to_mat_workspace,
        entry12_mat_pdp_for_value_assert,
    )
    from tests.demo1.optim1full.optim1full_localize_optim_nr_vs_matlab_trace import (
        _diagnose_divergence,
        _first_col_divergence,
    )
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_call4_rdp_pkl,
        optim1full_plot_fence_matlab_pdp_mat,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        spm_mdp_vb_xxx_with_ledger_segment_reuse,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp

    report = _REPO / "matlab_custom" / "optim1full_call4_pdp_causal_fields_diag.txt"
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        lines.append(msg)

    rdp_pkl = optim1full_call4_rdp_pkl()
    mat_pdp_path = optim1full_plot_fence_matlab_pdp_mat("dem_with_compression_rgb")
    with rdp_pkl.open("rb") as f:
        rdp = pickle.load(f)["rdp"]
    buf, manifest = load_validated_optim1full_ledger()
    seg = manifest.segment("vb_call4")
    log(f"RDP={rdp_pkl.name}  MATLAB_PDP={mat_pdp_path.name}")
    log(f"vb_call4 start={seg.start} k={seg.k}  lane=optim")

    mat_raw = _load_matlab_pdp(mat_pdp_path)
    mat_cmp = entry12_mat_pdp_for_value_assert(copy.deepcopy(mat_raw))

    pdp = spm_mdp_vb_xxx_with_ledger_segment_reuse(
        copy.deepcopy(rdp),
        buf,
        start=seg.start,
        k=seg.k,
        extra_vb_kwargs={"monitoring": False},
        vb_lane="optim",
    )
    py_cmp = entry12_align_mdp_to_mat_workspace(
        entry12_mat_pdp_for_value_assert(copy.deepcopy(pdp)),
        mat_cmp,
    )

    py_f = np.asarray(py_cmp.get("F"), dtype=float).ravel()
    mat_f = np.asarray(mat_cmp.get("F"), dtype=float).ravel()
    log(f"PDP.F max abs = {float(np.max(np.abs(py_f - mat_f)))}")

    reds = _diagnose_divergence(py_cmp, mat_cmp)
    log(f"diverging top-level/Q fields (VB compute order): {len(reds)}")
    for path, msg, mx, causal in reds:
        flag = " CAUSAL" if causal else ""
        mx_s = f" maxabs={mx:.6g}" if mx is not None else ""
        # keep message short
        short = msg if len(msg) < 160 else msg[:157] + "..."
        log(f"  {path}{flag}{mx_s}: {short}")

    if reds:
        log("--- first red (compute order) ---")
        log(f"{reds[0][0]}: {reds[0][1]}")

    log("--- trajectory first-col divergence (s/o/u/X/O) ---")
    for fld in ("s", "o", "u", "X", "O"):
        if fld not in py_cmp or fld not in mat_cmp:
            log(f"  {fld}: missing py={fld in py_cmp} mat={fld in mat_cmp}")
            continue
        res = _first_col_divergence(py_cmp[fld], mat_cmp[fld])
        if res is None:
            log(f"  {fld}: equal (or incomparable)")
        else:
            t, py_v, mat_v = res
            log(f"  {fld}: FIRST diverge at t={t} py={py_v} mat={mat_v}")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {report}")
    return 1 if reds else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
