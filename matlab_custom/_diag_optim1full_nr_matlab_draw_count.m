% Count scalar rand() for NR game 1 from saved MDP_pre (fsl_backward shadow).
here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
fslDir = fullfile(repoRoot, 'matlab_custom', 'fsl_backward');
optim1Dir = fullfile(repoRoot, 'tests', 'demo1', 'optim1', 'fixtures');
addpath(fslDir, '-begin');
addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
cd(repoRoot);

preMat = fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat');
load(preMat, 'MDP_pre_active_inference', 'Ne');
C = 32;
NS = 256;
NT = 256;

rgms_fsl_rand_log_begin();
i0 = rgms_fsl_rand_log_count();
RDP = spm_set_goals(MDP_pre_active_inference, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = fix(NT / Ne);
OPTIONS = struct();
OPTIONS.O = 1;
OPTIONS.Y = 1;
PDP = spm_MDP_VB_XXX(RDP, OPTIONS, false, false);
k = rgms_fsl_rand_log_count() - i0;
fprintf('[diag] MATLAB NR game1 VB scalar rand count k=%d T=%d Ne=%d\n', k, RDP.T, Ne);
