#!/usr/bin/env python3
"""FSL 1–11 **Validation (or Parity)** script: compare nested ``RDP`` from a saved run vs MATLAB ``.mat``.

The **FSL** 1–11 pytest writes ``ctx`` (including ``ctx["RDP"]``) to a PKL automatically after a **successful**
structural run (unless you override the output path with ``RGMS_ATARI_FSL_1_11_CONTEXT_PKL_PATH``).

This CLI loads that PKL plus the FSL MATLAB fixture (default ``fixtures/DEMAtariIII_fsl_1_11_rdp.mat``,
or ``RGMS_ATARI_FSL_1_11_MAT_PATH`` / ``--mat``). **Every run** applies, in order: **(1)** coarse
``spm_MDP_checkX``-style / ``T`` schema on **``ctx["RDP"]``**; **(2)** the same schema on the nested
**``RDP``** from ``loadmat``; **(3)** a **full nested type walk** (Python vs MATLAB structure / types; every mismatch
line, uncapped), each followed by two **``[mismatch detail]``** lines (PKL vs MATLAB at that path), then an **appended**
**focused probe** block for **``G``**, **``C``** (per modality), **``sB``**, and **``U``** (shape / scalar checks and
numeric squeeze-compare where applicable; **G** and **C** include further appended unnesting lines for dict/list cells),
then **append-only ``VALUE-DUMP``** sections: **``RDP.G``** full concatenated PKL vs MATLAB float64 ravels plus aligned
elementwise diff; **``RDP.MDP.G``** recursive per-index PKL vs MATLAB full ravels, diffs, and scalar unwrap lines;
**``C[g]``** full squeeze-ravel PKL/MAT vectors and elementwise diff per modality,
same stderr / report stream); **(4)** nested
parity via ``_assert_nested_rdp_equal``, unless
**``--check-rdp-checkx-schema-only``** or **``--report-type-mismatches-only``** stops after **(3)** (no assert).
It does **not** run ``run_dem_atariiii``. See
``Atari_example.md`` § **ENTRY 1-11** (subsection **C**). Each **validation** run writes a UTF-8 report under
``matlab_custom/fsl_1_11_compare_ctx_pkl_to_mat_output.txt`` (module docstring, then mirrored **stdout**
and **stderr** including tracebacks). **``-h`` / ``--help``** prints to the terminal only and **does not**
open or overwrite that file (so a help invocation cannot replace a prior diagnostic run).

--------------------------------------------------------------------
RDP as the object passed into Entry 12 VB (MATLAB names / audit paths)
--------------------------------------------------------------------

At the ledger boundary, ``RDP`` is the **generative-model bundle** that ``spm_MDP_VB_XXX`` treats as
``MDP`` on input. **MATLAB:** ``matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m`` immediately calls
``MDP = spm_MDP_checkX(MDP);`` (~line 207). **Checker reference:**
``matlab_src/toolbox/DEM/spm_MDP_checkX.m`` — documents and enforces the **MDP** shape (likelihood /
transition / priors / indices), including fields such as:

- **``A{g}``, ``B{f}``, ``C{g}``, ``D{f}``, ``E{f}``, ``H{f}``**, **``U``**, **``T``** (and optional
  concentration mirrors **``a,b,c,d,e,h``** when used).
- **``id``** subtree (e.g. **``id.g``**, **``id.A{g}``**, **``id.C{g}``**, …) for domain / co-domain
  bookkeeping.
- Normalization paths in ``checkX`` (e.g. forcing numeric **``A``/``B``** cells toward **``full``**
  ``double`` tensors and **``spm_dir_norm``** where applicable).

The **VB** header block in ``spm_MDP_VB_XXX.m`` (leading comments ~lines 5–50) lists additional
**``OPTIONS``**-gated behavior and optional fields (**``V``**, **``s,u,o,O``**, precisions, **``id.hid``** /
**``id.cid````, **``n``**, **``m``**, …). For **FSL 1–11 parity** we compare the **nested ``RDP``**
already produced by ``run_dem_atariiii(entry_stop=11)`` / MATLAB dump — **not** a post-``checkX`` VB
trajectory.

--------------------------------------------------------------------
``spm_MDP_checkX``-style schema (integrated — not optional)
--------------------------------------------------------------------

The **``_validate_rdp_checkx_schema``** pass is **always** applied to **both** trees (Python **``ctx["RDP"]``**
first, then MATLAB nested **``RDP``** after ``loadmat``). Before each schema pass, stderr lists **every**
top-level field as **``key=concise_type``** (e.g. ``ndarray(shape)``, ``list(len=…,elem=…)``, sparse
``typename(shape)``, ``dict(len=…)``). After both passes, one **non-fatal** line reports **only-in-PKL**
vs **only-in-MATLAB** top-level keys (with the same concise types for asymmetric keys); it never changes
the exit code by itself. **Then** the **nested type walk** always runs (full mismatch list plus **``[mismatch detail]``**
lines after each mismatch), then the **focused probe** append (**``G``**, **``C``**, **``sB``**, **``U``**). The schema pass mirrors the **inputs / coarse types** implied by
``matlab_src/toolbox/DEM/spm_MDP_checkX.m`` (likelihood **``A{g}``** / **``a``**, transitions **``B{f}``** /
**``b``**, **``U``**, **``C``**, **``D``**, **``E``**, **``id``**, header **``H``**) plus **``T``** (VB entry in
``spm_MDP_VB_XXX``). **PKL** schema **ERROR** aborts before MATLAB load, key diff, type walk, focused probe, or parity.
**MATLAB** schema **ERROR** still runs key diff, nested type walk, focused probe, then exits **1** before the
assert. **Default (non-strict):** only
**``B``/``b``** absence is **WARN**; missing **``U``**, **``C``**, … is reported only with
**``--check-rdp-checkx-strict``** (**ERROR** on **each** tree). Does **not** run ``spm_dir_norm``.

**``--check-rdp-checkx-schema-only``**
    After **(1)**–**(2)**, key diff, and **(3)** type walk: **exit** **0** if no schema **ERROR** on either
    side (**WARN** alone still **0**); **no** ``_assert_nested_rdp_equal``. Still requires the **``.mat``**.

**``--report-type-mismatches-only``**
    After the same **(1)**–**(3)** output as a full run, **exit** **0** without ``_assert_nested_rdp_equal``
    (parity verdict skipped).

After **each** type-walk mismatch line, **two** **``[mismatch detail]``** lines always follow, resolving the same path
on **PKL** vs **MATLAB** ``RDP`` (shape, dtype, short numeric preview where applicable, dict key heads, list/scalar
summaries). For paths under **``RDP.A``** / **``RDP.B``** / **``RDP.H``** / **``RDP.MDP.A``** / **``RDP.MDP.B``** /
**``RDP.MDP.H``**, when the mismatch involves tensor shapes that **jointly** include **524** and **485**, the first
detail line may be prefixed with
**``[accepted ledger dim 524 vs 485 - upstream Py/MATLAB; ENTRY 1-11 policy]``** (ledger drift accepted for validation).

**``--report-type-mismatches``**
    Accepted for backward compatibility; the type walk is **always** emitted (flag has no effect).

**``--check-rdp-checkx-strict``**
    Stricter schema on **both** PKL and MATLAB **``RDP``**: require **``B``/``b``**, **``U``**, **``C``**,
    **``D``**, **``E``**, **``id``**, **``H``**. **``T``** and **``A``/``a``** are always required.

--------------------------------------------------------------------
Optional CLI flags (**default: off** — compare aids only)
--------------------------------------------------------------------

**``--coerce-sparse-to-dense-for-compare``**
    Build **deep copies** of the Python ``RDP`` (from PKL) and the MATLAB-nested ``RDP`` (from
    ``loadmat`` → ``mat_nested_to_py``), then replace every **SciPy sparse** leaf that exposes
    ``.toarray()`` with ``numpy.asarray(..., dtype=float64)``. **Scalars and existing ``ndarray``**
    leaves are untouched. The **on-disk PKL is never modified**; only in-memory copies used for
    ``_assert_nested_rdp_equal``. Use when MATLAB’s ``loadmat`` path yields **sparse** tensors (e.g.
    ``csc_array``) while Python kept **dense** ``ndarray`` — same stored values, different container.
    This does **not** fix differing tensor **shapes** or **numeric** divergence; those surface as the next assertion errors if present.
"""
from __future__ import annotations

