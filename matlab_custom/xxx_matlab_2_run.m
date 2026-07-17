function xxx_matlab_2_run()
%XXX_MATLAB_2_RUN  Child reuse vs rebuild on call4 (XXX_matlab-2).
here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
rdpMat = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures', ...
    'DEMAtariIII_XXX_12_rgms_atari_optim1full_call4_rdp.mat');
addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(fullfile(here, 'xxx_matlab_2'), '-begin');
S = load(rdpMat, 'RDP');
global RGMS_XM2
RGMS_XM2 = struct('n', 0, 'rows', {{}});
rng(2);
fprintf(1, '[XM2] which=%s\n', which('spm_MDP_VB_XXX'));
t0 = tic;
spm_MDP_VB_XXX(S.RDP, struct(), false);
fprintf(1, '[XM2] wall_s=%.3f n_hier=%d\n', toc(t0), RGMS_XM2.n);
end
