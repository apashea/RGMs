"""ENTRY 12PLOT driver — fence composition; no VB re-run."""

from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf
from python_src.toolbox.DEM.spm_show_RGB import spm_show_RGB

DEFAULT_TAG = "rgms_canonical"


def entry12plot_timestamp() -> str:
    """Filename-friendly timestamp: ``yyyy-mm-dd-HH-MM-SS``."""
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def entry12plot_png_path(repo_root: Path, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return repo_root / "visualizations" / f"AtariIII_12plot_{ts}.png"


def fixtures_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / "tests" / "oracle" / "toolbox" / "DEM" / "fixtures"


def plot_ctx_mat_path(repo_root: Path | None = None) -> Path:
    return fixtures_dir(repo_root) / "DEMAtariIII_fsl_1_11_plot_ctx.mat"


def pdp_mat_path(repo_root: Path | None = None) -> Path:
    return fixtures_dir(repo_root) / "DEMAtariIII_XXX_12_pdp.mat"


def pdp_pkl_path(repo_root: Path | None = None) -> Path:
    return fixtures_dir(repo_root) / "DEMAtariIII_XXX_12_pdp.pkl"


def plot_oracle_mat_path(tag: str = DEFAULT_TAG, repo_root: Path | None = None) -> Path:
    return fixtures_dir(repo_root) / f"DEMAtariIII_entry12_{tag}_12PLOT.mat"


def spm_get_hits(o: Any, id_dict: dict) -> np.ndarray:
    """Mirror fence ``@(o,id) find(o(id.reward,:)>1)`` (1-based indices)."""
    reward_row = int(np.asarray(id_dict["reward"], dtype=int).ravel()[0])
    if isinstance(o, list) and o and isinstance(o[0], list):
        row = o[reward_row - 1]
        vals = np.asarray([float(np.asarray(c).ravel()[0]) for c in row], dtype=np.float64)
    else:
        arr = np.asarray(o, dtype=np.float64)
        if arr.ndim != 2:
            raise ValueError("spm_get_hits expects 2-D outcome matrix or cell grid")
        vals = arr[reward_row - 1, :]
    hits = np.flatnonzero(vals > 1.0) + 1
    return hits.astype(np.int64)


def rgb_dict_from_matlab_rgb(eng_or_rgb: Any) -> dict:
    """Build Python ``RGB`` dict from a MATLAB Engine ``RGB`` struct or nested dict."""
    if isinstance(eng_or_rgb, dict) and "N" in eng_or_rgb:
        return eng_or_rgb
    raise TypeError("rgb_dict_from_matlab_rgb expects a converted dict with key N")


def load_pdp_pkl_for_plot(path: Path) -> dict:
    """Load Python Entry 12 ``PDP`` and reshape hierarchical plot fields for ``spm_show_RGB``."""
    with open(path, "rb") as f:
        blob = pickle.load(f)
    pdp = blob["PDP"] if isinstance(blob, dict) and "PDP" in blob else blob
    return _normalize_pdp_pkl_for_plot(pdp)


def _normalize_pdp_pkl_for_plot(pdp: dict) -> dict:
    """Match MATLAB ``loadmat`` cell-grid layout expected by ``spm_show_RGB`` (compare-lane shapes)."""
    import copy

    out = copy.deepcopy(pdp)
    q = out.get("Q")
    if not isinstance(q, dict):
        return out
    nrow, ncol = _infer_hier_outcome_grid_shape(q)
    for field in ("O", "Y"):
        hier = q.get(field)
        if isinstance(hier, list) and len(hier) == 1:
            q[field][0] = _reshape_flat_hier_cell_grid(hier[0], nrow=nrow, ncol=ncol)
    e0 = q.get("E")
    if isinstance(e0, list) and e0 and isinstance(e0[0], list) and not isinstance(e0[0], np.ndarray):
        q["E"][0] = np.asarray(
            [float(np.asarray(x).ravel()[0]) for x in e0[0]],
            dtype=np.float64,
        ).reshape(1, -1)
    o0 = q.get("o")
    if isinstance(o0, list) and o0 and isinstance(o0[0], list):
        cols = [np.asarray(c, dtype=np.float64) for c in o0[0]]
        if cols and cols[0].ndim == 2 and cols[0].shape[1] == 1:
            q["o"][0] = np.hstack(cols)
    return out


def _infer_hier_outcome_grid_shape(q: dict) -> tuple[int, int]:
    """``(nrow, ncol)`` for hierarchical ``Q.O`` / ``Q.Y`` cell grids from ``Q.o`` lane."""
    ncol = 128
    o0 = q.get("o")
    if isinstance(o0, list) and o0:
        inner = o0[0]
        if isinstance(inner, list):
            ncol = len(inner)
        elif isinstance(inner, np.ndarray) and inner.ndim == 2:
            ncol = int(inner.shape[1])
    nrow = 111
    for field in ("O", "Y"):
        hier = q.get(field)
        if isinstance(hier, list) and hier and isinstance(hier[0], list):
            flat = hier[0]
            if flat and not isinstance(flat[0], list):
                nrow = len(flat) // ncol
                break
    return nrow, ncol


def _reshape_flat_hier_cell_grid(grid: Any, *, nrow: int, ncol: int) -> Any:
    """Linear cell list → ``nrow×ncol`` cell grid (MATLAB column-major / ``loadmat`` layout)."""
    if not isinstance(grid, list) or not grid:
        return grid
    if isinstance(grid[0], list):
        return grid
    n = len(grid)
    if ncol <= 0 or nrow <= 0 or nrow * ncol != n:
        return grid
    rows: list = []
    for i in range(nrow):
        row = [grid[j * nrow + i] for j in range(ncol)]
        rows.append(row)
    return rows


def load_pdp_mat_for_plot(path: Path) -> dict:
    """Load ``PDP`` from ``.mat`` preserving hierarchical ``Q.O`` / ``Q.Y`` cell layout."""
    raw = loadmat(str(path), struct_as_record=False, squeeze_me=False)
    return _mat_struct_to_plot_dict(_unwrap_matlab_scalar(raw["PDP"]))


def load_plot_ctx_from_mat(path: Path) -> Dict[str, Any]:
    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    gdp = _unwrap_matlab_scalar(raw["GDP"])
    if hasattr(gdp, "_fieldnames"):
        id_rec = _unwrap_matlab_scalar(gdp.id)
        gdp_id = {name: getattr(id_rec, name) for name in id_rec._fieldnames}
    else:
        gdp_id = gdp["id"] if isinstance(gdp, dict) else {}
    return {
        "RGB": _mat_rgb_to_py(_unwrap_matlab_scalar(raw["RGB"])),
        "GDP": {"id": _struct_to_dict(gdp_id)},
        "Nm": int(np.asarray(raw["Nm"]).ravel()[0]),
    }


def load_12plot_oracle_from_mat(path: Path) -> Dict[str, Any]:
    raw = loadmat(str(path), squeeze_me=False, struct_as_record=False)
    return {
        "J": np.asarray(raw["J"], dtype=np.uint8),
        "K": np.asarray(raw["K"], dtype=np.uint8),
        "h": np.asarray(raw["h"], dtype=np.int64).ravel(),
        "Nm": int(np.asarray(raw["Nm"]).ravel()[0]),
    }


def run_entry12plot(
    pdp: Any,
    plot_ctx: Dict[str, Any],
    *,
    repo_root: Path | None = None,
    save_png: bool = True,
    png_path: Path | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Path | None]:
    """Run staged ENTRY 12PLOT fence; does not invoke VB."""
    root = repo_root or Path(__file__).resolve().parents[3]
    rgb = plot_ctx["RGB"]
    gdp_id = plot_ctx["GDP"]["id"]
    nm = int(plot_ctx["Nm"])

    spm_figure("GetWin", "Generative AI")
    spm_figure_clf("Generative AI")
    j, k = spm_show_RGB(pdp, rgb)
    q_o = pdp["Q"]["o"]
    o1 = q_o[0] if isinstance(q_o, list) else q_o
    h = spm_get_hits(o1, gdp_id)

    plt.subplot(nm + 3, 2, 2 * (nm + 1))
    plt.plot(h, np.zeros_like(h, dtype=np.float64), ".r", markersize=16)
    plt.draw()

    out_png: Path | None = None
    if save_png:
        out_png = png_path or entry12plot_png_path(root)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(out_png, dpi=100)

    return j, k, h, out_png


def _mat_rgb_to_py(rgb: Any) -> dict:
    rgb = _unwrap_matlab_scalar(rgb)
    if hasattr(rgb, "_fieldnames"):
        out: dict = {}
        for name in rgb._fieldnames:
            val = getattr(rgb, name)
            if name in ("G", "V"):
                out[name] = _cell2nested(val)
            elif name == "N":
                out[name] = np.asarray(val, dtype=np.float64).ravel()
            else:
                out[name] = val
        return out
    if isinstance(rgb, dict):
        return rgb
    raise TypeError(f"unsupported RGB type from loadmat: {type(rgb)!r}")


def _unwrap_matlab_scalar(x: Any) -> Any:
    while isinstance(x, np.ndarray) and x.dtype == object and x.size == 1:
        x = x.flat[0]
    return x


def _cell2nested(cell: Any) -> list:
    arr = np.asarray(cell, dtype=object)
    nr, nc = arr.shape
    rows = []
    for i in range(nr):
        row = []
        for j in range(nc):
            row.append(np.asarray(arr[i, j], dtype=np.float64))
        rows.append(row)
    return rows


def _mat_struct_to_plot_dict(obj: Any) -> Any:
    if hasattr(obj, "_fieldnames"):
        return {f: _mat_struct_to_plot_dict(getattr(obj, f)) for f in obj._fieldnames}
    if isinstance(obj, np.ndarray) and obj.dtype == object:
        if obj.shape == (1, 1):
            inner = obj[0, 0]
            if hasattr(inner, "_fieldnames"):
                return _mat_struct_to_plot_dict(inner)
            return [_mat_struct_to_plot_dict(inner)]
        return _mat_cell_array_to_py(obj)
    if isinstance(obj, np.ndarray):
        return np.asarray(obj)
    return obj


def _mat_cell_array_to_py(arr: np.ndarray) -> Any:
    """Preserve ``1×1`` hierarchical cell wrappers; expand general cell grids to list-of-rows."""
    if arr.shape == (1, 1):
        return [_mat_struct_to_plot_dict(arr[0, 0])]
    rows: list = []
    for i in range(arr.shape[0]):
        row = []
        for j in range(arr.shape[1]):
            row.append(_mat_struct_to_plot_dict(arr[i, j]))
        rows.append(row)
    return rows


def _struct_to_dict(obj: Any) -> dict:
    obj = _unwrap_matlab_scalar(obj)
    if hasattr(obj, "_fieldnames"):
        return {n: np.asarray(getattr(obj, n)).ravel() for n in obj._fieldnames}
    if isinstance(obj, dict):
        return {k: np.asarray(v).ravel() if isinstance(v, (np.ndarray, list)) else v for k, v in obj.items()}
    return {"reward": obj}
