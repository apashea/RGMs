"""Log spm_sample calls with global draw index near parent t=2 policy (Call 2 bisect)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.entry12_atari_calls import (
    entry12_load_vb_rand_buf_for_tag,
    entry12_resolve_run_tag,
    entry12_vb_oracle_flags,
    load_entry12_rdp_for_tag,
)
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX

_LAST: list[Any] = [None]
_LOG: list[dict[str, Any]] = []


class _AuditingRandReplay(vb._VbMatlabRandReplay):
    def __init__(self, buf: np.ndarray) -> None:
        super().__init__(buf)
        self.draw_index = 0
        _LAST[0] = self

    def _shim(self, *args: Any, **kwargs: Any) -> float:
        v = float(super()._shim(*args, **kwargs))
        self.draw_index += 1
        return v


def main() -> int:
    tag = entry12_resolve_run_tag()
    buf = entry12_load_vb_rand_buf_for_tag(tag)
    orig_sample = vb._spm_sample
    orig_prior = vb._vb_prior_QP_paths_states_one_model
    policy_hits: list[dict[str, Any]] = []

    def _logged_sample(p: Any) -> int:
        ar = _LAST[0]
        i0 = 0 if ar is None else ar.draw_index
        out = int(orig_sample(p))
        i1 = 0 if ar is None else ar.draw_index
        if 245 <= i0 <= 256 or 245 <= i1 <= 256:
            pa = np.asarray(p)
            nz = int(np.count_nonzero(pa)) if pa.size else 0
            flat = pa.ravel(order="F").tolist()
            _LOG.append(
                {
                    "draw_start": i0,
                    "draw_end": i1,
                    "n_draws": i1 - i0,
                    "dtype": str(pa.dtype),
                    "shape": list(pa.shape),
                    "nz": nz,
                    "is_bool": bool(pa.dtype == bool),
                    "vals": flat[:12],
                    "out": out,
                    "depth": int(vb._VB_TIMING_DEPTH),
                }
            )
        return out

    def _prior_hook(mi, bundle, t_idx, Pu_vec):
        ar = _LAST[0]
        i0 = ar.draw_index if ar is not None else -1
        orig_prior(mi, bundle, t_idx, Pu_vec)
        if mi == 0 and t_idx == 1:
            pu = np.asarray(Pu_vec, dtype=np.float64).ravel()
            policy_hits.append(
                {
                    "draw_start": i0,
                    "draw_end": ar.draw_index if ar is not None else i0,
                    "k_policy": int(bundle.get("_entry12_last_k_pol", -1)),
                    "Pu_len": int(pu.size),
                }
            )

    import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb_mod

    orig_cls = vb._VbMatlabRandReplay
    vb._VbMatlabRandReplay = _AuditingRandReplay
    vb_mod._VbMatlabRandReplay = _AuditingRandReplay
    vb._spm_sample = _logged_sample
    vb._vb_prior_QP_paths_states_one_model = _prior_hook
    try:
        flags = entry12_vb_oracle_flags(reuse_matlab_draws=True)
        spm_MDP_VB_XXX(load_entry12_rdp_for_tag(tag), {}, **flags)
    finally:
        vb._VbMatlabRandReplay = orig_cls
        vb_mod._VbMatlabRandReplay = orig_cls
        vb._spm_sample = orig_sample
        vb._vb_prior_QP_paths_states_one_model = orig_prior

    out = {
        "tag": tag,
        "K": int(buf.size),
        "buf_252": float(buf[252]) if buf.size > 252 else None,
        "buf_253": float(buf[253]) if buf.size > 253 else None,
        "window_log": _LOG,
        "policy_hits": policy_hits,
    }
    out_path = ROOT / "matlab_custom" / "_diag_entry12_sample_window.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
