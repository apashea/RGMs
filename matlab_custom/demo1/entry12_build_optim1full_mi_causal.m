function causal = entry12_build_optim1full_mi_causal(MDP, o)
%ENTRY12_BUILD_OPTIM1FULL_MI_CAUSAL  Causal steps 1--4 inside ``spm_RDP_MI``.
% See ``OPTIM1.md`` § **11.5.1**. Mirrors ``spm_RDP_MI.m`` lines 29--88.

if nargin < 2, o = 1; end

n = numel(MDP);
try
    A = MDP{n}.a;
catch
    A = MDP{n}.A;
end
try
    B = MDP{n}.b{1};
catch
    B = MDP{n}.B{1};
end

Ns = size(B, 2);
Nu = size(B, 3);
for u = 1:Nu
    for s = 1:Ns
        if ~any(B(:, s, u))
            [j, i] = max(max(squeeze(B(:, s, :)), [], 2));
            B(i, s, u) = j;
        end
    end
end
causal.B_ambig = B;

A = spm_dir_norm(A);
B = spm_dir_norm(B);
causal.B_norm = B;

C = {};
for s = 2:max(MDP{1}.sB)
    pD = MDP{n - 1}.id.D{MDP{n - 1}.sB == s};
    pE = MDP{n - 1}.id.E{MDP{n - 1}.sB == s};
    ps = find(ismember([MDP{n}.id.A{:}], find(MDP{n}.sB == 1, 1, 'first')));
    pD = intersect(ps, pD);
    pE = intersect(ps, pE);
    if numel(pD)
        for p = 0:o
            for u = 1:Nu
                C{end + 1, 1} = A{pD} * (B(:, :, u)^p);
                C{end + 1, 1} = A{pE} * (B(:, :, u)^p);
            end
        end
    end
end

nc = numel(C);
causal.C_n = nc;
causal.C_shapes = zeros(nc, 2);
causal.C_sums = zeros(nc, 1);
for k = 1:nc
    causal.C_shapes(k, :) = size(C{k});
    causal.C_sums(k) = sum(C{k}(:));
end

R = spm_dir_reduce(C);
causal.R = full(R);
end