import argparse
import copy
import os
import pickle
import re
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

_MATLAB_LOADMAT_META = frozenset({"__header__", "__version__", "__globals__"})

_RDP_PATH_MISSING = object()

# ENTRY 1-11: Python PKL ledger uses state size 524 vs MATLAB dump 485 on A/B/H tensors — accepted for validation.
_ACCEPTED_LEDGER_524_485_PREFIXES: tuple[str, ...] = (
    "RDP.A",
    "RDP.B",
    "RDP.H",
    "RDP.MDP.A",
    "RDP.MDP.B",
    "RDP.MDP.H",
)

# Fields documented on ``MDP`` in spm_MDP_checkX.m (header + body); ``T`` is VB entry (spm_MDP_VB_XXX).
# ``spm_MDP_checkX`` assigns defaults when these are missing; **strict** mode still requires them on each RDP.
_CHECKX_STRICT_OPTIONAL_KEYS = ("U", "C", "D", "E", "id", "H")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _fsl_1_11_validation_output_txt_path() -> Path:
    """Per-run report: ``matlab_custom/fsl_1_11_compare_ctx_pkl_to_mat_output.txt`` under repo root."""
    return _repo_root() / "matlab_custom" / "fsl_1_11_compare_ctx_pkl_to_mat_output.txt"


class _TeeIO:
    """Duplicate text writes to multiple streams (console + report file)."""

    __slots__ = ("_streams",)

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            s = str(s)
        for st in self._streams:
            st.write(s)
        return len(s)

    def flush(self) -> None:
        for st in self._streams:
            st.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._streams[0], "isatty", lambda: False)())


