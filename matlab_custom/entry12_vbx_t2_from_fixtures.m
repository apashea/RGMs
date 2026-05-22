% VBX F at t=2 from paired Entry 12 fixtures (MATLAB .mat side).
root = fileparts(fileparts(mfilename('fullpath')));
tag = 'rgms_canonical';
fix = fullfile(root, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
addpath(fullfile(root, 'matlab_src', 'toolbox', 'DEM'));

E = load(fullfile(fix, ['DEMAtariIII_entry12_' tag '_12E.mat']));
F = load(fullfile(fix, ['DEMAtariIII_entry12_' tag '_12F.mat']));
C = load(fullfile(fix, ['DEMAtariIII_entry12_' tag '_12C.mat']));

out_e = E.out_t2;
out_f = F.out_t2;
t = 2;
m = 1;

Orow = cell(1, numel(out_e.O{m}));
for g = 1:numel(out_e.O{m})
    Og = out_e.O{m}{g};
    if iscell(Og)
        Orow{g} = full(double(Og{t}));
    else
        Orow{g} = full(double(Og(:, t)));
    end
end

Prow = cell(1, numel(out_f.P{m}));
for f = 1:numel(out_f.P{m})
    Pf = out_f.P{m}{f};
    if iscell(Pf)
        Prow{f} = full(double(Pf{t}));
    else
        Prow{f} = full(double(Pf(:, t)));
    end
end

Arow = cell(1, numel(C.A{m}));
for g = 1:numel(C.A{m})
    Arow{g} = full(double(C.A{m}{g}));
end

idm = out_f.MDP{m}.id;
[Q, Fvbx] = spm_VBX(Orow, Prow, Arow, idm);
fprintf('MATLAB fixture O,P at t=%d: F=%.16g\n', t, Fvbx);
fprintf('MDP.F on 12F snap: ');
Ff = out_f.MDP{m}.F;
disp(Ff(:)');
fprintf('phase post_vbx F_vbx: see entry12_phase_log\n');
