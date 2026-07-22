"""C4n contract: checked-child AB fuse (fingerprint gate + D/E-only refresh)."""
from __future__ import annotations

import numpy as np

from python_src.optimized.toolbox.DEM.vb_cold_optim import (
    vb_refresh_child_bundle_de_priors_only,
)
from python_src.optimized.toolbox.DEM.vb_entry_optim import (
    _vb_child_ab_fp,
    _vb_child_mdp_checked,
)
from python_src.optimized.toolbox.DEM.vb_run_arena_optim import VbRunArena


def _toy_mdp(*, a_scale: float = 1.0) -> dict:
    A = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64) * a_scale
    B = np.eye(2, dtype=np.float64)
    D = np.array([[0.5], [0.5]], dtype=np.float64)
    E = np.array([[1.0], [0.0]], dtype=np.float64)
    return {
        "A": [A.copy()],
        "B": [B.copy()],
        "a": [A.copy() * 512.0],
        "b": [B.copy() * 512.0],
        "D": [D.copy()],
        "E": [E.copy()],
        "T": 2.0,
    }


def test_ab_fp_stable_when_ab_unchanged_de_changed() -> None:
    m0 = _toy_mdp()
    m1 = _toy_mdp()
    m1["D"] = [np.array([[0.9], [0.1]], dtype=np.float64)]
    m1["E"] = [np.array([[0.0], [1.0]], dtype=np.float64)]
    assert _vb_child_ab_fp(m0) == _vb_child_ab_fp(m1)


def test_ab_fp_changes_when_a_changes() -> None:
    m0 = _toy_mdp(a_scale=1.0)
    m1 = _toy_mdp(a_scale=2.0)
    assert _vb_child_ab_fp(m0) != _vb_child_ab_fp(m1)


def test_arena_gate_requires_done_and_matching_fp() -> None:
    arena = VbRunArena()
    m = _toy_mdp()
    fp = _vb_child_ab_fp(m)
    assert not (
        arena.child_checkx_done.get(0)
        and arena.child_ab_fp.get(0) == fp
    )
    arena.child_checkx_done[0] = True
    arena.child_ab_fp[0] = fp
    assert arena.child_checkx_done.get(0) and arena.child_ab_fp.get(0) == fp
    m2 = _toy_mdp(a_scale=3.0)
    assert arena.child_ab_fp.get(0) != _vb_child_ab_fp(m2)


def test_de_only_refresh_updates_D_leaves_keeps_B_slot() -> None:
    md = _toy_mdp()
    # Minimal bundle shape for D/E-only path.
    B0 = np.eye(2, dtype=np.float64)
    bundle = {
        "Nm": 1,
        "Nf": [1],
        "Ns": np.array([[2]], dtype=np.int64),
        "Nu": np.array([[2]], dtype=np.int64),
        "process": [0.0],
        "gp": [{"D": [md["D"][0].copy()], "E": [md["E"][0].copy()]}],
        "T": 2,
        "O": [[[None, None]]],
        "qd": [[None]],
        "pd": [[None]],
        "D": [[None]],
        "qe": [[None]],
        "pe": [[None]],
        "E": [[None]],
        "B": [[B0]],
        "qb": [[None]],
        "pb": [[None]],
        "I": [[None]],
        "A": [[None]],
        "pa": [[None]],
        "qa": [[None]],
        "K": [[None]],
        "W": [[None]],
    }
    md["D"] = [np.array([[0.8], [0.2]], dtype=np.float64)]
    b_before = bundle["B"][0][0]
    vb_refresh_child_bundle_de_priors_only([md], bundle)
    assert bundle["B"][0][0] is b_before
    assert float(np.sum(bundle["D"][0][0])) > 0.0


def test_child_checkx_helper_exported() -> None:
    assert callable(_vb_child_mdp_checked)