def _fsl_1_11_mat_path() -> Path:
    raw = str(os.getenv("RGMS_ATARI_FSL_1_11_MAT_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parent / "fixtures" / "DEMAtariIII_fsl_1_11_rdp.mat"


def _load_matlab_nested_rdp_for_fsl_oracle(mat_path: Path) -> Any:
    """Load nested ``RDP`` from a MAT v7 file (``RDP`` or ``rdp11_nested_mat`` top-level)."""
    from scipy.io import loadmat

    from tests.oracle.toolbox.DEM.entry12_loadmat_convert import mat_nested_to_py

    p = mat_path.resolve()
    kw: dict[str, Any] = {}
    try:
        kw["simplify_cells"] = True
        raw = loadmat(str(p), **kw)
    except TypeError:
        raw = loadmat(str(p))
    for key in ("RDP", "rdp11_nested_mat"):
        if key in raw and key not in _MATLAB_LOADMAT_META:
            return mat_nested_to_py(raw[key])
    keys = sorted(k for k in raw if k not in _MATLAB_LOADMAT_META)
    raise KeyError(f"expected top-level RDP or rdp11_nested_mat in {p}, got keys={keys}")


def _norm_leaf(x: Any) -> Any:
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x


def _densify_sparse_leaves(x: Any) -> Any:
    """Deep structure copy with SciPy sparse leaves replaced by dense ``ndarray`` (``float64``)."""
    import numpy as np

    if isinstance(x, dict):
        return {k: _densify_sparse_leaves(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_densify_sparse_leaves(v) for v in x]
    if isinstance(x, tuple):
        return tuple(_densify_sparse_leaves(v) for v in x)
    if isinstance(x, (str, bytes, type(None), bool, int, float, np.integer, np.floating)):
        return x
    if isinstance(x, np.ndarray):
        return x
    if hasattr(x, "toarray") and callable(getattr(x, "toarray")):
        try:
            return np.asarray(x.toarray(), dtype=np.float64)
        except Exception:
            return x
    return x


def _unwrap_matlab_scalar_cell(x: Any) -> Any:
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x


def _is_empty_cellish(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    return False


def _is_numeric_tensor_like(x: Any, np: Any) -> bool:
    if isinstance(x, np.ndarray):
        return True
    if hasattr(x, "toarray") and callable(getattr(x, "toarray")) and hasattr(x, "shape"):
        return True
    return False


def _concise_value_desc(v: Any) -> str:
    """One-line type/shape summary for top-level ``RDP`` field values (stderr inventory)."""
    import numpy as np

    if isinstance(v, np.ndarray):
        return f"ndarray{tuple(v.shape)}"
    if isinstance(v, (np.integer, np.floating)):
        return type(v).__name__
    if isinstance(v, dict):
        return f"dict(len={len(v)})"
    if isinstance(v, list):
        if len(v) == 0:
            return "list(len=0)"
        e0 = _unwrap_matlab_scalar_cell(v[0])
        et = type(e0).__name__
        if isinstance(e0, np.ndarray):
            return f"list(len={len(v)},elem=ndarray{tuple(e0.shape)})"
        if hasattr(e0, "toarray") and callable(getattr(e0, "toarray")) and hasattr(e0, "shape"):
            try:
                return f"list(len={len(v)},elem={et}{tuple(e0.shape)})"
            except Exception:
                return f"list(len={len(v)},elem={et})"
        return f"list(len={len(v)},elem={et})"
    if isinstance(v, tuple):
        return f"tuple(len={len(v)})"
    if hasattr(v, "toarray") and callable(getattr(v, "toarray")) and hasattr(v, "shape"):
        tn = type(v).__name__
        try:
            return f"{tn}{tuple(v.shape)}"
        except Exception:
            return tn
    return type(v).__name__


def _safe_concise_value_desc(v: Any) -> str:
    try:
        return _concise_value_desc(v)
    except Exception as exc:
        return f"{type(v).__name__}(desc_error={type(exc).__name__})"


def _emit_rdp_top_level_field_inventory(tag: str, rdp: Any) -> None:
    """Print each top-level ``RDP`` key with concise type to stderr; never raises."""
    try:
        if not isinstance(rdp, dict):
            print(
                f"[checkX schema {tag} field] <not a dict> type={type(rdp).__name__}",
                file=sys.stderr,
            )
            return
        for k in sorted(rdp.keys(), key=str):
            desc = _safe_concise_value_desc(rdp[k])
            print(f"[checkX schema {tag} field] {k}={desc}", file=sys.stderr)
    except Exception as exc:
        print(
            f"[checkX schema {tag} field] <inventory failed> {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )


def _emit_rdp_top_level_key_diff(py_rdp: Any, mat_rdp: Any) -> None:
    """Print symmetric top-level key diff (with types for keys unique to one side); never raises."""
    try:
        if not isinstance(py_rdp, dict) or not isinstance(mat_rdp, dict):
            print(
                "[FSL 1-11 validation] RDP top-level key diff: skipped (one or both RDP not dict-like)",
                file=sys.stderr,
            )
            return
        sp = set(py_rdp.keys())
        sm = set(mat_rdp.keys())
        only_py = sorted(sp - sm, key=str)
        only_mat = sorted(sm - sp, key=str)

        def _fmt_side(keys: list[Any], rdp: dict[str, Any]) -> str:
            if not keys:
                return "(none)"
            return ",".join(f"{k}={_safe_concise_value_desc(rdp[k])}" for k in keys)

        py_part = _fmt_side(only_py, py_rdp)
        mat_part = _fmt_side(only_mat, mat_rdp)
        print(
            f"[FSL 1-11 validation] RDP top-level key diff: only_in_PKL={py_part}; only_in_MATLAB={mat_part}",
            file=sys.stderr,
        )
    except Exception as exc:
        print(
            f"[FSL 1-11 validation] RDP top-level key diff: emit failed ({type(exc).__name__}: {exc})",
            file=sys.stderr,
        )


def _parse_rdp_inner_segments(inner: str) -> list[tuple[str, int | None]]:
    inner = inner.strip()
    if not inner:
        return []
    parsed: list[tuple[str, int | None]] = []
    for seg in inner.split("."):
        seg = seg.strip()
        if not seg:
            continue
        m = re.fullmatch(r"(\w+)\[(\d+)\]", seg)
        if m:
            parsed.append((m.group(1), int(m.group(2))))
            continue
        if re.fullmatch(r"\w+", seg):
            parsed.append((seg, None))
            continue
        parsed.append((seg, None))
    return parsed


def _get_at_rdp_path(rdp_root: Any, fullpath: str) -> Any:
    if fullpath == "RDP":
        return rdp_root
    if not isinstance(rdp_root, dict):
        return _RDP_PATH_MISSING
    if fullpath.startswith("RDP."):
        inner = fullpath[4:]
    elif fullpath.startswith("RDP"):
        inner = fullpath[3:].lstrip(".")
    else:
        inner = fullpath
    cur: Any = rdp_root
    for name, idx in _parse_rdp_inner_segments(inner):
        if isinstance(cur, dict):
            if name not in cur:
                return _RDP_PATH_MISSING
            cur = cur[name]
        else:
            return _RDP_PATH_MISSING
        if idx is not None:
            if not isinstance(cur, list) or idx < 0 or idx >= len(cur):
                return _RDP_PATH_MISSING
            cur = cur[idx]
    return cur


def _shape_tuple_if_numeric_leaf(x: Any) -> tuple[int, ...] | None:
    import numpy as np

    if isinstance(x, np.ndarray):
        return tuple(int(i) for i in x.shape)
    if hasattr(x, "shape"):
        try:
            return tuple(int(i) for i in x.shape)
        except Exception:
            return None
    return None


def _ledger_524_485_pair(py: Any, mat: Any) -> bool:
    dims: set[int] = set()
    sp, sm = _shape_tuple_if_numeric_leaf(py), _shape_tuple_if_numeric_leaf(mat)
    if sp:
        dims |= set(sp)
    if sm:
        dims |= set(sm)
    return 524 in dims and 485 in dims


def _is_accepted_ledger_dim_mismatch(path: str, py: Any, mat: Any) -> bool:
    if py is _RDP_PATH_MISSING or mat is _RDP_PATH_MISSING:
        return False
    if not any(path.startswith(p) for p in _ACCEPTED_LEDGER_524_485_PREFIXES):
        return False
    return _ledger_524_485_pair(py, mat)


def _format_preview_1d(x: Any, k: int) -> str:
    import numpy as np

    try:
        if isinstance(x, np.ndarray):
            v = np.ravel(x)[:k]
            return np.array2string(v, precision=4, max_line_width=160)
        if hasattr(x, "toarray") and callable(getattr(x, "toarray")):
            v = np.ravel(np.asarray(x.toarray(), dtype=np.float64))[:k]
            return np.array2string(v, precision=4, max_line_width=160)
    except Exception as exc:
        return f"<preview_error {type(exc).__name__}>"
    return "<no preview>"


def _summarize_one_side(label: str, x: Any, preview_k: int = 8) -> str:
    import numpy as np

    if x is _RDP_PATH_MISSING:
        return f"{label}=<missing>"
    if isinstance(x, np.ndarray):
        return (
            f"{label} ndarray shape={tuple(int(i) for i in x.shape)} dtype={x.dtype} "
            f"preview_ravel[:{preview_k}]={_format_preview_1d(x, preview_k)}"
        )
    if hasattr(x, "toarray") and callable(getattr(x, "toarray")) and hasattr(x, "shape"):
        sh = tuple(int(i) for i in x.shape)
        nnz = getattr(x, "nnz", None)
        nnz_s = f" nnz={nnz}" if nnz is not None else ""
        return (
            f"{label} {type(x).__name__} shape={sh}{nnz_s} "
            f"preview_dense_ravel[:{preview_k}]={_format_preview_1d(x, preview_k)}"
        )
    if isinstance(x, dict):
        ks = sorted(x.keys(), key=str)[:24]
        parts = [f"{repr(k)}:{type(x[k]).__name__}" for k in ks[:8]]
        more = " …" if len(x) > 8 else ""
        return f"{label} dict(len={len(x)}) keys_head={ks[:8]!r}{more} key_types_head={parts}"
    if isinstance(x, list):
        e0 = _unwrap_matlab_scalar_cell(x[0]) if len(x) else None
        et = type(e0).__name__ if e0 is not None else "n/a"
        return f"{label} list(len={len(x)}) elem0_unwrap_type={et}"
    if isinstance(x, (bool, int, float, str, bytes)) or x is None:
        return f"{label} scalar repr={repr(x)[:200]}"
    if isinstance(x, (np.integer, np.floating)):
        return f"{label} numpy_scalar repr={repr(x)}"
    return f"{label} type={type(x).__name__} repr={repr(x)[:200]}"


def _mismatch_value_summary_lines(path: str, py: Any, mat: Any) -> list[str]:
    tag = ""
    if _is_accepted_ledger_dim_mismatch(path, py, mat):
        tag = "[accepted ledger dim 524 vs 485 - upstream Py/MATLAB; ENTRY 1-11 policy] "
    py_l = _summarize_one_side("PKL", py)
    mat_l = _summarize_one_side("MAT", mat)
    return [f"  {tag}[mismatch detail] {py_l}", f"  [mismatch detail] {mat_l}"]


def _type_walk_path_from_line(ln: str) -> str | None:
    if ": " not in ln:
        return None
    return ln.split(": ", 1)[0].strip()


def _validate_rdp_checkx_schema(rdp: Any, *, strict: bool) -> list[tuple[str, str]]:
    """Return (level, message) with level in {'ERROR','WARN'} from ``spm_MDP_checkX`` / VB entry expectations."""
    import numpy as np

    out: list[tuple[str, str]] = []

    def err(msg: str) -> None:
        out.append(("ERROR", msg))

    def warn(msg: str) -> None:
        out.append(("WARN", msg))

    def bump_optional(msg: str) -> None:
        if strict:
            err(msg)
        else:
            warn(msg)

    if not isinstance(rdp, dict):
        err("RDP is not a dict (MDP-like bundle expected)")
        return out

    a_cell = rdp.get("A")
    if _is_empty_cellish(a_cell):
        a_cell = rdp.get("a") if not _is_empty_cellish(rdp.get("a")) else None

    if a_cell is None:
        err("missing non-empty A{g} or a{g} (spm_MDP_checkX lines 45-46, 71)")
        return out
    if not isinstance(a_cell, list):
        err(f"A / a must be a cell-like list, got {type(a_cell).__name__}")
        return out
    if len(a_cell) == 0:
        err("A / a cell array is empty (numel(MDP.A) in spm_MDP_checkX)")
        return out

    for g, Ag in enumerate(a_cell):
        ag = _unwrap_matlab_scalar_cell(Ag)
        if not _is_numeric_tensor_like(ag, np):
            err(f"A{{{g + 1}}} is not a numeric tensor-like array (got {type(ag).__name__})")

    if "T" not in rdp or rdp["T"] is None:
        err("missing MDP.T (required for spm_MDP_VB_XXX; not assigned in spm_MDP_checkX)")

    has_b = not _is_empty_cellish(rdp.get("B"))
    has_b_mirror = not _is_empty_cellish(rdp.get("b"))
    if not has_b and not has_b_mirror:
        bump_optional(
            "B / b absent; spm_MDP_checkX would synthesize identity MDP.B{f} from size(MDP.A{1},2:ndims(...))",
        )

    if strict:
        for key in _CHECKX_STRICT_OPTIONAL_KEYS:
            if key not in rdp or rdp[key] is None:
                err(
                    f"field {key!r} absent (documented on MDP in spm_MDP_checkX.m; "
                    f"--check-rdp-checkx-strict requires it on this RDP)",
                )

    ident = rdp.get("id")
    if ident is not None and not isinstance(ident, dict):
        err(f"id must be a dict-like mapping if present, got {type(ident).__name__}")

    return out


def _run_checkx_schema_phase(tag: str, rdp: Any, *, strict: bool) -> bool:
    """Run field inventory + ``_validate_rdp_checkx_schema`` and print lines to stderr. Return True if any ERROR."""
    _emit_rdp_top_level_field_inventory(tag, rdp)
    issues = _validate_rdp_checkx_schema(rdp, strict=strict)
    print(
        f"[FSL 1-11 validation] checkX schema ({tag}): {len(issues)} issue(s) (strict={strict})",
        file=sys.stderr,
    )
    for level, msg in issues:
        print(f"[checkX schema {tag} {level}] {msg}", file=sys.stderr)
    return any(level == "ERROR" for level, _ in issues)


def _collect_type_mismatches(py: Any, mat: Any, path: str, out: list[str]) -> None:
    import numpy as np

    py = _norm_leaf(py)
    mat = _norm_leaf(mat)
    if isinstance(py, dict) and isinstance(mat, dict):
        for k in sorted(set(py) | set(mat), key=str):
            if k not in py:
                out.append(f"{path}.{k}: missing in Python RDP")
                continue
            if k not in mat:
                out.append(f"{path}.{k}: missing in MATLAB RDP")
                continue
            _collect_type_mismatches(py[k], mat[k], f"{path}.{k}", out)
        return
    if isinstance(py, list) and isinstance(mat, list):
        if len(py) != len(mat):
            out.append(f"{path}: list len py={len(py)} mat={len(mat)}")
            return
        for i, (a, b) in enumerate(zip(py, mat, strict=True)):
            _collect_type_mismatches(a, b, f"{path}[{i}]", out)
        return
    if type(py) is not type(mat):
        out.append(f"{path}: type py={type(py).__name__} mat={type(mat).__name__}")
        return
    if isinstance(py, np.ndarray) and isinstance(mat, np.ndarray):
        return
    return


def _full_ndarray_1d_string(arr: Any) -> str:
    """Full 1-D (or raveled) numeric array string for VALUE-DUMP lines (no ellipsis)."""
    import numpy as np

    if not isinstance(arr, np.ndarray):
        return repr(arr)
    flat = np.ravel(arr)
    return np.array2string(
        flat,
        separator=" ",
        max_line_width=10_000,
        threshold=max(int(flat.size), 10**9),
        precision=16,
        floatmode="maxprec_equal",
    )


def _numpy_squeeze_ravel_float64(x: Any) -> Any | None:
    """1-D float64 vector for numeric compare, or None if not array-like."""
    import numpy as np

    if isinstance(x, np.ndarray):
        return np.ravel(np.squeeze(x).astype(np.float64, copy=True))
    if hasattr(x, "toarray") and callable(getattr(x, "toarray")):
        try:
            return np.ravel(np.squeeze(np.asarray(x.toarray(), dtype=np.float64)))
        except Exception:
            return None
    return None


def _to_float64_flat_vector_or_none(x: Any) -> Any | None:
    """Like ``_numpy_squeeze_ravel_float64`` plus Python / numpy scalars → length-1 float64 vector."""
    import numpy as np

    v = _numpy_squeeze_ravel_float64(x)
    if v is not None:
        return v
    x = _unwrap_matlab_scalar_cell(x)
    if isinstance(x, (np.integer, np.floating)) or (isinstance(x, (int, float)) and not isinstance(x, bool)):
        return np.array([float(x)], dtype=np.float64)
    return None


def _pkl_rdp_g_concat_ravel_numeric(py_g: dict) -> tuple[Any | None, str]:
    """Ordered concat of float64 ravels per sorted dict key (MATLAB column semantics)."""
    import numpy as np

    if not isinstance(py_g, dict) or not py_g:
        return None, "not a non-empty dict"
    parts: list[Any] = []
    for k in sorted(py_g.keys(), key=str):
        v = _unwrap_matlab_scalar_cell(py_g[k])
        vec = _to_float64_flat_vector_or_none(v)
        if vec is None:
            return None, f"key={k!r} not convertible to numeric 1-D"
        parts.append(vec)
    return np.concatenate(parts), ""


def _append_pair_g_value_dump(prefix: str, tag: str, pv: Any, mv: Any, depth: int = 0) -> None:
    """Recursively append PKL vs MAT full numeric ravels and elementwise diffs; else full repr / per-index."""
    import numpy as np

    max_depth = 384
    if depth > max_depth:
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: stop (depth>{max_depth})",
            file=sys.stderr,
        )
        return
    pv = _unwrap_matlab_scalar_cell(pv)
    mv = _unwrap_matlab_scalar_cell(mv)
    va = _to_float64_flat_vector_or_none(pv)
    vb = _to_float64_flat_vector_or_none(mv)
    if va is not None and vb is not None and va.shape == vb.shape:
        diff = va - vb
        mad = float(np.max(np.abs(diff))) if diff.size else 0.0
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: PKL float64_ravel(len={va.size}) full={_full_ndarray_1d_string(va)}",
            file=sys.stderr,
        )
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: MAT float64_ravel(len={vb.size}) full={_full_ndarray_1d_string(vb)}",
            file=sys.stderr,
        )
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: elementwise_diff full={_full_ndarray_1d_string(diff)} max_abs_diff={mad}",
            file=sys.stderr,
        )
        return
    if va is not None and vb is not None and va.shape != vb.shape:
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: PKL float64_ravel len={va.size} full={_full_ndarray_1d_string(va)}",
            file=sys.stderr,
        )
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: MAT float64_ravel len={vb.size} full={_full_ndarray_1d_string(vb)}",
            file=sys.stderr,
        )
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: (length mismatch; no elementwise diff line)",
            file=sys.stderr,
        )
        return
    if va is not None and vb is None:
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: PKL float64_ravel len={va.size} full={_full_ndarray_1d_string(va)}",
            file=sys.stderr,
        )
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: MAT not numeric 1-D-extractable; repr={repr(mv)}",
            file=sys.stderr,
        )
        return
    if va is None and vb is not None:
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: PKL not numeric 1-D-extractable; repr={repr(pv)}",
            file=sys.stderr,
        )
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: MAT float64_ravel len={vb.size} full={_full_ndarray_1d_string(vb)}",
            file=sys.stderr,
        )
        return
    if isinstance(pv, list) and isinstance(mv, list):
        m = min(len(pv), len(mv))
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: both list PKL len={len(pv)} MAT len={len(mv)}; drilling {m} index pair(s)",
            file=sys.stderr,
        )
        for i in range(m):
            _append_pair_g_value_dump(prefix, f"{tag}[{i}]", pv[i], mv[i], depth + 1)
        if len(pv) != len(mv):
            print(
                f"  [focused probe G] VALUE-DUMP {prefix} {tag}: note: unequal list lengths after pairwise min={m}",
                file=sys.stderr,
            )
        return
    if isinstance(pv, dict) and isinstance(mv, dict):
        ks = sorted(set(pv.keys()) & set(mv.keys()), key=str)
        if not ks:
            ks = sorted(set(pv.keys()) | set(mv.keys()), key=str)
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: both dict — {len(ks)} key(s) in walk order",
            file=sys.stderr,
        )
        for k in ks:
            if k not in pv or k not in mv:
                print(
                    f"  [focused probe G] VALUE-DUMP {prefix} {tag}[key={k!r}]: PKL_present={k in pv} MAT_present={k in mv}",
                    file=sys.stderr,
                )
                continue
            _append_pair_g_value_dump(prefix, f"{tag}[key={k!r}]", pv[k], mv[k], depth + 1)
        return
    psc = _python_scalar_for_mat_int(pv)
    msc = _python_scalar_for_mat_int(mv)
    if psc is not None and msc is not None:
        eq = float(psc) == float(msc) if isinstance(psc, float) or isinstance(msc, float) else int(psc) == int(msc)
        print(
            f"  [focused probe G] VALUE-DUMP {prefix} {tag}: scalar unwrap PKL={psc!r} MAT={msc!r} equal={eq}",
            file=sys.stderr,
        )
        return
    print(
        f"  [focused probe G] VALUE-DUMP {prefix} {tag}: PKL repr={repr(pv)}",
        file=sys.stderr,
    )
    print(
        f"  [focused probe G] VALUE-DUMP {prefix} {tag}: MAT repr={repr(mv)}",
        file=sys.stderr,
    )


