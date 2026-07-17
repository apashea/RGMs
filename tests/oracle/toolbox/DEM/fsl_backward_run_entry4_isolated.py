#!/usr/bin/env python3
"""FSL backward — run Entry 4 only on MATLAB-fed boundary (no ``entry_stop=4``).

Loads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl``.
Writes ``fixtures/DEMAtariIII_fsl_backward_entry4_post.pkl``.

**Sign-off (default):** ``RGMS_FSL_ENTRY4_MATLAB_STRUCTURE_LEARNING=1`` — Engine MATLAB
``spm_faster_structure_learning`` on paired ``PDP_O``; compare vs ``MDP_pre_entry5``. Hook-only
Python (flag ``0`` + Lane D) is diagnostic until native tensor parity.

Compare with ``fsl_backward_compare_entry4_pkl_to_mat.py``.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _pre4_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_MDP_PRE4_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry4.pkl"


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY4_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry4_post.pkl"


def _env_on(name: str, default: str = "1") -> bool:
    raw = str(os.getenv(name, default)).strip().lower()
    return raw not in ("0", "false", "no", "off")


def _default_authority_mat() -> Path:
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.mat"


def _matlab_hooks(eng: Any) -> dict[str, Any]:
    from tests.oracle.toolbox.DEM.test_spm_faster_structure_learning import (
        _make_matlab_link_dir_mi_fn,
        _make_matlab_rgm_eig_pair,
        _make_rgm_mi_override_fn_matlab,
    )

    hooks: dict[str, Any] = {}
    if _env_on("RGMS_FSL_RGM_MATLAB_EIG"):
        hooks["rgm_eig_pair"] = _make_matlab_rgm_eig_pair(eng)
    if _env_on("RGMS_FSL_RGM_MATLAB_MI_PUSH"):
        if "rgm_eig_pair" not in hooks:
            raise RuntimeError(
                "RGMS_FSL_RGM_MATLAB_MI_PUSH requires RGMS_FSL_RGM_MATLAB_EIG=1 for FSL Entry 4 sign-off"
            )
        hooks["rgm_mi_override_fn"] = _make_rgm_mi_override_fn_matlab(eng)
    if _env_on("RGMS_FSL_LINK_DIR_MI_MATLAB"):
        hooks["link_dir_mi_fn"] = _make_matlab_link_dir_mi_fn(eng)
    return hooks


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry4 import (
        run_entry4_from_boundary,
        run_entry4_matlab_structure_learning,
    )

    pre = _pre4_pkl()
    if not pre.is_file():
        print(
            f"[FSL backward Entry 4 isolated] missing {pre}\n"
            "Run: python fsl_backward_materialize_mdp_pre_entry4_pkl.py",
            file=sys.stderr,
        )
        return 2

    with pre.open("rb") as f:
        boundary = pickle.load(f)
    print(f"[FSL backward Entry 4 isolated] input {pre}", file=sys.stderr)
    print(
        f"[FSL backward Entry 4 isolated] o_cols={boundary.get('entry4_o_cols')} "
        f"PDP_O_cols={boundary.get('PDP_O_cols')}",
        file=sys.stderr,
    )

    if _env_on("RGMS_FSL_ENTRY4_MATLAB_STRUCTURE_LEARNING"):
        import matlab.engine

        mat_path = _default_authority_mat()
        eng = matlab.engine.start_matlab()
        try:
            from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

            dem_path = configure_dem_matlab_engine(eng, _REPO)
            print(
                "[FSL backward Entry 4 isolated] RGMS_FSL_ENTRY4_MATLAB_STRUCTURE_LEARNING=1 "
                f"(Engine spm_faster_structure_learning on {mat_path.name})",
                file=sys.stderr,
            )
            out_payload = run_entry4_matlab_structure_learning(eng, authority_mat_path=mat_path)
        finally:
            eng.quit()
    elif (
        _env_on("RGMS_FSL_RGM_MATLAB_EIG")
        or _env_on("RGMS_FSL_RGM_MATLAB_MI_PUSH")
        or _env_on("RGMS_FSL_LINK_DIR_MI_MATLAB")
    ):
        import matlab.engine

        eng = matlab.engine.start_matlab()
        try:
            from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

            dem_path = configure_dem_matlab_engine(eng, _REPO)
            hooks = _matlab_hooks(eng)
            print(
                "[FSL backward Entry 4 isolated] hooks: "
                f"eig={_env_on('RGMS_FSL_RGM_MATLAB_EIG')} "
                f"mi_push={_env_on('RGMS_FSL_RGM_MATLAB_MI_PUSH')} "
                f"link_mi={_env_on('RGMS_FSL_LINK_DIR_MI_MATLAB')}",
                file=sys.stderr,
            )
            out_payload = run_entry4_from_boundary(boundary, **hooks)
        finally:
            eng.quit()
    else:
        hooks: dict[str, Any] = {}
        if _env_on("RGMS_FSL_RGM_NATIVE_EIG_NOBALANCE", default="0"):
            from python_src.utils.eig_nobalance import eig_nobalance, resolve_backend

            hooks["rgm_eig_pair"] = eig_nobalance
            print(
                "[FSL backward Entry 4 isolated] native eig_nobalance "
                f"(backend={resolve_backend()}, T0 order 51/58 on dump corpus — eig.md §24)",
                file=sys.stderr,
            )
        else:
            print(
                "[FSL backward Entry 4 isolated] native scipy.linalg.eig "
                "(set RGMS_FSL_RGM_NATIVE_EIG_NOBALANCE=1 for eig_nobalance)",
                file=sys.stderr,
            )
        out_payload = run_entry4_from_boundary(boundary, **hooks)

    print(
        f"[FSL backward Entry 4 isolated] Nm={out_payload.get('Nm')}",
        file=sys.stderr,
    )
    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "C": float(boundary.get("C", 32.0)),
                "source_pre4_pkl": str(pre),
                "validation": {
                    "lane": "fsl_backward_entry4",
                    "authority_var": "MDP_pre_entry5",
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 4 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
