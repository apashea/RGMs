"""Compare mat vs py child P and parent O[3] at 12E out_t2."""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIX = ROOT / "tests/oracle/toolbox/DEM/fixtures"
TAG = "rgms_canonical"


def _peak(v):
    a = np.asarray(v, dtype=float).ravel()
    return int(np.argmax(a) + 1), a.size, float(np.max(a)), a[:6].tolist()


def main() -> None:
    mat_path = FIX / f"DEMAtariIII_entry12_{TAG}_12E.mat"
    pkl_path = FIX / f"DEMAtariIII_entry12_{TAG}_12E.pkl"
    mat = loadmat(str(mat_path), struct_as_record=False, squeeze_me=True)
    with open(pkl_path, "rb") as f:
        py = pickle.load(f)

    for label, snap in [("mat", mat), ("py", py)]:
        # out_t2 boundary
        for key in ("out_t2", "out_t2_O"):
            if key not in snap and key not in getattr(snap, "_fieldnames", []):
                continue
        payload = snap.get("out_t2") if isinstance(snap, dict) else None
        if payload is None and hasattr(snap, "out_t2"):
            payload = snap.out_t2
        if payload is None:
            print(label, "keys", list(snap.keys()) if isinstance(snap, dict) else dir(snap))
            continue
        O = payload.get("O") if isinstance(payload, dict) else getattr(payload, "O", None)
        if O is None:
            print(label, "no O in out_t2")
            continue
        o3 = O[0][3] if isinstance(O[0], (list, tuple)) else O[3]
        print(f"{label} O[0][3]:", _peak(o3))

    # child after hierarchical from py run monitor - use 12E pkl full
    with open(pkl_path, "rb") as f:
        d = pickle.load(f)
    if "child_after" in d:
        ca = d["child_after"]
        if "P" in ca:
            for fi, Pf in enumerate(ca["P"]):
                print("py child P", fi, _peak(Pf[:, -1]))


if __name__ == "__main__":
    main()
