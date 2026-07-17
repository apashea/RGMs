"""ENTRY 12PLOT driver — fence composition; no VB re-run."""

from __future__ import annotations

import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat

from python_src.toolbox.DEM.spm_figure import spm_figure, spm_figure_clf
from python_src.toolbox.DEM.spm_show_RGB import spm_show_RGB
from python_src.toolbox.DEM.entry12_matlab_capture import _entry12_flatten_Q_E_nested_for_compare

DEFAULT_TAG = "rgms_canonical"


def entry12plot_timestamp() -> str:
    """Filename-friendly timestamp: ``yyyy-mm-dd-HH-MM-SS``."""
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def entry12plot_png_path(repo_root: Path, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return repo_root / "visualizations" / f"AtariIII_12plot_{ts}.png"


def entry12plot_python_pkl_pdp_png_path(repo_root: Path, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return repo_root / "visualizations" / f"AtariIII_12plot_python_pkl_pdp_{ts}.png"


def entry12plot_compare_matlab_vs_pklpdp_path(repo_root: Path, ts: str | None = None) -> Path:
    ts = ts or entry12plot_timestamp()
    return repo_root / "visualizations" / f"AtariIII_12plot_compare_matlab_vs_pklpdp_{ts}.png"


def visualizations_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / "visualizations"


def fixtures_dir(repo_root: Path | None = None) -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


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


def load_pdp_pkl_for_plot(path: Path, *, mat_template_path: Path | None = None) -> dict:
    """Load Python Entry 12 ``PDP`` and reshape hierarchical plot fields for ``spm_show_RGB``."""
    with open(path, "rb") as f:
        blob = pickle.load(f)
    pdp = blob["PDP"] if isinstance(blob, dict) and "PDP" in blob else blob
    pdp = _normalize_pdp_pkl_for_plot(pdp)
    mat_path = mat_template_path or pdp_mat_path()
    if mat_path.is_file():
        mat_pdp = load_pdp_mat_for_plot(mat_path)
        pdp = _align_pdp_pkl_q_e_to_mat_for_plot(pdp, mat_pdp)
    return pdp


def _coerce_q_e_level_to_vector(level: Any) -> np.ndarray:
    """One ``Q.E{n}`` level → 1-D ``float64`` (``spm_show_RGB`` uses ``numel``).

    Nested list blocks from script **3** pickle → flat vector (same semantics as
    MATLAB ``[Q.E{L} mdp.F]`` / ``loadmat`` layout; see compare-lane flatten).
    """
    if isinstance(level, list):
        return np.asarray(_entry12_flatten_Q_E_nested_for_compare(level), dtype=np.float64).ravel()
    return np.asarray(level, dtype=np.float64).ravel()


def _reshape_q_e_level_for_plot(level: Any) -> np.ndarray:
    """``Q.E{n}`` as ``(1, T)`` row vector like MATLAB ``loadmat`` on **12H** ``PDP``."""
    vec = _coerce_q_e_level_to_vector(level)
    if vec.size == 0:
        return vec
    return vec.reshape(1, -1)


def _align_pdp_pkl_q_e_to_mat_for_plot(pkl_pdp: dict, mat_pdp: dict) -> dict:
    """
    Reshape ``Q.E`` to MATLAB ``loadmat`` template shape when numel already matches.

    After correct nested flatten, only ``reshape(..., order='F')`` may be needed;
    pad/truncate with zeros remains a fallback if lane sizes diverge on refresh.
    """
    import copy

    out = copy.deepcopy(pkl_pdp)
    pkl_q = out.get("Q")
    mat_q = mat_pdp.get("Q")
    if not isinstance(pkl_q, dict) or not isinstance(mat_q, dict):
        return out
    pkl_e = pkl_q.get("E")
    mat_e = mat_q.get("E")
    if not isinstance(pkl_e, list) or not isinstance(mat_e, list):
        return out
    aligned: list[Any] = []
    for i, mat_level in enumerate(mat_e):
        mat_vec = np.asarray(mat_level, dtype=np.float64).ravel()
        if i < len(pkl_e):
            py_vec = _coerce_q_e_level_to_vector(pkl_e[i])
        else:
            py_vec = np.zeros(0, dtype=np.float64)
        if py_vec.size < mat_vec.size:
            py_vec = np.concatenate([py_vec, np.zeros(mat_vec.size - py_vec.size, dtype=np.float64)])
        elif py_vec.size > mat_vec.size:
            py_vec = py_vec[: mat_vec.size]
        mat_shape = np.asarray(mat_level, dtype=np.float64).shape
        aligned.append(py_vec.reshape(mat_shape) if mat_shape else py_vec)
    pkl_q["E"] = aligned
    return out


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
    e_field = q.get("E")
    if isinstance(e_field, list):
        q["E"] = [_reshape_q_e_level_for_plot(level) for level in e_field]
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


def _unwrap_hier_q_field_mat_miswrap(field: Any) -> Any:
    """Repair ``Q.O``/``Q.Y`` saved as ``1×N`` row-of-row-cells vs ``{1×1}``{N×T} wrapper."""
    if not isinstance(field, list) or len(field) != 1 or not isinstance(field[0], list):
        return field
    inner = field[0]
    if not inner or not isinstance(inner[0], list):
        return field
    if len(inner[0]) == 1 and isinstance(inner[0][0], list) and len(inner[0][0]) > 1:
        nrow = len(inner)
        ncol = len(inner[0][0])
        grid = [[inner[r][0][c] for c in range(ncol)] for r in range(nrow)]
        return [grid]
    return field


def _fix_mat_pdp_hier_plot_layout(pdp: dict) -> dict:
    """Normalize hierarchical ``Q.O``/``Q.Y`` after ``loadmat`` for ``spm_show_RGB``."""
    import copy

    out = copy.deepcopy(pdp)
    q = out.get("Q")
    if isinstance(q, dict):
        for fk in ("O", "Y"):
            if fk in q:
                q[fk] = _unwrap_hier_q_field_mat_miswrap(q[fk])
    return out


def load_pdp_mat_for_plot(path: Path) -> dict:
    """Load ``PDP`` from ``.mat`` preserving hierarchical ``Q.O`` / ``Q.Y`` cell layout."""
    raw = loadmat(str(path), struct_as_record=False, squeeze_me=False)
    pdp = _mat_struct_to_plot_dict(_unwrap_matlab_scalar(raw["PDP"]))
    return _fix_mat_pdp_hier_plot_layout(pdp)


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

    spm_figure("GetWin", "Generative AI")
    spm_figure_clf("Generative AI")
    j, k = spm_show_RGB(pdp, rgb)
    q_o = pdp["Q"]["o"]
    o1 = q_o[0] if isinstance(q_o, list) else q_o
    h = spm_get_hits(o1, gdp_id)

    fig = plt.gcf()
    ax_elbo = getattr(fig, "_rgms_elbo_ax", None)
    if ax_elbo is None:
        raise RuntimeError("spm_show_RGB did not set fig._rgms_elbo_ax for hits overlay")
    ax_elbo.plot(h, np.zeros_like(h, dtype=np.float64), ".r", markersize=16)
    plt.draw()

    out_png: Path | None = None
    if save_png:
        out_png = png_path or entry12plot_png_path(root)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.gcf().savefig(out_png, dpi=100, bbox_inches="tight", pad_inches=0.15)

    return j, k, h, out_png


def resolve_matlab_12plot_reference_png(
    repo_root: Path | None = None,
    *,
    tag: str = DEFAULT_TAG,
) -> Optional[Path]:
    """MATLAB capture PNG for Phase **4** compare (``12PLOT.mat`` meta, env, or newest capture)."""
    root = repo_root or Path(__file__).resolve().parents[3]
    env = str(os.getenv("RGMS_ENTRY12_12PLOT_MATLAB_PNG", "")).strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
    oracle = plot_oracle_mat_path(tag, root)
    if oracle.is_file():
        raw = loadmat(str(oracle), squeeze_me=True, struct_as_record=False)
        meta = raw.get("meta")
        if meta is not None:
            meta = _unwrap_matlab_scalar(meta)
            if hasattr(meta, "_fieldnames") and "png_path" in meta._fieldnames:
                p = Path(str(getattr(meta, "png_path")))
                if p.is_file():
                    return p.resolve()
    vis = visualizations_dir(root)
    if not vis.is_dir():
        return None
    skip = ("python", "compare", "matpdp", "pklpdp")
    candidates = [
        p
        for p in vis.glob("AtariIII_12plot_*.png")
        if not any(s in p.name.lower() for s in skip)
    ]
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime).resolve()
    return None


def compose_entry12plot_matlab_vs_pklpdp_png(
    matlab_png: Path,
    pkl_python_png: Path,
    out_path: Path,
) -> Path:
    """Side-by-side: MATLAB (left), Python **``.pkl``** PDP plot (right)."""
    from PIL import Image, ImageDraw

    left = Image.open(matlab_png).convert("RGB")
    right = Image.open(pkl_python_png).convert("RGB")
    target_h = max(left.height, right.height)

    def _scale(im: Any) -> Any:
        if im.height == target_h:
            return im
        w = int(im.width * target_h / im.height)
        return im.resize((w, target_h), Image.Resampling.LANCZOS)

    left_s, right_s = _scale(left), _scale(right)
    label_h, gap = 28, 16
    w = left_s.width + gap + right_s.width
    canvas = Image.new("RGB", (w, label_h + target_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 4), "MATLAB (left)  |  Python .pkl PDP (right)", fill=(0, 0, 0))
    canvas.paste(left_s, (0, label_h))
    canvas.paste(right_s, (left_s.width + gap, label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path


def _stack_labeled_pngs(labeled_paths: list[tuple[str, Path]], out_path: Path) -> Path:
    """Vertical stack of labeled PNG panels (Phase **4** review compares)."""
    from PIL import Image, ImageDraw

    imgs = [Image.open(p).convert("RGB") for _, p in labeled_paths]
    label_h, gap = 28, 12
    w = max(im.width for im in imgs)
    h = sum(label_h + im.height + gap for im in imgs) - gap
    out = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(out)
    y = 0
    for (label, _), im in zip(labeled_paths, imgs):
        draw.text((8, y + 4), label, fill=(0, 0, 0))
        y += label_h
        out.paste(im, ((w - im.width) // 2, y))
        y += im.height + gap
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return out_path


def run_entry12plot_phase_b_visual_review(
    repo_root: Path | None = None,
    *,
    ts: str | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Path, Optional[Path]]:
    """Phase **B** plot PNG + MATLAB-vs-**``.pkl``** side-by-side compare (no VB re-run)."""
    root = repo_root or Path(__file__).resolve().parents[3]
    ts = ts or entry12plot_timestamp()
    ctx = load_plot_ctx_from_mat(plot_ctx_mat_path(root))
    pdp = load_pdp_pkl_for_plot(pdp_pkl_path(root))
    pkl_png = entry12plot_python_pkl_pdp_png_path(root, ts)
    j, k, h, saved = run_entry12plot(pdp, ctx, repo_root=root, save_png=True, png_path=pkl_png)
    assert saved is not None
    matlab_ref = resolve_matlab_12plot_reference_png(root)
    compare: Optional[Path] = None
    if matlab_ref is not None:
        compare = compose_entry12plot_matlab_vs_pklpdp_png(
            matlab_ref,
            saved,
            entry12plot_compare_matlab_vs_pklpdp_path(root, ts),
        )
    return j, k, h, saved, compare


def run_entry12plot_visual_review_pngs(
    repo_root: Path | None = None,
    *,
    ts: str | None = None,
) -> dict[str, Optional[Path]]:
    """Regenerate Phase **4** review PNG set (``.mat``/``.pkl`` singles + compare panels)."""
    root = repo_root or Path(__file__).resolve().parents[3]
    ts = ts or entry12plot_timestamp()
    vis = visualizations_dir(root)
    ctx = load_plot_ctx_from_mat(plot_ctx_mat_path(root))
    mat_pdp = load_pdp_mat_for_plot(pdp_mat_path(root))
    pkl_pdp = load_pdp_pkl_for_plot(pdp_pkl_path(root))
    mat_png_path = vis / f"AtariIII_12plot_python_mat_pdp_{ts}.png"
    pkl_png_path = entry12plot_python_pkl_pdp_png_path(root, ts)
    _, _, _, mat_png = run_entry12plot(
        mat_pdp, ctx, repo_root=root, save_png=True, png_path=mat_png_path
    )
    _, _, _, pkl_png = run_entry12plot(
        pkl_pdp, ctx, repo_root=root, save_png=True, png_path=pkl_png_path
    )
    assert mat_png is not None and pkl_png is not None
    matlab_ref = resolve_matlab_12plot_reference_png(root)
    compare_mk: Optional[Path] = None
    compare_3: Optional[Path] = None
    if matlab_ref is not None:
        compare_mk = compose_entry12plot_matlab_vs_pklpdp_png(
            matlab_ref,
            pkl_png,
            entry12plot_compare_matlab_vs_pklpdp_path(root, ts),
        )
        compare_3 = _stack_labeled_pngs(
            [
                ("MATLAB (12PLOT capture)", matlab_ref),
                (f"Python .mat PDP ({ts})", mat_png),
                (f"Python .pkl PDP ({ts})", pkl_png),
            ],
            vis / f"AtariIII_12plot_compare_matlab_matpdp_pklpdp_{ts}.png",
        )
    compare_pp = _stack_labeled_pngs(
        [
            (f"Python .mat PDP ({ts})", mat_png),
            (f"Python .pkl PDP ({ts})", pkl_png),
        ],
        vis / f"AtariIII_12plot_compare_matpdp_vs_pklpdp_{ts}.png",
    )
    return {
        "ts": ts,
        "matlab_reference": matlab_ref,
        "python_mat_pdp": mat_png,
        "python_pkl_pdp": pkl_png,
        "compare_matlab_vs_pklpdp": compare_mk,
        "compare_matpdp_vs_pklpdp": compare_pp,
        "compare_matlab_matpdp_pklpdp": compare_3,
    }


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
