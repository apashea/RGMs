% patch_mdp_pre_entry5_to_pre_entry10_mat.m
%
% Append ``MDP_pre_entry5`` (post–Entry 4 / pre-forget) to an existing
% DEMAtariIII_fsl_backward_MDP_pre_entry10.mat using the same rng(2) ledger preamble
% as dump_MDP_pre_entry10.m.
%
%   matlab -batch "cd('...\matlab_custom\fsl_backward'); patch_mdp_pre_entry5_to_pre_entry10_mat;"

function patch_mdp_pre_entry5_to_pre_entry10_mat()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
demo1_add_matlab_src(repoRoot);
outDir = demo1_fixtures_dir(repoRoot);
outMat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry10.mat');
if ~isfile(outMat)
    error('Missing %s — run dump_MDP_pre_entry10.m first.', outMat);
end

rng(2);
fprintf(1, '[FSL backward patch] rng(2) — Entry 5 input MDP_pre_entry5\n');

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C  = 32;

[GDP, ~, ~, ~, ~] = spm_MDP_pong(Nr, Nc, Nd, true, 0);

S = ones(4, 3);
S(1, :) = [Nr, Nc, 1];
S(2, :) = [1, 1, 1];
S(3, :) = [1, 1, 1];
S(4, :) = [1, 1, 1];

GDP.tau = 1;
GDP.T   = 10000;
PDP = spm_MDP_generate(GDP);

MDP = spm_faster_structure_learning(PDP.O(:, 1:1000), S, Sc);
MDP_pre_entry5 = MDP;

fprintf(1, '[FSL backward patch] MDP_pre_entry5: Nm=%d\n', numel(MDP_pre_entry5));
save(outMat, 'MDP_pre_entry5', '-append');
fprintf(1, '[FSL backward patch] appended MDP_pre_entry5 to %s\n', outMat);
end
