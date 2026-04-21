"""Compare spm_parents(id,g,s_col) MATLAB vs Python for Pong GDP."""
from pathlib import Path

import numpy as np
import matlab.engine

from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from python_src.toolbox.DEM.spm_parents import spm_parents


def main():
    root = Path(__file__).resolve().parents[1]
    dem = root / "matlab_src" / "toolbox" / "DEM"
    eng = matlab.engine.start_matlab()
    eng.addpath(str(root / "matlab_src"), nargout=0)
    eng.addpath(str(dem), nargout=0)
    eng.cd(str(dem), nargout=0)

    eng.eval(
        "rng(0); [GDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,1,0);",
        nargout=0,
    )
    ng = int(np.asarray(eng.eval("numel(GDP.A)"), dtype=int).item())
    s1 = np.asarray(eng.eval("GDP.s(:,1)"), dtype=float).ravel()

    gdp = spm_MDP_pong(4, 4, 1, 1, 0)[0]
    py_id = gdp["id"]

    mism = []
    for g in range(1, ng + 1):
        eng.eval(f"jm = []; im = []; [jm,im] = spm_parents(GDP.id,{g},GDP.s(:,1));", nargout=0)
        jm = np.asarray(eng.eval("jm"), dtype=float)
        im_m = np.asarray(eng.eval("im"), dtype=float)

        jp, ip = spm_parents(py_id, g, s1)

        def norm_i(x):
            return np.asarray(x, dtype=float).ravel(order="F")

        if jm.shape != np.asarray(jp).shape or not np.allclose(jm, jp):
            mism.append(("j", g, jm, jp))
        if norm_i(im_m).shape != norm_i(ip).shape or not np.allclose(
            norm_i(im_m), norm_i(ip)
        ):
            mism.append(("i", g, norm_i(im_m), norm_i(ip)))

    print("s column", s1)
    if mism:
        for tag, g, a, b in mism[:20]:
            print(f"mismatch {tag} g={g}\n matlab {a}\n python {b}")
    else:
        print("spm_parents: all g match for t=1 states")

    eng.quit()


if __name__ == "__main__":
    main()
