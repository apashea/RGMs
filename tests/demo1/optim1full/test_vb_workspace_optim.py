"""Bridge tests for Phase 4-W ``VbWorkspace`` (no MATLAB)."""
from __future__ import annotations

import copy

import numpy as np

from python_src.optimized.toolbox.DEM.vb_workspace_optim import (
    ws_assign_o_slot,
    ws_bridge_max_abs_diff,
    ws_copy_p_column,
    ws_from_bundle,
    ws_o_compact_column,
    ws_set_p_onehot,
    ws_to_bundle,
)


def _mini_bundle() -> dict:
    t = 4
    d0 = np.array([[0.7], [0.3]], dtype=np.float64)
    e0 = np.array([[0.5], [0.5]], dtype=np.float64)
    o0 = np.array([[0.1], [0.9]], dtype=np.float64)
    q_legacy = [[copy.deepcopy(d0) for _ in range(t)]]
    p_legacy = [[copy.deepcopy(e0) for _ in range(t)]]
    o_legacy = [[copy.deepcopy(o0) for _ in range(t)]]
    x_arr = np.tile(d0, (1, t))
    s_arr = np.tile(e0, (1, t))
    return {
        "T": t,
        "Nm": 1,
        "Nf": [1],
        "Ng": np.array([[1]], dtype=np.int64),
        "No": np.array([[2]], dtype=np.int64),
        "D": [[d0]],
        "E": [[e0]],
        "Q": [q_legacy],
        "P": [p_legacy],
        "O": [o_legacy],
        "X": [[x_arr]],
        "S": [[s_arr]],
    }


def test_ws_from_bundle_roundtrip_zero_diff() -> None:
    bundle = _mini_bundle()
    ws = ws_from_bundle(bundle)
    assert ws.T == 4
    assert ws.nm == 1
    assert ws.Q[0][0].shape == (2, 4)
    assert ws.P[0][0].shape == (2, 4)
    assert ws.O[0][0].shape == (2, 4)
    assert ws_bridge_max_abs_diff(ws, bundle) == 0.0


def test_ws_to_bundle_roundtrip() -> None:
    bundle = _mini_bundle()
    ws = ws_from_bundle(bundle)
    ws.Q[0][0][0, 2] = 0.99
    ws.Q[0][0][1, 2] = 0.01
    ws_to_bundle(ws, bundle)
    col = np.asarray(bundle["Q"][0][0][2], dtype=np.float64).reshape(-1)
    np.testing.assert_allclose(col, [0.99, 0.01], rtol=0, atol=0)


def test_ws_alloc_varied_t() -> None:
    """Different T per call — no fixed call4 horizon."""
    for t in (1, 8, 64, 128):
        b = _mini_bundle()
        b["T"] = t
        b["Q"] = [[ [copy.deepcopy(b["D"][0][0]) for _ in range(t)] ]]
        b["P"] = [[ [copy.deepcopy(b["E"][0][0]) for _ in range(t)] ]]
        b["O"] = [[ [copy.deepcopy(np.array([[0.1], [0.9]], dtype=np.float64)) for _ in range(t)] ]]
        b["X"] = [[ np.tile(b["D"][0][0], (1, t)) ]]
        b["S"] = [[ np.tile(b["E"][0][0], (1, t)) ]]
        ws = ws_from_bundle(b)
        assert ws.T == t
        assert ws.Q[0][0].shape[1] == t


def test_ws_set_p_onehot() -> None:
    bundle = _mini_bundle()
    ws = ws_from_bundle(bundle)
    ws_set_p_onehot(ws, 0, 0, 2, 2)
    assert ws.P[0][0][1, 2] == 1.0
    ws_to_bundle(ws, bundle)
    col = np.asarray(bundle["P"][0][0][2], dtype=np.float64).reshape(-1)
    np.testing.assert_allclose(col, [0.0, 1.0], rtol=0, atol=0)


def test_ws_copy_p_column() -> None:
    bundle = _mini_bundle()
    ws = ws_from_bundle(bundle)
    ws.P[0][0][:, 1] = np.array([0.2, 0.8], dtype=np.float64)
    ws_copy_p_column(ws, 0, 0, 3, 1)
    np.testing.assert_allclose(ws.P[0][0][:, 3], [0.2, 0.8], rtol=0, atol=0)
    ws_to_bundle(ws, bundle)


def test_ws_o_roundtrip_and_assign() -> None:
    bundle = _mini_bundle()
    ws = ws_from_bundle(bundle)
    new_col = np.array([[0.25], [0.75]], dtype=np.float64)
    ws_assign_o_slot(ws, bundle, 0, 0, 2, new_col)
    np.testing.assert_allclose(ws.O[0][0][:, 2], [0.25, 0.75], rtol=0, atol=0)
    compact = ws_o_compact_column(ws, bundle, 0, 0, 2)
    np.testing.assert_allclose(compact, [0.25, 0.75], rtol=0, atol=0)
    ws_to_bundle(ws, bundle)
    leg = np.asarray(bundle["O"][0][0][2], dtype=np.float64).reshape(-1)
    np.testing.assert_allclose(leg, [0.25, 0.75], rtol=0, atol=0)
    assert ws_bridge_max_abs_diff(ws, bundle) == 0.0
