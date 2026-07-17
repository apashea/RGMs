"""OPTIM1 Product A — native compare helpers (optim ≡ fidelity Python, no MATLAB)."""

from __future__ import annotations

import copy
import pickle
from pathlib import Path
from typing import Any

import numpy as np

try:
    import scipy.sparse as sp
except ImportError:  # pragma: no cover
    sp = None  # type: ignore[assignment]

from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_python_native_driver_ctx_path
from tests.demo1.demo1_native_fixtures import (
    DEMO1_NATIVE_LADDER_ENTRY_STOPS,
    load_demo1_native_entry_ctx,
)


def load_demo1_native_authority_ctx(*, entry_stop: int) -> dict[str, Any]:
    """Load DEMO1 Product A authority ``ctx`` frozen at ladder ``entry_stop``.

    Requires one prior ``demo1_native_dump.py`` run (seed **2**). OPTIM1 Tier **3**
    compares optim-only runs to these fixtures — **no** live fidelity re-run.
    """
    n = int(entry_stop)
    if n >= 12:
        n = 12
    if n not in DEMO1_NATIVE_LADDER_ENTRY_STOPS:
        raise ValueError(
            f"entry_stop={entry_stop}: native authority fixtures exist for "
            f"{DEMO1_NATIVE_LADDER_ENTRY_STOPS} only"
        )
    return load_demo1_native_entry_ctx(n)


def load_demo1_native_reference_ctx(path: Path | None = None) -> dict[str, Any]:
    """Load DEMO1 Product A reference driver ctx (``tests/demo1/python_native/``)."""
    pkl = path or demo1_python_native_driver_ctx_path()
    if not pkl.is_file():
        raise FileNotFoundError(
            f"missing DEMO1 native reference PKL: {pkl} "
            "(run DEM_AtariIII_demo1_python.py --save-artifacts with native seed 2)"
        )
    with pkl.open("rb") as f:
        blob = pickle.load(f)
    if not isinstance(blob, dict):
        raise TypeError(f"expected dict in {pkl}")
    return blob


def compare_entry89_fidelity_vs_optim_native(
    *,
    pre_entry9_pkl: Path | None = None,
) -> None:
    """Run fidelity + optim Entry **8+9** on the same boundary; assert ``MDP`` match."""
    from python_src.optimized.toolbox.DEM.fsl_backward_entry9_optim import (
        run_entry9_optim_from_boundary,
    )
    from python_src.toolbox.DEM.fsl_backward_entry9 import run_entry9_from_boundary
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import _assert_mdp_full_equal

    pre9 = pre_entry9_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry9.pkl"
    )
    if not pre9.is_file():
        raise FileNotFoundError(f"missing pre_entry9 PKL: {pre9}")
    with pre9.open("rb") as f:
        boundary = pickle.load(f)
    if not isinstance(boundary, dict):
        raise TypeError(f"expected dict in {pre9}")

    fid = run_entry9_from_boundary(copy.deepcopy(boundary))
    opt = run_entry9_optim_from_boundary(copy.deepcopy(boundary))
    _assert_mdp_full_equal(opt["mdp"], fid["mdp"], k=9)


