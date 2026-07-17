% patch_entry6_authority_to_pre_entry10_mat.m
%
% Append Entry 6 authority variables to an existing
% DEMAtariIII_fsl_backward_MDP_pre_entry10.mat (rng(2) ledger).
% Run once after extending dump_MDP_pre_entry10.m, or when the .mat lacks entry6_*.
%
%   matlab -batch "cd('...\matlab_custom\fsl_backward'); patch_entry6_authority_to_pre_entry10_mat;"

function patch_entry6_authority_to_pre_entry10_mat()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
outDir = demo1_fixtures_dir(repoRoot);
outMat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry10.mat');
if ~isfile(outMat)
    error('Missing %s — run dump_MDP_pre_entry10.m first.', outMat);
end
S = load(outMat);
if ~isfield(S, 'PDP_o') || ~isfield(S, 'GDP_id_reward')
    error('%s missing PDP_o / GDP_id_* — re-run dump_MDP_pre_entry10.m.', outMat);
end
Ne = S.Ne;
PDP_o = S.PDP_o;
id.reward = S.GDP_id_reward;
id.contraint = S.GDP_id_contraint;
r = find(PDP_o(id.reward, :) > 1);
c = find(PDP_o(id.contraint, :) > 1);
entry6_r = r;
entry6_c = c;
entry6_t_windows = {};
wi = 0;
for i = 1:numel(r)
    s = c(find(c < r(i), 1, 'last'));
    t = (s + Ne):(r(i) + Ne);
    if numel(t)
        wi = wi + 1;
        entry6_t_windows{wi} = t;
    end
end
fprintf(1, '[FSL backward patch] Entry 6: numel(r)=%d numel(c)=%d n_windows=%d\n', ...
    numel(r), numel(c), wi);
save(outMat, 'entry6_r', 'entry6_c', 'entry6_t_windows', '-append');
fprintf(1, '[FSL backward patch] appended entry6_* to %s\n', outMat);
end
