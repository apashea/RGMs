% patch_entry2_authority_to_pre_entry10_mat.m
%
% Append Entry 2 authority (post-pong, pre-generate) to
% DEMAtariIII_fsl_backward_MDP_pre_entry10.mat on the rng(2) ledger.
%
%   matlab -batch "cd('...\matlab_custom\fsl_backward'); patch_entry2_authority_to_pre_entry10_mat;"

function patch_entry2_authority_to_pre_entry10_mat()
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
Nr = 12;
Nc = 9;
Nd = 4;
fprintf(1, '[FSL backward patch Entry 2] rng(2) spm_MDP_pong(%d,%d,%d,true,0)\n', Nr, Nc, Nd);

[GDP_post_entry2, hid_post_entry2, cid_post_entry2, con_post_entry2, RGB_post_entry2] = ...
    spm_MDP_pong(Nr, Nc, Nd, true, 0);

S_post_entry2 = ones(4, 3);
S_post_entry2(1, :) = [Nr, Nc, 1];

save(outMat, 'GDP_post_entry2', 'RGB_post_entry2', 'S_post_entry2', ...
    'hid_post_entry2', 'cid_post_entry2', 'con_post_entry2', '-append');
fprintf(1, '[FSL backward patch Entry 2] appended GDP_post_entry2, RGB_post_entry2, S_post_entry2 to %s\n', outMat);
end
