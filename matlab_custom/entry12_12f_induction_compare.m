% Compare spm_induction R and spm_dot with Python-frozen inputs.
function entry12_12f_induction_compare()
    S = load('entry12_12f_live_inputs.mat');
    B = S.Bslice;
    H = S.Hlist;
    P = S.Pnow;
    id = S.idm;
    R = spm_induction(B, H, P, S.Nhoriz, id);
    if isvector(R)
        R = R(:)';
    end
    Qf = S.Qf;
    d = spm_dot(R, Qf);
    fprintf('MAT R nnz=%d sum=%g\n', nnz(R), sum(R));
    fprintf('MAT R nz indices (1-based): ');
    fprintf('%d ', find(R > 0));
    fprintf('\n');
    fprintf('MAT spm_dot=%g\n', d);
end
