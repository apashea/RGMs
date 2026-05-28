"""Pass 1 transliteration of ``spm_show_RGB.m`` (DEM toolbox)."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse

from python_src.spm_cat import spm_cat
from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size
from python_src.toolbox.DEM.spm_O2rgb import spm_O2rgb
from python_src.toolbox.DEM.spm_imshow import spm_imshow


def spm_show_RGB(
    MDP: Any,
    RGB: dict,
    Nt: int | None = None,
    MOVIE: int | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Graphical illustration of active inference — mirror ``spm_show_RGB.m``.

    Returns ``(J, K)`` predicted and observed RGB time-series (``uint8``).
    """
    if Nt is None:
        Nt = 4
    if MOVIE is None:
        MOVIE = 1

    O = _spm_get_O(MDP)
    try:
        Y = _q_hier_list(MDP["Q"]["Y"])
    except (KeyError, TypeError):
        Y = []
    Y = list(Y)
    Y.append(MDP["Y"])

    Nm = len(O)
    B = spm_cat(MDP["X"])
    plt.subplot(Nm + 3, 2, 1)
    _plot_matrix_panel(B, title=f"Posterior (states) level {Nm}")

    Nf = _factor_count(MDP)
    if Nf > 1:
        for f in range(1, Nf + 1):
            Bf = _transition_matrix(MDP, f)
            plt.subplot(Nm + 3, 2 * Nf, Nf + f)
            Bplot = np.sum(Bf, axis=2) > (1.0 / 16.0)
            _plot_matrix_panel(Bplot, title=f"Transitions (f = {f})")
            plt.axis("square")
    else:
        Bf = _transition_matrix(MDP, 1)
        Nu = int(Bf.shape[2]) if Bf.ndim == 3 else 1
        if Nu < 4:
            for u in range(1, Nu + 1):
                plt.subplot(Nm + 3, 2 * Nu, Nu + u)
                slice_u = Bf[:, :, u - 1] if Bf.ndim == 3 else Bf
                panel = slice_u > (1.0 / 16.0)
                _plot_matrix_panel(panel, title=f"Transitions (u = {u})")
                plt.axis("square")
        else:
            plt.subplot(Nm + 3, 2, 2)
            Bplot = np.sum(Bf, axis=2) > (1.0 / 16.0)
            _plot_matrix_panel(Bplot, title=f"Transitions (Nu = {Nu})")
            plt.axis("square")

    mdp = MDP
    for n in range(1, Nm + 1):
        L = Nm - n + 1
        y_level = Y[L - 1]
        if L > 1:
            i_d = _spm_cat_index_vector(mdp["MDP"]["id"]["D"])
            i_e = _spm_cat_index_vector(mdp["MDP"]["id"]["E"])
        else:
            if isinstance(y_level, list) and y_level and isinstance(y_level[0], list):
                i_d = np.arange(1, len(y_level) + 1, dtype=int)
            else:
                y_arr = np.asarray(y_level, dtype=np.float64)
                i_d = np.arange(1, y_arr.shape[0] + 1, dtype=int)
            i_e = np.array([], dtype=int)

        plt.subplot(Nm + 3, 2, (n - 1) * 2 + 3)
        q_states = spm_cat(_subset_rows(y_level, i_d))
        _plot_raster(q_states, title=f"Predictive posterior (states) level {L}")

        if L > 1:
            plt.subplot(Nm + 3, 2, (n - 1) * 2 + 4)
            q_paths = spm_cat(_subset_rows(y_level, i_e))
            _plot_raster(q_paths, title=f"Predictive posterior (paths) level {L}")

        if n < Nm:
            mdp = mdp["MDP"]

    plt.subplot(Nm + 3, 2, 2 * (Nm + 1))
    q_e_series = _elbo_q_e_series(MDP["Q"]["E"])
    T = len(q_e_series[0]) if q_e_series else 1
    t_horizon = int(np.asarray(MDP["T"], dtype=int).ravel()[0])
    t_line = np.linspace(1, T, t_horizon)
    plt.plot(t_line, np.asarray(MDP["F"], dtype=np.float64).ravel())
    for qen in q_e_series:
        t_n = np.linspace(1, T, len(qen))
        plt.plot(t_n, qen)
    plt.title("ELBO")
    _spm_axis_tight()

    frames_j: list[np.ndarray] = []
    frames_k: list[np.ndarray] = []
    for t in range(1, T + 1):
        if not MOVIE and t > Nt:
            return _stack_frames_list(frames_j), _stack_frames_list(frames_k)

        o_col = _column_of_cells(O[0], t)
        y_col = _column_of_cells(Y[0], t)
        x_rgb = spm_O2rgb(o_col, RGB)
        p_rgb = spm_O2rgb(y_col, RGB)

        plt.subplot(Nm + 3, Nt, Nt * (Nm + 1) + min(Nt, t))
        spm_imshow(p_rgb)
        plt.title(f"Predicted: t = {t}")

        plt.subplot(Nm + 3, Nt, Nt * (Nm + 2) + min(Nt, t))
        spm_imshow(x_rgb)
        if isinstance(mdp, dict) and "S" in mdp:
            plt.title("Stimulus")
        else:
            plt.title("Generated")

        plt.draw()
        n_frames = int(p_rgb.shape[3]) if p_rgb.ndim == 4 else 1
        for fi in range(n_frames):
            frames_j.append(
                np.asarray(p_rgb[:, :, :, fi] if p_rgb.ndim == 4 else p_rgb, dtype=np.uint8)
            )
            frames_k.append(
                np.asarray(x_rgb[:, :, :, fi] if x_rgb.ndim == 4 else x_rgb, dtype=np.uint8)
            )

    return _stack_frames_list(frames_j), _stack_frames_list(frames_k)


