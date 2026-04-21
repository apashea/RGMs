"""
MDP structure for a simple game of Pong (MATLAB-compatible).

Pass 1 transliteration of spm_MDP_pong.m including local helpers for PNG load
and image resize.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, MutableSequence, Tuple

import numpy as np
import png
from scipy import sparse
from scipy.ndimage import zoom

from matlab_compat import full
from python_src.spm_cat import spm_cat
from python_src.spm_cross import spm_cross
from python_src.spm_dir_norm import spm_dir_norm
from python_src.spm_softmax import spm_softmax
from python_src.spm_speye import spm_speye
from python_src.spm_vec import spm_vec


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _dem_asset_dir() -> Path:
    return _repo_root() / "matlab_src" / "toolbox" / "DEM"


def _read_png_rgb(path: Path) -> np.ndarray:
    """Decode PNG to uint8 H×W×3 (strip alpha). Uses PyPNG for baseline decoding."""
    reader = png.Reader(filename=str(path))
    width, height, pixels, meta = reader.asDirect()
    pix = np.vstack(list(map(np.uint8, pixels)))
    planes = pix.shape[1] // width
    arr = pix.reshape(height, width, planes)
    if planes == 4:
        arr = arr[:, :, :3].copy()
    return arr


def _imresize_like_matlab(rgb: np.ndarray, n: int, m: int) -> np.ndarray:
    """Resize uint8 image to (n, m, 3); bicubic-like via scipy zoom."""
    zh = n / rgb.shape[0]
    zw = m / rgb.shape[1]
    out = zoom(rgb.astype(np.float64), (zh, zw, 1), order=3)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _sub2ind(nr: int, nc: int, i: int, j: int) -> int:
    """MATLAB sub2ind([Nr,Nc], i, j), 1-based."""
    return int(i + (j - 1) * nr)


def _ismember_rows(S: np.ndarray, r: np.ndarray) -> np.ndarray:
    """MATLAB ismember(S, r, 'rows') for S (Ng×4) and r (1×4)."""
    return np.all(S == r.reshape(1, 4), axis=1)


def spm_MDP_pong(
    Nr: int,
    Nc: int,
    Nd: int | None = None,
    Na: int | None = None,
    Np: int | None = None,
) -> Tuple[
    Dict[str, Any],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    Dict[str, Any],
    np.ndarray,
]:
    if Nd is None:
        Nd = 1
    if Na is None:
        Na = 0
    if Np is None:
        Np = 0

    Ng = Nr * Nc
    Ns_max = 4098

    A: MutableSequence[np.ndarray] = []
    for _g in range(Ng):
        Ag = np.zeros((5, Ns_max, Nc), dtype=bool)
        Ag[4, :, :] = True
        A.append(Ag)

    B1 = np.zeros((Ns_max, Ns_max, 1), dtype=bool)

    S = np.zeros((Ng, 4), dtype=np.float64)
    i = 2
    j = 2
    p = 1
    q = 1

    for s_loop in range(1, Ns_max + 1):
        rvec = np.array([[i, j, p, q]], dtype=np.float64)
        k = _ismember_rows(S, rvec)
        if np.any(k):
            r_ml = np.flatnonzero(k) + 1
            s_ml = s_loop - 1
            B1[s_ml, s_ml - 1, 0] = False
            for rr in np.atleast_1d(r_ml).ravel():
                B1[int(rr - 1), int(s_ml - 1), 0] = True
            ss = s_ml
            B1 = B1[:ss, :ss, :]
            for g in range(Ng):
                A[g] = A[g][:, :ss, :]
            break

        if s_loop - 1 >= S.shape[0]:
            # MATLAB expands ``S(s,:)`` with zero-filled rows on demand.
            grow = max(int(Ng), 1)
            S = np.vstack([S, np.zeros((grow, 4), dtype=np.float64)])
        S[s_loop - 1, :] = rvec.ravel()

        n = _sub2ind(Nr, Nc, i, j)
        A[n - 1][:, s_loop - 1, :] = False
        A[n - 1][0, s_loop - 1, :] = True
        B1[s_loop, s_loop - 1, 0] = True

        if i in (1, Nr):
            p = -p
        if j in (1, Nc):
            q = -q
        i = i + p
        j = j + q

    Ns = B1.shape[1]
    B1 = np.asarray(B1[:Ns, :Ns, 0], dtype=bool)
    for g in range(Ng):
        A[g] = A[g][:, :Ns, :]

    B: List[Any] = [B1]
    Nu_paddle = 3
    B2 = np.zeros((Nc, Nc, Nu_paddle), dtype=bool)
    for u in range(1, Nu_paddle + 1):
        B2[:, :, u - 1] = np.asarray(
            full(spm_speye(Nc, Nc, u - 2, 2)), dtype=bool
        )
    B.append(B2)

    for s in range(1, Nc + 1):
        if s > 1:
            n = _sub2ind(Nr, Nc, 1, s - 1)
            A[n - 1][:, :, s - 1] = False
            A[n - 1][1, :, s - 1] = True

        n = _sub2ind(Nr, Nc, 1, s)
        A[n - 1][:, :, s - 1] = False
        A[n - 1][2, :, s - 1] = True

        if s < Nc:
            n = _sub2ind(Nr, Nc, 1, s + 1)
            A[n - 1][:, :, s - 1] = False
            A[n - 1][3, :, s - 1] = True

    con = np.zeros((1, Nc), dtype=np.float64)
    for s in range(1, Nc + 1):
        con[0, s - 1] = _sub2ind(Nr, Nc, 1, s)

    hid = np.zeros((2, 0), dtype=np.float64)
    cid = np.zeros((2, 0), dtype=np.float64)
    for s1 in range(1, B[0].shape[0] + 1):
        for s2 in range(1, B[1].shape[0] + 1):
            if S[s1 - 1, 0] == 1 and s2 != S[s1 - 1, 1]:
                col = np.array([[s1], [s2]], dtype=np.float64)
                cid = np.concatenate((cid, col), axis=1)
            if S[s1 - 1, 0] == 1 and s2 == S[s1 - 1, 1]:
                col = np.array([[s1], [s2]], dtype=np.float64)
                hid = np.concatenate((hid, col), axis=1)

    id_: Dict[str, Any] = {}
    id_["A"] = []
    for _g in range(len(A)):
        id_["A"].append(np.array([[1, 2]], dtype=np.float64))

    if Na:
        a = np.zeros((2, B[0].shape[0], B[1].shape[0]), dtype=bool)
        a[0, :, :] = True
        for s in range(hid.shape[1]):
            a[0, int(hid[0, s]) - 1, int(hid[1, s]) - 1] = False
            a[1, int(hid[0, s]) - 1, int(hid[1, s]) - 1] = True
        A.append(a)
        id_["A"].append(np.array([[1, 2]], dtype=np.float64))
        id_["reward"] = float(len(A))

        a = np.zeros((2, B[0].shape[0], B[1].shape[0]), dtype=bool)
        a[0, :, :] = True
        for s in range(cid.shape[1]):
            a[0, int(cid[0, s]) - 1, int(cid[1, s]) - 1] = False
            a[1, int(cid[0, s]) - 1, int(cid[1, s]) - 1] = True
        A.append(a)
        id_["A"].append(np.array([[1, 2]], dtype=np.float64))
        id_["contraint"] = float(len(A))

        A.append(np.eye(Nc, dtype=np.float64))
        id_["A"].append(np.array([[2]], dtype=np.float64))
        id_["control"] = float(len(A))

    con_list = [float(con[0, ii]) for ii in range(con.shape[1])]
    nP_out = np.zeros((1, Np), dtype=np.float64)
    for ii in range(Np):
        jpix = int(np.ceil(float(np.random.rand()) * (Nc * Nr)))
        while jpix in con_list:
            jpix = int(np.ceil(float(np.random.rand()) * (Nc * Nr)))
        Aj = np.asarray(full(spm_speye(5, 3)), dtype=bool)
        A[jpix - 1] = Aj
        s_sp = spm_speye(3, 3, -1, 1)
        B.append(np.asarray(full(s_sp), dtype=np.float64) + 1.0)
        id_["A"][jpix - 1] = np.array([[float(len(B))]], dtype=np.float64)
        nP_out[0, ii] = float(jpix)

    B = spm_dir_norm(B)

    Nf = len(B)
    Ng_out = len(A)
    Ns_f = np.zeros(Nf, dtype=np.int64)
    Nu_f = np.zeros(Nf, dtype=np.int64)
    for f in range(Nf):
        bf = B[f]
        Ns_f[f] = bf.shape[0]
        Nu_f[f] = bf.shape[2] if bf.ndim >= 3 else 1

    No = np.zeros(Ng_out, dtype=np.int64)
    for g in range(Ng_out):
        No[g] = A[g].shape[0]

    C: List[np.ndarray] = []
    for g in range(Ng_out):
        C.append(spm_softmax(np.ones((int(No[g]), 1), dtype=np.float64)))

    D: List[Any] = []
    E: List[Any] = []
    H: List[Any] = []
    for f in range(Nf):
        d = int(min(int(Ns_f[f]), int(Nd)))
        Nsf = int(Ns_f[f])
        Nuf = int(Nu_f[f])
        rows = np.arange(0, d, dtype=np.int32)
        cols = np.zeros(d, dtype=np.int32)
        data = np.ones(d, dtype=np.float64) / float(d)
        D.append(sparse.csr_matrix((data, (rows, cols)), shape=(Nsf, 1)))
        E.append(sparse.csr_matrix(([1.0], ([0], [0])), shape=(Nuf, 1)))
        H.append(np.zeros((0, 0), dtype=np.float64))

    U = np.zeros((1, len(B)), dtype=np.float64)
    U[0, 1] = 1.0

    MDP: Dict[str, Any] = {}
    MDP["T"] = 8.0
    MDP["U"] = U
    MDP["A"] = A
    MDP["B"] = B
    MDP["C"] = C
    MDP["D"] = D
    MDP["E"] = E
    MDP["H"] = H
    MDP["N"] = 0.0
    MDP["id"] = id_

    dem_dir = _dem_asset_dir()
    ball = _read_png_rgb(dem_dir / "baseball.png")
    batt = _read_png_rgb(dem_dir / "bat.png")
    back = np.zeros_like(ball)
    batl = batt[0:32, 0:32, :]
    batc = batt[0:32, 32:34, :]
    batr = batt[0:32, 32:64, :]

    n = 8
    RGB: Dict[str, Any] = {}
    RGB["N"] = np.array([3.0, float(Nr * n), float(Nc * n)], dtype=np.float64)

    imgs = [ball, batl, batc, batr, back]
    V_list: List[np.ndarray] = []
    for idx in range(len(imgs)):
        rsz = _imresize_like_matlab(imgs[idx], n, n)
        perm = np.transpose(rsz, (2, 0, 1))
        vc = spm_vec(perm)
        V_list.append(np.asarray(vc, dtype=np.float64).ravel(order="F"))
    V = np.column_stack(V_list)

    G: List[List[np.ndarray]] = [[None for _j in range(Nc)] for _i in range(Nr)]
    I = [[np.zeros((n, n), dtype=np.float64) for _j in range(Nc)] for _i in range(Nr)]

    for ii in range(1, Nr + 1):
        for jj in range(1, Nc + 1):
            k_cells = copy.deepcopy(I)
            k_cells[ii - 1][jj - 1] = k_cells[ii - 1][jj - 1] + 1.0
            k_arr = spm_cat(k_cells)
            k_cross = spm_cross(k_arr, np.ones((1, 3), dtype=np.float64))
            k_perm = np.transpose(k_cross, (2, 0, 1))
            k_flat = np.asarray(spm_vec(k_perm), dtype=np.float64).ravel(order="F")
            kk = np.flatnonzero(k_flat)
            G[ii - 1][jj - 1] = (kk.reshape(-1, 1).astype(np.float64) + 1.0)

    RGB["G"] = G
    RGB["V"] = [[V.copy() for _j in range(Nc)] for _i in range(Nr)]

    return MDP, hid, cid, con, RGB, nP_out


spm_MDP_pong.__doc__ = """
FORMAT [MDP,hid,cid,con,RGB,nP] = spm_MDP_pong(Nr,Nc,Nd,Na,Np)

Nr    - number of rows
Nc    - number of columns
Nd    - number of initial states [default: 1]
Na    - returns rewards, costs and action
Np    - number of distractor pixels

hid   - Hidden states corresponding to hits
cid   - Hidden states corresponding to misses
con   - output modalities reporting control
RGB   - display structure
"""
