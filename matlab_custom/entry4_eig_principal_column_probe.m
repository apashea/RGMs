% Entry 4 — mirror spm_rgm_group spectral step on one MI block (inspection only).
% Called from Python Engine instruments (eig.md §28); not production FSL.
function out = entry4_eig_principal_column_probe(sub_mi)
    A = sub_mi;
    n = size(A, 1);
    [e, v] = eig(A, 'nobalance');
    w = diag(v);
    aw = abs(w);
    [~, jmax] = max(aw, [], 1);
    col = e(:, jmax);
    absv = abs(col);
    [sorted_absv, order] = sort(absv, 'descend');
    [~, kmax] = max(abs(col));
    out.n = n;
    out.jmax = jmax;
    out.e = e;
    out.v = v;
    out.w = w;
    out.principal_col = col;
    out.absv = absv;
    out.order = order;
    out.sorted_absv = sorted_absv;
    out.kmax_abs_entry = kmax;
    out.col_l2_norm = norm(col);
    out.w_ascending = all(aw(1:end-1) <= aw(2:end) + 1e-15);
end
