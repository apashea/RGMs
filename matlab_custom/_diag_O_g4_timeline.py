"""Timeline of O[0][3][1] mutations during full VB run."""
from __future__ import annotations

import copy
import sys

import numpy as np

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

events: list[str] = []
mi, o_idx, t_idx = 0, 3, 1


def _peek(bundle) -> str:
    try:
        v = bundle["O"][mi][o_idx][t_idx]
        a = np.asarray(v, dtype=float).ravel()
        return f"len={a.size} argmax={int(np.argmax(a)+1) if a.size else 0} head={a[:4].tolist()}"
    except Exception as e:
        return f"err={e}"


def wrap(name, fn):
    def inner(*a, **k):
        before = _peek(a[1]) if len(a) > 1 and isinstance(a[1], dict) and "O" in a[1] else "?"
        out = fn(*a, **k)
        after = _peek(a[1]) if len(a) > 1 and isinstance(a[1], dict) and "O" in a[1] else "?"
        if before != after:
            events.append(f"{name}: {before} -> {after}")
        return out

    return inner


def main() -> None:
    vb._vb_generate_outcomes_if_options_o = wrap(
        "generate", vb._vb_generate_outcomes_if_options_o
    )
    vb._vb_hierarchical_subordinate_outcomes = wrap(
        "hier", vb._vb_hierarchical_subordinate_outcomes
    )
    vb.spm_MDP_VB_XXX(
        spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp())),
        {},
        monitoring=False,
        dump_subentries=False,
        reuse_matlab_draws=True,
    )
    print(f"events at O[0][3][1]: {len(events)}")
    for e in events[:30]:
        print(e)
    if len(events) > 30:
        print("...")
        for e in events[-10:]:
            print(e)


if __name__ == "__main__":
    main()
