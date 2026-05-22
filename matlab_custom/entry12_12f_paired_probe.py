"""Step 1 plan: paired parent t=1 probe (Python replay + MATLAB entry12_dump)."""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp


def _run_python_probe() -> dict:
    vb._PROBE_12F_PARENT = None
    os.environ["RGMS_PROBE_12F_PARENT_T1"] = "1"
    try:
        rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
        pdp = vb.spm_MDP_VB_XXX(
            rdp, {}, monitoring=False, dump_subentries=False, reuse_matlab_draws=True
        )
        probe = vb._PROBE_12F_PARENT or {}
    finally:
        os.environ.pop("RGMS_PROBE_12F_PARENT_T1", None)
        vb._PROBE_12F_PARENT = None

    import numpy as np

    g1 = float(np.asarray(pdp["G"][0], dtype=np.float64).ravel()[0])
    out = dict(probe)
    out["PDP_G1"] = g1
    out["lane"] = "python replay dump_subentries=False"
    return out


def _run_matlab_probe() -> dict:
    import matlab.engine
    import numpy as np

    eng = matlab.engine.start_matlab()
    try:
        for p in (
            r"C:\Users\andre\Documents\MATLAB\spm-main",
            r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM",
            str(ROOT / "matlab_src" / "toolbox" / "DEM"),
            str(ROOT / "matlab_custom" / "entry12"),
        ):
            eng.addpath(p, nargout=0)
        mat = str(ROOT / "tests/oracle/toolbox/DEM/fixtures/DEMAtariIII_XXX_12_rdp.mat").replace(
            "\\", "/"
        )
        eng.eval(
            "global RGMS_PROBE_12F; RGMS_PROBE_12F = struct('probe_induction', true);",
            nargout=0,
        )
        eng.eval(f"load('{mat}');", nargout=0)
        eng.eval("rdp = spm_MDP_checkX(RDP);", nargout=0)
        eng.eval(
            "OPTIONS = struct('B',0,'C',0,'D',0,'N',0,'O',1,'P',0,'Y',1); "
            "dumpSpec = struct('enabled', false); "
            "pdp = spm_MDP_VB_XXX_entry12_dump(rdp, OPTIONS, dumpSpec);",
            nargout=0,
        )
        g1 = float(np.asarray(eng.eval("pdp.G{1}(1)", nargout=1)).reshape(-1)[0])
        scalar_fields = [
            "G_before_iH",
            "ih_term",
            "G_after_iH",
            "spm_dot_R_Q",
            "G_after_dot",
            "dot_manual_RQ",
            "R_max",
            "R_sum",
            "ind_branch",
            "hid_all_zero",
            "D_is_scalar",
            "D_nnz",
            "Nh",
            "R_nnz_ind",
        ]
        out: dict = {"PDP_G1": g1, "lane": "matlab entry12_dump native RNG"}
        for f in scalar_fields:
            try:
                if f == "ind_branch":
                    out[f] = str(eng.eval(f"RGMS_PROBE_12F.{f}", nargout=1))
                else:
                    out[f] = float(eng.eval(f"RGMS_PROBE_12F.{f}", nargout=1))
            except Exception:
                out[f] = float("nan") if f != "ind_branch" else ""
        for f in ("R_shape", "r_factors", "Q_at_R_nz", "hid_shape"):
            try:
                val = eng.eval(f"RGMS_PROBE_12F.{f}", nargout=1)
                out[f] = _jsonify(val)
            except Exception:
                out[f] = None
        try:
            out["R_nz_idx"] = _jsonify(
                eng.eval("RGMS_PROBE_12F.R_nz_idx(:)'", nargout=1)
            )
        except Exception:
            out["R_nz_idx"] = None
        for fi in range(1, 9):
            for prefix in ("Qf_len_f", "Qf_max_f", "Pf_sum_f"):
                key = f"{prefix}{fi}"
                try:
                    out[key] = float(eng.eval(f"RGMS_PROBE_12F.{key}", nargout=1))
                except Exception:
                    pass
        return out
    finally:
        eng.quit()


def _jsonify(obj: object) -> object:
    import numpy as np

    try:
        arr = np.asarray(obj)
        if arr.size == 1:
            return float(arr.reshape(-1)[0])
        if arr.size > 1:
            return arr.tolist()
    except (TypeError, ValueError):
        pass
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, dict):
        return {str(k): _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(x) for x in obj]
    return obj


def main() -> None:
    import numpy as np

    py = _run_python_probe()
    print("=== Python (rand replay) ===")
    print(json.dumps(_jsonify(py), indent=2))
    print("=== MATLAB (native RNG, entry12_dump) ===")
    mat = _run_matlab_probe()
    print(json.dumps(_jsonify(mat), indent=2))
    print("=== Delta (PY - MAT) ===")
    skip = {"lane", "R_shape", "r_factors", "R_nz_idx", "Q_at_R_nz", "done"}
    for k in sorted(set(py) | set(mat)):
        if k in skip:
            continue
        if k in py and k in mat:
            try:
                d = float(py[k]) - float(mat[k])
                print(f"  {k}: {d:+.6f}")
            except (TypeError, KeyError, ValueError):
                pass
    out_path = ROOT / "matlab_custom" / "entry12_12f_paired_probe_results.json"
    out_path.write_text(
        json.dumps(_jsonify({"python": py, "matlab": mat}), indent=2), encoding="utf-8"
    )
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
