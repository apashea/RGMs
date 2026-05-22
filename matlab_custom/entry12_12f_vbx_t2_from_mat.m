% Compare spm_VBX F at parent t=2 (inputs from entry12_12f_vbx_F_probe.py).
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'matlab_src', 'toolbox', 'DEM'));
if isfolder(fullfile(getenv('USERPROFILE'), '.cursor', 'Atari_spm_dependencies'))
    addpath(fullfile(getenv('USERPROFILE'), '.cursor', 'Atari_spm_dependencies'));
end
S = load(fullfile(fileparts(mfilename('fullpath')), 'entry12_12f_vbx_t2_inputs.mat'));
[Q, F] = spm_VBX(S.Orow, S.Prow, S.Arow, S.idm);
fprintf('MATLAB spm_VBX F t2 = %.16g\n', F);
fprintf('Q{1} numel = %d\n', numel(Q{1}));
