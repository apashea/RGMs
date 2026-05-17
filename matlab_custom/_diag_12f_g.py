"""One-off 12F G decomposition at parent t=1."""
import copy
import os

import numpy as np

os.environ["RGMS_ENTRY12_DUMP_SUBENTRIES"] = "0"
os.environ["RGMS_DIAG_12F_G"] = "1"

from python_src.toolbox.DEM.spm_MDP_checkX import spm_MDP_checkX
import python_src.toolbox.DEM.spm_MDP_VB_XXX as vb
from tests.oracle.toolbox.DEM.test_DEM_AtariIII_XXX_12 import _load_xxx12_rdp

rdp = spm_MDP_checkX(copy.deepcopy(_load_xxx12_rdp()))
orig_fwd = vb.spm_forwards
orig_bel = vb._vb_belief_after_forwards
state: dict = {"n": 0}


def fwd(*a, **kw):
    G, P, F, id_l, Pa = orig_fwd(*a, **kw)
    return G, P, F, id_l, Pa


def bel(mi, bundle, t_m, t_idx, G_m, alpha):
    Gw, Z = orig_bel(mi, bundle, t_m, t_idx, G_m, alpha)
    if t_m == 1 and mi == 0 and np.asarray(Gw).size:
        print("belief out Gw", np.asarray(Gw, float).ravel()[:3])
    return Gw, Z


vb.spm_forwards = fwd
vb._vb_belief_after_forwards = bel
opts = vb._default_options_vb()
opts["monitoring"] = 0
vb.spm_MDP_VB_XXX(rdp, options=opts, reuse_matlab_draws=True)
print("mat target G ~", -32.40546511)
