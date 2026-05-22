% VERIFY_PDP_O_DIMENSIONS — truth report for PDP.O at 12H (rgms_canonical).
% Read-only diagnostic; not Entry 12 sign-off.
p = fullfile('C:\Users\andre\.cursor\RGMs\tests\oracle\toolbox\DEM\fixtures', ...
    'DEMAtariIII_entry12_rgms_canonical_12H.mat');
S = load(p);
PDP = S.PDP;
fprintf('=== MATLAB fixture: %s ===\n', p);
fprintf('PDP.O: class=%s size=[%s] ndims=%d numel=%d\n', ...
    class(PDP.O), num2str(size(PDP.O)), ndims(PDP.O), numel(PDP.O));
if iscell(PDP.O)
    ng = size(PDP.O, 1);
    nt = size(PDP.O, 2);
    fprintf('  cell grid: Ng=%d T=%d (rows=modality, cols=time if 2-D cell)\n', ng, nt);
    for g = [1, 2, ng]
        if g <= ng
            og = PDP.O{g, 1};
            if iscell(og)
                fprintf('  O(g=%d,t=1) nested cell len=%d\n', g, numel(og));
            else
                fprintf('  O(g=%d,t=1) class=%s size=[%s]\n', g, class(og), num2str(size(og)));
            end
            if nt >= 2
                og2 = PDP.O{g, nt};
                fprintf('  O(g=%d,t=%d) class=%s size=[%s]\n', g, nt, class(og2), num2str(size(og2)));
            end
        end
    end
    % Column-major linear index: g + (t-1)*Ng for 2-D cell (Ng x T)
    g0 = 1; t0 = 1; t1 = nt;
    v00 = PDP.O{g0, t0};
    v01 = PDP.O{g0, t1};
    if isnumeric(v00) && isnumeric(v01)
        fprintf('  sample O(g=1,t=1) first3: %s\n', mat2str(v00(1:min(3,end))', 6));
        fprintf('  sample O(g=1,t=%d) first3: %s\n', t1, mat2str(v01(1:min(3,end))', 6));
    end
end
fprintf('PDP.n: size=[%s]\n', num2str(size(PDP.n)));
if isfield(PDP, 'id') && isfield(PDP.id, 'g')
    ig = PDP.id.g;
    if isnumeric(ig)
        fprintf('PDP.id.g: size=[%s] first5=%s\n', num2str(size(ig)), mat2str(ig(1:min(5,end))', 6));
    else
        fprintf('PDP.id.g: class=%s size=[%s]\n', class(ig), num2str(size(ig)));
    end
end
if isfield(PDP, 'MDP') && isfield(PDP.MDP, 'O')
    mo = PDP.MDP.O;
    fprintf('PDP.MDP.O: class=%s size=[%s] numel=%d\n', class(mo), num2str(size(mo)), numel(mo));
    if iscell(mo) && numel(size(mo)) >= 2
        fprintf('  MDP.O grid: [%s]\n', num2str(size(mo)));
    elseif iscell(mo) && numel(mo) <= 5
        for k = 1:numel(mo)
            fprintf('  MDP.O(k=%d) class=%s size=[%s]\n', k, class(mo{k}), num2str(size(mo{k})));
        end
    end
end
fprintf('PDP.T = %g\n', PDP.T);
