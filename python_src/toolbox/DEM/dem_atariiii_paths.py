"""DEM_AtariIII ledger helpers shared by driver and FSL backward Entry 10."""

from __future__ import annotations

import numpy as np


def dem_atariiii_paths_to_hits_P(
    B_mask: np.ndarray, hid_1based: np.ndarray | list[int], nt: int
) -> np.ndarray:
    """Paths-to-hits matrix ``P`` (DEM_AtariIII ledger after ``spm_set_goals``).

    MATLAB::

        B = sum(MDP{Nm}.b{1},3) > 0;
        h = sparse(1,hid,1,1,Ns);
        for t = 1:Nt
            P(t,:) = h;
            h = (h + h*B) > 0;
        end

    ``hid_1based`` are 1-based state indices (``MDP{end}.id.hid`` layout).
    """
    B = np.asarray(B_mask, dtype=np.float64)
    ns = int(B.shape[0])
    if B.shape != (ns, ns):
        raise ValueError("B_mask must be square")
    hid = np.asarray(hid_1based, dtype=np.int64).ravel(order="F")
    nt_i = int(nt)
    h = np.zeros((1, ns), dtype=np.float64)
    for idx in hid.tolist():
        j0 = int(idx) - 1
        if 0 <= j0 < ns:
            h[0, j0] = 1.0
    p_out = np.zeros((nt_i, ns), dtype=np.float64)
    for t in range(nt_i):
        p_out[t, :] = h[0, :]
        h = ((h + (h @ B)) > 0).astype(np.float64)
    return p_out
