#!/usr/bin/env python3
"""Phase C — push Python forwards inputs at t=41 into MATLAB and rematch EFE.

If MATLAB reproduces Python G (~-26.56/-29.37), forwards algebra matches and the
authority gap is inputs/path. If MATLAB reproduces fence G (~-36.78/-29.60) on the
same inputs, Python term wiring is wrong.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def main() -> int:
    from scipy.io import savemat

    inp_path = _REPO / "matlab_custom" / "optim1full_call4_forwards_t41_inputs.pkl"
    out_mat = _REPO / "matlab_custom" / "optim1full_call4_forwards_t41_inputs.mat"
    out_json = _REPO / "matlab_custom" / "optim1full_call4_matlab_efe_from_py_inputs.json"
    report = _REPO / "matlab_custom" / "optim1full_call4_matlab_efe_from_py_inputs_diag.txt"
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        lines.append(msg)

    inp = pickle.load(inp_path.open("rb"))
    # Pack for MATLAB: BP is Ns x Ns x Nk; cells for A/C/K.
    BP0 = np.stack([inp["BP"][0][k] for k in range(len(inp["BP"][0]))], axis=2)
    P = np.asarray(inp["P"][0], dtype=np.float64)
    H = np.asarray(inp["H"][0], dtype=np.float64)
    R = np.asarray(inp["R"], dtype=np.float64) if inp["R"] is not None else np.zeros((0, 0))
    A = np.empty((len(inp["A"]),), dtype=object)
    C = np.empty((len(inp["C"]),), dtype=object)
    K = np.empty((len(inp["K"]),), dtype=object)
    for g, a in enumerate(inp["A"]):
        A[g] = np.asarray(a, dtype=np.float64)
    for g, c in enumerate(inp["C"]):
        C[g] = np.zeros((0, 0)) if c is None else np.asarray(c, dtype=np.float64)
    for g, k in enumerate(inp["K"]):
        K[g] = np.zeros((0, 0)) if k is None else np.asarray(k, dtype=np.float64)

    id_g = np.empty((len(inp["id_g"]),), dtype=object)
    for i, gvec in enumerate(inp["id_g"]):
        id_g[i] = np.asarray(gvec, dtype=np.float64).reshape(1, -1)

    savemat(
        out_mat,
        {
            "P": P,
            "H": H,
            "BP": BP0,
            "R": R,
            "A": A,
            "C": C,
            "K": K,
            "id_g": id_g,
            "id_iH": np.asarray(inp["id_iH"], dtype=np.float64).reshape(1, -1),
            "id_fu": np.asarray(inp["id_fu"], dtype=np.float64).reshape(1, -1),
            "matlab_G_target": np.asarray(
                [-36.7786396005819, -29.602188814778557, -29.602188814604503, -29.602188814778557]
            ),
            "python_G": np.asarray(
                [-26.55729055047906, -29.36532157385193, -29.36532157381481, -29.36532157385193]
            ),
        },
        do_compression=True,
    )
    log(f"wrote {out_mat}")

    eng_script = _REPO / "matlab_custom" / "optim1full" / "diag_call4_efe_from_py_inputs.m"
    eng_script.write_text(
        r"""
