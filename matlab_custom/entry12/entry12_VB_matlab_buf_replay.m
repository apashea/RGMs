function out = entry12_VB_matlab_buf_replay()
%ENTRY12_VB_MATLAB_BUF_REPLAY Run VB replaying fixtures/vb_rand_buf (v5 lane).
%
% Uses the same RDP as XXX 12 (DEMAtariIII_fsl_1_11_rdp.mat), entry12_dump fork with
% dumps disabled, monitoring false. Scalar rand() is replayed via rand.m shadow
% in this directory (not twister seed). Compare G{1} to Python XXX 12 replay.
%
% Does not refresh vb_rand_buf.

global rgms_entry12_buf rgms_entry12_i rgms_entry12_use_replay

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));
fixtures = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
bufPath = fullfile(fixtures, 'DEMAtariIII_entry12_vb_matlab_rand_buf.mat');
rdpPath = fullfile(fixtures, 'DEMAtariIII_fsl_1_11_rdp.mat');

S = load(bufPath);
rgms_entry12_buf = S.vb_rand_buf(:);
rgms_entry12_i = 1;
rgms_entry12_use_replay = true;
K = numel(rgms_entry12_buf);

addpath(here, '-begin');  % rand.m shadow
addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(here);

Srdp = load(rdpPath);
MDP = spm_MDP_checkX(Srdp.RDP);
OPTIONS = entry12_default_options_sp_mdp_vb_xxx();
dumpSpec = struct('enabled', false);

tic;
PDP = spm_MDP_VB_XXX_entry12_dump(MDP, OPTIONS, dumpSpec);
wall = toc;

if rgms_entry12_i > K
    error('buffer overrun: used %d draws, K=%d', rgms_entry12_i - 1, K);
end
unused = K - rgms_entry12_i + 1;

g1 = NaN;
if iscell(PDP.G)
    g1 = double(PDP.G{1}(1));
elseif isnumeric(PDP.G)
    g1 = double(PDP.G(1));
end

out = struct();
out.K = K;
out.draws_used = rgms_entry12_i - 1;
out.unused_draws = unused;
out.G1 = g1;
out.wall_s = wall;
out.lane = 'entry12_dump enabled=false monitoring=false rand_buf_replay';

fprintf('[entry12 VB buf replay] %s\n', out.lane);
fprintf('  K=%d draws_used=%d unused=%d G1=%.12g wall_s=%.3f\n', ...
    K, out.draws_used, unused, g1, wall);

rgms_entry12_use_replay = false;

end


function OPTIONS = entry12_default_options_sp_mdp_vb_xxx()
OPTIONS = struct();
try, OPTIONS.B; catch, OPTIONS.B = 0; end
try, OPTIONS.C; catch, OPTIONS.C = 0; end
try, OPTIONS.D; catch, OPTIONS.D = 0; end
try, OPTIONS.N; catch, OPTIONS.N = 0; end
try, OPTIONS.O; catch, OPTIONS.O = 1; end
try, OPTIONS.P; catch, OPTIONS.P = 0; end
try, OPTIONS.Y; catch, OPTIONS.Y = 1; end
end
