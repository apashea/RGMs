% xor thresholded B
S = load(fullfile(fileparts(fileparts(mfilename('fullpath'))), 'optim1full_call4_b_or.mat'));
u = 1/32;
b = false(size(S.BP, 1), size(S.BP, 2));
for k = 1:size(S.BP, 3)
    b = b | (S.BP(:, :, k) > u);
end
fprintf('xor nnz=%d py_nnz=%d mat_nnz=%d\n', nnz(xor(b, logical(S.b_py))), nnz(S.b_py), nnz(b));
