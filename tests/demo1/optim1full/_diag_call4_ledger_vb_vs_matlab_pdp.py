#!/usr/bin/env python3
"""Diagnostic: call-4 PDP on proven-equal assembled RDP + ledger vb_call4 segment.

Assembled call-4 INPUT RDP is proven ≡ MATLAB (tier-2-style compare PASS). The plot-fence
``PDP.F`` red is therefore downstream of assembly. This diagnostic:

1. Loads ``DEMAtariIII_optim1full_call4_rdp.pkl`` (proven assembly).
2. Runs **optim** and **fidelity** VB with the Model B ledger ``vb_call4`` segment (k=4096).
3. Compares each lane's ``PDP.F`` (and full nested assert) to the independent MATLAB
   fence ``DEMAtariIII_optim1full_dem_with_compression_rgb_matlab_pdp.mat``.

Report: ``matlab_custom/optim1full_call4_ledger_vb_vs_matlab_pdp_diag.txt``.
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
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_mat_pdp_for_value_assert
    from tests.demo1.optim1full.optim1full_paths import (
        optim1full_call4_rdp_pkl,
        optim1full_plot_fence_matlab_pdp_mat,
    )
    from tests.demo1.optim1full.optim1full_rand_ledger import (
        load_validated_optim1full_ledger,
        spm_mdp_vb_xxx_with_ledger_segment_reuse,
    )
    from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import _load_matlab_pdp
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    report = _REPO / "matlab_custom" / "optim1full_call4_ledger_vb_vs_matlab_pdp_diag.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, file=sys.stderr, flush=True)
        lines.append(msg)

    rdp_pkl = optim1full_call4_rdp_pkl()
    mat_pdp = optim1full_plot_fence_matlab_pdp_mat("dem_with_compression_rgb")
    if not rdp_pkl.is_file():
        log(f"missing call4 RDP pkl: {rdp_pkl}")
        return 2
    if not mat_pdp.is_file():
        log(f"missing matlab fence PDP: {mat_pdp}")
        return 2

    with rdp_pkl.open("rb") as f:
        payload = pickle.load(f)
    rdp = payload["rdp"]
    buf, manifest = load_validated_optim1full_ledger()
    seg = manifest.segment("vb_call4")
    log(f"RDP={rdp_pkl.name}  MATLAB_PDP={mat_pdp.name}")
    log(f"vb_call4 segment start={seg.start} k={seg.k}")

    mat_raw = _load_matlab_pdp(mat_pdp)
    mat_cmp = entry12_mat_pdp_for_value_assert(copy.deepcopy(mat_raw))
    mat_f = np.asarray(mat_cmp.get("F"), dtype=float).ravel()

    results: dict[str, int] = {}
    for lane in ("optim", "fidelity"):
        log(f"--- lane={lane} ---")
        pdp = spm_mdp_vb_xxx_with_ledger_segment_reuse(
            copy.deepcopy(rdp),
            buf,
            start=seg.start,
            k=seg.k,
            extra_vb_kwargs={"monitoring": False},
            vb_lane=lane,
        )
        py_f = np.asarray(pdp.get("F"), dtype=float).ravel()
        if py_f.shape != mat_f.shape:
            log(f"F shape py={py_f.shape} mat={mat_f.shape}")
            results[lane] = 1
            continue
        max_abs = float(np.max(np.abs(py_f - mat_f))) if py_f.size else 0.0
        log(f"PDP.F max abs diff vs MATLAB fence = {max_abs}")
        try:
            _assert_nested_rdp_equal(pdp, mat_cmp, f"call4 ledger VB ({lane}) vs matlab_pdp")
            log(f"RESULT {lane}: PASS full PDP")
            results[lane] = 0
        except AssertionError as exc:
            log(f"RESULT {lane}: FAIL — {exc}")
            results[lane] = 1

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {report}")
    # Exit 0 only if both lanes pass; else 1 so we see the signal clearly.
    return 0 if all(v == 0 for v in results.values()) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
