root = fileparts(fileparts(mfilename('fullpath')));
tag = 'rgms_canonical';
fix = fullfile(root, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
addpath(fullfile(root, 'matlab_src', 'toolbox', 'DEM'));
wsE = load(fullfile(fix, ['DEMAtariIII_entry12_' tag '_12E.mat']));
wsF = load(fullfile(fix, ['DEMAtariIII_entry12_' tag '_12F.mat']));
wsC = load(fullfile(fix, ['DEMAtariIII_entry12_' tag '_12C.mat']));
out_e = wsE.out_t2;
out_f = wsF.out_t2;
t = 2;
m = 1;
O = out_e.O;
P = out_f.P;
if iscell(O)
    Om = O{m};
else
    Om = O(m).O;
end
if iscell(P)
    Pm = P{m};
else
    Pm = P(m).P;
end
Orow = cell(1, numel(Om));
for g = 1:numel(Om)
    Og = Om{g};
    if iscell(Og)
        Orow{g} = full(double(Og{t}));
    else
        Orow{g} = full(double(Og(:, t)));
    end
end
Prow = cell(1, numel(Pm));
for f = 1:numel(Pm)
    Pf = Pm{f};
    if iscell(Pf)
        Prow{f} = full(double(Pf{t}));
    else
        Prow{f} = full(double(Pf(:, t)));
    end
end
Arow = cell(1, numel(wsC.A{m}));
for g = 1:numel(wsC.A{m})
    Arow{g} = full(double(wsC.A{m}{g}));
end
idm = out_f.MDP(m).id;
[Q, Fvbx] = spm_VBX(Orow, Prow, Arow, idm);
fprintf('Fvbx=%.16g\n', Fvbx);
Ff = full(double(out_f.MDP(m).F(:)));
fprintf('MDP_F_snap_len=%d\n', numel(Ff));
fprintf('MDP_F_snap=%.16g %.16g\n', Ff(1), Ff(min(2,end)));
