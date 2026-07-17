% patch_entry1_authority_to_pre_entry10_mat.m
%
% Append Entry 1 snippet constants to DEMAtariIII_fsl_backward_MDP_pre_entry10.mat.
% Same values as dump_MDP_pre_entry10.m / DEM_AtariIII Entry 1 block.
%
%   matlab -batch "cd('...\matlab_custom\fsl_backward'); patch_entry1_authority_to_pre_entry10_mat;"

function patch_entry1_authority_to_pre_entry10_mat()
thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(thisDir));
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
outDir = demo1_fixtures_dir(repoRoot);
outMat = fullfile(outDir, 'DEMAtariIII_fsl_backward_MDP_pre_entry10.mat');
if ~isfile(outMat)
    error('Missing %s — run dump_MDP_pre_entry10.m first.', outMat);
end

entry1_Nr = 12;
entry1_Nc = 9;
entry1_Sc = 9;
entry1_Nd = 4;
entry1_C  = 32;

save(outMat, 'entry1_Nr', 'entry1_Nc', 'entry1_Sc', 'entry1_Nd', 'entry1_C', '-append');
fprintf(1, '[FSL backward patch Entry 1] appended entry1_* to %s\n', outMat);
end
