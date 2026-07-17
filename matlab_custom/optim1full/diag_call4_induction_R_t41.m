% Compare MATLAB VB-local spm_induction against Python dump R at call4 t=41.
% Uses induction logic from matlab_src/toolbox/DEM/spm_MDP_VB_XXX.m (local).
repoRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
inMat = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_induction_inputs.mat');
outJson = fullfile(repoRoot, 'matlab_custom', 'optim1full_call4_matlab_R_t41.json');

% Ensure inputs exist (written by Python companion)
assert(isfile(inMat), 'missing %s — run companion Python first', inMat);
S = load(inMat);
B = cell(1, 1, size(S.BP, 3));
for k = 1:size(S.BP, 3)
    B{1, 1, k} = S.BP(:, :, k);
end
H = {S.H};
Q = {S.Q};
id = struct();
id.hid = S.hid;
id.cid = [];

[R, hif, meta] = spm_induction_vb_local_(B, H, Q, S.N, id);
nz = find(R(:) > 0);
fid = fopen(outJson, 'w');
fprintf(fid, '{\n  \"nnz\": %d,\n  \"sum\": %.17g,\n  \"n_sel\": %d,\n  \"goal_i\": %d,\n  \"col\": %d,\n  \"hif\": [', ...
    nnz(R > 0), sum(R(:)), meta.n_sel, meta.goal_i, meta.col);
fprintf(fid, '%d', hif(1));
for i = 2:numel(hif), fprintf(fid, ', %d', hif(i)); end
fprintf(fid, '],\n  \"nz_idx\": [');
for i = 1:numel(nz)
    if i > 1, fprintf(fid, ', '); end
    fprintf(fid, '%d', nz(i));
end
fprintf(fid, ']\n}\n');
fclose(fid);
fprintf(1, '[diag] MATLAB induction R nnz=%d sum=%g n_sel=%d goal_i=%d col=%d\n', ...
    nnz(R > 0), sum(R(:)), meta.n_sel, meta.goal_i, meta.col);

function [R, hif, meta] = spm_induction_vb_local_(B, H, Q, N, id)
% Faithful extract of local spm_induction from spm_MDP_VB_XXX.m
meta = struct('n_sel', 0, 'goal_i', 0, 'col', 0);
if isfield(id, 'hid')
    hid = id.hid;
    hif = find(any(hid, 2))';
else
    hid = [];
    hif = [];
    for f = 1:numel(H)
        if numel(H{f})
            [~, s] = max(H{f});
            hid(end + 1, 1) = s; %#ok<AGROW>
            hif(1, end + 1) = f; %#ok<AGROW>
        end
    end
end
if isfield(id, 'cid')
    if isempty(id.cid)
        D = true;
    else
        error('cid nonempty not needed for this diag');
    end
else
    D = true;
end
if isempty(hif), R = []; return, end
if isempty(hid), R = 32 * D; return, end
N = min(N, 64);
if isfield(id, 'D') && N < 4
    N = 64;
end
u = 1 / 32;
for f = hif
    b{f} = false; %#ok<AGROW>
    for k = 1:size(B, 3)
        try
            b{f} = b{f} | (B{1, f, k} > u);
        catch
            b{f} = b{f} | (B{1, f, 1} > u);
        end
    end
end
Bf = 1;
Qf = 1;
Ns = [];
for f = hif
    Ns(end + 1) = size(B{f}, 1); %#ok<AGROW>  % match .m (not B{1,f,1})
    Bf = spm_kron(b{f}, Bf);
    Qf = spm_kron(Q{f}, Qf);
end
Bf = and(Bf, D(:));
if size(Bf, 2) > 512
    N = min(N, 32);
end
Nh = size(hid, 2);
for i = 1:Nh
    I = true;
    for f = 1:numel(hif)
        h = false(Ns(f), 1);
        h(hid(f, i)) = true;
        I = spm_kron(h, I);
    end
    Pf(:, i) = logical(I); %#ok<AGROW>
end
G = zeros(N, Nh);
for i = 1:Nh
    I = logical(Pf(:, i));
    for n = 1:N
        j = any(Bf(I(:, n), :), 1)';
        I(:, n + 1) = j;
        if ~any(j), break, end
    end
    j = 1:size(I, 2);
    G(j, i) = I' * Qf;
    P{i} = I; %#ok<AGROW>
end
G(1, :) = 0;
[d, n] = max(G, [], 1);
i = d > u;
if any(i)
    P = P(i);
    n = n(i);
    [n, i] = min(n);
    col = max(n - 1, 1);
    meta.n_sel = n;
    meta.goal_i = i;
    meta.col = col;
    P = P{i}(:, col);
    R = reshape(full(P), [Ns, 1]);
    R = 32 * and(R, D);
else
    R = [];
end
end
