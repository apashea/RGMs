#!/usr/bin/env python3
"""FSL backward — run Entry 10 only on MATLAB-fed ``MDP`` (no ``entry_stop=10``).

Loads ``fixtures/DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl``.
Writes ``fixtures/DEMAtariIII_fsl_backward_entry10_post.pkl``.

**Sign-off (default):** ``RGMS_FSL_RDP_SORT_MATLAB_EIG`` defaults to **on** — Engine
``eig(B,'nobalance')`` is injected into Python ``spm_RDP_sort`` so sorting uses MATLAB's
eigen determination while prune / compress / goals / ``P`` remain Python. See
``Atari_example.md`` § **Entry 10 — eigen limitation (project-critical)**.

Native eig diagnostic: ``RGMS_FSL_RDP_SORT_MATLAB_EIG=0``.

Compare with ``fsl_backward_compare_entry10_pkl_to_mat.py``.
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _fixtures_dir() -> Path:
    from tests.demo1.demo1_paths import demo1_fixtures_dir

    return demo1_fixtures_dir()


def _pre10_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_MDP_PRE10_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_MDP_pre_entry10.pkl"


def _out_pkl() -> Path:
    raw = str(os.getenv("RGMS_FSL_BACKWARD_ENTRY10_POST_PKL_PATH", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _fixtures_dir() / "DEMAtariIII_fsl_backward_entry10_post.pkl"


def _env_matlab_eig() -> bool:
    """FSL backward Entry 10 sign-off defaults to MATLAB ``eig`` injection (see Atari_example.md)."""
    raw = str(os.getenv("RGMS_FSL_RDP_SORT_MATLAB_EIG", "1")).strip().lower()
    return raw not in ("0", "false", "no", "off")


def main() -> int:
    from python_src.toolbox.DEM.fsl_backward_entry10 import run_entry10_from_mdp

    pre = _pre10_pkl()
    if not pre.is_file():
        print(
            f"[FSL backward Entry 10 isolated] missing {pre}\n"
            "Run: matlab dump_MDP_pre_entry10.m, then "
            "python fsl_backward_materialize_mdp_pre_entry10_pkl.py",
            file=sys.stderr,
        )
        return 2

    with pre.open("rb") as f:
        boundary = pickle.load(f)
    mdp = boundary["mdp"]
    c_val = float(boundary["C"])
    print(f"[FSL backward Entry 10 isolated] input {pre}", file=sys.stderr)

    eig_fn = None
    if _env_matlab_eig():
        import matlab.engine

        from tests.oracle.toolbox.DEM.test_spm_RDP_sort import _make_matlab_spm_RDP_sort_eig

        eng = matlab.engine.start_matlab()
        try:
            from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine

            dem_path = configure_dem_matlab_engine(eng, _REPO)
            eig_fn = _make_matlab_spm_RDP_sort_eig(eng)
            print(
                "[FSL backward Entry 10 isolated] RGMS_FSL_RDP_SORT_MATLAB_EIG=1 "
                "(Engine eig(B,'nobalance'))",
                file=sys.stderr,
            )
            out_payload = run_entry10_from_mdp(mdp, c_val=c_val, eig=eig_fn)
        finally:
            eng.quit()
    else:
        backend = str(os.getenv("RGMS_SPM_RDP_SORT_EIG_BACKEND", "auto")).strip() or "auto"
        print(
            f"[FSL backward Entry 10 isolated] native eig backend={backend}",
            file=sys.stderr,
        )
        out_payload = run_entry10_from_mdp(mdp, c_val=c_val)
    out = _out_pkl()
    out.parent.mkdir(parents=True, exist_ok=True)
    eig_source = "matlab_engine" if eig_fn is not None else "native"
    with out.open("wb") as f:
        pickle.dump(
            {
                **out_payload,
                "C": c_val,
                "source_pre10_pkl": str(pre),
                "validation": {
                    "lane": "fsl_backward_entry10",
                    "eig_source": eig_source,
                    "matlab_eig_injected": eig_fn is not None,
                    "RGMS_FSL_RDP_SORT_MATLAB_EIG": _env_matlab_eig(),
                    "eig_backend": (
                        "matlab_engine_nobalance"
                        if eig_fn is not None
                        else str(os.getenv("RGMS_SPM_RDP_SORT_EIG_BACKEND", "auto")).strip()
                        or "auto"
                    ),
                },
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"[FSL backward Entry 10 isolated] wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
