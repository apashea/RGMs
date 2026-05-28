% One-off: replay spm_VBX on nested child from Entry 12 12F out_t1 snap (call2).
% Usage (from RGMs root): matlab -batch "addpath('matlab_custom'); probe_child_vbx_from_12f"
tag = 'rgms_atari_call2';
fx = fullfile('tests', 'oracle', 'toolbox', 'DEM', 'fixtures', ...
    ['DEMAtariIII_entry12_' tag '_12F.mat']);
addpath(fullfile(pwd, 'matlab_src', 'toolbox', 'DEM'));
S = load(fx);
snap = S.out_t1;
mdp = snap.MDP.MDP;
if iscell(mdp), mdp = mdp{1}; end
ng = numel(mdp.A);
O = cell(1, ng);
for g = 1:ng
    if iscell(mdp.O) && size(mdp.O, 1) >= 1 && size(mdp.O, 2) >= g
        Og = mdp.O{1, g};
    elseif iscell(mdp.O) && numel(mdp.O) == ng
        Og = mdp.O{g};
        if iscell(Og), Og = Og{1}; end
    else
        error('probe_child_vbx: unexpected mdp.O layout');
    end
    O{g} = Og(:);
end
P = cell(1, numel(mdp.P));
for f = 1:numel(P)
    Pf = mdp.P{f};
    if isvector(Pf), P{f} = Pf(:); else, P{f} = Pf(:, 1); end
end
mdp = spm_MDP_check(mdp);
id = mdp.id;
[~, Fvbx] = spm_VBX(O, P, mdp.A, id);
fprintf('numel_idg=%d\n', numel(id.g));
fprintf('Fvbx_t1=%.12g\n', Fvbx);
fprintf('stored_F=%s\n', mat2str(mdp.F(:)'));
