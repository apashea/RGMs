% Frozen ih / spm_dot from Python-saved parent t=1 inputs (replay lane).
function entry12_matlab_frozen_g_terms()
    S = load('entry12_12f_live_inputs.mat');
    R = S.Rv;
    if isvector(R)
        R = R(:)';
    end
    Qf = S.Qf;
    Hf = S.Hf;
    ih = (Qf' * (spm_log(Qf) - spm_log(Hf)));
    d = spm_dot(R, {Qf});
    fprintf('MAT ih=%g spm_dot=%g\n', ih, d);
    fprintf('R nz: '); fprintf('%d ', find(R > 0)); fprintf('\n');
    nz = find(R > 0);
    if ~isempty(nz)
        fprintf('Qf at R>0: %g %g\n', Qf(nz(1)), Qf(min(2, numel(nz))));
    end
end
