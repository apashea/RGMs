function out = entry12_spm_induction_internals(B, H, Q, N, id)
%ENTRY12_SPM_INDUCTION_INTERNALS Frozen induction with selection diagnostics.
[R, hif] = entry12_spm_induction(B, H, Q, N, id);
out = struct();
out.R_sum = sum(R(:));
out.R_nz = find(R(:) > 0)';
if isempty(out.R_nz)
    out.R_nz = [];
end
out.hif = hif;
% Re-run selection block only (mirror entry12_spm_induction) for dbg fields.
u = 1/32;
if isfield(id, 'hid')
    hid = id.hid;
    hif2 = find(any(hid, 2))';
else
  error('internals: expected id.hid');
end
if isempty(hif2) || isempty(hid)
    out.goal_i = 0;
    out.n_col = 0;
    out.P_nnz = 0;
    out.Pf_col1_nnz = 0;
    out.G_max_row = 0;
    return;
end
N = min(N, 64);
if isfield(id, 'D') && N < 4
    N = 64;
end
for f = hif2
    b{f} = false;
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
for f = hif2
    Ns(end + 1) = size(B{f}, 1);
    Bf = spm_kron(b{f}, Bf);
    Qf = spm_kron(Q{f}, Qf);
end
if isfield(id, 'cid') && ~isempty(id.cid)
    % D already applied in full call; skip for dbg counts
end
Bf = and(Bf, true(size(Bf)));
Nh = size(hid, 2);
for i = 1:Nh
    I = true;
    for f = 1:numel(hif2)
        h = false(Ns(f), 1);
        h(hid(f, i)) = true;
        I = spm_kron(h, I);
    end
    Pf(:, i) = logical(I);
end
G = zeros(N, Nh);
P = cell(1, Nh);
for i = 1:Nh
    I = logical(Pf(:, i));
    for n = 1:N
        j = any(Bf(I(:, n), :), 1)';
        I(:, n + 1) = j;
        if ~any(j)
            break;
        end
    end
    jj = 1:size(I, 2);
    G(jj, i) = I' * Qf;
    P{i} = I;
end
G(1, :) = 0;
[d, n] = max(G, [], 1);
mask = d > u;
out.Pf_col1_nnz = nnz(Pf(:, 1));
out.G_max_row = size(G, 1);
if any(mask)
    Pm = P(mask);
    nm = n(mask);
    [ncol, gi] = min(nm);
    out.goal_i = gi;
    out.n_col = ncol;
    Pcol = Pm{gi}(:, max(ncol - 1, 1));
    out.P_nnz = nnz(Pcol);
else
    out.goal_i = 0;
    out.n_col = 0;
    out.P_nnz = 0;
end
end
