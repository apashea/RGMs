"""Pass 1 transliteration of ``spm_O2rgb.m`` (DEM toolbox)."""

from __future__ import annotations

from typing import Any, List, Sequence

import numpy as np


def spm_O2rgb(O: Sequence[Any], RGB: dict) -> np.ndarray:
    """Outcome cell(s) to RGB ``uint8`` image — mirror ``spm_O2rgb.m``."""
    o_mat = _normalize_o_cell_matrix(O)
    if not o_mat or not o_mat[0]:
        raise ValueError("O must be a non-empty cell matrix (list-of-rows).")
    n_o = len(o_mat)
    t_cols = len(o_mat[0])
    if t_cols > 1:
        if "R" not in RGB:
            raise KeyError(
                'RGB["R"] is required when O has more than one column (MATLAB: RGB.R).'
            )
        r_step = int(RGB["R"])
        if r_step != 1:
            raise ValueError(
                "Staged MATLAB spm_O2rgb assigns I(:,:,:,end+(1:RGB.R)) from a "
                "single-frame image; use RGB.R==1 (see DEM_image_compression.m)."
            )
        frames: list[np.ndarray] = []
        for t in range(t_cols):
            col = [o_mat[g][t] for g in range(n_o)]
            frames.append(spm_O2rgb(col, RGB))
        return np.stack(frames, axis=-1).astype(np.uint8)

    n = np.asarray(RGB["N"], dtype=np.float64).ravel()
    c0, h, w = int(n[0]), int(n[1]), int(n[2])
    if c0 != 3:
        raise ValueError(f"RGB.N[0] must be 3, got {c0}")
    i_acc = np.zeros((c0, h, w), dtype=np.float64)

    g_pairs = _rgb_g_column_major(RGB)
    for g_1 in range(1, len(g_pairs) + 1):
        g_i = g_1 - 1
        i_pi, j_pi = g_pairs[g_i]
        if "A" in RGB:
            rgb_o = np.asarray(RGB["O"], dtype=np.float64).ravel()
            pos = np.flatnonzero(rgb_o == float(g_1)) + 1
            u = np.zeros((pos.size, 1), dtype=np.float64)
            for m in range(pos.size):
                om = int(pos[m])
                a_m = np.asarray(RGB["A"][om - 1], dtype=np.float64)
                o_cell = o_mat[om - 1][0]
                oc = np.asarray(o_cell, dtype=np.float64).reshape(-1, 1)
                u[m, 0] = float((a_m @ oc).item())
        else:
            u = np.asarray(o_mat[g_i][0], dtype=np.float64).reshape(-1, 1)

        if u.size == 0:
            continue
        v_g = np.asarray(RGB["V"][i_pi][j_pi], dtype=np.float64)
        g_idx = np.asarray(RGB["G"][i_pi][j_pi], dtype=np.float64).astype(np.int64).ravel() - 1
        upd = (v_g @ u).ravel()
        i_flat = i_acc.ravel(order="F")
        np.add.at(i_flat, g_idx, upd)
        i_acc = i_flat.reshape((c0, h, w), order="F")

    i_mid = np.reshape(i_acc, (3, 1, h, w), order="F")
    i_perm = np.transpose(i_mid, (2, 3, 0, 1))
    out = np.squeeze(i_perm, axis=-1)
    return np.asarray(np.clip(np.round(out), 0, 255), dtype=np.uint8)


def _normalize_o_cell_matrix(O: Sequence[Any]) -> List[List[np.ndarray]]:
    """``No`` × ``T`` list-of-lists like MATLAB ``O{g,t}``."""
    if len(O) == 0:
        return []
    first = O[0]
    if isinstance(first, np.ndarray):
        # Column cell vector ``O{g}`` for a single time index (``No×1``).
        return [[np.asarray(x, dtype=np.float64)] for x in O]
    out: List[List[np.ndarray]] = []
    for row in O:
        if isinstance(row, (list, tuple)):
            out.append([np.asarray(x, dtype=np.float64) for x in row])
        else:
            out.append([np.asarray(row, dtype=np.float64)])
    return out


def _rgb_g_column_major(RGB: dict) -> list[tuple[int, int]]:
    """Linear order of ``RGB.G`` / ``RGB.V`` cells: column-major over ``Nr×Nc``."""
    g = RGB["G"]
    nr = len(g)
    nc = len(g[0]) if nr else 0
    pairs: list[tuple[int, int]] = []
    for j in range(nc):
        for i in range(nr):
            pairs.append((i, j))
    return pairs
