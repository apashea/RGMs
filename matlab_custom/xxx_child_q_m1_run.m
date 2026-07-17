function xxx_child_q_m1_run()
%XXX_CHILD_Q_M1_RUN  Process M1 — Q identity probe on call4 RDP (one process).
% Instrumented fork: matlab_custom/xxx_child_q_m1/spm_MDP_VB_XXX.m (shadows matlab_src).

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
fixDir = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures');
rdpMat = fullfile(fixDir, 'DEMAtariIII_XXX_12_rgms_atari_optim1full_call4_rdp.mat');
if ~isfile(rdpMat)
    error('RGMs:MissingFixture', 'Missing RDP: %s', rdpMat);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));
% Instrumented fork must win over matlab_src (Engine may already have matlab_src on path).
addpath(fullfile(here, 'xxx_child_q_m1'), '-begin');

S = load(rdpMat, 'RDP');
RDP = S.RDP;

global RGMS_M1_QPROBE
RGMS_M1_QPROBE = struct('n', 0, 'done', false, 'seen_no_Q', 0);

rng(2);
fprintf(1, '[M1-Q] start call4 RDP rng=2\n');
which_vb = which('spm_MDP_VB_XXX');
fprintf(1, '[M1-Q] which spm_MDP_VB_XXX=%s\n', which_vb);
t0 = tic;
spm_MDP_VB_XXX(RDP, struct(), false);
wall_s = toc(t0);
fprintf(1, '[M1-Q] finished wall_s=%.3f\n', wall_s);

if isempty(RGMS_M1_QPROBE) || ~isfield(RGMS_M1_QPROBE, 'done') || ~RGMS_M1_QPROBE.done
    fprintf(1, '[M1-Q] FAIL: probe did not complete\n');
    disp(RGMS_M1_QPROBE);
else
    fprintf(1, '[M1-Q] SUMMARY\n');
    fprintf(1, '  t=%g m=%g prior_no_Q_hits=%g\n', RGMS_M1_QPROBE.t, RGMS_M1_QPROBE.m, RGMS_M1_QPROBE.A_seen_no_Q_before);
    fprintf(1, '  A_isequal=%d A_map_mdp2par=%d A_map_par2mdp=%d A_E_numel=%g A_F=%g\n', ...
        RGMS_M1_QPROBE.A_isequal, RGMS_M1_QPROBE.A_mdp_map_write_visible_on_parent, ...
        RGMS_M1_QPROBE.A_parent_map_write_visible_on_mdp, RGMS_M1_QPROBE.A_E_numel, RGMS_M1_QPROBE.A_F);
    fprintf(1, '  B_parent_E_unchanged=%g B_isequal_Q=%g\n', ...
        RGMS_M1_QPROBE.B_parent_E_unchanged, RGMS_M1_QPROBE.B_isequal_Q);
    fprintf(1, '  C_isequal=%d C_shared_handle=%d C_E_numel=%g C_F=%g\n', ...
        RGMS_M1_QPROBE.C_isequal, RGMS_M1_QPROBE.C_shared_via_handle, ...
        RGMS_M1_QPROBE.C_E_numel, RGMS_M1_QPROBE.C_F);
end
end