def _spm_cat_index_vector(field: Any) -> np.ndarray:
    arr = spm_cat(_dense_leaf(field))
    if sparse.issparse(arr):
        arr = arr.toarray()
    return np.asarray(arr, dtype=int).ravel()


def _dense_leaf(x: Any) -> Any:
    if sparse.issparse(x):
        return np.asarray(x.toarray(), dtype=np.float64)
    if isinstance(x, np.ndarray) and x.dtype == object:
        return [_dense_leaf(v) for v in x.ravel(order="F")]
    if isinstance(x, list):
        return [_dense_leaf(v) for v in x]
    return x


def _spm_get_O(RDP: Any) -> List[Any]:
    try:
        q = _cell_list(RDP["Q"]["O"])
    except (KeyError, TypeError):
        q = []
    q = list(q)
    q.append(RDP["O"])
    return q


def _factor_count(mdp: Any) -> int:
    if "b" in mdp:
        b = mdp["b"]
        if isinstance(b, list):
            return len(b)
        return 1
    if "B" in mdp:
        b = mdp["B"]
        if isinstance(b, list):
            return len(b)
        return 1
    return int(spm_MDP_size(mdp)[0])


def _transition_matrix(mdp: Any, f_1: int) -> np.ndarray:
    f_i = f_1 - 1
    try:
        b_field = mdp["b"]
        if isinstance(b_field, list):
            b_entry = b_field[f_i]
        else:
            b_entry = b_field
        B = spm_dir_norm(b_entry)
    except (KeyError, TypeError, IndexError):
        b_field = mdp["B"]
        if isinstance(b_field, list):
            B = np.asarray(b_field[f_i], dtype=np.float64)
        else:
            B = np.asarray(b_field, dtype=np.float64)
    return np.asarray(B, dtype=np.float64)


def _cell_list(x: Any) -> List[Any]:
    if isinstance(x, np.ndarray) and x.dtype == object:
        return list(x.ravel(order="F"))
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _column_of_cells(grid: Any, t_1: int) -> List[Any]:
    """``grid(:, t)`` for MATLAB ``Ng×T`` cell grid (column-major)."""
    t_i = t_1 - 1
    if isinstance(grid, np.ndarray) and grid.dtype == object:
        if grid.ndim == 2:
            return list(grid[:, t_i].ravel(order="F"))
        if grid.ndim == 1:
            return [grid[t_i]]
    if isinstance(grid, list):
        if grid and isinstance(grid[0], (list, tuple)):
            col = []
            for row in grid:
                col.append(row[t_i])
            return col
        return [grid[t_i]]
    raise TypeError(f"unsupported outcome grid type: {type(grid)!r}")


def _subset_rows(y_level: Any, idx_1: Sequence[int]) -> Any:
    if not len(idx_1):
        return y_level
    rows = [int(i) - 1 for i in idx_1]
    if isinstance(y_level, list) and y_level and isinstance(y_level[0], list):
        return [[y_level[r][c] for c in range(len(y_level[r]))] for r in rows]
    arr = np.asarray(y_level, dtype=np.float64)
    return arr[rows, :]


def _elbo_q_e_series(q_e_field: Any) -> list[np.ndarray]:
    series: list[np.ndarray] = []
    for item in _cell_list(q_e_field):
        series.append(np.asarray(item, dtype=np.float64).ravel(order="F"))
    return series


def _q_hier_list(field: Any) -> List[Any]:
    if isinstance(field, list):
        return list(field)
    return [field]


def _plot_matrix_panel(B: Any, title: str) -> None:
    arr = np.asarray(B.todense() if sparse.issparse(B) else B, dtype=np.float64)
    if arr.shape[0] > 128:
        plt.spy(arr > 0, markersize=0.5)
    else:
        plt.imshow(1.0 - arr, aspect="auto")
    plt.title(title)


def _plot_raster(Q: Any, title: str) -> None:
    arr = np.asarray(Q.todense() if sparse.issparse(Q) else Q, dtype=np.float64)
    plt.imshow((1.0 - arr) * 64.0, aspect="auto")
    plt.title(title)


def _spm_axis_tight() -> None:
    ax = plt.gca()
    ylim = ax.get_ylim()
    if abs(ylim[1] - ylim[0]) < 1e-12:
        ax.set_ylim(ylim[0] - 1.0, ylim[1] + 1.0)
    else:
        pad = (ylim[1] - ylim[0]) / 16.0
        ax.set_ylim(ylim[0] - pad, ylim[1] + pad)


def _stack_frames_list(frames: list[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.array([], dtype=np.uint8)
    if len(frames) == 1:
        f0 = frames[0]
        if f0.ndim == 3:
            return f0[:, :, :, np.newaxis]
        return f0
    return np.stack(frames, axis=-1)


def _stack_frames(vol: np.ndarray) -> np.ndarray:
    if vol.size == 0:
        return np.array([], dtype=np.uint8)
    if vol.ndim == 4:
        return vol
    if vol.ndim == 3:
        h, w, c = vol.shape
        return vol.reshape(h, w, c, 1)
    return vol.astype(np.uint8)
