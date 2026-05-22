% Extract O,P at t=2 from paired MAT fixtures; print sums and VBX F.
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
% unwrap struct if saved as struct array
if isstruct(O) && numel(O) >= m
    Om = O(m);
elseif iscell(O)
    Om = O{m};
else
    error('O layout');
end
if isstruct(P) && numel(P) >= m
    Pm = P(m);
elseif iscell(P)
    Pm = P{m};
else
    error('P layout');
end

Orow = cell(1, numel(Om));
for g = 1:numel(Om)
    Og = Om{g};
    if iscell(Og)
        Orow{g} = full(double(Og{t}));
    else
        Orow{g} = full(double(Og(:, t)));
    end
    fprintf('O g%d sum=%.16g numel=%d peak=%d\n', g, sum(Orow{g}), numel(Orow{g}), ...
        find(Orow{g}==max(Orow{g}), 1));
end

Prow = cell(1, numel(Pm));
for f = 1:numel(Pm)
    Pf = Pm{f};
    if iscell(Pf)
        Prow{f} = full(double(Pf{t}));
    else
        Prow{f} = full(double(Pf(:, t)));
    end
    fprintf('P f%d sum=%.16g numel=%d peak=%d\n', f, sum(Prow{f}), numel(Prow{f}), ...
        find(Prow{f}==max(Prow{f}), 1));
end

Arow = cell(1, numel(wsC.A{m}));
for g = 1:numel(wsC.A{m})
    Arow{g} = full(double(wsC.A{m}{g}));
end
idm = out_f.MDP(m).id;
[Q, Fvbx] = spm_VBX(Orow, Prow, Arow, idm);
fprintf('spm_VBX F mat fixtures = %.16g\n', Fvbx);
Ff = full(double(out_f.MDP(m).F(:)));
fprintf('MDP.F snap vec = '); fprintf('%.6g ', Ff); fprintf('\n');
