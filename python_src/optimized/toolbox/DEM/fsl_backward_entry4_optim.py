"""OPTIM1 FSL backward — Entry 4 (``spm_faster_structure_learning_optim``).

Ledger: ``faster_structure_learning_optim`` from ``dem_atariiii_entry4_optim``.

Authority for OPTIM1 holistic: **optim ≡ fidelity native** on ``MDP_pre_entry4`` boundary
(same contract as ``DEM_AtariIII_optim`` ENTRY4). FSL Product B MATLAB-hook lane unchanged.
"""

from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any, Callable, Tuple

import numpy as np

from python_src.optimized.toolbox.DEM.dem_atariiii_entry4_optim import (
    faster_structure_learning_optim,
)
from python_src.toolbox.DEM.fsl_backward_entry4 import entry4_boundary_from_driver_ctx
from tests.demo1.demo1_paths import demo1_fixtures_dir
from tests.demo1.optim1.optim1_paths import optim1_fixtures_dir


def run_entry4_optim_from_boundary(
    boundary: dict[str, Any],
    *,
    rgm_eig_pair: Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]] | None = None,
    rgm_mi_override_fn: Callable[[list[Any], int], np.ndarray] | None = None,
    link_dir_mi_fn: Callable[[np.ndarray], float] | None = None,
) -> dict[str, Any]:
    """Run Entry **4** optim ledger from materialized pre-Entry-4 boundary dict.

    ``rgm_eig_pair`` / ``rgm_mi_override_fn`` / ``link_dir_mi_fn`` are optional MATLAB
    reuse hooks forwarded to ``spm_faster_structure_learning_optim``. Default ``None``
    keeps native compute unchanged for OPTIM1 / native lanes. OPTIM1FULL Product B
    parity wires MATLAB MI + ``eig(...,'nobalance')`` + link ``spm_dir_MI`` through
    these hooks (see ``tests/demo1/optim1full/optim1full_entry4_matlab.py``).
    """
    t0 = time.perf_counter()
    mdp_out = faster_structure_learning_optim(
        boundary["pdp_o_sl"],
        np.asarray(boundary["S"], dtype=np.float64),
        int(boundary["Sc"]),
        rgm_eig_pair=rgm_eig_pair,
        rgm_mi_override_fn=rgm_mi_override_fn,
        link_dir_mi_fn=link_dir_mi_fn,
    )
    entry4_loop_s = time.perf_counter() - t0
    return {
        "mdp": mdp_out,
        "Nm": len(mdp_out),
        "entry4_o_cols": int(boundary.get("entry4_o_cols", 1000)),
        "entry4_loop_s": float(entry4_loop_s),
    }


def run_entry4_optim_from_pre_entry4_pkl(
    *,
    pre_entry4_pkl: Path | None = None,
) -> dict[str, Any]:
    """Run Entry **4** optim from DEMO1 ``MDP_pre_entry4`` boundary PKL."""
    pkl = pre_entry4_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"
    )
    if not pkl.is_file():
        raise FileNotFoundError(f"missing DEMO1 pre_entry4 PKL: {pkl}")
    with pkl.open("rb") as f:
        boundary = pickle.load(f)
    if not isinstance(boundary, dict):
        raise TypeError(f"expected dict in {pkl}")
    t0 = time.perf_counter()
    out = run_entry4_optim_from_boundary(boundary)
    wall_s = time.perf_counter() - t0
    return {
        **out,
        "validation_lane": "optim_pre_entry4",
        "source_pre4_pkl": str(pkl),
        "entry4_wall_s": wall_s,
    }


