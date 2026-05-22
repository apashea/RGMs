% spm_VBX at parent t=2 on inputs saved by entry12_12f_vbx_t2_crosslane.py (pre-forwards).
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'matlab_src', 'toolbox', 'DEM'));
S = load(fullfile(fileparts(mfilename('fullpath')), 'entry12_12f_vbx_t2_pre_fwd.mat'));
[Q, F] = spm_VBX(S.Orow, S.Prow, S.Arow, S.idm);
fprintf('MATLAB spm_VBX F t2 pre-fwd = %.16g\n', F);
fprintf('Prow{1} numel = %d\n', numel(S.Prow{1}));
