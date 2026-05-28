% Replay spm_VBX on Python-saved compute-time O/P (probe_child_vbx_t1.npz).
addpath(fullfile(pwd, 'matlab_src', 'toolbox', 'DEM'));
addpath(genpath(fullfile(pwd, '..', 'Documents', 'MATLAB', 'spm-main')));
S = load('matlab_custom/probe_child_vbx_t1.mat');
O = cell(1, numel(S.O_row));
for g = 1:numel(O)
    Og = S.O_row{g};
    if iscell(Og), Og = Og{1}; end
    O{g} = Og(:);
end
P = cell(1, numel(S.P_row));
for f = 1:numel(P)
    Pf = S.P_row{f};
    if iscell(Pf), Pf = Pf{1}; end
    P{f} = Pf(:);
end
fx = fullfile('tests', 'oracle', 'toolbox', 'DEM', 'fixtures', ...
    'DEMAtariIII_entry12_rgms_atari_call2_12F.mat');
snap = load(fx, 'out_t1');
mdp = snap.out_t1.MDP.MDP;
if iscell(mdp), mdp = mdp{1}; end
mdp = spm_MDP_checkX(mdp);
[~, Fm] = spm_VBX(O, P, mdp.A, mdp.id);
fprintf('py_saved_F_vbx=%.12g\n', S.F_vbx_py);
fprintf('matlab_F_vbx=%.12g\n', Fm);
fprintf('mat_child_F_t1=%.12g\n', mdp.F(1));