def write_entry4_optim_post_pkl(payload: dict[str, Any], path: Path | None = None) -> Path:
    """Persist OPTIM1 Entry **4** post blob under ``tests/demo1/optim1/fixtures/``."""
    out = path or (optim1_fixtures_dir() / "DEMAtariIII_optim1_entry4_post.pkl")
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "mdp": payload["mdp"],
        "Nm": payload.get("Nm"),
        "entry4_o_cols": payload.get("entry4_o_cols"),
        "entry4_loop_s": payload.get("entry4_loop_s"),
        "entry4_wall_s": payload.get("entry4_wall_s"),
        "validation_lane": payload.get("validation_lane"),
        "source_pre4_pkl": payload.get("source_pre4_pkl"),
        "validation": {
            "lane": "optim1_entry4",
            "authority": "fidelity_native",
        },
    }
    with out.open("wb") as f:
        pickle.dump(blob, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def compare_entry4_optim_to_fidelity_native(
    optim_out: dict[str, Any],
    *,
    pre_entry4_pkl: Path | None = None,
) -> None:
    """Assert optim Entry **4** ≡ fidelity Entry **4** on same boundary (native Python)."""
    from python_src.toolbox.DEM.fsl_backward_entry4 import run_entry4_from_boundary

    pkl = pre_entry4_pkl or (
        demo1_fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"
    )
    with pkl.open("rb") as f:
        boundary = pickle.load(f)
    fid = run_entry4_from_boundary(boundary)
    _assert_entry4_mdp_native_equal(optim_out["mdp"], fid["mdp"], k=4)


def _assert_entry4_mdp_native_equal(
    py_mdp: list[dict[str, Any]],
    ref_mdp: list[dict[str, Any]],
    *,
    k: int,
) -> None:
    """Entry **4** native ``MDP`` compare — ``ss.*`` cells are dict maps, not numeric tensors."""
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_array_equal_exact,
        _to_tensor,
        _canonical_tensor_shape,
    )

    if len(py_mdp) != len(ref_mdp):
        raise AssertionError(f"call={k} level-count py={len(py_mdp)} ref={len(ref_mdp)}")
    for n in range(len(py_mdp)):
        p = py_mdp[n]
        m = ref_mdp[n]
        if not np.isclose(float(p["T"]), float(m["T"]), rtol=0.0, atol=1e-12):
            raise AssertionError(f"call={k} lev={n+1} field=T py={float(p['T'])} ref={float(m['T'])}")
        for field in ("sA", "sB", "sC"):
            if list(p[field]) != list(m[field]):
                raise AssertionError(f"call={k} lev={n+1} field={field} mismatch")
        if _normalize_entry4_id_a(p["id"]["A"]) != _normalize_entry4_id_a(m["id"]["A"]):
            raise AssertionError(f"call={k} lev={n+1} id.A mismatch")
        for field in ("D", "E"):
            if p["id"][field] != m["id"][field]:
                raise AssertionError(f"call={k} lev={n+1} id.{field} mismatch")
        if p["G"].keys() != m["G"].keys():
            raise AssertionError(f"call={k} lev={n+1} G key mismatch")
        for sk in p["G"].keys():
            pg = p["G"][sk]
            mg = m["G"][sk]
            if len(pg) != len(mg):
                raise AssertionError(f"call={k} lev={n+1} G[{sk}] group-count mismatch")
            for gi in range(len(pg)):
                pv = np.asarray(pg[gi], dtype=np.int64).ravel(order="F")
                mv = np.asarray(mg[gi], dtype=np.int64).ravel(order="F")
                if not np.array_equal(pv, mv):
                    raise AssertionError(f"call={k} lev={n+1} G[{sk}]{{{gi+1}}} mismatch")
        if len(p["a"]) != len(m["a"]):
            raise AssertionError(f"call={k} lev={n+1} a-count mismatch")
        if len(p["b"]) != len(m["b"]):
            raise AssertionError(f"call={k} lev={n+1} b-count mismatch")
        for g in range(len(p["a"])):
            pa = _canonical_tensor_shape(_to_tensor(p["a"][g]))
            ma = _canonical_tensor_shape(_to_tensor(m["a"][g]))
            _assert_array_equal_exact(pa, ma, f"lev={n+1} a[{g+1}]", k)
        for f in range(len(p["b"])):
            pb = _canonical_tensor_shape(_to_tensor(p["b"][f]))
            mb = _canonical_tensor_shape(_to_tensor(m["b"][f]))
            _assert_array_equal_exact(pb, mb, f"lev={n+1} b[{f+1}]", k)
        for ss_field in ("D", "E", "ID", "IE"):
            p_ss = p["ss"][ss_field]
            m_ss = m["ss"][ss_field]
            if len(p_ss) != len(m_ss):
                raise AssertionError(f"call={k} lev={n+1} ss.{ss_field} row-count mismatch")
            for i in range(len(p_ss)):
                if len(p_ss[i]) != len(m_ss[i]):
                    raise AssertionError(
                        f"call={k} lev={n+1} ss.{ss_field} col-count mismatch at row={i+1}"
                    )
                for j in range(len(p_ss[i])):
                    _assert_entry4_ss_cell_equal(
                        p_ss[i][j],
                        m_ss[i][j],
                        f"lev={n+1} ss.{ss_field}[{i+1},{j+1}]",
                        k,
                    )


def _normalize_entry4_id_a(v: Any) -> list[int]:
    """Normalize ``id.A`` scalar-cell layout for native-vs-MATLAB Engine compares."""
    out: list[int] = []
    for item in v:
        if isinstance(item, list):
            if len(item) != 1:
                raise AssertionError(f"id.A expected scalar cell, got {item!r}")
            out.append(int(item[0]))
        else:
            out.append(int(item))
    return out


def _assert_entry4_ss_cell_equal(pv: Any, rv: Any, label: str, k: int) -> None:
    if _entry4_empty_cell(pv) and _entry4_empty_cell(rv):
        return
    if _entry4_empty_cell(pv) or _entry4_empty_cell(rv):
        raise AssertionError(f"call={k} {label}: None mismatch py={pv!r} ref={rv!r}")
    if isinstance(pv, dict) and isinstance(rv, dict):
        if set(pv.keys()) != set(rv.keys()):
            raise AssertionError(
                f"call={k} {label}: dict keys py={sorted(pv.keys())} ref={sorted(rv.keys())}"
            )
        for key in pv:
            p_val = pv[key]
            r_val = rv[key]
            if isinstance(p_val, (bool, np.bool_)) or isinstance(r_val, (bool, np.bool_)):
                if bool(p_val) != bool(r_val):
                    raise AssertionError(f"call={k} {label} key={key}: {p_val!r} vs {r_val!r}")
            elif isinstance(p_val, (int, np.integer)) and isinstance(r_val, (int, np.integer)):
                if int(p_val) != int(r_val):
                    raise AssertionError(f"call={k} {label} key={key}: {p_val!r} vs {r_val!r}")
            elif not np.isclose(float(p_val), float(r_val), rtol=0.0, atol=1e-12):
                raise AssertionError(f"call={k} {label} key={key}: {p_val!r} vs {r_val!r}")
        return
    from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry8 import (
        _assert_array_equal_exact,
        _canonical_tensor_shape,
        _to_tensor,
    )

    pt = _canonical_tensor_shape(_to_tensor(pv))
    rt = _canonical_tensor_shape(_to_tensor(rv))
    _assert_array_equal_exact(pt, rt, label, k)


def _entry4_empty_cell(v: Any) -> bool:
    if v is None:
        return True
    try:
        return np.asarray(v).size == 0
    except Exception:
        return False


__all__ = [
    "entry4_boundary_from_driver_ctx",
    "run_entry4_optim_from_boundary",
    "run_entry4_optim_from_pre_entry4_pkl",
    "write_entry4_optim_post_pkl",
    "compare_entry4_optim_to_fidelity_native",
]
