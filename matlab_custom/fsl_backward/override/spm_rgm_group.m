function [G] = spm_rgm_group(O,dx,m)
% Instrumented copy for Entry 4 spectral eig dump (see dump_entry4_rgm_spectral_eig.m).
% Logs each ``eig(MI(i,i),'nobalance')`` iteration to global rgms_entry4_spectral_records.
% Do not use on path for normal FSL runs — dump script prepends this directory only.

global rgms_entry4_spectral_records rgms_entry4_rgm_call_id
if isempty(rgms_entry4_rgm_call_id)
    rgms_entry4_rgm_call_id = 0;
end
rgms_entry4_rgm_call_id = rgms_entry4_rgm_call_id + 1;
call_id = rgms_entry4_rgm_call_id;

if nargin < 2, dx = 16; end
if nargin < 3, m  = 1;  end

[No,Nt] = size(O);

if ~No,     G = {};     return, end

if No < dx, G = {1:No}; return, end

R     = {};
for t = 1:Nt
    i = 1;
    for o = 1:m:No
        p = O{o,t};
        for r = 1:(m - 1)
            p = kron(p,O{o + r,t});
        end
        R{i,t} = p;
        i = i + 1;
    end
end

No    = size(R,1);
n     = false(1,No);
r     = cell(1,No);
for o = 1:No
    r{o} = spm_cat(R(o,:));
    n(o) = any(diff(r{o},[],2),'all');
end

MI    = zeros(No,No);
for i = 1:No
    for j = i:No
        p = 0;
        if n(i) && n(j)
            p       = r{i}*r{j}';
            MI(i,j) = spm_MDP_MI(p);
            MI(j,i) = MI(i,j);
        end
    end
end

i  = 1:No;
G  = {};
dx = fix(dx);
U  = exp(-16);
iter_idx = 0;
while numel(i)

    iter_idx = iter_idx + 1;
    sub = MI(i,i);
    [e,v] = eig(sub,'nobalance');
    [~,jmax] = max(diag(v),[],1);
    [e_sorted,j] = sort(abs(e(:,jmax)),'descend');
    k     = 1:min(numel(j),dx);
    j     = j(k);

    rec = struct();
    rec.call_id = call_id;
    rec.iter_idx = iter_idx;
    rec.m = m;
    rec.dx = dx;
    rec.u_thresh = U;
    rec.active_before = i;
    rec.sub_mi = sub;
    rec.vals = diag(v);
    rec.evecs = e;
    rec.jmax = jmax;
    rec.absv_sorted = e_sorted;
    rec.sort_idx = j;
    rec.chosen = i(j);
    if isempty(rgms_entry4_spectral_records)
        rgms_entry4_spectral_records = {rec};
    else
        rgms_entry4_spectral_records{end + 1} = rec;
    end

    j(e_sorted(k) < U) = [];
    G{end + 1}  = i(j);
    i(j)        = [];

end

for g = 1:numel(G)
    j = (G{g} - 1)*m;
    k = [];
    for ii = 1:numel(j)
       k = [k, (j(ii) + (1:m))];
    end
    G{g} = k;
end

return
