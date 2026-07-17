% Entry 4 — compare MATLAB sort(abs(x),'descend') on exported abs vectors.
% Called from Python inspection (eig.md §22); not used in production FSL.
function out = entry4_sort_abs_descend_probe(absvec)
    x = absvec(:);
    [~, ix] = sort(x, 'descend');
    out.ix = ix;
    out.sorted = x(ix);
end