% diag_call4_efe_from_py_inputs.m — EFE rematch on Python-exported inputs at t=41
repoRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
inMat = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_forwards_t41_inputs.mat');
outJson = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_matlab_efe_from_py_inputs.json');
S = load(inMat);
P = S.P; H = S.H; BP = S.BP; R = S.R; A = S.A; C = S.C; K = S.K;
id_g = S.id_g; id_iH = S.id_iH;
Nk = size(BP, 3); Ni = numel(id_g);
G = zeros(Nk, Ni);
No = zeros(1, Ni);
terms = struct();
for k = 1:Nk
    Q = BP(:,:,k) * P;
    % iH
    ih = 0;
    for f = id_iH
        ih = ih + Q'*(spm_log(Q) - spm_log(H));
    end
    G(k,:) = G(k,:) - ih;
    % risk
    if numel(R)
        G(k,:) = G(k,:) + R*Q;  % R is 1xNs row for single factor
    end
    after_risk = G(k,1);
    ent_s = 0; cost_s = 0; amb_s = 0;
    for i = 1:Ni
        gi = id_g{i};
        for g = gi
            qo = A{g} * Q;
            No(i) = No(i) + spm_log(numel(qo));
            ent = qo'*spm_log(qo);
            G(k,i) = G(k,i) - ent;
            ent_s = ent_s + ent;
            if numel(C{g})
                U = spm_log(C{g});
                cost = qo'*U;
                G(k,i) = G(k,i) + cost;
                cost_s = cost_s + cost;
            end
            if numel(K{g})
                amb = K{g}*Q;  % K is No x Ns typically; use as row? —— use spm_dot-like: K'*? 
                % In .m: spm_dot(K{m,g},Q(j)) for tensors. Here K is likelihood ambiguity array.
                % Prefer: if size(K{g},2)==size(Q,1), amb = K{g}*Q then sum? 
                % Actual MATLAB: G += spm_dot(K,Q(j)). For matrix (No x Ns) and vector Q, 
                % spm_dot contracts state dim → vector over outcomes then? Check lengths.
                try
                    amb = spm_dot(K{g}, Q);
                catch
                    amb = sum(K{g} * Q);
                end
                if ~isscalar(amb), amb = sum(amb(:)); end
                G(k,i) = G(k,i) + amb;
                amb_s = amb_s + amb;
            end
        end
    end
    terms(k).ih = ih;
    terms(k).after_risk = after_risk;
    terms(k).ent = ent_s;
    terms(k).cost = cost_s;
    terms(k).amb = amb_s;
    terms(k).after_outcomes = G(k,1);
end
G = plus(G, No);
G = sum(G, 2);

fid = fopen(outJson,'w');
fprintf(fid,'{\n  \"G\": [');
for i=1:numel(G)
  if i>1, fprintf(fid,', '); end
  fprintf(fid,'%.17g', G(i));
end
fprintf(fid,'],\n  \"No\": [');
for i=1:numel(No)
  if i>1, fprintf(fid,', '); end
  fprintf(fid,'%.17g', No(i));
end
fprintf(fid,'],\n  \"terms\": [\n');
for k=1:Nk
  if k>1, fprintf(fid,',\n'); end
  fprintf(fid,'    {\"k\":%d,\"ih\":%.17g,\"after_risk\":%.17g,\"ent\":%.17g,\"cost\":%.17g,\"amb\":%.17g,\"after_outcomes\":%.17g}', ...
    k-1, terms(k).ih, terms(k).after_risk, terms(k).ent, terms(k).cost, terms(k).amb, terms(k).after_outcomes);
end
fprintf(fid,'\n  ]\n}\n');
fclose(fid);
fprintf(1,'[diag] wrote %s G=%s\n', outJson, mat2str(G',6));
""",
        encoding="utf-8",
    )
    log(f"wrote {eng_script}")

    import matlab.engine

    eng = matlab.engine.start_matlab()
    try:
        eng.cd(str(_REPO / "matlab_custom" / "optim1full"))
        # Ensure SPM + spm_log / spm_dot on path
        eng.addpath(eng.genpath(str(_REPO / "matlab_src")), nargout=0)
        eng.addpath(r"C:\Users\andre\Documents\MATLAB\spm-main", nargout=0)
        eng.diag_call4_efe_from_py_inputs(nargout=0)
    finally:
        eng.quit()

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    g = np.asarray(payload["G"], float).ravel()
    log(f"MATLAB-on-py-inputs G={g.tolist()}")
    log(f"python_G         ={[-26.55729055047906, -29.36532157385193, -29.36532157381481, -29.36532157385193]}")
    log(f"fence matlab_G   ={[-36.7786396005819, -29.602188814778557, -29.602188814604503, -29.602188814778557]}")
    d_py = g - np.asarray([-26.55729055047906, -29.36532157385193, -29.36532157381481, -29.36532157385193])
    d_fence = g - np.asarray([-36.7786396005819, -29.602188814778557, -29.602188814604503, -29.602188814778557])
    log(f"vs python maxabs={float(np.max(np.abs(d_py)))}")
    log(f"vs fence  maxabs={float(np.max(np.abs(d_fence)))}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