def _assert_native_values_equal(a: Any, b: Any, *, path: str) -> None:
    """Recursive exact compare for native Product A authority (arrays, nested dicts)."""
    if sp is not None and (sp.issparse(a) or sp.issparse(b)):
        aa = a.tocsr() if sp.issparse(a) else sp.csr_matrix(np.asarray(a))
        bb = b.tocsr() if sp.issparse(b) else sp.csr_matrix(np.asarray(b))
        if aa.shape != bb.shape:
            raise AssertionError(f"{path}: sparse shape {aa.shape} vs {bb.shape}")
        diff = aa - bb
        if diff.nnz != 0:
            raise AssertionError(f"{path}: sparse mismatch nnz={diff.nnz}")
        return

    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        aa = np.asarray(a)
        bb = np.asarray(b)
        if aa.shape != bb.shape:
            raise AssertionError(f"{path}: shape {aa.shape} vs {bb.shape}")
        if aa.dtype.kind in "fc" or bb.dtype.kind in "fc":
            np.testing.assert_allclose(aa, bb, rtol=0.0, atol=1e-12, err_msg=path)
        else:
            np.testing.assert_array_equal(aa, bb, err_msg=path)
        return

    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            raise AssertionError(
                f"{path}: keys optim={sorted(a.keys())} ref={sorted(b.keys())}"
            )
        for k in sorted(a.keys()):
            _assert_native_values_equal(a[k], b[k], path=f"{path}.{k}")
        return

    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            raise AssertionError(f"{path}: len {len(a)} vs {len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            _assert_native_values_equal(ai, bi, path=f"{path}[{i}]")
        return

    if type(a) is not type(b) and not (
        isinstance(a, (np.ndarray, float, int))
        and isinstance(b, (np.ndarray, float, int))
    ):
        raise AssertionError(f"{path}: type mismatch {type(a).__name__} vs {type(b).__name__}")

    if isinstance(a, (float, np.floating)) or isinstance(b, (float, np.floating)):
        if not np.isclose(float(a), float(b), rtol=0.0, atol=1e-12):
            raise AssertionError(f"{path}: {a!r} vs {b!r}")
        return

    if a != b:
        raise AssertionError(f"{path}: {a!r} vs {b!r}")


def assert_native_entry_ctx_full_equal(
    optim_ctx: dict[str, Any],
    ref_ctx: dict[str, Any],
    *,
    entry_stop: int,
) -> None:
    """Full top-level ``ctx`` parity at driver ``entry_stop`` (all keys, all nested fields)."""
    n = int(entry_stop)
    if set(optim_ctx.keys()) != set(ref_ctx.keys()):
        raise AssertionError(
            f"entry_stop={n} ctx keys: optim={sorted(optim_ctx.keys())} "
            f"ref={sorted(ref_ctx.keys())}"
        )
    for k in sorted(ref_ctx.keys()):
        _assert_native_values_equal(optim_ctx[k], ref_ctx[k], path=f"ctx.{k}")


def _assert_native_pdp_o_equal(optim_ctx: dict[str, Any], ref_ctx: dict[str, Any]) -> None:
    p_opt = optim_ctx.get("PDP", {})
    p_ref = ref_ctx.get("PDP", {})
    if not isinstance(p_opt, dict) or not isinstance(p_ref, dict):
        raise AssertionError("PDP must be dict in both ctx")
    o_opt = np.asarray(p_opt.get("o"), dtype=np.float64)
    o_ref = np.asarray(p_ref.get("o"), dtype=np.float64)
    np.testing.assert_array_equal(
        o_opt,
        o_ref,
        err_msg="PDP.o mismatch (native Product A compare)",
    )


def assert_native_driver_ctx_equal_at_entry_stop(
    optim_ctx: dict[str, Any],
    ref_ctx: dict[str, Any],
    entry_stop: int,
    *,
    compare_path_ledgers: bool = True,
    compare_pdp_o: bool = True,
) -> None:
    """Ladder compare — fields defined at driver ``entry_stop`` (``optim1_native_gate --entry-stop``)."""
    if entry_stop in (3, 7, 9, 12):
        assert_native_entry_ctx_full_equal(optim_ctx, ref_ctx, entry_stop=entry_stop)
        return

    raise ValueError(
        f"native gate ladder --entry-stop {entry_stop}: supported ladder nodes are 3, 7, 9, 12"
    )


def assert_native_driver_ctx_equal(
    optim_ctx: dict[str, Any],
    ref_ctx: dict[str, Any],
    *,
    compare_path_ledgers: bool = True,
    compare_pdp_o: bool = True,
) -> None:
    """Full Product A driver ctx compare — optim must match fidelity end-to-end.

    Checks scalars, path ledgers (``NS``, ``NU``), ``GDP``/``RDP``/``MDP`` structure,
    and ``PDP.o``. No field may be omitted for sign-off.
    """
    for key in ("Nm", "Ne"):
        if optim_ctx.get(key) != ref_ctx.get(key):
            raise AssertionError(f"scalar {key}: optim={optim_ctx.get(key)!r} ref={ref_ctx.get(key)!r}")

    if compare_path_ledgers:
        for key in ("NS", "NU"):
            if optim_ctx.get(key) != ref_ctx.get(key):
                raise AssertionError(f"ledger {key}: optim/ref length or values differ")

    g_opt = optim_ctx.get("GDP", {})
    g_ref = ref_ctx.get("GDP", {})
    if not isinstance(g_opt, dict) or not isinstance(g_ref, dict):
        raise AssertionError("GDP must be dict in both ctx")
    if not np.isclose(float(g_opt.get("T", 0)), float(g_ref.get("T", 0)), rtol=0.0, atol=1e-12):
        raise AssertionError(f"GDP.T mismatch: optim={g_opt.get('T')} ref={g_ref.get('T')}")

    r_opt = optim_ctx.get("RDP", {})
    r_ref = ref_ctx.get("RDP", {})
    if not isinstance(r_opt, dict) or not isinstance(r_ref, dict):
        raise AssertionError("RDP must be dict in both ctx")
    if not np.isclose(float(r_opt.get("T", 0)), float(r_ref.get("T", 0)), rtol=0.0, atol=1e-12):
        raise AssertionError(f"RDP.T mismatch: optim={r_opt.get('T')} ref={r_ref.get('T')}")

    m_opt = optim_ctx.get("MDP")
    m_ref = ref_ctx.get("MDP")
    if not isinstance(m_opt, list) or not isinstance(m_ref, list):
        raise AssertionError("MDP must be list in both ctx")
    if len(m_opt) != len(m_ref):
        raise AssertionError(f"MDP level-count: optim={len(m_opt)} ref={len(m_ref)}")
    for i, (p, r) in enumerate(zip(m_opt, m_ref)):
        if not np.isclose(float(p.get("T", 0)), float(r.get("T", 0)), rtol=0.0, atol=1e-12):
            raise AssertionError(f"MDP[{i}].T mismatch: optim={p.get('T')} ref={r.get('T')}")
        for path_key in ("sA", "sB", "sC"):
            if list(p.get(path_key, [])) != list(r.get(path_key, [])):
                raise AssertionError(f"MDP[{i}].{path_key} path mismatch")

    if compare_pdp_o:
        _assert_native_pdp_o_equal(optim_ctx, ref_ctx)