def _append_mdp_g_nested_value_dumps(prefix: str, gpy: Any, gmat: Any) -> None:
    print(f"  [focused probe G] {prefix} VALUE-DUMP (append-only): begin", file=sys.stderr)
    if gpy is None and gmat is None:
        print(f"  [focused probe G] {prefix} VALUE-DUMP: both None", file=sys.stderr)
        return
    if isinstance(gpy, dict) and isinstance(gmat, list):
        ks = sorted(gpy.keys(), key=str)
        m = min(len(ks), len(gmat))
        for j in range(m):
            _append_pair_g_value_dump(prefix, f"slot={j}_PKL_key={ks[j]!r}", gpy[ks[j]], gmat[j], 0)
        return
    if isinstance(gpy, list) and isinstance(gmat, list):
        m = min(len(gpy), len(gmat))
        for j in range(m):
            _append_pair_g_value_dump(prefix, f"slot={j}", gpy[j], gmat[j], 0)
        return
    if isinstance(gpy, dict) and isinstance(gmat, dict):
        ks = sorted(set(gpy.keys()) & set(gmat.keys()), key=str)
        if not ks:
            ks = sorted(set(gpy.keys()) | set(gmat.keys()), key=str)
        for k in ks:
            if k not in gpy or k not in gmat:
                print(
                    f"  [focused probe G] VALUE-DUMP {prefix} key={k!r}: PKL_present={k in gpy} MAT_present={k in gmat}",
                    file=sys.stderr,
                )
                continue
            _append_pair_g_value_dump(prefix, f"key={k!r}", gpy[k], gmat[k], 0)
        return
    print(
        f"  [focused probe G] {prefix} VALUE-DUMP: skip structure (PKL {type(gpy).__name__} vs MAT {type(gmat).__name__})",
        file=sys.stderr,
    )


