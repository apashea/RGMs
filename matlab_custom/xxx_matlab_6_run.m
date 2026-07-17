function xxx_matlab_6_run()
%XXX_MATLAB_6_RUN  Call4 MATLAB PDP export with paired vb_rand_buf (XXX_matlab-6).
%
% Native matlab_src spm_MDP_VB_XXX + entry12 rand.m replay of the OPTIM1FULL
% call4 buffer. Saves PDP under logs/ — does not overwrite Product B fixtures.
%
% Authority: XXX_optim.md § XXX_matlab (HARD DIRECTIVE: no fidelity lane).

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(here);
fix = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures');
tag = 'rgms_atari_optim1full_call4';
rdpMat = fullfile(fix, sprintf('DEMAtariIII_XXX_12_%s_rdp.mat', tag));
bufMat = fullfile(fix, sprintf('DEMAtariIII_entry12_vb_matlab_rand_buf_%s.mat', tag));
outMat = fullfile(repoRoot, 'logs', sprintf('xxx_matlab_6_%s_matlab_pdp.mat', tag));
logPath = fullfile(repoRoot, 'logs', sprintf('optim1full_w2_XXX_matlab_6_matlab_export_%s.log', ...
    datestr(now, 'yyyymmdd_HHMMSS')));

diary(logPath);
fprintf(1, '[XM6] start %s\n', datestr(now, 31));
fprintf(1, '[XM6] tag=%s\n', tag);
fprintf(1, '[XM6] rdp=%s\n', rdpMat);
fprintf(1, '[XM6] buf=%s\n', bufMat);
fprintf(1, '[XM6] out=%s\n', outMat);

if ~isfile(rdpMat)
    error('XM6: missing RDP %s', rdpMat);
end
if ~isfile(bufMat)
    error('XM6: missing vb_rand_buf %s', bufMat);
end

global rgms_entry12_buf rgms_entry12_i rgms_entry12_use_replay
Sbuf = load(bufMat, 'vb_rand_buf');
rgms_entry12_buf = Sbuf.vb_rand_buf(:);
rgms_entry12_i = 1;
rgms_entry12_use_replay = true;
K = numel(rgms_entry12_buf);
fprintf(1, '[XM6] vb_rand_buf.k=%d\n', K);

% Scalar rand() shadow before matlab_src (same lane as entry12_VB_matlab_src_buf_replay).
addpath(fullfile(here, 'entry12'), '-begin');
addpath(genpath(fullfile(repoRoot, 'matlab_src')));

fprintf(1, '[XM6] which(spm_MDP_VB_XXX)=%s\n', which('spm_MDP_VB_XXX'));
fprintf(1, '[XM6] which(rand)=%s\n', which('rand'));

Srdp = load(rdpMat, 'RDP');
MDP = spm_MDP_checkX(Srdp.RDP);
OPTIONS = struct('B', 0, 'C', 0, 'D', 0, 'N', 0, 'O', 1, 'P', 0, 'Y', 1);

t0 = tic;
PDP = spm_MDP_VB_XXX(MDP, OPTIONS, false, false);
wall_s = toc(t0);

draws_used = rgms_entry12_i - 1;
unused = K - draws_used;
fprintf(1, '[XM6] wall_s=%.6f draws_used=%d unused=%d\n', wall_s, draws_used, unused);

meta = struct();
meta.tag = tag;
meta.K = K;
meta.draws_used = draws_used;
meta.unused_draws = unused;
meta.wall_s = wall_s;
meta.which_vb = which('spm_MDP_VB_XXX');
meta.which_rand = which('rand');
meta.rdp_mat = rdpMat;
meta.buf_mat = bufMat;
meta.note = 'XXX_matlab-6 MATLAB PDP export; paired vb_rand_buf; monitoring=false dump=false';

% v7 for scipy.io.loadmat (not v7.3 HDF5).
save(outMat, 'PDP', 'meta', '-v7');
fprintf(1, '[XM6] wrote %s\n', outMat);

rgms_entry12_use_replay = false;
fprintf(1, '[XM6] done %s\n', datestr(now, 31));
diary off;
end
