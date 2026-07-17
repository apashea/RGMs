"""Pass-1 ``spm_dir_orbits`` — latent coords ``u`` (+ optional plot).

OPTIM1FULL Product B policy B: Python owns glue (norm, subset, hid remap, plot).
Spectral steps accept injects for MATLAB ``eig(...,'nobalance')`` and ``spm_svd``.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

import numpy as np

from python_src.spm_dir_norm import spm_dir_norm
from python_src.spm_svd import spm_svd

EigFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]
SvdFn = Callable[..., np.ndarray]
NessOrderFn = Callable[[np.ndarray, int], np.ndarray]


def spm_dir_orbits(
    b: Any,
    hid: Any = None,
    N: Optional[int] = None,
    *,
    eig: Optional[EigFn] = None,
    svd: Optional[SvdFn] = None,
    ness_order: Optional[NessOrderFn] = None,
    eng: Any = None,
    plot: bool = True,
) -> np.ndarray:
    """
    Approximate latent coords of graph Laplacian of transitions.

    MATLAB::

        [u] = spm_dir_orbits(b,hid,N)

    ``eig`` / ``svd`` injects (Product B): ``eig(B) -> (vals, vecs)``;
    ``svd(X[, thresh]) -> U``. Optional ``ness_order(B, N) -> j0`` uses MATLAB
    ``max``+``sort(p,'descend')`` when ULP ties on ``p`` would reorder the subset.
    """
    b_in = np.asarray(b, dtype=np.float64)
    if b_in.ndim == 2:
        b_work = b_in
    elif b_in.ndim == 3:
        b_work = np.sum(b_in, axis=2)
    else:
        raise ValueError("spm_dir_orbits: b must be 2-D or 3-D")

    Ns = int(b_work.shape[0])
    b_norm = spm_dir_norm((b_work > (1.0 / 16.0)).astype(np.float64))
    if N is None:
        N_use = Ns
    else:
        N_use = int(N)

    b_norm_arr = np.asarray(b_norm, dtype=np.float64)

    # eigenvalue / NESS subset — Product B uses MATLAB ness_order when available
    if ness_order is not None:
        j = np.asarray(ness_order(b_norm_arr, N_use), dtype=np.int64).ravel()
    else:
        if eig is not None:
            vals, vecs = eig(b_norm_arr)
        else:
            vals, vecs = np.linalg.eig(b_norm_arr)
        vals = np.asarray(vals, dtype=np.complex128).reshape(-1)
        vecs = np.asarray(vecs, dtype=np.complex128)
        if vecs.ndim == 1:
            vecs = vecs.reshape(-1, 1, order="F")
        i_ness = int(np.argmax(np.real(vals)))
        p = spm_dir_norm(np.abs(vecs[:, i_ness]).reshape(-1, 1, order="F"))
        p = np.asarray(p, dtype=np.float64).reshape(-1)
        j = np.argsort(-p, kind="stable")
        j = j[: min(int(j.size) - 0, N_use)]

    N_sub = int(j.size)
    B = spm_dir_norm(b_norm_arr[np.ix_(j, j)])

    hid_plot: Optional[np.ndarray] = None
    if hid is not None:
        h = np.zeros(Ns, dtype=bool)
        hid_arr = np.asarray(hid, dtype=np.int64).ravel(order="F")
        for idx in hid_arr.tolist():
            i0 = int(idx) - 1
            if 0 <= i0 < Ns:
                h[i0] = True
        h_sub = h[j]
        hid_plot = np.flatnonzero(h_sub) + 1  # 1-based into subset

    # state space (graph Laplacian)
    b_lap = np.asarray(B, dtype=np.float64) + np.asarray(B, dtype=np.float64).T
    b_lap = b_lap + np.eye(N_sub, dtype=np.float64)
    if svd is not None:
        u = np.asarray(svd(b_lap), dtype=np.float64)
    elif eng is not None:
        u = spm_svd(b_lap, eng=eng)
    else:
        u = spm_svd(b_lap)
    if u.ndim == 1:
        u = u.reshape(-1, 1, order="F")
    # Ensure at least 3 columns for plot3 (pad zeros if SVD truncated early).
    if u.shape[1] < 3:
        pad = np.zeros((u.shape[0], 3 - u.shape[1]), dtype=np.float64)
        u = np.concatenate([u, pad], axis=1)

    if plot:
        import matplotlib.pyplot as plt

        ax = plt.gca()
        # Display X/Y swapped vs column order so matplotlib view matches MATLAB plot3 look;
        # returned ``u`` columns are unchanged (parity numerics).
        ax.plot(u[:, 1], u[:, 0], u[:, 2], ".r", markersize=16)
        # flow based upon transition probabilities (B)
        B_arr = np.asarray(B, dtype=np.float64)
        for jj in range(N_sub):
            r = np.flatnonzero(B_arr[:, jj])
            for ii in r.tolist():
                X = [u[jj, 1], u[ii, 1]]
                Y = [u[jj, 0], u[ii, 0]]
                Z = [u[jj, 2], u[ii, 2]]
                ax.plot(X, Y, Z, color=(0.5, 0.5, 0.5), linewidth=0.125)
        ax.set_title("Orbits")
        ax.set_xlabel("2nd dimension")
        ax.set_ylabel("1st dimension")
        # Display only: match MATLAB 2nd-dimension sense (left→right = high→low).
        ax.invert_xaxis()
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass
        if hid_plot is not None and hid_plot.size:
            h0 = hid_plot.astype(np.int64) - 1
            ax.plot(u[h0, 1], u[h0, 0], u[h0, 2], ".g", markersize=16)

    return u