def _append_rdp_g_top_level_value_dump(py_g: Any, mat_g: Any) -> None:
    import numpy as np

    print("  [focused probe G] RDP.G VALUE-DUMP (append-only): begin", file=sys.stderr)
    if isinstance(py_g, dict):
        pkl_vec, err = _pkl_rdp_g_concat_ravel_numeric(py_g)
        if pkl_vec is None:
            print(f"  [focused probe G] RDP.G VALUE-DUMP PKL dict concat: skip ({err})", file=sys.stderr)
        else:
            print(
                f"  [focused probe G] RDP.G VALUE-DUMP PKL dict concat→float64_ravel n={pkl_vec.size} full={_full_ndarray_1d_string(pkl_vec)}",
                file=sys.stderr,
            )
    else:
        pv = _unwrap_matlab_scalar_cell(py_g)
        pv_v = _to_float64_flat_vector_or_none(pv)
        if pv_v is None:
            print(
                f"  [focused probe G] RDP.G VALUE-DUMP PKL non-dict: not 1-D numeric; repr={repr(py_g)}",
                file=sys.stderr,
            )
        else:
            print(
                f"  [focused probe G] RDP.G VALUE-DUMP PKL non-dict float64_ravel n={pv_v.size} full={_full_ndarray_1d_string(pv_v)}",
                file=sys.stderr,
            )
    mv = _unwrap_matlab_scalar_cell(mat_g)
    mat_v = _to_float64_flat_vector_or_none(mv)
    if mat_v is None:
        print(
            f"  [focused probe G] RDP.G VALUE-DUMP MAT: not 1-D numeric; repr={repr(mat_g)}",
            file=sys.stderr,
        )
    else:
        print(
            f"  [focused probe G] RDP.G VALUE-DUMP MAT float64_ravel n={mat_v.size} full={_full_ndarray_1d_string(mat_v)}",
            file=sys.stderr,
        )
    if isinstance(py_g, dict):
        pkl_vec, _err = _pkl_rdp_g_concat_ravel_numeric(py_g)
    else:
        pkl_vec = _to_float64_flat_vector_or_none(_unwrap_matlab_scalar_cell(py_g))
    mat_v2 = _to_float64_flat_vector_or_none(_unwrap_matlab_scalar_cell(mat_g))
    if pkl_vec is not None and mat_v2 is not None and pkl_vec.shape == mat_v2.shape:
        d = pkl_vec - mat_v2
        mx = float(np.max(np.abs(d))) if d.size else 0.0
        print(
            f"  [focused probe G] RDP.G VALUE-DUMP aligned elementwise_diff n={d.size} full={_full_ndarray_1d_string(d)} max_abs={mx}",
            file=sys.stderr,
        )
    elif pkl_vec is not None and mat_v2 is not None:
        print(
            f"  [focused probe G] RDP.G VALUE-DUMP: PKL len={pkl_vec.size} MAT len={mat_v2.size} (no single aligned diff line)",
            file=sys.stderr,
        )
    print("  [focused probe G] RDP.G VALUE-DUMP (append-only): end", file=sys.stderr)


def _python_scalar_for_mat_int(py: Any) -> float | int | None:
    """Best-effort scalar when MATLAB side is int / numpy scalar."""
    import numpy as np

    py = _norm_leaf(py)
    if isinstance(py, np.ndarray) and py.size >= 1:
        v = np.ravel(py)[0]
        if isinstance(v, (np.floating, float)):
            return float(v)
        return int(v)
    if isinstance(py, (np.integer, np.floating)):
        return int(py) if isinstance(py, np.integer) else float(py)
    if isinstance(py, (int, float)) and not isinstance(py, bool):
        return py
    if isinstance(py, list) and len(py) == 1:
        return _python_scalar_for_mat_int(py[0])
    return None


