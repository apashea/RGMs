#!/usr/bin/env python3
"""Diagnostic: call-4 RDP assembly via the *spine* overlay path vs MATLAB.

Same as ``optim1full_compare_call4_rdp_pkl_to_mat`` but Python assembles through
``template_mat`` + Engine overlay (``run_spm_RDP_sort_matlab`` else-branch), which is
what ``run_optim1full_through_vb_call4_from_authority`` uses — not the disk-only
``mat_path`` path that the tier-2-style compare just proven PASS.

Does not edit production code. Report: ``matlab_custom/optim1full_call4_overlay_rdp_diag.txt``.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    import matlab.engine

    from python_src.optimized.toolbox.DEM.dem_atariiii_post12_optim import atari_ns_concentration
    from python_src.toolbox.DEM.entry12_matlab_capture import entry12_rdp_for_vb_from_mat_nested
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.optim1full.optim1full_compare_call4_rdp_pkl_to_mat import (
        _matlab_call4_rdp_from_post_nr_mat,
    )
    from tests.demo1.optim1full.optim1full_matlab_sort import (
        assemble_rdp_call4_post_nr_optim1full_parity,
        optim1full_matlab_sort_enabled,
    )
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_paths import optim1full_mdp_post_nr_mat
    from tests.demo1.optim1full.optim1full_replay import atari_c_value
    from tests.oracle.toolbox.DEM.test_spm_mdp2rdp import _assert_nested_rdp_equal

    report = _REPO / "matlab_custom" / "optim1full_call4_overlay_rdp_diag.txt"
    report.parent.mkdir(parents=True, exist_ok=True)

    if not optim1full_matlab_sort_enabled():
        print("SORT MATLAB=0", file=sys.stderr)
        return 2

    post = optim1full_mdp_post_nr_mat()
    mdp = load_mdp_from_mat(post, "MDP_post_nr")
    c_val = atari_c_value()
    ns = atari_ns_concentration()

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, _REPO)
        # Spine path: mat_path=None, template_mat=post → overlay then Engine sort → Py MI…
        rdp_py = assemble_rdp_call4_post_nr_optim1full_parity(
            eng,
            mdp,
            c_val,
            ns,
            mat_path=None,
            mat_var="MDP_post_nr",
            template_mat=post,
        )
    finally:
        eng.quit()

    rdp_mat = _matlab_call4_rdp_from_post_nr_mat(post, c_val=c_val, ns=ns)
    py_vb = entry12_rdp_for_vb_from_mat_nested(rdp_py)
    mat_vb = entry12_rdp_for_vb_from_mat_nested(rdp_mat)

    with report.open("w", encoding="utf-8") as rf:
        def _tee(s: str) -> None:
            print(s, file=sys.stderr)
            rf.write(s + "\n")

        _tee("[call4 overlay diag] spine assemble (template_mat overlay) vs MATLAB call4 assembly")
        _tee(f"MDP_post_nr={post}")
        try:
            _assert_nested_rdp_equal(py_vb, mat_vb, "call4 spine-overlay VB-input RDP")
            _tee("RESULT: PASS — overlay-path call4 RDP ≡ MATLAB call4 RDP")
            return 0
        except AssertionError as exc:
            _tee(f"RESULT: FAIL — {exc}")
            traceback.print_exc(file=rf)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
