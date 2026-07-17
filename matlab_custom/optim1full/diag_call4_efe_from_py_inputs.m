% diag_call4_efe_from_py_inputs.m — EFE rematch on Python-exported inputs at t=41
% Faithful to spm_MDP_VB_XXX.m spm_forwards policy loop (single-factor Atari call4).
repoRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
inMat = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_forwards_t41_inputs.mat');
outJson = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_matlab_efe_from_py_inputs.json');
S = load(inMat);
P = S.P; H = S.H; BP = S.BP; R = S.R; A = S.A; C = S.C; K = S.K;
id_g = S.id_g; id_iH = S.id_iH;
Nk = size(BP, 3); Ni = numel(id_g);
G = zeros(Nk, Ni);
terms = struct();
for k = 1:Nk
    Q = BP(:,:,k) * P;
    ih = 0;
    for f = id_iH(:)'
        ih = ih + Q' * (spm_log(Q) - spm_log(H));
    end
    G(k,:) = G(k,:) - ih;
    if numel(R)
        % R is 1xNs (row); Q is Ns x 1 → scalar
        G(k,:) = G(k,:) + (R * Q);
    end
    after_risk = G(k,1);
    No = zeros(1, Ni);
    ent_s = 0; cost_s = 0; amb_s = 0;
    for i = 1:Ni
        gi = id_g{i};
        for g = gi(:)'
            qo = A{g} * Q;
            No(i) = No(i) + spm_log(numel(qo));
            ent = qo' * spm_log(qo);
            G(k,i) = G(k,i) - ent;
            ent_s = ent_s + ent;
            if numel(C{g})
                U = spm_log(C{g}(:));
                cost = qo' * U;
                G(k,i) = G(k,i) + cost;
                cost_s = cost_s + cost;
            end
            if numel(K{g})
                % MATLAB: G += spm_dot(K{m,g}, Q(j)); single parent factor
                amb = spm_dot(K{g}, {Q});
                if ~isscalar(amb)
                    amb = sum(amb(:));
                end
                G(k,i) = G(k,i) + amb;
                amb_s = amb_s + amb;
            end
        end
    end
    G(k,:) = G(k,:) + No;
    terms(k).ih = ih;
    terms(k).after_risk = after_risk;
    terms(k).ent = ent_s;
    terms(k).cost = cost_s;
    terms(k).amb = amb_s;
    terms(k).No = No(1);
    terms(k).after_outcomes_plus_No = G(k,1);
end
G = sum(G, 2);

fid = fopen(outJson, 'w');
fprintf(fid, '{\n  \"G\": [');
for i = 1:numel(G)
    if i > 1, fprintf(fid, ', '); end
    fprintf(fid, '%.17g', G(i));
end
fprintf(fid, '],\n  \"terms\": [\n');
for k = 1:Nk
    if k > 1, fprintf(fid, ',\n'); end
    fprintf(fid, ['    {\"k\":%d,\"ih\":%.17g,\"after_risk\":%.17g,\"ent\":%.17g,' ...
        '\"cost\":%.17g,\"amb\":%.17g,\"No\":%.17g,\"G\":%.17g}'], ...
        k-1, terms(k).ih, terms(k).after_risk, terms(k).ent, terms(k).cost, ...
        terms(k).amb, terms(k).No, terms(k).after_outcomes_plus_No);
end
fprintf(fid, '\n  ]\n}\n');
fclose(fid);
fprintf(1, '[diag] wrote %s G=%s\n', outJson, mat2str(G', 6));
