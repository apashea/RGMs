function xxx_matlab_7_run()
%XXX_MATLAB_7_RUN  Post-record F/Q.E sizes on call4 (XXX_matlab-7).
% Fork: matlab_custom/xxx_matlab_7/spm_MDP_VB_XXX.m + entry12 vb_rand_buf replay.
% Docs: XXX_optim.md § XXX_matlab. Does not overwrite Product B fixtures.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
fix = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures');
tag = 'rgms_atari_optim1full_call4';
rdpMat = fullfile(fix, sprintf('DEMAtariIII_XXX_12_%s_rdp.mat', tag));
bufMat = fullfile(fix, sprintf('DEMAtariIII_entry12_vb_matlab_rand_buf_%s.mat', tag));
outMat = fullfile(repoRoot, 'logs', sprintf('xxx_matlab_7_%s_matlab_rows.mat', tag));
logPath = fullfile(repoRoot, 'logs', sprintf('optim1full_w2_XXX_matlab_7_matlab_%s.log', ...
    datestr(now, 'yyyymmdd_HHMMSS')));

diary(logPath);
fprintf(1, '[XM7] start %s\n', datestr(now, 31));
fprintf(1, '[XM7] tag=%s rdp=%s buf=%s\n', tag, rdpMat, bufMat);

global rgms_entry12_buf rgms_entry12_i rgms_entry12_use_replay RGMS_XM7
Sbuf = load(bufMat, 'vb_rand_buf');
rgms_entry12_buf = Sbuf.vb_rand_buf(:);
rgms_entry12_i = 1;
rgms_entry12_use_replay = true;
K = numel(rgms_entry12_buf);
RGMS_XM7 = struct('on', true, 'n', 0, 'rows', {{}});

addpath(fullfile(here, 'entry12'), '-begin');
addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(fullfile(here, 'xxx_matlab_7'), '-begin');

fprintf(1, '[XM7] which(spm_MDP_VB_XXX)=%s\n', which('spm_MDP_VB_XXX'));
fprintf(1, '[XM7] which(rand)=%s\n', which('rand'));
fprintf(1, '[XM7] vb_rand_buf.k=%d\n', K);

Srdp = load(rdpMat, 'RDP');
MDP = spm_MDP_checkX(Srdp.RDP);
OPTIONS = struct('B', 0, 'C', 0, 'D', 0, 'N', 0, 'O', 1, 'P', 0, 'Y', 1);

t0 = tic;
spm_MDP_VB_XXX(MDP, OPTIONS, false, false);
wall_s = toc(t0);
draws_used = rgms_entry12_i - 1;
unused = K - draws_used;
fprintf(1, '[XM7] wall_s=%.6f draws_used=%d unused=%d n_rows=%d\n', ...
    wall_s, draws_used, unused, RGMS_XM7.n);

rows = RGMS_XM7.rows;
meta = struct('tag', tag, 'K', K, 'draws_used', draws_used, ...
    'unused_draws', unused, 'wall_s', wall_s, 'n_rows', RGMS_XM7.n, ...
    'note', 'XXX_matlab-7 post-record F/Q.E sizes');
save(outMat, 'rows', 'meta', '-v7');
fprintf(1, '[XM7] wrote %s\n', outMat);

% First diverge-friendly summary
if ~isempty(rows)
    r1 = rows{1};
    r2 = rows{min(2, numel(rows))};
    fprintf(1, '[XM7] SUMMARY first: n=%d t=%d path=%s F_numel=%d QE_L_numel=%d F_sum=%.6g Q_F=%.6g\n', ...
        r1.n, r1.t, r1.path, r1.F_numel, r1.QE_L_numel, r1.F_sum, r1.Q_F);
    if numel(rows) >= 2
        fprintf(1, '[XM7] SUMMARY second: n=%d t=%d path=%s F_numel=%d QE_L_numel=%d F_sum=%.6g Q_F=%.6g\n', ...
            r2.n, r2.t, r2.path, r2.F_numel, r2.QE_L_numel, r2.F_sum, r2.Q_F);
    end
    last = rows{end};
    fprintf(1, '[XM7] SUMMARY last: n=%d t=%d path=%s F_numel=%d QE_L_numel=%d F_sum=%.6g Q_F=%.6g\n', ...
        last.n, last.t, last.path, last.F_numel, last.QE_L_numel, last.F_sum, last.Q_F);
end

rgms_entry12_use_replay = false;
RGMS_XM7.on = false;
fprintf(1, '[XM7] done %s\n', datestr(now, 31));
diary off;
end
