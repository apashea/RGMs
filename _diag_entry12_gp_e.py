"""One-off diagnostic: inspect MATLAB rgms_rdp11.MDP.E before VB (Entry 12 capture blocker)."""
from __future__ import annotations

import matlab.engine
from pathlib import Path

from tests.oracle.toolbox.DEM.test_DEM_AtariIII_entry10 import (
    _matlab_build_entry10_training_end_boundary,
    _matlab_run_entry10_sort_goals_and_P,
)


def main() -> None:
    repo = Path(__file__).resolve().parent
    dem_path = repo / "matlab_src" / "toolbox" / "DEM"
    eng = matlab.engine.start_matlab()
    eng.addpath(str(repo), nargout=0)
    eng.addpath(str(repo / "matlab_src"), nargout=0)
    eng.addpath(str(dem_path), nargout=0)
    eng.addpath("c:/Users/andre/Documents/MATLAB/spm-main/toolbox/DEM", nargout=0)
    old_cd = eng.pwd(nargout=1)
    eng.cd(str(dem_path), nargout=0)
    try:
        training_t, n_outer = 10000, 2
        _matlab_build_entry10_training_end_boundary(eng, training_t, n_outer)
        _matlab_run_entry10_sort_goals_and_P(eng)
        eng.eval(
            "rgms_mdp11_costs = spm_set_costs(rgms_mdp10_goals,[2,3],[C,-C]); "
            "rgms_rdp11 = spm_mdp2rdp(rgms_mdp11_costs); rgms_rdp11.T = 64; ",
            nargout=0,
        )
        eng.eval(
            "disp('fields rgms_rdp11:'); disp(fieldnames(rgms_rdp11)); "
            "disp('fields MDP:'); disp(fieldnames(rgms_rdp11.MDP)); ",
            nargout=0,
        )
        has_e = bool(eng.eval("isfield(rgms_rdp11,'E')"))
        has_e_mdp = bool(eng.eval("isfield(rgms_rdp11.MDP,'E')"))
        print(f"isfield(rdp11,'E')={has_e} isfield(rdp11.MDP,'E')={has_e_mdp}")
        eng.eval("tmp = rgms_rdp11;", nargout=0)
        if bool(eng.eval("isfield(tmp,'E')")):
            expr = "tmp"
        elif bool(eng.eval("isfield(tmp.MDP,'E')")):
            expr = "tmp.MDP"
            eng.eval("tmp = rgms_rdp11.MDP;", nargout=0)
        else:
            print("No E field on rdp11 or rdp11.MDP")
            expr = ""
        if expr:
            nf = int(eng.eval(f"numel({expr}.E)"))
            print(f"numel({expr}.E) = {nf}")
            for f in range(1, nf + 1):
                cls = str(eng.eval(f"class({expr}.E{{{f}}})"))
                sz = eng.eval(f"size({expr}.E{{{f}}})")
                is_log = bool(eng.eval(f"isa({expr}.E{{{f}}},'logical')"))
                any_v = bool(eng.eval(f"any({expr}.E{{{f}}}(:))"))
                print(f"  E{{{f}}}: class={cls} logical={is_log} any={any_v} size={sz}")
            eng.eval(f"pu = spm_norm({expr}.E{{1}});", nargout=0)
            pu_cls = str(eng.eval("class(pu)"))
            print(f"spm_norm(E{{1}}) class={pu_cls}")
        eng.eval(
            "try, spm_MDP_VB_XXX(rgms_rdp11); catch ME, disp(getReport(ME)); end;",
            nargout=0,
        )
    finally:
        eng.cd(old_cd, nargout=0)
        eng.quit()


if __name__ == "__main__":
    main()
