"""Replicate hierarchical id.E update for child P{2} at parent t=2; mat vs py."""
from __future__ import annotations

import copy
import sys

import numpy as np

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.spm_dot import spm_dot
from python_src.toolbox.DEM.entry12_matlab_capture import (
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
)
from python_src.toolbox.DEM.spm_parents import spm_parents
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _spm_multiply, _vb_q_row_for_parents
from tests.oracle.toolbox.DEM.XXX_12_compare_pdp_pkl_to_mat import (
    _entry12_run_tag,
    _entry12_workspace_payload,
    _load_subentry_pkl,
    _mat_blob_to_py,
    _subentry_pkl_path,
)

F = 1
G_OUT = 4  # parent modality g=4 -> O[3]


def _child(snap):
    m0 = snap["MDP"][0] if isinstance(snap["MDP"], list) else snap["MDP"]
    c = m0["MDP"]
    return copy.deepcopy(c[0] if isinstance(c, list) else c)


def _parent_Q_at_t(snap12f, t_idx: int):
    Q = snap12f["Q"]
    if isinstance(Q[0], (list, tuple)) and len(Q) > 0 and not isinstance(Q[0][0], (list, tuple, np.ndarray)):
        return Q
    # flattened per-factor vectors
    return Q


def _apply_forward_carry(child: dict) -> dict:
    ch = copy.deepcopy(child)
    nf = len(ch["E"])
    Tc = int(np.asarray(ch.get("T", 1)).ravel()[0])
    U = np.asarray(ch.get("U", np.zeros((1, nf))), dtype=np.float64)
    if U.ndim == 1:
        U = U.reshape(-1, 1)
    for f in range(nf):
        has_u = bool(f < U.shape[1] and np.any(U[:, f]))
        if "P" not in ch or not has_u:
            continue
        if Tc > 1:
            ch["E"][f] = np.asarray(ch["P"][f], dtype=np.float64)[:, Tc - 1 : Tc]
            ps = np.asarray(ch["X"][f], dtype=np.float64)[:, Tc - 1 : Tc]
            pu = np.asarray(ch["E"][f], dtype=np.float64).reshape(-1, 1)
            if pu.size > 1:
                from python_src.spm_dot import spm_dot as sd

                ch["D"][f] = np.asarray(sd(ch["B"][f], [pu]), dtype=np.float64) @ ps
            else:
                ch["D"][f] = np.asarray(ch["B"][f], dtype=np.float64) @ ps
        ch["D"][f] = np.asarray(
            __import__(
                "python_src.toolbox.DEM.spm_MDP_VB_XXX", fromlist=["_spm_norm"]
            )._spm_norm(np.ones((int(np.asarray(ch["D"][f]).shape[0]), 1), dtype=np.float64))
        )
    return ch


def _empirical_E(ch: dict, parent_id: dict, parent_A: list, parent_Qmi: list, t_idx: int) -> np.ndarray:
    Ef = np.asarray(ch["E"][F], dtype=np.float64).reshape(-1, 1)
    idE = ch.get("id", {}).get("E", [])
    if F >= len(idE):
        return Ef.ravel()
    Qrow = _vb_q_row_for_parents(parent_Qmi, t_idx)
    for g in np.atleast_1d(np.asarray(idE[F], dtype=np.int64).ravel()).tolist():
        j, _ = spm_parents(parent_id, int(g), Qrow)
        j_arr = np.atleast_1d(np.asarray(j, dtype=np.int64).ravel())
        q_list = [parent_Qmi[int(jj) - 1][t_idx] for jj in j_arr]
        po = np.asarray(spm_dot(parent_A[int(g) - 1], q_list), dtype=np.float64).reshape(-1, 1)
        Ef = _spm_multiply(Ef, po)
    return Ef.ravel()


def main() -> None:
    tag = _entry12_run_tag()
    py_f = _entry12_workspace_payload(_load_subentry_pkl(_subentry_pkl_path("12F")), "12F")
    mat_f = _entry12_workspace_payload(
        _mat_blob_to_py(load_entry12_subentry_mat(entry12_subentry_mat_path(tag, "12F"))),
        "12F",
    )
    # Parent model 0 from 12F out_t1 (Q after parent t=1) — use same snap for Q, id, A via nested parent fields
    snap = py_f["out_t1"]
    m0 = snap["MDP"][0] if isinstance(snap["MDP"], list) else snap["MDP"]
    parent_id = m0.get("id", {})
    parent_A = m0.get("A", [])
    parent_Q = snap["Q"]
    t_idx = 1

    for label, snap12 in ("mat", mat_f["out_t1"]), ("py", py_f["out_t1"]):
        ch0 = _child(snap12)
        ch1 = _apply_forward_carry(ch0)
        Ea = _empirical_E(ch1, parent_id, parent_A, parent_Q, t_idx)
        print(label, "id.E[f]", ch0.get("id", {}).get("E", [])[F] if ch0.get("id") else None)
        print(label, "E after carry+empirical", Ea[:6], "peak", int(np.argmax(Ea) + 1))


if __name__ == "__main__":
    main()