def _g_dict_key_drill_lines(py_g: dict) -> None:
    """Append one line per PKL RDP.G dict key (up to 8 keys if more exist)."""
    ks = sorted(py_g.keys(), key=str)
    cap = len(ks) if len(ks) <= 8 else 8
    print(f"  [focused probe G] RDP.G PKL dict: per-key drill ({cap} of {len(ks)} key(s))", file=sys.stderr)
    for k in ks[:cap]:
        v = py_g[k]
        if isinstance(v, list):
            e0 = _unwrap_matlab_scalar_cell(v[0]) if len(v) else None
            e0s = _summarize_one_side("elem0", e0) if len(v) else "empty list"
            print(f"  [focused probe G]   key={k!r}: list len={len(v)}; {e0s}", file=sys.stderr)
            if len(v) and isinstance(v[0], list) and len(v[0]) > 0:
                e00 = _unwrap_matlab_scalar_cell(v[0][0])
                print(f"  [focused probe G]     key={k!r} elem00: {_summarize_one_side('e00', e00)}", file=sys.stderr)
        elif isinstance(v, dict):
            sk = sorted(v.keys(), key=str)[:12]
            print(f"  [focused probe G]   key={k!r}: dict len={len(v)} keys_head={sk!r}", file=sys.stderr)
        else:
            print(f"  [focused probe G]   key={k!r}: {_summarize_one_side('value', v)}", file=sys.stderr)


def _g_mat_ndarray_stats_line(mat_g: Any) -> None:
    import numpy as np

    if not isinstance(mat_g, np.ndarray) or mat_g.size == 0:
        return
    flat = np.ravel(mat_g)
    if np.issubdtype(flat.dtype, np.number):
        print(
            f"  [focused probe G] MAT ndarray ravel: dtype={flat.dtype} size={flat.size} "
            f"min={flat.min()} max={flat.max()}",
            file=sys.stderr,
        )
    else:
        print(
            f"  [focused probe G] MAT ndarray ravel: dtype={flat.dtype} size={flat.size} (non-numeric; no min/max)",
            file=sys.stderr,
        )


def _print_g_slot_pair_lines(prefix: str, slot: Any, label_p: str, pv: Any, mv: Any) -> None:
    """One slot: PKL vs MAT value with one list-elem0 level and optional second list level."""
    if isinstance(pv, list) and len(pv) > 0:
        pe = _unwrap_matlab_scalar_cell(pv[0])
        ps = f"list len={len(pv)}; elem0 {_summarize_one_side('PKL', pe)}"
        if isinstance(pv[0], list) and len(pv[0]) > 0:
            pe00 = _unwrap_matlab_scalar_cell(pv[0][0])
            ps += f"; elem00 {_summarize_one_side('PKL', pe00)}"
    else:
        ps = _summarize_one_side("PKL", pv)
    if isinstance(mv, list) and len(mv) > 0:
        me = _unwrap_matlab_scalar_cell(mv[0])
        ms = f"list len={len(mv)}; elem0 {_summarize_one_side('MAT', me)}"
        if isinstance(mv[0], list) and len(mv[0]) > 0:
            me00 = _unwrap_matlab_scalar_cell(mv[0][0])
            ms += f"; elem00 {_summarize_one_side('MAT', me00)}"
    else:
        ms = _summarize_one_side("MAT", mv)
    lab = f"slot={slot}" if label_p == "" else f"slot={slot} {label_p}"
    print(f"  [focused probe G] {prefix} nested {lab}: {ps} || {ms}", file=sys.stderr)


def _print_mdp_g_nested_lines(prefix: str, gpy: Any, gmat: Any) -> None:
    if gpy is None and gmat is None:
        return
    if isinstance(gpy, dict) and isinstance(gmat, list):
        ks = sorted(gpy.keys(), key=str)
        m = min(len(ks), len(gmat))
        print(
            f"  [focused probe G] {prefix} nested: PKL dict vs MAT list — {m} aligned slot(s) (PKL keys order)",
            file=sys.stderr,
        )
        for j in range(m):
            _print_g_slot_pair_lines(prefix, j, f"PKL_key={ks[j]!r}", gpy[ks[j]], gmat[j])
        return
    if isinstance(gpy, list) and isinstance(gmat, list):
        m = min(len(gpy), len(gmat))
        print(f"  [focused probe G] {prefix} nested: list vs list — {m} slot(s)", file=sys.stderr)
        for j in range(m):
            _print_g_slot_pair_lines(prefix, j, "", gpy[j], gmat[j])
        return
    if isinstance(gpy, dict) and isinstance(gmat, dict):
        ks = sorted(set(gpy.keys()) & set(gmat.keys()), key=str)
        if not ks:
            ks = sorted(set(gpy.keys()) | set(gmat.keys()), key=str)[:8]
        m = min(len(ks), 16)
        print(f"  [focused probe G] {prefix} nested: dict vs dict — up to {m} key(s)", file=sys.stderr)
        for k in ks[:m]:
            if k not in gpy or k not in gmat:
                print(
                    f"  [focused probe G]   key={k!r}: PKL_present={k in gpy} MAT_present={k in gmat}",
                    file=sys.stderr,
                )
                continue
            _print_g_slot_pair_lines(prefix, k, f"key={k!r}", gpy[k], gmat[k])
        return
    print(
        f"  [focused probe G] {prefix} nested: skip (PKL {type(gpy).__name__} vs MAT {type(gmat).__name__})",
        file=sys.stderr,
    )


def _focused_probe_g(py_rdp: Any, mat_rdp: Any) -> None:
    import numpy as np

    if not isinstance(py_rdp, dict) or not isinstance(mat_rdp, dict):
        print("  [focused probe G] skip: RDP not dict-like on one side", file=sys.stderr)
        return
    py_g = py_rdp.get("G")
    mat_g = mat_rdp.get("G")
    print(f"  [focused probe G] PKL {_summarize_one_side('v', py_g)}", file=sys.stderr)
    print(f"  [focused probe G] MAT {_summarize_one_side('v', mat_g)}", file=sys.stderr)
    if isinstance(py_g, dict) and isinstance(mat_g, np.ndarray):
        arr = np.ravel(mat_g)
        print(
            f"  [focused probe G] PKL dict len={len(py_g)} vs MAT ndarray ravel len={arr.size}",
            file=sys.stderr,
        )
    if isinstance(py_g, dict) and len(py_g) > 0:
        _g_dict_key_drill_lines(py_g)
    if isinstance(mat_g, np.ndarray):
        _g_mat_ndarray_stats_line(mat_g)
    _append_rdp_g_top_level_value_dump(py_g, mat_g)
    mdp_py = py_rdp.get("MDP") if isinstance(py_rdp.get("MDP"), dict) else None
    mdp_mat = mat_rdp.get("MDP") if isinstance(mat_rdp.get("MDP"), dict) else None
    if mdp_py is not None and mdp_mat is not None and ("G" in mdp_py or "G" in mdp_mat):
        gpy, gmat = mdp_py.get("G"), mdp_mat.get("G")
        print(f"  [focused probe G] RDP.MDP.G PKL {_summarize_one_side('v', gpy)}", file=sys.stderr)
        print(f"  [focused probe G] RDP.MDP.G MAT {_summarize_one_side('v', gmat)}", file=sys.stderr)
        _print_mdp_g_nested_lines("RDP.MDP.G", gpy, gmat)
        _append_mdp_g_nested_value_dumps("RDP.MDP.G", gpy, gmat)
        print("  [focused probe G] RDP.MDP.G VALUE-DUMP (append-only): end", file=sys.stderr)


