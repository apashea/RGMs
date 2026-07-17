"""W2 Phase 5-S-1 — optim-owned hierarchical Q/O field helpers."""
from __future__ import annotations

import copy
import os
from typing import Any

import numpy as np

from python_src.optimized.toolbox.DEM.vb_primitives_optim import _vb_o_cell_to_column
from python_src.toolbox.DEM.spm_VBX import _a_colon_s_coerce_likelihood_

def _vb_hierarchical_q_O_is_ng_t_rows(level: Any) -> bool:
    """``mdp.Q.O{L}`` as ``Ng`` rows of ragged time vectors (MATLAB ``cell(Ng,T)`` / loadmat)."""
    if not isinstance(level, list) or not level:
        return False
    first = level[0]
    return isinstance(first, (list, tuple))


def _vb_hierarchical_O_field_to_ng_t_rows(
    O_field: Any,
    t_child: int,
    *,
    ng: int = 0,
    no: list[int] | None = None,
) -> list[list[np.ndarray]]:
    """
    ``mdp.Q.O{L} = [mdp.Q.O{L} mdp.O]`` (~1238): store/append as ``Ng×T`` ragged rows.

    Child ``mdp.O`` after assemble is post-``shiftdim`` ``O[t][g]`` (T×Ng); MATLAB ``Q.O``
    uses ``cell(Ng,T)`` (``O[g][t]``) before paired compare transpose. Each row is one modality's
    ``No(g)`` outcome vector at time ``t``.
    """
    t_child = max(0, int(t_child))
    no_use = list(no) if no else []
    ng_use = int(ng)

    if isinstance(O_field, list) and O_field and isinstance(O_field[0], (list, tuple)):
        n_outer = len(O_field)
        n_inner = len(O_field[0]) if O_field[0] else 0
        if ng_use > 0 and n_outer == ng_use:
            ncol = min(
                t_child,
                max((len(O_field[g]) for g in range(ng_use)), default=0),
            )
            out = []
            for g in range(ng_use):
                n_g = int(no_use[g]) if g < len(no_use) else 0
                row_g = O_field[g]
                row = []
                for t in range(ncol):
                    part = row_g[t] if t < len(row_g) else None
                    row.append(
                        _vb_o_cell_to_column(part, n_g).ravel().copy()
                        if part is not None
                        else np.zeros(max(1, n_g), dtype=np.float64)
                    )
                out.append(row)
            return out
        if t_child > 0 and n_outer == t_child and (ng_use <= 0 or n_inner == ng_use):
            ng_use = n_inner if ng_use <= 0 else ng_use
            ncol = min(t_child, n_outer)
            out = []
            for g in range(ng_use):
                n_g = int(no_use[g]) if g < len(no_use) else 0
                row = []
                for t in range(ncol):
                    part = (
                        O_field[t][g]
                        if t < len(O_field) and g < len(O_field[t])
                        else None
                    )
                    row.append(
                        _vb_o_cell_to_column(part, n_g).ravel().copy()
                        if part is not None
                        else np.zeros(max(1, n_g), dtype=np.float64)
                    )
                out.append(row)
            return out

    mat = _vb_hierarchical_O_field_to_matrix(O_field, t_child, no=no_use)
    if mat.size == 0 or int(mat.shape[1]) < 1:
        return []
    ncol = min(t_child, int(mat.shape[1]))
    if ng_use < 1:
        ng_use = len(no_use) if no_use else 1
    if len(no_use) < ng_use:
        step = max(1, int(mat.shape[0] // max(1, ng_use)))
        no_use = [step] * (ng_use - 1) + [max(1, int(mat.shape[0] - step * (ng_use - 1)))]
    out = []
    for g in range(ng_use):
        row0 = sum(int(no_use[gi]) for gi in range(g))
        n_g = int(no_use[g]) if g < len(no_use) else 1
        row = []
        for t in range(ncol):
            col = np.asarray(mat[:, t], dtype=np.float64).reshape(-1, order="F")
            if row0 + n_g <= col.shape[0]:
                row.append(np.asarray(col[row0 : row0 + n_g], dtype=np.float64).copy())
            else:
                row.append(np.zeros(max(1, n_g), dtype=np.float64))
        out.append(row)
    return out


def _vb_hierarchical_q_O_ng_t_hstack(
    old: Any,
    new_rows: list[list[np.ndarray]],
) -> list[list[np.ndarray]]:
    """MATLAB ``[mdp.Q.O{L} mdp.O]`` on ``cell(Ng,T)`` — append time along columns (dim 2)."""
    if old is None:
        return copy.deepcopy(new_rows)
    if isinstance(old, np.ndarray):
        ng_guess = len(new_rows)
        old_rows = _vb_hierarchical_O_field_to_ng_t_rows(
            old,
            t_child=int(old.shape[1]) if old.ndim >= 2 else 1,
            ng=ng_guess,
        )
        return _vb_hierarchical_q_O_ng_t_hstack(old_rows, new_rows)
    if isinstance(old, list) and old and _vb_hierarchical_q_O_is_ng_t_rows(old):
        ng = max(len(old), len(new_rows))
        out: list[list[np.ndarray]] = []
        for g in range(ng):
            row_old = list(old[g]) if g < len(old) else []
            row_new = list(new_rows[g]) if g < len(new_rows) else []
            out.append(
                [np.asarray(x, dtype=np.float64).copy() for x in row_old]
                + [np.asarray(x, dtype=np.float64).copy() for x in row_new]
            )
        return out
    return copy.deepcopy(new_rows)


def _vb_hierarchical_q_O_prev_ncols(ol: Any, *, ng: int = 0) -> int:
    """
    MATLAB ``size(mdp.Q.O{mdp.L}, 2)`` — column count for hierarchical ``S`` segment offset.

    Canonical ``mdp.Q.O{L}`` is ``Ng×T`` ragged rows (``len(row[g])`` = time width). Legacy flat
    rows and stacked matrices are still supported for migration/oracles.
    """
    if ol is None:
        return 0
    if isinstance(ol, np.ndarray):
        arr = np.asarray(ol, dtype=np.float64)
        if arr.ndim >= 2:
            return int(arr.shape[1])
        return int(arr.size > 0)
    if isinstance(ol, list):
        if not ol:
            return 0
        if _vb_hierarchical_q_O_is_ng_t_rows(ol):
            return int(max(len(ol[g]) for g in range(len(ol))))
        n_leaf = int(len(ol))
        if n_leaf < 1:
            return 0
        max_ncol = 256
        max_ng_record = 200
        child_ng = int(ng)
        if child_ng > 0 and n_leaf % child_ng == 0:
            ncol_child = n_leaf // child_ng
            if ncol_child <= max_ncol:
                return int(ncol_child)
        best_ng = 0
        best_ncol = 0
        for ng_c in range(1, min(n_leaf, max_ng_record) + 1):
            if n_leaf % ng_c != 0:
                continue
            ncol = n_leaf // ng_c
            if ncol > max_ncol:
                continue
            if ng_c > best_ng:
                best_ng = ng_c
                best_ncol = ncol
        if best_ncol > 0:
            return int(best_ncol)
        try:
            arr = np.asarray(ol, dtype=np.float64)
            if arr.ndim >= 2:
                return int(arr.shape[1])
        except Exception:
            pass
        return n_leaf
    return 0


def _vb_no_list_from_mdp(md: dict[str, Any]) -> list[int]:
    """``No(m,g) = size(MDP(m).A{g},1)`` (~386) for hierarchical ``Q.O`` cell splits."""
    A = md.get("A", [])
    if not isinstance(A, list):
        return []
    out: list[int] = []
    for ag in A:
        try:
            out.append(int(_a_colon_s_coerce_likelihood_(ag).shape[0]))
        except Exception:
            out.append(1)
    return out


def _vb_hierarchical_q_o_field_to_cell_row(
    O_field: Any,
    t_child: int,
    *,
    ng: int = 0,
    no: list[int] | None = None,
) -> list[Any]:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~1238 ``mdp.Q.O{mdp.L} = [.. mdp.O]``.

    After child VB, ``mdp.O`` is ``shiftdim(O,1)`` (~1759–1764) → ``T×Ng`` cells via
    ``_vb_shiftdim_o_ng_t_cells``. Flatten ``g`` then ``t`` (MATLAB ``(:)`` on ``T×Ng``,
    index ``t + g*T``) for ``mdp.Q.O{L}=[..mdp.O]`` (~1238). Variable ``No(g)`` splits
    use ``size(MDP(m).A{g},1)`` (~386), not equal row blocks.
    """
    t_child = int(t_child)
    if isinstance(O_field, list) and O_field and isinstance(O_field[0], (list, tuple)):
        n_outer = len(O_field)
        n_inner = len(O_field[0]) if O_field[0] else 0
        # ``_vb_shiftdim_o_ng_t_cells``: out[t][g]
        no_use = list(no) if no else []
        if t_child > 0 and n_outer == t_child and (ng <= 0 or n_inner == ng):
            # Post-``shiftdim`` ``mdp.O`` is ``T×Ng`` (~1764). ``[mdp.Q.O{L} mdp.O]`` (~1238) linearizes
            # that cell block as MATLAB ``(:)`` — column-major on ``T×Ng``, index ``t + g*T``.
            cells: list[Any] = []
            ng_use = int(ng) if int(ng) > 0 else n_inner
            ncol = min(t_child, n_outer)
            for g in range(ng_use):
                for t in range(ncol):
                    n_g = int(no_use[g]) if g < len(no_use) else 0
                    if t < len(O_field) and g < len(O_field[t]):
                        part = O_field[t][g]
                    else:
                        part = None
                    if part is None:
                        cells.append(np.zeros((max(1, n_g), 1), dtype=np.float64))
                    else:
                        cells.append(_vb_o_cell_to_column(part, n_g))
            return cells
        # Internal ``O{m,g,t}`` shell: ``O_mi[g][t]`` on ``Ng×T`` — MATLAB ``(:)`` uses ``g + t*Ng``.
        if ng > 0 and n_outer == ng:
            cells = []
            ncol = min(t_child, max((len(O_field[g]) for g in range(ng)), default=0))
            for g in range(ng):
                for t in range(ncol):
                    row_g = O_field[g]
                    if t < len(row_g) and row_g[t] is not None:
                        n_g = int(no_use[g]) if g < len(no_use) else 0
                        cells.append(_vb_o_cell_to_column(row_g[t], n_g))
                    else:
                        n_g = int(no_use[g]) if g < len(no_use) else 1
                        cells.append(np.zeros((max(1, n_g), 1), dtype=np.float64))
            return cells
    mat = _vb_hierarchical_O_field_to_matrix(O_field, t_child, no=no)
    if mat.size == 0:
        return []
    ncol = min(t_child, int(mat.shape[1]))
    if ncol < 1:
        return []
    ng_i = int(ng) if int(ng) > 0 else (len(no) if no else 0)
    if ng_i < 1:
        return [np.asarray(mat, dtype=np.float64).reshape(-1, 1, order="F")]
    no_use = list(no) if no else []
    if len(no_use) < ng_i:
        step = max(1, int(mat.shape[0] // ng_i))
        no_use = [step] * (ng_i - 1) + [max(1, int(mat.shape[0] - step * (ng_i - 1)))]
    cells: list[Any] = []
    for g in range(ng_i):
        n_g = int(no_use[g]) if g < len(no_use) else 0
        row0 = sum(int(no_use[gi]) for gi in range(g))
        for t in range(ncol):
            col = np.asarray(mat[:, t], dtype=np.float64).reshape(-1, order="F")
            if n_g < 1:
                cells.append(np.zeros((1, 1), dtype=np.float64))
            elif row0 + n_g <= col.shape[0]:
                cells.append(
                    np.asarray(col[row0 : row0 + n_g], dtype=np.float64).reshape(-1, 1, order="F")
                )
            else:
                cells.append(np.zeros((max(1, n_g), 1), dtype=np.float64))
    return cells


def _vb_hierarchical_O_field_to_matrix(
    O_field: Any,
    t_int: int,
    *,
    no: list[int] | None = None,
) -> np.ndarray:
    """
    Normalize ``mdp.O`` / assembled ``shiftdim`` cells to a 2-D matrix for ``[Q.O{L} old new]``.

    MATLAB appends ``mdp.O`` horizontally; list-concat of ``shiftdim`` cells breaks ``size(...,2)``.
    """
    if O_field is None:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    if isinstance(O_field, np.ndarray):
        arr = np.asarray(O_field, dtype=np.float64)
        if arr.ndim == 1:
            return arr.reshape(-1, 1, order="F")
        return np.asfortranarray(arr)
    if isinstance(O_field, list) and O_field:
        if isinstance(O_field[0], list):
            cols: list[np.ndarray] = []
            n_t = int(t_int) if int(t_int) > 0 else len(O_field)
            no_use = list(no) if no else []
            for ti in range(min(n_t, len(O_field))):
                row = O_field[ti]
                ng_row = len(row)
                parts = [
                    _vb_o_cell_to_column(
                        row[g],
                        int(no_use[g]) if g < len(no_use) else 0,
                    )
                    for g in range(ng_row)
                ]
                if parts:
                    cols.append(np.vstack(parts))
            if not cols:
                return np.zeros((0, 0), dtype=np.float64, order="F")
            return np.asfortranarray(np.hstack(cols))
        try:
            arr = np.asarray(O_field, dtype=np.float64)
            if arr.ndim >= 2:
                return np.asfortranarray(arr)
        except Exception:
            pass
    return np.zeros((0, 0), dtype=np.float64, order="F")


def _vb_hierarchical_apply_S_as_O_if_present(child: dict[str, Any]) -> None:
    """
    Ground truth: ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` ~1178–1191.

    After ``rmfield(mdp,'O')`` / ``rmfield(mdp,'o')`` (~1169–1173), optional ``mdp.O = mdp.S(:,seg(j))``
    (dense matrix, **not** ``mdp.O{g,t}``). Child init ~732–752 must not treat that matrix as one row per ``g``
    (see ``_vb_mdp_O_is_cell_gt_layout``).
    """
    if "S" not in child or child.get("S") is None:
        return
    S = np.asarray(child["S"], dtype=np.float64)
    if S.size == 0:
        return
    t_md = int(np.asarray(child.get("T", 1)).ravel()[0])
    L = max(1, int(np.asarray(child.get("L", 1)).ravel()[0]))
    S2 = S.reshape(S.shape[0], -1, order="F") if S.ndim >= 2 else S.reshape(-1, 1, order="F")
    n_col_s = int(S2.shape[1])
    prev_cols = 0
    qrec = child.get("Q")
    if isinstance(qrec, dict) and "O" in qrec:
        Oc = qrec.get("O")
        if isinstance(Oc, (list, tuple)) and len(Oc) >= L:
            ol = Oc[L - 1]
            ng_m = len(child.get("A", [])) if isinstance(child.get("A"), list) else 0
            prev_cols = _vb_hierarchical_q_O_prev_ncols(ol, ng=ng_m)
    seg = np.arange(1, t_md + 1, dtype=np.int64) + int(prev_cols)
    mask = seg <= n_col_s
    use = seg[mask]
    n_row = int(S2.shape[0])
    if use.size == 0:
        child["O"] = np.zeros((n_row, 0), dtype=np.float64, order="F")
    else:
        idx0 = (use - 1).astype(np.int64, copy=False)
        child["O"] = np.asfortranarray(np.asarray(S2[:, idx0], dtype=np.float64))
    if os.getenv("RGMS_ENTRY12_PROBE_HIER"):
        import sys as _sys

        print(
            f"[12E S→O] T={t_md} prev_cols={prev_cols} seg={seg.ravel()[:6]} "
            f"O.shape={np.asarray(child.get('O')).shape}",
            file=_sys.stderr,
            flush=True,
        )


def _vb_hierarchical_field_to_ot_nested(field: Any, *, t_child: int) -> list[list[Any]]:
    """
    ``mdp.Y{o,t}`` / ``mdp.j{g,t}`` as nested ``[o][t]`` (Ng×T), not a flat ``(:)`` row.

    ``mdp.o`` is an ``Ng×T`` **scalar** matrix (~725, ~4965); use the ``s``/``u``/``o`` matrix
    append branch in ``_vb_hierarchical_q_append_level``, not this helper.
    """
    t_child = max(0, int(t_child))
    if not isinstance(field, list) or not field:
        if isinstance(field, np.ndarray):
            arr = np.asarray(field, dtype=np.float64)
            if arr.ndim == 2 and arr.size:
                ncol = min(t_child, int(arr.shape[1]))
                return [
                    [np.asarray(arr[g, t], dtype=np.float64).reshape(1).copy() for t in range(ncol)]
                    for g in range(int(arr.shape[0]))
                ]
        return []
    if isinstance(field[0], (list, tuple)):
        out: list[list[Any]] = []
        for o_row in field:
            row = list(o_row) if isinstance(o_row, (list, tuple)) else [o_row]
            out.append(
                [
                    copy.deepcopy(row[t]) if t < len(row) else None
                    for t in range(t_child)
                ]
            )
        return out
    arr = np.asarray(field, dtype=np.float64)
    if arr.ndim >= 2:
        ncol = min(t_child, int(arr.shape[1]))
        return [
            [np.asarray(arr[o, t], dtype=np.float64).reshape(-1, 1).copy() for t in range(ncol)]
            for o in range(int(arr.shape[0]))
        ]
    return [[np.asarray(arr, dtype=np.float64).reshape(-1, 1).copy()]]


def _vb_hierarchical_q_ot_nested_hstack(
    old: Any,
    new_nested: list[list[Any]],
) -> list[list[Any]]:
    """MATLAB ``[mdp.Q.Y{L} mdp.Y]`` on ``cell(Ng,T)`` — append along time (columns)."""
    if old is None:
        return copy.deepcopy(new_nested)
    if isinstance(old, list) and old and isinstance(old[0], (list, tuple)):
        ng = max(len(old), len(new_nested))
        out: list[list[Any]] = []
        for o in range(ng):
            row_old = list(old[o]) if o < len(old) else []
            row_new = list(new_nested[o]) if o < len(new_nested) else []
            out.append(list(row_old) + list(row_new))
        return out
    return copy.deepcopy(new_nested)


def _vb_hierarchical_q_ot_grid_to_cell_row(field: list[Any], *, t_child: int) -> list[Any]:
    """
    Flatten ``mdp.Y{o,t}`` / ``mdp.j{g,t}``-style nested lists ``field[o][t]`` to a cell row.

    MATLAB stores these as ``Ng``×``T`` cell matrices; ``[Q.*{L} mdp.*]`` uses ``(:)`` order
    (column-major): flat index ``o + t*Ng``.
    """
    cells: list[Any] = []
    n_o = len(field)
    for t in range(t_child):
        for o in range(n_o):
            row = field[o]
            if not isinstance(row, (list, tuple)) or t >= len(row) or row[t] is None:
                cells.append(np.zeros((1, 1), dtype=np.float64))
                continue
            cells.append(np.asarray(row[t], dtype=np.float64).reshape(-1, 1, order="F"))
    return cells


def _vb_hierarchical_q_field_to_cell_row(field: Any, *, t_child: int, kind: str) -> list[Any]:
    """
    Flatten one child ``mdp`` field to a MATLAB-style cell row for ``mdp.Q.*{L} = [old new]``.

  ``O`` uses ``_vb_hierarchical_q_o_field_to_cell_row`` (``shiftdim`` cells or ``S`` matrix); other keys use cell rows.
    """
    if field is None:
        return []
    if kind == "O":
        return _vb_hierarchical_q_o_field_to_cell_row(field, t_child)
    if kind in ("s", "u"):
        arr = np.asarray(field, dtype=np.float64).reshape(-1, 1)
        return [arr.copy()]
    if kind in ("P", "X") and isinstance(field, list):
        out_mats: list[Any] = []
        for pf in field:
            arr = np.asarray(pf, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            ncol = min(t_child, int(arr.shape[1]))
            out_mats.append(np.asfortranarray(arr[:, :ncol].copy()))
        return out_mats
    if isinstance(field, list) and len(field) == 1:
        return _vb_hierarchical_q_field_to_cell_row(field[0], t_child=t_child, kind=kind)
    if isinstance(field, list) and field and isinstance(field[0], (list, tuple)):
        if kind in ("Y", "j", "i", "o"):
            return _vb_hierarchical_q_ot_grid_to_cell_row(field, t_child=t_child)
    if kind in ("Y", "j", "o") or isinstance(field, (list, tuple)):
        arr = np.asarray(field, dtype=np.float64)
        if arr.ndim >= 3:
            ncol = min(t_child, int(arr.shape[1]))
            cells = []
            for t in range(ncol):
                slab = arr[:, t, ...]
                for g in range(int(slab.shape[0])):
                    cells.append(np.asarray(slab[g, ...], dtype=np.float64).reshape(-1, 1, order="F"))
            return cells
    arr = np.asarray(field, dtype=np.float64)
    if arr.ndim == 2:
        return [arr[:, t : t + 1].copy() for t in range(min(t_child, arr.shape[1]))]
    return [arr.reshape(-1, 1, order="F")]


def _vb_hierarchical_q_O_flat_cells_to_matrix(
    cells: list[Any],
    *,
    ng: int,
    no: list[int],
) -> np.ndarray:
    """Rebuild numeric ``mdp.Q.O{L}`` from flat row (``g`` outer, ``t`` inner; index ``t + g*ncol``)."""
    if not cells or ng < 1:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    n_leaf = len(cells)
    if n_leaf % ng != 0:
        return _vb_hierarchical_O_field_to_matrix(
            cells, max(1, n_leaf // max(1, ng)), no=no
        )
    ncol = n_leaf // ng
    no_use = list(no) if no else [1] * ng
    cols: list[np.ndarray] = []
    for t in range(ncol):
        parts: list[np.ndarray] = []
        for g in range(ng):
            idx = t + g * ncol
            n_g = int(no_use[g]) if g < len(no_use) else 1
            parts.append(_vb_o_cell_to_column(cells[idx], n_g))
        cols.append(np.vstack(parts) if parts else np.zeros((0, 1), dtype=np.float64))
    if not cols:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    max_h = max(int(c.shape[0]) for c in cols)
    out = np.zeros((max_h, ncol), dtype=np.float64, order="F")
    for t, col in enumerate(cols):
        out[: col.shape[0], t : t + 1] = col
    return out


def _vb_hierarchical_q_O_level_to_matrix(
    level: Any,
    *,
    t_child: int,
    ng: int,
    no: list[int],
) -> np.ndarray:
    """
  MATLAB ``mdp.Q.O{mdp.L} = [mdp.Q.O{mdp.L} mdp.O]`` (~1238): horizontal matrix concat, not cell-list cat.
    """
    if level is None:
        return np.zeros((0, 0), dtype=np.float64, order="F")
    if isinstance(level, list) and level and _vb_hierarchical_q_O_is_ng_t_rows(level):
        ncol = max((len(level[g]) for g in range(len(level))), default=0)
        cols: list[np.ndarray] = []
        no_use = list(no) if no else []
        ng_use = len(level) if ng <= 0 else ng
        for t in range(ncol):
            parts: list[np.ndarray] = []
            for g in range(ng_use):
                n_g = int(no_use[g]) if g < len(no_use) else 0
                row_g = level[g] if g < len(level) else []
                part = row_g[t] if t < len(row_g) else None
                parts.append(
                    _vb_o_cell_to_column(part, n_g)
                    if part is not None
                    else np.zeros((max(1, n_g), 1), dtype=np.float64)
                )
            cols.append(np.vstack(parts) if parts else np.zeros((0, 1), dtype=np.float64))
        if not cols:
            return np.zeros((0, 0), dtype=np.float64, order="F")
        return np.asfortranarray(np.hstack(cols))
    if isinstance(level, np.ndarray):
        arr = np.asarray(level, dtype=np.float64)
        if arr.ndim == 1:
            return arr.reshape(-1, 1, order="F")
        return np.asfortranarray(arr)
    if isinstance(level, list) and level:
        if isinstance(level[0], (list, tuple)):
            return _vb_hierarchical_O_field_to_matrix(level, t_child, no=no)
        return _vb_hierarchical_q_O_flat_cells_to_matrix(level, ng=ng, no=no)
    return np.zeros((0, 0), dtype=np.float64, order="F")


