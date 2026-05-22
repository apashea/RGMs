function out = entry12_bf_I_goal_compare(goalCol)
%ENTRY12_BF_I_GOAL_COMPARE Bf/I/G for one hid column on frozen inputs.
if nargin < 1
    goalCol = 21;
end
here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));
inpPath = fullfile(repoRoot, 'matlab_custom', 'entry12_12f_induction_inputs.mat');
S = load(inpPath);
B = S.B;
Q = S.Q;
for f = 1:numel(Q)
    Q{f} = full(Q{f}(:));
end
N = min(double(S.N(1)), 64);
hid = S.id_hid;
u = 1 / 32;
b = false(size(B{1, 1, 1}, 1), 1);
for k = 1:size(B, 3)
    b = b | (B{1, 1, k} > u);
end
Bf = spm_kron(b, 1);
Qf = spm_kron(Q{1}, 1);
Bf = and(Bf, true(size(Bf)));
h = false(size(b));
h(hid(1, goalCol)) = true;
I = spm_kron(h, true);
for n = 1:N
    j = any(Bf(I(:, n), :), 1)';
    I(:, n + 1) = j;
    if ~any(j)
        break;
    end
end
Gcol = I' * Qf;
Gcol(1) = 0;
[~, nmx] = max(Gcol);
out = struct();
out.Bf_nnz = nnz(Bf);
out.Qf_shape = size(Qf);
out.Gcol_argmax = nmx;
out.P_nz_at_argmax = find(I(:, nmx))';
end
