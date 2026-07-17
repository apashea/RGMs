"""OPTIM1 Product B (parity) 12PLOT — verbatim copy of DEMO1 ``spm_show_RGB.py`` (parity baseline)."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from scipy import sparse

from python_src.spm_cat import spm_cat
from python_src.spm_dir_norm import spm_dir_norm
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size
from python_src.toolbox.DEM.spm_O2rgb import spm_O2rgb
from python_src.toolbox.DEM.spm_imshow import spm_imshow


def spm_show_RGB_optim(
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
    fig = plt.gcf()
    _ensure_figure_size(fig)

    gs = _build_gridspec(fig, Nm=Nm, Nt=Nt)

    B = spm_cat(MDP["X"])
    _plot_matrix_panel(B, title=f"Posterior (states) level {Nm}", ax=_ax_diag(gs, 0, 0))

    Nf = _factor_count(MDP)
    if Nf > 1:
        for f in range(1, Nf + 1):
            Bf = _transition_matrix(MDP, f)
            Bplot = np.sum(Bf, axis=2) > (1.0 / 16.0)
            _plot_matrix_panel(
                Bplot,
                title=f"Transitions (f = {f})",
                ax=_ax_diag(gs, 0, min(f, 1)),
                axis_square=True,
            )
    else:
        Bf = _transition_matrix(MDP, 1)
        Nu = int(Bf.shape[2]) if Bf.ndim == 3 else 1
        if Nu < 4:
            for u in range(1, Nu + 1):
                slice_u = Bf[:, :, u - 1] if Bf.ndim == 3 else Bf
                panel = slice_u > (1.0 / 16.0)
                col_slice = slice(2 + (u - 1) * 2 // Nu, 2 + u * 2 // Nu) if Nu > 1 else slice(2, 4)
                ax_t = fig.add_subplot(gs[0, col_slice])
                _plot_matrix_panel(panel, title=f"Transitions (u = {u})", ax=ax_t, axis_square=True)
        else:
            Bplot = np.sum(Bf, axis=2) > (1.0 / 16.0)
            _plot_matrix_panel(
                Bplot,
                title=f"Transitions (Nu = {Nu})",
                ax=_ax_diag(gs, 0, 1),
                axis_square=True,
            )

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

        # ``subplot(Nm+3,2,(n-1)*2+3)`` → row ``n`` (0-based) in the 2-column diagnostic block
        diag_row = n
        q_states = spm_cat(_subset_rows(y_level, i_d))
        _plot_raster(
            q_states,
            title=f"Predictive posterior (states) level {L}",
            ax=_ax_diag(gs, diag_row, 0),
        )

        if L > 1:
            q_paths = spm_cat(_subset_rows(y_level, i_e))
            _plot_raster(
                q_paths,
                title=f"Predictive posterior (paths) level {L}",
                ax=_ax_diag(gs, diag_row, 1),
            )

        if n < Nm:
            mdp = mdp["MDP"]

    ax_elbo = _ax_diag(gs, Nm, 1)
    q_e_series = _elbo_q_e_series(MDP["Q"]["E"])
    T = len(q_e_series[0]) if q_e_series else 1
    t_horizon = int(np.asarray(MDP["T"], dtype=int).ravel()[0])
    t_line = np.linspace(1, T, t_horizon)
    plt.sca(ax_elbo)
    ax_elbo.plot(t_line, np.asarray(MDP["F"], dtype=np.float64).ravel())
    for qen in q_e_series:
        t_n = np.linspace(1, T, len(qen))
        ax_elbo.plot(t_n, qen)
    ax_elbo.set_title("ELBO")
    _spm_axis_tight(ax_elbo)
    fig._rgms_elbo_ax = ax_elbo  # ENTRY 12PLOT fence: hits overlay on same axes (not ``plt.subplot``)

    frames_j: list[np.ndarray] = []
    frames_k: list[np.ndarray] = []
    movie_row_pred = Nm + 1
    movie_row_gen = Nm + 2
    movie_pred_axes = [fig.add_subplot(gs[movie_row_pred, c]) for c in range(Nt)]
    movie_gen_axes = [fig.add_subplot(gs[movie_row_gen, c]) for c in range(Nt)]
    for t in range(1, T + 1):
        if not MOVIE and t > Nt:
            return _stack_frames_list(frames_j), _stack_frames_list(frames_k)

        o_col = _column_of_cells(O[0], t)
        y_col = _column_of_cells(Y[0], t)
        x_rgb = spm_O2rgb(o_col, RGB)
        p_rgb = spm_O2rgb(y_col, RGB)

        t_col = min(Nt, t) - 1
        ax_pred = movie_pred_axes[t_col]
        plt.sca(ax_pred)
        spm_imshow(p_rgb)
        ax_pred.set_title(f"Predicted: t = {t}")

        ax_gen = movie_gen_axes[t_col]
        plt.sca(ax_gen)
        spm_imshow(x_rgb)
        if isinstance(mdp, dict) and "S" in mdp:
            ax_gen.set_title("Stimulus")
        else:
            ax_gen.set_title("Generated")

        _hide_image_axis_ticks(ax_pred)
        _hide_image_axis_ticks(ax_gen)

        n_frames = int(p_rgb.shape[3]) if p_rgb.ndim == 4 else 1
        for fi in range(n_frames):
            frames_j.append(
                np.asarray(p_rgb[:, :, :, fi] if p_rgb.ndim == 4 else p_rgb, dtype=np.uint8)
            )
            frames_k.append(
                np.asarray(x_rgb[:, :, :, fi] if x_rgb.ndim == 4 else x_rgb, dtype=np.uint8)
            )

    return _stack_frames_list(frames_j), _stack_frames_list(frames_k)


def _ensure_figure_size(fig: Any) -> None:
    """MATLAB ``saveas`` scale (~1059×1526 px at 100 dpi) — avoid default 640×480 crush."""
    w, h = fig.get_size_inches()
    if w < 9.0 or h < 13.0:
        fig.set_size_inches(10.6, 15.2)


def _build_gridspec(fig: Any, *, Nm: int, Nt: int) -> GridSpec:
    """
    One layout for diagnostic (half-width pairs) + movie (``Nt`` columns).

    Mirrors ``subplot(Nm+3,2,…)`` top rows and ``subplot(Nm+3,Nt,…)`` movie rows
    without mixing incompatible ``plt.subplot`` grid shapes on one figure.
    """
    n_rows = Nm + 3
    return GridSpec(
        n_rows,
        Nt,
        figure=fig,
        hspace=0.55,
        wspace=0.35,
        height_ratios=[1.0] * (Nm + 1) + [0.85, 0.85],
    )


def _ax_diag(gs: GridSpec, row: int, side: int) -> Any:
    """Diagnostic panel: ``side`` 0 = left half, 1 = right half (2×``Nt`` col span)."""
    half = gs.ncols // 2
    fig = gs.figure
    if side == 0:
        return fig.add_subplot(gs[row, 0:half])
    return fig.add_subplot(gs[row, half : gs.ncols])


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


def _hide_image_axis_ticks(ax: Any) -> None:
    """MATLAB ``imshow`` — image + title only, no axis ticks or values."""
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(axis="both", which="both", length=0, labelbottom=False, labelleft=False)


def _plot_matrix_panel(
    B: Any,
    title: str,
    *,
    ax: Any | None = None,
    axis_square: bool = False,
) -> None:
    """``imagesc(1-B)`` / ``spm_spy(B)`` per ``spm_show_RGB.m``."""
    if ax is None:
        ax = plt.gca()
    arr = np.asarray(B.todense() if sparse.issparse(B) else B, dtype=np.float64)
    if arr.dtype == bool or np.issubdtype(arr.dtype, np.bool_):
        spy_m = arr
    elif arr.max() <= 1.0 + 1e-12:
        spy_m = arr > 0.5
    else:
        spy_m = arr > 0

    used_spy = arr.shape[0] > 128
    if used_spy:
        ax.spy(spy_m, markersize=1.6, origin="upper", color="k")
        ax.xaxis.tick_bottom()
        ax.xaxis.set_label_position("bottom")
        ax.tick_params(axis="x", top=False, labeltop=False, bottom=True, labelbottom=True)
    else:
        img = 1.0 - arr
        ax.imshow(
            img,
            cmap="gray",
            vmin=0.0,
            vmax=1.0,
            aspect="auto",
            origin="upper",
            interpolation="nearest",
        )
    ax.set_title(title)
    if axis_square:
        ax.set_aspect("equal", adjustable="box")
    elif used_spy:
        ax.set_aspect("auto")


def _plot_raster(Q: Any, title: str, *, ax: Any | None = None) -> None:
    """MATLAB ``image((1 - Q) * 64)`` — grayscale raster, not default colormap."""
    if ax is None:
        ax = plt.gca()
    arr = np.asarray(Q.todense() if sparse.issparse(Q) else Q, dtype=np.float64)
    ax.imshow(
        (1.0 - arr) * 64.0,
        cmap="gray",
        vmin=0.0,
        vmax=64.0,
        aspect="auto",
        origin="upper",
        interpolation="nearest",
    )
    ax.set_title(title)


def _spm_axis_tight(ax: Any | None = None) -> None:
    if ax is None:
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
