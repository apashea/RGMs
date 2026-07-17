function xxx_matlab_3_run()
%XXX_MATLAB_3_RUN  Forwards/policy process counts on call4 (XXX_matlab-3).
here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
rdpMat = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures', ...
    'DEMAtariIII_XXX_12_rgms_atari_optim1full_call4_rdp.mat');
addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(fullfile(here, 'xxx_matlab_3'), '-begin');
S = load(rdpMat, 'RDP');
global RGMS_XM3
RGMS_XM3 = struct('n_fwd',0,'n_vbx',0,'n_ind',0,'n_efe_rec',0,'N_vals',[],'t_vals',[]);
rng(2);
fprintf(1, '[XM3] which=%s\n', which('spm_MDP_VB_XXX'));
% Also report MDP.N from RDP if present
if isfield(S.RDP, 'N')
    fprintf(1, '[XM3] RDP.N=%g\n', S.RDP.N);
elseif isstruct(S.RDP) && numel(S.RDP) >= 1 && isfield(S.RDP(1), 'N')
    fprintf(1, '[XM3] RDP(1).N=%g\n', S.RDP(1).N);
else
    fprintf(1, '[XM3] RDP.N field absent (default 0 in .m)\n');
end
t0 = tic;
spm_MDP_VB_XXX(S.RDP, struct(), false);
fprintf(1, '[XM3] wall_s=%.3f\n', toc(t0));
fprintf(1, '[XM3] SUMMARY n_fwd=%d n_vbx=%d n_ind=%d n_efe_rec=%d\n', ...
    RGMS_XM3.n_fwd, RGMS_XM3.n_vbx, RGMS_XM3.n_ind, RGMS_XM3.n_efe_rec);
if ~isempty(RGMS_XM3.N_vals)
    fprintf(1, '[XM3] N unique=%s\n', mat2str(unique(RGMS_XM3.N_vals)));
    fprintf(1, '[XM3] t unique (first 20)=%s\n', mat2str(unique(RGMS_XM3.t_vals(1:min(end,20)))));
end
end
