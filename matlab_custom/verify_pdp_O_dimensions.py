"""Truth report: PDP.O dimensions MATLAB .mat vs Python 12H pickle (rgms_canonical).

Read-only; not Entry 12 sign-off. Full (g,t) grid check after honest align.
"""
from __future__ import annotations

import copy
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(r"C:\Users\andre\.cursor\RGMs")
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    _entry12_align_mdp_O_ng_t_cells,
    _entry12_align_pdp_assemble_shell,
    default_entry12_mat_output_dir,
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

TAG = "rgms_canonical"
FIX = ROOT / "tests/oracle/toolbox/DEM/fixtures"
MAT_PATH = FIX / f"DEMAtariIII_entry12_{TAG}_12H.mat"
PKL_PATH = default_entry12_mat_output_dir() / f"DEMAtariIII_entry12_{TAG}_12H.pkl"


def _describe_o_list(label: str, o: list, sample_gt: tuple[int, int] | None = None) -> None:
    print(f"\n--- {label} ---")
    print(f"  type=list len={len(o)}")
    if not o:
        return
    e0 = o[0]
    if isinstance(e0, list):
        print(f"  layout: outer len={len(o)}; o[0] inner len={len(e0)} (interpret as time-outer if outer==T)")
        ng = len(e0)
        nt = len(o)
        print(f"  inferred T_outer={nt} Ng_inner={ng}")
        for t in [0, 1, nt - 1]:
            if t < nt and isinstance(o[t], list):
                for g in [0, 1, ng - 1]:
                    if g < len(o[t]):
                        leaf = np.asarray(o[t][g])
                        print(f"  O[{t}][{g}] shape={leaf.shape} dtype={leaf.dtype}")
    else:
        print(f"  o[0] type={type(e0).__name__} shape={np.asarray(e0).shape}")
    if sample_gt is not None:
        g, t = sample_gt
        if g < len(o) and isinstance(o[g], list) and t < len(o[g]):
            v = np.asarray(o[g][t], dtype=np.float64).ravel()
            print(f"  O{{{g+1},{t+1}}} MATLAB-style index sample first5: {v[:5]}")


def _full_grid_maxdiff(py_o: list, mat_o: list) -> tuple[float, int, int, int, int]:
    """Assume modality-outer mat_o[g][t] after align."""
    worst = 0.0
    wg = wt = -1
    n_ok = n_bad_shape = 0
    for g in range(len(py_o)):
        if not isinstance(py_o[g], list):
            continue
        for t in range(len(py_o[g])):
            if g >= len(mat_o) or not isinstance(mat_o[g], list):
                continue
            pv = np.asarray(py_o[g][t], dtype=np.float64).ravel()
            mv = np.asarray(mat_o[g][t], dtype=np.float64).ravel()
            if pv.size != mv.size:
                n_bad_shape += 1
                continue
            n_ok += 1
            d = float(np.max(np.abs(pv - mv))) if pv.size else 0.0
            if d > worst:
                worst, wg, wt = d, g, t
    return worst, wg, wt, n_ok, n_bad_shape


