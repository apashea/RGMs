% Evaluate spm_dot(R, Q(r)) on Python-frozen R, Qf at parent t=1.
RGMS = load('entry12_12f_frozen_RQf.mat');
R = RGMS.R;
Qf = RGMS.Qf;
r = RGMS.r;
Q = {Qf};
gdot = spm_dot(R, Q(r));
fprintf('MATLAB spm_dot frozen: %g  numel(R)=%d  nnz(R)=%d\n', gdot, numel(R), nnz(R));
if nnz(R) > 0
    nz = find(R > 0);
    fprintf('R_nz(1:4)=%s Q_at_nz=%s\n', mat2str(nz(1:min(4,end))'), mat2str(Qf(nz(1:min(4,end)))'));
end
