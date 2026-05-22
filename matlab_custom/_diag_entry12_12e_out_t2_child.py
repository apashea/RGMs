"""Compare nested child MDP fields at 12F boundaries (py vs mat) for 12E.out_t2 diagnosis."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
    _entry12_run_tag,
    _entry12_workspace_payload,
    _load_subentry_pkl,
    _mat_blob_to_py,
    _subentry_pkl_path,
)


def _nested_child(snap: dict) -> dict:
    m0 = snap["MDP"]
    if isinstance(m0, list):
        m0 = m0[0]
    c = m0["MDP"]
    if isinstance(c, list):
        c = c[0]
    return c


def _q_o_width(child: dict) -> int | None:
    q = child.get("Q")
    if not isinstance(q, dict):
        return None
    oc = q.get("O")
    if not isinstance(oc, (list, tuple)) or not oc:
        return None
    L = max(1, int(np.asarray(child.get("L", 1)).ravel()[0]))
    ol = oc[L - 1] if len(oc) >= L else oc[-1]
    a = np.asarray(ol)
    return int(a.shape[1]) if a.ndim >= 2 else int(a.size > 0)


def main() -> int:
    tag = _entry12_run_tag()
    py = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    f = 1  # factor 2 -> P{f}
    for key in ("out_t1", "out_t2", "out_t3"):
        pc, mc = _nested_child(py[key]), _nested_child(mat[key])
        Pf = np.asarray(pc["P"][f], dtype=np.float64)
        Mf = np.asarray(mc["P"][f], dtype=np.float64)
        print(f"\n=== 12F {key} ===")
        print(f"P{{2}} shape py {Pf.shape} mat {Mf.shape}")
        print(f"P{{2}} last py {Pf[:, -1].ravel()[:6]} mat {Mf[:, -1].ravel()[:6]}")
        print(f"Q.O width py {_q_o_width(pc)} mat {_q_o_width(mc)}")
        if "O" in pc:
            Oraw = pc["O"]
            if isinstance(Oraw, np.ndarray):
                print(f"child O shape py {Oraw.shape}")
            else:
                print(f"child O type py {type(Oraw).__name__} (cell/list)")
        if "S" in pc:
            print(f"S shape py {np.asarray(pc['S']).shape} mat {np.asarray(mc['S']).shape}")
        for label, c in ("py", pc), ("mat", mc):
            Ef = np.asarray(c["E"][f]).ravel()[:6]
            print(f"  {label} E{{2}} {Ef}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
