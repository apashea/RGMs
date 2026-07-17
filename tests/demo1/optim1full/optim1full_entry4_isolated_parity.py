#!/usr/bin/env python3
"""OPTIM1FULL — isolated Entry **4** parity: optim SL (MATLAB MI/eig) vs MATLAB SL.

Proves that ``spm_faster_structure_learning_optim`` — with the OPTIM1FULL spectral
fence (MATLAB ``MI`` + ``eig(...,'nobalance')`` reused for :func:`spm_rgm_group`, plus
MATLAB ``spm_dir_MI`` for linked stream matrices) — matches MATLAB
``spm_faster_structure_learning`` on the shared ``rng(2)`` Entry 4 boundary
(``PDP_O(:,1:1000)``). This isolates the ``G``-field / structure divergence that the
integrated 4a/4b gate surfaced, and is the pre-gate for the full OPTIM1FULL ladder.

Authority: MATLAB ``spm_faster_structure_learning`` on the same boundary (genuine
MATLAB lineage), **not** any Python fidelity dump. Both sides run in one Engine session.

Usage (from repo root, ``conda activate rgms``):
    python -m tests.demo1.optim1full.optim1full_entry4_isolated_parity
Exit **0** = optim (MATLAB MI/eig/link) ≡ MATLAB on
``G``/``a``/``b``/``id``/``sA/sB/sC``/``ss``.
"""
from __future__ import annotations

import pickle
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from python_src.optimized.toolbox.DEM.fsl_backward_entry4_optim import (
        _assert_entry4_mdp_native_equal,
        run_entry4_optim_from_boundary,
    )
    from python_src.toolbox.DEM.fsl_backward_entry4 import (
        run_entry4_matlab_structure_learning,
    )
    from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
    from tests.demo1.demo1_paths import demo1_fixtures_dir, demo1_repo_root
    from tests.demo1.optim1full.optim1full_entry4_matlab import (
        make_optim1full_link_dir_mi_fn,
        make_optim1full_rgm_eig_pair,
        make_optim1full_rgm_mi_override_fn,
        optim1full_entry4_link_dir_mi_enabled,
        optim1full_entry4_matlab_eig_enabled,
        optim1full_entry4_matlab_mi_enabled,
    )

    fixtures = demo1_fixtures_dir()
    pre4 = fixtures / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"
    authority = fixtures / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"
    if not pre4.is_file():
        print(f"[optim1full entry4 parity] missing boundary {pre4}", file=sys.stderr)
        return 2
    if not authority.is_file():
        print(f"[optim1full entry4 parity] missing authority {authority}", file=sys.stderr)
        return 2

    if (
        not optim1full_entry4_matlab_eig_enabled()
        or not optim1full_entry4_matlab_mi_enabled()
        or not optim1full_entry4_link_dir_mi_enabled()
    ):
        print(
            "[optim1full entry4 parity] Entry 4 MATLAB MI/eig/link fences must all be on "
            "(RGMS_OPTIM1FULL_ENTRY4_MATLAB_EIG=1, "
            "RGMS_OPTIM1FULL_ENTRY4_MATLAB_MI=1, "
            "RGMS_OPTIM1FULL_ENTRY4_LINK_DIR_MI=1)",
            file=sys.stderr,
        )
        return 2

    with pre4.open("rb") as f:
        boundary = pickle.load(f)
    print(
        f"[optim1full entry4 parity] boundary {pre4.name} "
        f"o_cols={boundary.get('entry4_o_cols')} PDP_O_cols={boundary.get('PDP_O_cols')}",
        file=sys.stderr,
    )

    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        configure_dem_matlab_engine(eng, demo1_repo_root())
        eig_pair = make_optim1full_rgm_eig_pair(eng)
        mi_fn = make_optim1full_rgm_mi_override_fn(eng)
        link_mi_fn = make_optim1full_link_dir_mi_fn(eng)

        t0 = time.perf_counter()
        optim_out = run_entry4_optim_from_boundary(
            boundary,
            rgm_eig_pair=eig_pair,
            rgm_mi_override_fn=mi_fn,
            link_dir_mi_fn=link_mi_fn,
        )
        t_optim = time.perf_counter() - t0
        print(
            f"[optim1full entry4 parity] optim SL (MATLAB MI/eig/link) Nm={optim_out.get('Nm')} "
            f"in {t_optim:.1f}s",
            file=sys.stderr,
        )

        t1 = time.perf_counter()
        mat_out = run_entry4_matlab_structure_learning(eng, authority_mat_path=authority)
        t_mat = time.perf_counter() - t1
        print(
            f"[optim1full entry4 parity] MATLAB SL Nm={mat_out.get('Nm')} in {t_mat:.1f}s",
            file=sys.stderr,
        )
    finally:
        eng.quit()

    _assert_entry4_mdp_native_equal(optim_out["mdp"], mat_out["mdp"], k=4)
    print(
        "[optim1full entry4 parity] PASS: optim spm_faster_structure_learning_optim "
        "(MATLAB MI/eig/link fences) == MATLAB spm_faster_structure_learning on the Entry 4 boundary",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
