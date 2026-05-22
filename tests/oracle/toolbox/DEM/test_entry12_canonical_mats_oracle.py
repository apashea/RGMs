"""Entry 12 canonical ``.mat`` oracle hooks (MATLAB capture vs Python).

Requires artifacts from ``DEMAtariIII_entry12_dump_all_subentries.m`` with
``RGMS_ENTRY12_CAPTURE_RUN_TAG`` matching :data:`ENTRY12_CANONICAL_RUN_TAG` (default ``rgms_canonical``),
plus ``matlab_custom/saved_rdp_DEM_AtariIII.mat``. Skip cleanly when files are absent.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from python_src.toolbox.DEM.entry12_matlab_capture import (
    ENTRY12_CANONICAL_RUN_TAG,
    default_entry12_mat_output_dir,
    entry12_subentry_mat_path,
    load_entry12_subentry_mat,
    rgms_repo_root,
    saved_rdp_dem_atariiii_mat_path,
)
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.entry12_loadmat_convert import (
    load_saved_rdp_as_py,
    mat_nested_to_py,
)
from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal


def _effective_run_tag() -> str:
    return (os.getenv("RGMS_ENTRY12_CAPTURE_RUN_TAG") or ENTRY12_CANONICAL_RUN_TAG).strip()


def _effective_out_dir() -> Path:
    raw = os.getenv("RGMS_ENTRY12_CAPTURE_OUT_DIR")
    return Path(raw) if raw else default_entry12_mat_output_dir()


def _require_saved_rdp() -> Path:
    p = saved_rdp_dem_atariiii_mat_path()
    if not p.is_file():
        pytest.skip(f"missing canonical RDP source: {p} (run matlab_custom/dump_rdp_DEM_AtariIII.m)")
    return p


def _require_mat12a() -> Path:
    tag = _effective_run_tag()
    od = _effective_out_dir()
    p12a = entry12_subentry_mat_path(tag, "12A", out_dir=od)
    if not p12a.is_file():
        pytest.skip(
            f"missing 12A capture: {p12a} "
            f"(MATLAB: setenv RGMS_ENTRY12_CAPTURE_RUN_TAG,{tag} "
            f"and run DEMAtariIII_entry12_dump_all_subentries)"
        )
    return p12a


@pytest.mark.slow
def test_entry12a_python_checkx_matches_matlab_capture_mdp() -> None:
    """Parity: ``spm_MDP_checkX(RDP)`` vs ``MDP`` in ``_12A.mat`` (same ``saved_rdp`` lineage)."""
    _require_saved_rdp()
    path_12a = _require_mat12a()

    rdp_py = load_saved_rdp_as_py(saved_rdp_dem_atariiii_mat_path())
    py_mdp = spm_MDP_checkX(copy.deepcopy(rdp_py))

    blob = load_entry12_subentry_mat(path_12a)
    assert "MDP" in blob
    mat_mdp = mat_nested_to_py(blob["MDP"])

    _assert_nested_rdp_equal(py_mdp, mat_mdp, "entry12.12A.MDP")


@pytest.mark.parametrize(
    "code",
    ("12A", "12B", "12C", "12D", "12E", "12F", "12G", "12H", "12I"),
)
def test_entry12_subentry_mat_loads_when_present(code: str) -> None:
    """Smoke: each subentry ``.mat`` loads under effective tag/out-dir when files exist."""
    tag = _effective_run_tag()
    od = _effective_out_dir()
    p = entry12_subentry_mat_path(tag, code, out_dir=od)
    if not p.is_file():
        pytest.skip(f"missing {p}")
    blob = load_entry12_subentry_mat(p)
    assert "OPTIONS" in blob and "meta" in blob
    if code == "12I":
        assert "OPTIONS" in blob and "meta" in blob
    if code == "12H":
        assert "PDP" in blob


def test_entry12_Q_Y_flat_level_canonicalize_to_ng_t() -> None:
    """``Q.Y{L}`` flat ``Ng×T`` row → nested ``[o][t]`` (index ``o + t*Ng``)."""
    from python_src.toolbox.DEM.entry12_matlab_capture import _entry12_canonicalize_Q_ot_grid_levels

    ng, t_count = 3, 2
    flat = [f"o{o}t{t}" for t in range(t_count) for o in range(ng)]
    nested = [[f"o{o}t{t}" for t in range(t_count)] for o in range(ng)]
    assert _entry12_canonicalize_Q_ot_grid_levels([flat]) == [nested]
    assert _entry12_canonicalize_Q_ot_grid_levels(nested) == nested


def test_entry12_O_nested_canonicalize_tg_to_gt() -> None:
    """``MDP.MDP.O``: post-``shiftdim`` ``O[t][g]`` → ``O[g][t]`` for paired ``.mat`` compare."""
    import numpy as np

    from python_src.toolbox.DEM.entry12_matlab_capture import (
        _entry12_canonicalize_O_nested_block,
        _entry12_transpose_O_tg_to_gt,
    )

    tg = [[f"t{t}g{g}" for g in range(3)] for t in range(2)]
    gt = _entry12_transpose_O_tg_to_gt(tg)
    assert len(gt) == 3 and len(gt[0]) == 2
    assert gt[1][0] == "t0g1"
    assert _entry12_canonicalize_O_nested_block(tg) == gt
    mat_nested = [[f"t{t}g{g}" for t in range(2)] for g in range(3)]
    assert _entry12_canonicalize_O_nested_block(mat_nested) == mat_nested
    arr = np.empty((3, 2), dtype=object)
    for g in range(3):
        for t in range(2):
            arr[g, t] = f"t{t}g{g}"
    assert _entry12_canonicalize_O_nested_block(arr) == mat_nested


def test_entry12_ss_D_canonicalize_matches_py_flat16() -> None:
    """``ss.D``: symmetric flatten of mat ``4×4`` nested matches py length-16 dump."""
    import numpy as np

    from python_src.toolbox.DEM.entry12_matlab_capture import (
        _entry12_canonicalize_ss_cell_block,
    )

    nested = [[{"i": i, "j": j} for j in range(4)] for i in range(4)]
    flat = [{"i": i, "j": j} for i in range(4) for j in range(4)]
    assert len(_entry12_canonicalize_ss_cell_block(nested)) == 16
    assert len(_entry12_canonicalize_ss_cell_block(flat)) == 16
    cell = np.empty((4, 4), dtype=object)
    for i in range(4):
        for j in range(4):
            cell[i, j] = {"i": i, "j": j}
    assert len(_entry12_canonicalize_ss_cell_block(cell)) == 16


def test_mat_nested_to_py_preserves_2d_object_cell_grid() -> None:
    """MATLAB ``cell(Ng,T)`` must not flatten to ``Ng*T`` (e.g. ``entry12_Yfill``)."""
    import numpy as np

    cell = np.empty((2, 3), dtype=object)
    for i in range(2):
        for j in range(3):
            cell[i, j] = {"g": i, "t": j}
    out = mat_nested_to_py(cell)
    assert isinstance(out, list) and len(out) == 2
    assert all(isinstance(row, list) and len(row) == 3 for row in out)
    assert out[1][2] == {"g": 1, "t": 2}


def test_entry12_canonical_paths_documented() -> None:
    """Sanity: canonical tag resolves (no I/O)."""
    assert ENTRY12_CANONICAL_RUN_TAG
    p = entry12_subentry_mat_path(ENTRY12_CANONICAL_RUN_TAG, "12A")
    assert p.name.startswith("DEMAtariIII_entry12_")


def test_repo_root_contains_matlab_custom() -> None:
    assert (rgms_repo_root() / "matlab_custom").is_dir()
