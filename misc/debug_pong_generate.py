"""Debug script: compare GDP / PK / rollout vs MATLAB for pong + generate."""
from pathlib import Path
from unittest.mock import patch

import numpy as np

from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong


def main():
    root = Path(__file__).resolve().parents[1]
    import matlab.engine

    eng = matlab.engine.start_matlab()
    dem = root / "matlab_src" / "toolbox" / "DEM"
    eng.addpath(str(dem), nargout=0)
    eng.cd(str(dem), nargout=0)

    eng.eval(
        "rng(0); "
        "[GDP,hid,cid,con,RGB,nP] = spm_MDP_pong(4,4,1,1,0); "
        "GDP.T = 4; GDP.tau = 1;",
        nargout=0,
    )

    ng_m = int(np.asarray(eng.eval("numel(GDP.A)"), dtype=int).item())
    nf_m = int(np.asarray(eng.eval("numel(GDP.B)"), dtype=int).item())
    u_any = np.asarray(eng.eval("any(GDP.U,1)"), dtype=float).ravel()
    npm = int(np.asarray(eng.eval(
        "u = spm_combinations(cellfun(@(x) size(GDP.B{x},3), num2cell(find(any(GDP.U,1))))); "
        "Np = size(u,1)"
    ), dtype=int).item())

    # Recompute Np like MATLAB generate
    eng.eval(
        "k = find(any(GDP.U,1)); "
        "Nu_mk = cellfun(@(x) size(GDP.B{x},3), num2cell(k)); "
        "u = spm_combinations(Nu_mk); "
        "V = zeros(size(u,1), numel(GDP.B)); "
        "V(:,k) = u; "
        "Np_real = size(V,1);",
        nargout=0,
    )
    np_real = int(np.asarray(eng.eval("Np_real"), dtype=int).item())

    tau = float(np.asarray(eng.eval("GDP.tau"), dtype=float).item())
    eng.eval(
        f"PK = (1 - 1/{tau})*eye(Np_real,Np_real) + (1/{tau})/Np_real; "
        "PK = spm_norm(PK);",
        nargout=0,
    )
    pk_m = np.asarray(eng.eval("PK"), dtype=float)

    print("MATLAB Ng", ng_m, "Nf", nf_m, "Np", np_real, "tau", tau)
    print("MATLAB any(U,1)", u_any)
    print("MATLAB PK first col", pk_m[:, 0].ravel())

    gdp = spm_MDP_pong(4, 4, 1, 1, 0)[0]
    gdp["T"] = 4.0
    gdp["tau"] = 1.0

    U = np.asarray(gdp["U"], dtype=float)
    u_row = np.any(U, axis=0)
    from python_src.spm_combinations import spm_combinations

    k_list = np.flatnonzero(u_row) + 1
    B = gdp["B"]
    nu_mk = [
        int(np.asarray(B[int(i) - 1]).shape[2])
        if np.asarray(B[int(i) - 1]).ndim >= 3
        else 1
        for i in k_list.tolist()
    ]
    u_mat = spm_combinations(np.asarray(nu_mk, dtype=np.float64))
    vpy = np.zeros((u_mat.shape[0], len(B)), dtype=np.float64)
    for j, col in enumerate(k_list.tolist()):
        vpy[:, int(col) - 1] = u_mat[:, j]
    npm_py = vpy.shape[0]
    pk_py = (1.0 - 1.0 / tau) * np.eye(npm_py) + (1.0 / tau) / npm_py
    pk_py = pk_py / pk_py.sum(axis=0, keepdims=True)
    pk_py = np.nan_to_num(pk_py, nan=1.0 / pk_py.shape[0])

    print("Python Np", npm_py, "any(U,1)", u_row.astype(float))
    print("Python PK first col", pk_py[:, 0])

    eng.quit()

    eng = matlab.engine.start_matlab()
    eng.addpath(str(dem), nargout=0)
    eng.cd(str(dem), nargout=0)
    eng.eval(f"rng(0); rgms_rand_buf = rand(64, 1);", nargout=0)
    rand_seq = np.asarray(eng.eval("rgms_rand_buf"), dtype=float).ravel().tolist()
    eng.quit()

    with patch("numpy.random.rand", side_effect=rand_seq):
        pdp = spm_MDP_generate(gdp)

    print("Python s:\n", np.asarray(pdp["s"], dtype=float))


if __name__ == "__main__":
    main()
