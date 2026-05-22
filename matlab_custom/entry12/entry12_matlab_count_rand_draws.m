function out = entry12_matlab_count_rand_draws()
%ENTRY12_MATLAB_COUNT_RAND_DRAWS Count scalar rand() during VB (native RNG).
%
% Does not use vb_rand_buf replay. Logical spm_sample uses randperm (not counted).

global rgms_entry12_rand_count rgms_entry12_use_replay

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));
fixtures = fullfile(repoRoot, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
rdpPath = fullfile(fixtures, 'DEMAtariIII_fsl_1_11_rdp.mat');

addpath(here, '-begin');
addpath(genpath(fullfile(repoRoot, 'matlab_src')));

Srdp = load(rdpPath);
MDP = spm_MDP_checkX(Srdp.RDP);
OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

rgms_entry12_use_replay = false;
rgms_entry12_rand_count = 0;

% Count only via shadow rand when counting flag set
counting = true;
rgms_entry12_use_replay = counting;

tic;
PDP_dump = spm_MDP_VB_XXX(MDP, OPTIONS, false, true);
t_dump = toc;
n_dump = rgms_entry12_rand_count;

rgms_entry12_rand_count = 0;
tic;
PDP_src = spm_MDP_VB_XXX(MDP, OPTIONS, false, false);
t_src = toc;
n_src = rgms_entry12_rand_count;

g1_dump = local_g1(PDP_dump);
g1_src = local_g1(PDP_src);

Sk = load(fullfile(fixtures, 'entry12_vb_rand_K.mat'));
K_preflight = Sk.K(1);

out = struct();
out.K_preflight = K_preflight;
out.dump_subentries_true = struct('rand_calls', n_dump, 'G1', g1_dump, 'wall_s', t_dump);
out.dump_subentries_false = struct('rand_calls', n_src, 'G1', g1_src, 'wall_s', t_src);
out.delta_dump_minus_src = n_dump - n_src;
out.delta_dump_minus_K = n_dump - K_preflight;

fprintf('[entry12 count rand] K_preflight=%d\n', K_preflight);
fprintf('  dump=true  rand_calls=%d G1=%.12g\n', n_dump, g1_dump);
fprintf('  dump=false rand_calls=%d G1=%.12g\n', n_src, g1_src);

rgms_entry12_use_replay = false;

end


function g = local_g1(PDP)
g = NaN;
if iscell(PDP.G)
    g = double(PDP.G{1}(1));
elseif isnumeric(PDP.G)
    g = double(PDP.G(1));
end
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