def _append_focused_probe_c_modal_value_dump(g: int, a: Any, b: Any, va: Any, vb: Any) -> None:
    """Full squeeze-ravel vectors and elementwise diff for modality ``g`` (stderr only; append-only)."""
    import numpy as np

    print(f"  [focused probe C[{g}]] VALUE-DUMP (append-only): begin", file=sys.stderr)

    def _one(side: str, raw: Any, vec: Any) -> None:
        if vec is not None:
            print(
                f"  [focused probe C[{g}]] VALUE-DUMP {side} squeeze-ravel float64 len={vec.size} "
                f"full={_full_ndarray_1d_string(vec)}",
                file=sys.stderr,
            )
            return
        u = _unwrap_matlab_scalar_cell(raw)
        if isinstance(u, np.ndarray):
            try:
                alt = np.ravel(np.squeeze(u.astype(np.float64, copy=True)))
                print(
                    f"  [focused probe C[{g}]] VALUE-DUMP {side} raw ndarray coerced float64 ravel "
                    f"len={alt.size} full={_full_ndarray_1d_string(alt)}",
                    file=sys.stderr,
                )
            except Exception as exc:
                print(
                    f"  [focused probe C[{g}]] VALUE-DUMP {side} raw ndarray coerce failed "
                    f"{type(exc).__name__}: {exc}; repr={repr(u)}",
                    file=sys.stderr,
                )
        else:
            print(
                f"  [focused probe C[{g}]] VALUE-DUMP {side} non-ndarray-after-unwrap repr={repr(u)}",
                file=sys.stderr,
            )

    _one("PKL", a, va)
    _one("MAT", b, vb)
    if va is not None and vb is not None and va.shape == vb.shape:
        diff = va - vb
        mad = float(np.max(np.abs(diff))) if diff.size else 0.0
        print(
            f"  [focused probe C[{g}]] VALUE-DUMP elementwise_diff float64 len={diff.size} "
            f"full={_full_ndarray_1d_string(diff)} max_abs_diff={mad}",
            file=sys.stderr,
        )
    elif va is not None and vb is not None:
        print(
            f"  [focused probe C[{g}]] VALUE-DUMP: no same-length elementwise_diff "
            f"(squeeze-ravel lens PKL={va.size} MAT={vb.size})",
            file=sys.stderr,
        )
    else:
        print(
            f"  [focused probe C[{g}]] VALUE-DUMP: no elementwise_diff line "
            f"(missing one or both float64 squeeze-ravels)",
            file=sys.stderr,
        )
    print(f"  [focused probe C[{g}]] VALUE-DUMP (append-only): end", file=sys.stderr)


def _focused_probe_c(py_rdp: Any, mat_rdp: Any) -> None:
    import numpy as np

    c_py = py_rdp.get("C") if isinstance(py_rdp, dict) else None
    c_mat = mat_rdp.get("C") if isinstance(mat_rdp, dict) else None
    if not isinstance(c_py, list) or not isinstance(c_mat, list):
        print(
            f"  [focused probe C] skip: C not list-like (PKL {type(c_py).__name__}, MAT {type(c_mat).__name__})",
            file=sys.stderr,
        )
        return
    n = min(len(c_py), len(c_mat))
    print(f"  [focused probe C] list lens PKL={len(c_py)} MAT={len(c_mat)}; comparing first {n} elements", file=sys.stderr)
    for g in range(n):
        a = _unwrap_matlab_scalar_cell(c_py[g])
        b = _unwrap_matlab_scalar_cell(c_mat[g])
        sa = tuple(int(x) for x in getattr(a, "shape", ())) if hasattr(a, "shape") else None
        sb = tuple(int(x) for x in getattr(b, "shape", ())) if hasattr(b, "shape") else None
        va = _numpy_squeeze_ravel_float64(a)
        vb = _numpy_squeeze_ravel_float64(b)
        line = f"  [focused probe C[{g}]] PKL shape={sa} MAT shape={sb}"
        mad: float | None = None
        if va is not None and vb is not None and va.shape == vb.shape:
            mad = float(np.max(np.abs(va - vb)))
            line += f"; squeeze-ravel same len={va.size}; max_abs_diff={mad}"
        elif va is not None and vb is not None:
            line += f"; squeeze-ravel PKL len={va.size} MAT len={vb.size} (not same length after squeeze)"
        print(line, file=sys.stderr)
        if isinstance(a, list) and len(a) > 0:
            ae = _unwrap_matlab_scalar_cell(a[0])
            print(
                f"  [focused probe C[{g}]] PKL inner: list len={len(a)}; elem0 {_summarize_one_side('e0', ae)}",
                file=sys.stderr,
            )
            if isinstance(a[0], list) and len(a[0]) > 0:
                ae2 = _unwrap_matlab_scalar_cell(a[0][0])
                print(
                    f"  [focused probe C[{g}]] PKL inner2: elem00 {_summarize_one_side('e00', ae2)}",
                    file=sys.stderr,
                )
        if isinstance(b, list) and len(b) > 0:
            be = _unwrap_matlab_scalar_cell(b[0])
            print(
                f"  [focused probe C[{g}]] MAT inner: list len={len(b)}; elem0 {_summarize_one_side('e0', be)}",
                file=sys.stderr,
            )
            if isinstance(b[0], list) and len(b[0]) > 0:
                be2 = _unwrap_matlab_scalar_cell(b[0][0])
                print(
                    f"  [focused probe C[{g}]] MAT inner2: elem00 {_summarize_one_side('e00', be2)}",
                    file=sys.stderr,
                )
        if mad is not None and mad == 0.0 and sa != sb:
            print(
                f"  [focused probe C[{g}]] note: raw shapes PKL {sa} vs MAT {sb} differ; "
                f"max_abs_diff=0 applies after squeeze-ravel only",
                file=sys.stderr,
            )
        _append_focused_probe_c_modal_value_dump(g, a, b, va, vb)


def _focused_probe_sb(py_rdp: Any, mat_rdp: Any) -> None:
    import numpy as np

    py_sb = py_rdp.get("sB") if isinstance(py_rdp, dict) else None
    mat_sb = mat_rdp.get("sB") if isinstance(mat_rdp, dict) else None
    mat_sb_n = _norm_leaf(mat_sb)
    print(f"  [focused probe sB] PKL {_summarize_one_side('v', py_sb)}", file=sys.stderr)
    print(f"  [focused probe sB] MAT {_summarize_one_side('v', mat_sb)}", file=sys.stderr)
    if isinstance(py_sb, list) and len(py_sb) > 1:
        print(
            f"  [focused probe sB] note: PKL list len={len(py_sb)} (MAT is scalar-like); scalar line below is best-effort unwrap only",
            file=sys.stderr,
        )
    psc = _python_scalar_for_mat_int(py_sb)
    if isinstance(mat_sb_n, (int, np.integer)) and psc is not None:
        eq = int(psc) == int(mat_sb_n)
        print(
            f"  [focused probe sB] scalar compare: int(PKL unwrap)={int(psc)} int(MAT)={int(mat_sb_n)} equal={eq}",
            file=sys.stderr,
        )


