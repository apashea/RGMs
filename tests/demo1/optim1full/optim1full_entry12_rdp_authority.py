"""OPTIM1FULL — assemble Entry **12** RDP mats from Python authority via Engine overlay."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matlab.engine

_REPO = Path(__file__).resolve().parents[3]


def _posix(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/")


def _save_engine_rdp_v7(eng: matlab.engine.MatlabEngine, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    eng.eval(f"save('{_posix(out_path)}','RDP','-v7');", nargout=0)


def save_call2_rdp_from_authority_pre(
    eng: matlab.engine.MatlabEngine,
    *,
    pre_mat: Path,
    out_path: Path,
    c_val: float = 32.0,
    ns: float = 256.0,
    nt: int = 256,
) -> None:
    """NR game-1 call-2 RDP: overlay Python ``MDP_pre`` then MATLAB assembly."""
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat, load_ne_from_mat
    from tests.demo1.optim1full.optim1full_mdp_engine_io import overlay_full_py_mdp_to_engine

    mdp = load_mdp_from_mat(pre_mat, "MDP_pre_active_inference")
    ne = load_ne_from_mat(pre_mat, "Ne")
    eng.eval(f"load('{_posix(pre_mat)}','MDP_pre_active_inference','Ne');", nargout=0)
    overlay_full_py_mdp_to_engine(eng, mdp, "MDP_pre_active_inference")
    eng.eval(f"C = {float(c_val)}; NS = {float(ns)}; NT = {float(nt)}; Ne = {float(ne)};", nargout=0)
    eng.eval(
        "RDP = spm_set_goals(MDP_pre_active_inference, [2, 3], [C, -C]); "
        "RDP = spm_set_costs(RDP, [2, 3], [C, -C]); "
        "RDP = spm_mdp2rdp(RDP, 0, 1 / NS); "
        "RDP.T = fix(NT / Ne);",
        nargout=0,
    )
    _save_engine_rdp_v7(eng, out_path)


def save_call3_rdp_from_authority_post(
    eng: matlab.engine.MatlabEngine,
    *,
    post_mat: Path,
    out_path: Path,
    c_val: float = 32.0,
    ns: float = 256.0,
) -> None:
    """Post-NR call-3 RDP: overlay Python ``MDP_post_nr`` then Engine ``spm_RDP_sort`` path."""
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_mdp_engine_io import overlay_full_py_mdp_to_engine

    mdp = load_mdp_from_mat(post_mat, "MDP_post_nr")
    eng.eval(f"load('{_posix(post_mat)}','MDP_post_nr');", nargout=0)
    overlay_full_py_mdp_to_engine(eng, mdp, "MDP_post_nr")
    eng.eval(f"C = {float(c_val)}; NS = {float(ns)};", nargout=0)
    eng.eval(
        "RDP = spm_RDP_sort(MDP_post_nr); "
        "RDP = spm_set_goals(RDP, [2, 3], [C, -C]); "
        "RDP = spm_set_costs(RDP, [2, 3], [C, -C]); "
        "RDP = spm_mdp2rdp(RDP, 0, 1 / NS); "
        "RDP.T = 128;",
        nargout=0,
    )
    _save_engine_rdp_v7(eng, out_path)


def save_call4_rdp_from_authority_post(
    eng: matlab.engine.MatlabEngine,
    *,
    post_mat: Path,
    out_path: Path,
    c_val: float = 32.0,
    ns: float = 256.0,
) -> None:
    """Post-NR call-4 RDP: overlay + sort + ``spm_RDP_MI``."""
    from tests.demo1.optim1full.optim1full_mi_boundary import load_mdp_from_mat
    from tests.demo1.optim1full.optim1full_mdp_engine_io import overlay_full_py_mdp_to_engine

    mdp = load_mdp_from_mat(post_mat, "MDP_post_nr")
    eng.eval(f"load('{_posix(post_mat)}','MDP_post_nr');", nargout=0)
    overlay_full_py_mdp_to_engine(eng, mdp, "MDP_post_nr")
    eng.eval(f"C = {float(c_val)}; NS = {float(ns)};", nargout=0)
    eng.eval(
        "RDP = spm_RDP_sort(MDP_post_nr); "
        "RDP = spm_RDP_MI(RDP); "
        "RDP = spm_set_goals(RDP, [2, 3], [C, -C]); "
        "RDP = spm_set_costs(RDP, [2, 3], [C, -C]); "
        "RDP = spm_mdp2rdp(RDP, 0, 1 / NS); "
        "RDP.T = 128;",
        nargout=0,
    )
    _save_engine_rdp_v7(eng, out_path)


def save_all_entry12_rdp_mats_from_authority(
    eng: matlab.engine.MatlabEngine,
    *,
    fixtures: Path,
    pre_mat: Path,
    post_mat: Path,
    c_val: float,
    ns: float,
) -> dict[str, Path]:
    from tests.demo1.optim1full.entry12_atari_calls_optim1full import (
        ENTRY12_OPTIM1FULL_CALL2_TAG,
        ENTRY12_OPTIM1FULL_CALL3_TAG,
        ENTRY12_OPTIM1FULL_CALL4_TAG,
        optim1full_entry12_atari_call_rdp_mat_path,
    )

    out: dict[str, Path] = {}
    specs = (
        (ENTRY12_OPTIM1FULL_CALL2_TAG, save_call2_rdp_from_authority_pre, {"pre_mat": pre_mat}),
        (ENTRY12_OPTIM1FULL_CALL3_TAG, save_call3_rdp_from_authority_post, {"post_mat": post_mat}),
        (ENTRY12_OPTIM1FULL_CALL4_TAG, save_call4_rdp_from_authority_post, {"post_mat": post_mat}),
    )
    for tag, fn, kw in specs:
        path = optim1full_entry12_atari_call_rdp_mat_path(tag)
        fn(eng, out_path=path, c_val=c_val, ns=ns, **kw)
        out[tag] = path
        print(f"[optim1full_entry12_rdp] wrote {path}", flush=True)
    return out
