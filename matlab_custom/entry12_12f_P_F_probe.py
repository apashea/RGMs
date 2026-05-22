"""Log parent m=1 P_row sizes and F_elbo at t=1..3 (Entry 12F MDP.F first red)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_PROBE: dict[str, object] = {}
_ORIG = vb.spm_forwards


def _hook(*args, **kw):
    O, P, A, B, C, H, K, W, I, t, T, N, m, id_list, pA, qa = args
    if vb._VB_TIMING_DEPTH == 1 and int(m) == 1 and int(t) in (1, 2, 3):
        mi = 0
        pre = [int(np.asarray(P[mi][f][t - 1]).size) for f in range(len(P[mi]))]
        _PROBE.setdefault(f"t{int(t)}_pre", {})["P_sizes"] = pre
    G, P2, f_fwd, id2, pa = _ORIG(*args, **kw)
    if vb._VB_TIMING_DEPTH == 1 and int(m) == 1 and int(t) in (1, 2, 3):
        mi = 0
        sizes = [int(np.asarray(P2[mi][f][t - 1]).size) for f in range(len(P2[mi]))]
        _PROBE[f"t{int(t)}"] = {
            "n_factors_shell": len(P2[mi]),
            "P_sizes": sizes,
            "F_forwards": float(f_fwd),
            "F_traj_slot": float(np.asarray(vb._PROBE_F_TRAJ.get(t - 1, np.nan))),
        }
    return G, P2, f_fwd, id2, pa


def main() -> None:
    vb._PROBE_F_TRAJ = {}
    _orig_assign = None

    def _after_forwards(mi, bundle, t_m, t_idx, G_m, alpha):
        if vb._VB_TIMING_DEPTH == 1 and mi == 0 and t_idx in (0, 1, 2):
            vb._PROBE_F_TRAJ[t_idx] = float(bundle.get("_last_F_elbo", np.nan))

    # patch loop to capture F_elbo
    orig_loop = vb._vb_run_partial_t_loop

    def _loop(models, bundle, alpha, recurse_partial, *, reuse_matlab_draws=False):
        orig_sf = vb.spm_forwards

        def _sf(*a, **k):
            g, p, f, idl, pa = orig_sf(*a, **k)
            if vb._VB_TIMING_DEPTH == 1:
                bundle["_last_F_elbo"] = float(f)
            return g, p, f, idl, pa

        vb.spm_forwards = _sf
        try:
            orig_loop(models, bundle, alpha, recurse_partial, reuse_matlab_draws=reuse_matlab_draws)
        finally:
            vb.spm_forwards = orig_sf

    vb._vb_run_partial_t_loop = _loop
    vb.spm_forwards = _hook
    try:
        vb.spm_MDP_VB_XXX(
            spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb.spm_forwards = _ORIG
        vb._vb_run_partial_t_loop = orig_loop

    out = ROOT / "matlab_custom" / "entry12_12f_P_F_probe.json"
    out.write_text(json.dumps(_PROBE, indent=2), encoding="utf-8")
    print(json.dumps(_PROBE, indent=2))


if __name__ == "__main__":
    main()
