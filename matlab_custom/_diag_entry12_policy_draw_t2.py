"""Find replay draw index for parent policy sample at generation t=2."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_VB_XXX import _vb_load_matlab_rand_buf, spm_MDP_VB_XXX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

_LAST: list[Any] = [None]


class _AuditingRandReplay(vb._VbMatlabRandReplay):
    def __init__(self, buf: np.ndarray) -> None:
        super().__init__(buf)
        self.draw_index = 0
        self.history: list[tuple[int, float]] = []
        _LAST[0] = self

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        v = float(super()._shim(*args, **kwargs))
        self.history.append((self.draw_index, v))
        self.draw_index += 1
        return v


def main() -> int:
    buf = np.asarray(_vb_load_matlab_rand_buf(), dtype=np.float64).ravel()
    policy_events: list[dict[str, Any]] = []
    orig_prior = vb._vb_prior_QP_paths_states_one_model

    def _prior_hook(mi, bundle, t_idx, Pu_vec):
        ar = _LAST[0]
        i0 = ar.draw_index if ar is not None else -1
        orig_prior(mi, bundle, t_idx, Pu_vec)
        i1 = ar.draw_index if ar is not None else -1
        if mi == 0 and t_idx == 1:
            pu = np.asarray(Pu_vec, dtype=np.float64).ravel()
            k_pol = int(bundle.get("_entry12_last_k_pol", -1))
            r_used = float(buf[i0]) if 0 <= i0 < buf.size else None
            policy_events.append(
                {
                    "draw_start": i0,
                    "draw_end": i1,
                    "k_policy": k_pol,
                    "Pu_uniform": bool(np.allclose(pu, pu[0] if pu.size else 0)),
                    "Pu": pu.tolist(),
                    "r_at_draw_start": r_used,
                    "k_from_buf_at_start": int(np.flatnonzero(r_used < np.cumsum(pu))[0] + 1)
                    if r_used is not None and pu.size
                    else None,
                    "r_at_next": float(buf[i0 + 1]) if i0 + 1 < buf.size else None,
                    "k_from_buf_at_next": int(np.flatnonzero(float(buf[i0 + 1]) < np.cumsum(pu))[0] + 1)
                    if i0 + 1 < buf.size and pu.size
                    else None,
                }
            )

    rdp = _load_xxx12_rdp()
    vb_mod = vb
    orig_cls = vb._VbMatlabRandReplay
    vb._VbMatlabRandReplay = _AuditingRandReplay
    vb_mod._VbMatlabRandReplay = _AuditingRandReplay
    vb._vb_prior_QP_paths_states_one_model = _prior_hook
    try:
        spm_MDP_VB_XXX(
            rdp,
            {},
            monitoring=False,
            dump_subentries=False,
            reuse_matlab_draws=True,
        )
    finally:
        vb._VbMatlabRandReplay = orig_cls
        vb_mod._VbMatlabRandReplay = orig_cls
        vb._vb_prior_QP_paths_states_one_model = orig_prior

    ar = _LAST[0]
    out = {
        "K": int(buf.size),
        "total_draws": int(ar.draw_index) if ar is not None else None,
        "policy_events_parent_m1_t2": policy_events,
        "mat_k_policy_t2_expected": 2,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
