% diag_call4_G_t41_from_fence.m
% OPTIM1FULL Phase C (diagnostic only): extract MATLAB authority G at the diverge
% timestep from the plot-fence PDP (capture_optim1full_plot_fence).
%
% PDP.G is a T-cell (or T x Np matrix). Cell/index 41 (1-based) == Python list index 40.
% Writes matlab_custom/optim1full_call4_matlab_G_t41.json
%
% Usage (from repo root, MATLAB):
%   run('matlab_custom/optim1full/diag_call4_G_t41_from_fence.m')

repoRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
matPath = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures', ...
    'DEMAtariIII_optim1full_dem_with_compression_rgb_matlab_pdp.mat');
outJson = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_matlab_G_t41.json');

assert(isfile(matPath), 'missing fence PDP: %s', matPath);
S = load(matPath);
if isfield(S, 'PDP')
    PDP = S.PDP;
elseif isfield(S, 'pdp')
    PDP = S.pdp;
else
    error('fence mat missing PDP');
end

G = PDP.G;
t1 = 41; % MATLAB 1-based
if iscell(G)
    assert(numel(G) >= t1, 'G cell too short');
    g = G{t1};
elseif isnumeric(G)
    % packed T x Np
    assert(size(G, 1) >= t1 || size(G, 2) >= t1, 'G numeric short');
    if size(G, 1) >= t1
        g = G(t1, :);
    else
        g = G(:, t1);
    end
else
    error('unexpected G type');
end
g = full(double(g(:))).';

meta = struct();
if isfield(S, 'metaPdp'), meta = S.metaPdp; end

payload = struct();
payload.matlab_t_1based = t1;
payload.python_cell_index_0based = t1 - 1;
payload.G = g;
payload.mat_path = matPath;
payload.capture = '';
try, payload.capture = char(meta.capture); catch, end

% Write JSON without depending on JSON Toolbox quirks for nested structs.
fid = fopen(outJson, 'w');
assert(fid > 0, 'cannot write %s', outJson);
fprintf(fid, '{\n');
fprintf(fid, '  "matlab_t_1based": %d,\n', t1);
fprintf(fid, '  "python_cell_index_0based": %d,\n', t1 - 1);
fprintf(fid, '  "G": [');
for i = 1:numel(g)
    if i > 1, fprintf(fid, ', '); end
    fprintf(fid, '%.17g', g(i));
end
fprintf(fid, '],\n');
fprintf(fid, '  "mat_path": "%s",\n', strrep(matPath, '\', '/'));
fprintf(fid, '  "capture": "%s"\n', payload.capture);
fprintf(fid, '}\n');
fclose(fid);
fprintf(1, '[diag_call4_G_t41] wrote %s G=%s\n', outJson, mat2str(g, 6));