def main() -> None:
    print("=== scipy loadmat RAW (no simplify_cells) ===")
    raw = loadmat(str(MAT_PATH), simplify_cells=False)
    pdp_sa = raw["PDP"]
    if isinstance(pdp_sa, np.ndarray) and pdp_sa.dtype.names:
        o_field = pdp_sa["O"][0, 0]
        n_field = pdp_sa["n"][0, 0] if "n" in pdp_sa.dtype.names else None
        print(f"PDP.O raw loadmat: ndarray shape={o_field.shape} dtype={o_field.dtype}")
        if o_field.dtype == object:
            print(f"  numel={o_field.size} ndim={o_field.ndim} (Fortran ravel order for 2-D cell)")
            flat_f = o_field.ravel(order="F")
            print(f"  ravel(F)[0] type={type(flat_f[0])} sample shape={np.asarray(flat_f[0]).shape}")
        if n_field is not None:
            print(f"PDP.n raw shape={n_field.shape}")
    else:
        print(f"PDP unexpected type {type(pdp_sa)}")

    print("\n=== scipy loadmat simplify_cells=True ===")
    raw2 = loadmat(str(MAT_PATH), simplify_cells=True)
    pdp2 = raw2["PDP"]
    o2 = pdp2["O"] if isinstance(pdp2, dict) else pdp2
    if isinstance(pdp2, np.ndarray) and pdp2.dtype.names:
        o2 = pdp2["O"].item() if hasattr(pdp2["O"], "item") else pdp2["O"]
    print(f"PDP.O type={type(o2)}")
    if isinstance(o2, np.ndarray):
        print(f"  ndarray shape={o2.shape} dtype={o2.dtype}")
    elif isinstance(o2, list):
        print(f"  list len={len(o2)}")

    mat_pdp = mat_nested_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(TAG, "12H", out_dir=FIX)))["PDP"]
    py_pdp = pickle.load(open(PKL_PATH, "rb"))["PDP"]

    _describe_o_list("Python pickle PDP.O (raw)", py_pdp["O"])
    _describe_o_list("MATLAB convert PDP.O (raw)", mat_pdp["O"], sample_gt=(0, 0))

    n = np.asarray(mat_pdp.get("n"))
    print(f"\nPDP.n mat convert shape={n.shape}")
    ig = mat_pdp.get("id", {}).get("g")
    if ig is not None:
        print(f"PDP.id.g flat={np.asarray(ig).ravel()}")

    # Transpose align only (no full shell)
    po_raw = list(py_pdp["O"])
    mo_raw = list(mat_pdp["O"])
    aligned = _entry12_align_mdp_O_ng_t_cells(po_raw, mo_raw)
    print(f"\n=== After _entry12_align_mdp_O_ng_t_cells only ===")
    print(f"  py len {len(po_raw)} -> {len(aligned)}")
    _describe_o_list("aligned py O", aligned, sample_gt=(0, 0))
    worst, wg, wt, n_ok, n_bad = _full_grid_maxdiff(aligned, mo_raw)
    print(f"  FULL grid: cells compared={n_ok} shape_mismatch={n_bad}")
    print(f"  worst maxdiff={worst} at g={wg} t={wt} (0-based)")

    # Full shell
    py_c = copy.deepcopy(py_pdp)
    mat_c = mat_pdp
    _entry12_align_pdp_assemble_shell(py_c, mat_c)
    worst2, wg2, wt2, n_ok2, n_bad2 = _full_grid_maxdiff(py_c["O"], mat_c["O"])
    print(f"\n=== After _entry12_align_pdp_assemble_shell ===")
    print(f"  top PDP.O len py={len(py_c['O'])} mat={len(mat_c['O'])}")
    print(f"  FULL grid maxdiff={worst2} at g={wg2} t={wt2} n_ok={n_ok2} n_bad_shape={n_bad2}")

    # Nested MDP.O
    if "MDP" in py_pdp and "MDP" in mat_pdp:
        py_m = py_pdp["MDP"]["O"]
        mat_m = mat_pdp["MDP"]["O"]
        print(f"\n=== Nested PDP.MDP.O raw ===")
        print(f"  py len={len(py_m)} mat len={len(mat_m)}")
        if py_m and isinstance(py_m[0], list):
            print(f"  py time-outer: T={len(py_m)} Ng={len(py_m[0])}")
        am = _entry12_align_mdp_O_ng_t_cells(list(py_m), list(mat_m))
        w3, _, _, n3, b3 = _full_grid_maxdiff(am, list(mat_m))
        print(f"  after align: len={len(am)} full grid maxdiff={w3} n_ok={n3} n_bad={b3}")

    # Column-major flat index check: mat list from 20x64 cell -> element order
    if isinstance(o2, np.ndarray) and o2.dtype == object and o2.ndim == 2:
        ng, nt = o2.shape
        print(f"\n=== MATLAB column-major linear index on {ng}x{nt} cell ===")
        flat = o2.ravel(order="F")
        print(f"  ravel(F) len={len(flat)}; flat[0] shape={np.asarray(flat[0]).shape}")


if __name__ == "__main__":
    main()