def _focused_probe_u(py_rdp: Any, mat_rdp: Any) -> None:
    import numpy as np

    py_u = py_rdp.get("U") if isinstance(py_rdp, dict) else None
    mat_u = mat_rdp.get("U") if isinstance(mat_rdp, dict) else None
    print(f"  [focused probe U] PKL {_summarize_one_side('v', py_u)}", file=sys.stderr)
    print(f"  [focused probe U] MAT {_summarize_one_side('v', mat_u)}", file=sys.stderr)
    psc = _python_scalar_for_mat_int(py_u)
    mat_n = _norm_leaf(mat_u)
    if isinstance(mat_n, (int, np.integer)) and psc is not None:
        eq = abs(float(psc) - float(int(mat_n))) < 1e-12 if isinstance(psc, float) else int(psc) == int(mat_n)
        print(
            f"  [focused probe U] scalar compare: PKL unwrap={psc!r} MAT={int(mat_n)} equal={eq}",
            file=sys.stderr,
        )


def _emit_rdp_focused_probes(py_rdp: Any, mat_rdp: Any) -> None:
    """Append-only stderr lines (teed to report): deeper facts for G, C, sB, U."""
    print("[FSL 1-11 validation] focused probe (append): G, C, sB, U", file=sys.stderr)
    for name, fn in (
        ("G", _focused_probe_g),
        ("C", _focused_probe_c),
        ("sB", _focused_probe_sb),
        ("U", _focused_probe_u),
    ):
        try:
            fn(py_rdp, mat_rdp)
        except Exception as exc:
            print(f"  [focused probe {name}] {type(exc).__name__}: {exc}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)


def _emit_nested_type_walk(py_rdp: Any, mat_rdp: Any) -> None:
    """Always-on nested Python vs MATLAB ``RDP`` type / shape drift plus PKL/MAT detail lines (stderr + report file)."""
    lines: list[str] = []
    _collect_type_mismatches(py_rdp, mat_rdp, "RDP", lines)
    print(f"[FSL 1-11 validation] type walk: {len(lines)} mismatch line(s)", file=sys.stderr)
    for ln in lines:
        print(ln, file=sys.stderr)
        path = _type_walk_path_from_line(ln)
        if path is None:
            continue
        py_val = _norm_leaf(_get_at_rdp_path(py_rdp, path))
        mat_val = _norm_leaf(_get_at_rdp_path(mat_rdp, path))
        for dl in _mismatch_value_summary_lines(path, py_val, mat_val)[:2]:
            print(dl, file=sys.stderr)


def _argv_requests_help(argv: list[str]) -> bool:
    return any(a in ("-h", "--help") for a in argv)


def _build_fsl_1_11_argument_parser() -> ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "FSL 1–11 validation: spm_MDP_checkX-style schema on PKL RDP and MATLAB RDP, then nested parity"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Full flag semantics are in the module docstring at the top of this file.",
    )
    p.add_argument(
        "--pkl",
        type=Path,
        default=None,
        help="Pickle from FSL run (default: tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_fsl_1_11_ctx.pkl)",
    )
    p.add_argument(
        "--mat",
        type=Path,
        default=None,
        help="MATLAB v7 fixture (default: same dir / DEMAtariIII_fsl_1_11_rdp.mat or RGMS_ATARI_FSL_1_11_MAT_PATH)",
    )
    p.add_argument(
        "--coerce-sparse-to-dense-for-compare",
        action="store_true",
        help="Dense SciPy sparse leaves on in-memory copies before assert (see module docstring).",
    )
    p.add_argument(
        "--report-type-mismatches",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--report-type-mismatches-only",
        action="store_true",
        help="Only print type walk; skip assertion (exit 0).",
    )
    p.add_argument(
        "--check-rdp-checkx-schema",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--check-rdp-checkx-schema-only",
        action="store_true",
        help="After checkX schema on PKL and MATLAB RDP, exit (no nested assert).",
    )
    p.add_argument(
        "--check-rdp-checkx-strict",
        action="store_true",
        help="Stricter checkX schema on both PKL and MATLAB RDP (see module docstring).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if _argv_requests_help(argv):
        _build_fsl_1_11_argument_parser().print_help(file=sys.stdout)
        return 0

    parser = _build_fsl_1_11_argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else 2

    out_path = _fsl_1_11_validation_output_txt_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_f = open(out_path, "w", encoding="utf-8")
    try:
        report_f.write(__doc__ or "")
        report_f.write(f"\n--- RUN OUTPUT (stdout + stderr) — {out_path} ---\n")
        report_f.flush()
        old_err, old_out = sys.stderr, sys.stdout
        sys.stderr = _TeeIO(old_err, report_f)
        sys.stdout = _TeeIO(old_out, report_f)
        try:
            return _execute_fsl_1_11_validation(args)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 1
        finally:
            sys.stderr = old_err
            sys.stdout = old_out
    finally:
        report_f.close()


def _execute_fsl_1_11_validation(args: Namespace) -> int:
    pkl_path = (args.pkl or (Path(__file__).resolve().parent / "fixtures" / "DEMAtariIII_fsl_1_11_ctx.pkl")).resolve()
    if not pkl_path.is_file():
        print(f"error: missing pickle: {pkl_path}", file=sys.stderr)
        return 2

    mat_path = (args.mat or _fsl_1_11_mat_path()).resolve()
    if not mat_path.is_file():
        print(f"error: missing .mat: {mat_path}", file=sys.stderr)
        return 2

    with pkl_path.open("rb") as f:
        ctx = pickle.load(f)
    if not isinstance(ctx, dict) or "RDP" not in ctx:
        print("error: pickle must be a dict with key 'RDP' (full run_dem_atariiii context)", file=sys.stderr)
        return 2

    py_rdp = ctx["RDP"]
    strict = bool(args.check_rdp_checkx_strict)

    if _run_checkx_schema_phase("PKL", py_rdp, strict=strict):
        print(
            "[FSL 1-11 validation] top-level key diff: skipped (MATLAB RDP not loaded — PKL schema ERROR)",
            file=sys.stderr,
        )
        print(
            "[FSL 1-11 validation] type walk: skipped (MATLAB RDP not loaded — PKL schema ERROR)",
            file=sys.stderr,
        )
        print(
            "[FSL 1-11 validation] focused probe (append): skipped (MATLAB RDP not loaded — PKL schema ERROR)",
            file=sys.stderr,
        )
        return 1

    mat_rdp = _load_matlab_nested_rdp_for_fsl_oracle(mat_path)

    mat_schema_err = _run_checkx_schema_phase("MATLAB", mat_rdp, strict=strict)

    _emit_rdp_top_level_key_diff(py_rdp, mat_rdp)
    _emit_nested_type_walk(py_rdp, mat_rdp)
    _emit_rdp_focused_probes(py_rdp, mat_rdp)

    if mat_schema_err:
        return 1

    if args.check_rdp_checkx_schema_only:
        print(
            "OK: ctx['RDP'] (PKL) and MATLAB nested RDP passed checkX / VB-entry schema (--check-rdp-checkx-schema-only)",
            file=sys.stderr,
        )
        return 0

    if args.report_type_mismatches_only:
        return 0

    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    if args.coerce_sparse_to_dense_for_compare:
        py_cmp = _densify_sparse_leaves(copy.deepcopy(py_rdp))
        mat_cmp = _densify_sparse_leaves(copy.deepcopy(mat_rdp))
        _assert_nested_rdp_equal(py_cmp, mat_cmp, "RDP")
    else:
        _assert_nested_rdp_equal(py_rdp, mat_rdp, "RDP")

    print(f"OK: ctx['RDP'] matches MATLAB nested RDP in {mat_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
