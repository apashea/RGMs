function DEMAtariIII_entry12_dump_all_subentries(mode)
%DEMATARIII_ENTRY12_DUMP_ALL_SUBENTRIES  Entry 12 MATLAB runner (script **1b**).
% Optional ``mode``:
%   ``'refresh_call2'`` — call-2 VB capture only (``RDP`` + ``K`` mats on disk).
%   ``'capture_call3'`` — ledger + NR active-inference loop + call-3 VB oracle
%      (``rgms_atari_call3``, post-loop ``spm_RDP_sort`` / ``T=128``).
%   ``'capture_call4'`` — same NR loop + call-4 VB oracle
%      (``rgms_atari_call4``, post-loop sort + ``spm_RDP_MI`` / ``T=128``).
%   ``'capture_optim1full_mi_boundaries'`` — same NR loop; write OPTIM1FULL
%      ``spm_RDP_MI`` authority mats (lines **382** + **429**) to
%      ``tests/demo1/optim1/fixtures/``; **no** VB capture (see ``OPTIM1.md`` § **11**).
%   ``'capture_optim1full_parity'`` — one ``rng(2)`` session: MI mats +
%      ``MDP_pre_active_inference`` + full NR (native VB) + call-3/4 Entry **12**
%      sign-off dumps to ``tests/demo1/optim1/fixtures/`` (see ``OPTIM1.md`` § **11.7.1**).
%   ``'capture_optim1full_call2_nr'`` — *(retired)* per-game call-2 tags — use
%      ``'capture_optim1full_rand_ledger'`` (§ ``OPTIM1.md`` **11.7.2**).
%   ``'capture_optim1full_dem_generative_ai'`` — Model **B** ledger replay through
%      ``vb_call1``; write ``DEMAtariIII_optim1full_dem_generative_ai_input.mat`` +
%      ``…_oracle.mat`` (Generative AI fence). See ``OPTIM1FULL.md`` § W1.
%   ``'capture_optim1full_rand_ledger'`` — one ``rng(2)`` scalar ledger + manifest
%      for full OPTIM1FULL compute path (no plot); writes ``optim1full_dem_atari_rand_buf.mat``.
%   ``'capture_optim1full_nr_g01_ledger'`` — Phase C: ledger ``MDP_pre`` NR game **1** RDP
%      → Entry **12** tag ``rgms_optim1full_nr_g01`` (§ ``OPTIM1.md`` **11.7.4**).
%   ``'capture_optim1full_entry12_from_authority'`` — Entry **12** tags **3a/3e/3f**
%      from on-disk Python authority ``MDP_pre`` / ``MDP_post_nr`` (no inline DEM, no
%      overwrite of authority ``.mat`` files). See ``OPTIM1FULL.md``.
%   ``'capture_optim1full_mi_from_authority'`` — MI-382/429 authority from on-disk
%      Python ``MDP_post_nr`` only (no NR loop; does **not** overwrite ``MDP_post_nr.mat``).
%      See ``optim1full_capture_mi_from_authority.py`` / ``OPTIM1FULL.md``.
%   ``'refresh_optim1full_call2_nr'`` — re-dump Entry **12** from on-disk ``RDP.mat``
%      per tag (no NR loop). Use after **12F** v7.3 save fix; env ``FROM``/``TO`` as above.
%
% One ``rng(2)`` session: FSL 1--11 ledger (inline), VB capture **call 1**
% (``rgms_canonical``), continue ``DEM_AtariIII.m`` through active-inference game 1,
% VB capture **call 2** (``rgms_atari_call2``). Same ``vb_rand_buf`` preamble-rewind
% per call. No separate RDP-build scripts.
%
% Optional (legacy call-1-only refresh from existing FSL ``.mat``):
%   RGMS_ENTRY12_CAPTURE_LEGACY_LOAD=1
%   RGMS_ENTRY12_CAPTURE_RDP_MAT=<path>   (default FSL fixture)
%   RGMS_ENTRY12_CAPTURE_SKIP_CALL2=1
%
% Environment (optional):
%   RGMS_ENTRY12_CAPTURE_RUN_TAG       — used only for legacy single-call load path
%   RGMS_ENTRY12_CAPTURE_OUT_DIR
%   RGMS_ENTRY12_CAPTURE_Y_PROBE
%
% Before **1b**: run **1a** ``entry12_preflight_vb_rand_k.py`` for ``rgms_canonical``.
% Call 2 ``K`` is counted inside this script (same draw sites as **1a**) before call-2 VB.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));

outDir = getenv('RGMS_ENTRY12_CAPTURE_OUT_DIR');
if isempty(outDir)
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    outDir = demo1_fixtures_dir(repoRoot);
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

addpath(genpath(fullfile(repoRoot, 'matlab_src')));
addpath(here);

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'refresh_call2')
    rdpPath = entry12_xxx12_rdp_mat_(outDir, 'rgms_atari_call2');
    if ~isfile(rdpPath)
        error('Missing call-2 RDP mat: %s', rdpPath);
    end
    S = load(rdpPath, 'RDP');
    fprintf(1, '[entry12 dump] refresh_call2 started %s\n', datestr(now, 31));
    entry12_dump_one_vb_call_(S.RDP, 'rgms_atari_call2', outDir, rdpPath, 'refresh_call2');
    fprintf(1, '[entry12 dump] refresh_call2 done\n');
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_call2_game1')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_call2_game1 started %s\n', datestr(now, 31));
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    MDP_pre_active_inference = entry12_mdp_mat_deep_copy_(MDP);
    meta = struct('capture', 'capture_call2_game1', 'timestamp', datestr(now, 31));
    save(fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat'), ...
        'MDP_pre_active_inference', 'Nm', 'Ne', 'meta', '-v7');
    fprintf(1, '[entry12 dump] wrote %s\n', fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat'));
    RDP2 = entry12_dem_call2_rdp_game1_(MDP, GDP, Ne, C);
    entry12_count_and_save_vb_rand_k_(RDP2, outDir, 'rgms_atari_optim1full_call2');
    entry12_dump_one_vb_call_(RDP2, 'rgms_atari_optim1full_call2', outDir, 'optim1full_call2_game1', 'capture_call2_game1');
    fprintf(1, '[entry12 dump] capture_call2_game1 finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_call3')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_call3 started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    NT = 256;
    NS = 256;
    NR = 32;
    MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR);
    RDP3 = entry12_dem_call3_rdp_post_loop_(MDP, C, NS);
    entry12_count_and_save_vb_rand_k_(RDP3, outDir, 'rgms_atari_call3');
    entry12_dump_one_vb_call_(RDP3, 'rgms_atari_call3', outDir, 'inline_nr_loop_post_call3', 'capture_call3');
    fprintf(1, '[entry12 dump] capture_call3 finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_mi_boundaries')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_mi_boundaries started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    NT = 256;
    NS = 256;
    NR = 32;
    MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR);
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    entry12_save_optim1full_mi_boundaries_(MDP, Nm, optim1Dir);
    fprintf(1, '[entry12 dump] capture_optim1full_mi_boundaries finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_parity')
    % One rng(2) session: MI authority mats + NR entry MDP + call-3/4 VB sign-off chain.
    % NR loop uses native rand (authority for MDP_post_nr). Per-game call-2 buffers: future work.
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_parity started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    MDP_pre_active_inference = entry12_mdp_mat_deep_copy_(MDP);
    meta = struct('capture', 'capture_optim1full_parity', 'timestamp', datestr(now, 31));
    save(fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat'), ...
        'MDP_pre_active_inference', 'Nm', 'Ne', 'meta', '-v7');
    fprintf(1, '[entry12 dump] wrote %s\n', fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat'));
    NT = 256;
    NS = 256;
    NR = 32;
    MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR);
    entry12_save_optim1full_mi_boundaries_(MDP, Nm, optim1Dir);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    RDP3 = entry12_dem_call3_rdp_post_loop_(MDP, C, NS);
    entry12_count_and_save_vb_rand_k_(RDP3, outDir, 'rgms_atari_optim1full_call3');
    entry12_dump_one_vb_call_(RDP3, 'rgms_atari_optim1full_call3', outDir, 'optim1full_parity_call3', 'capture_optim1full_parity');
    RDP4 = entry12_dem_call4_rdp_post_loop_(MDP, C, NS);
    entry12_count_and_save_vb_rand_k_(RDP4, outDir, 'rgms_atari_optim1full_call4');
    entry12_dump_one_vb_call_(RDP4, 'rgms_atari_optim1full_call4', outDir, 'optim1full_parity_call4', 'capture_optim1full_parity');
    fprintf(1, '[entry12 dump] capture_optim1full_parity finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_call2_nr')
    % OPTIM1FULL tier **3b–3c**: per-game call-2 ``vb_rand_buf`` for NR games **2–32**.
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_call2_nr started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    NT = 256;
    NS = 256;
    NR = 32;
    firstGame = entry12_env_int_('RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM', 2);
    lastGame = entry12_env_int_('RGMS_OPTIM1FULL_CALL2_CAPTURE_TO', 32);
    firstGame = max(1, min(firstGame, NR));
    lastGame = max(firstGame, min(lastGame, NR));
    fprintf(1, '[entry12 dump] call-2 NR capture games %d..%d (game 1 native when firstGame>1)\n', ...
        firstGame, lastGame);
    MDP = entry12_dem_active_inference_nr_loop_call2_capture_( ...
        MDP, GDP, Ne, C, Nm, NT, NS, NR, outDir, ...
        'capture_optim1full_call2_nr', firstGame, lastGame);
    fprintf(1, '[entry12 dump] capture_optim1full_call2_nr finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_nr_g01_ledger')
    % OPTIM1FULL Phase C — Entry **12** tag on ledger ``MDP_pre`` NR game **1** RDP (§ **11.7.4**).
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_nr_g01_ledger started %s\n', datestr(now, 31));
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    preMat = fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat');
    if ~isfile(preMat)
        error('OPTIM1FULL Phase C: missing %s — run capture_optim1full_rand_ledger first', preMat);
    end
    S = load(preMat, 'MDP_pre_active_inference', 'Ne');
    MDP = S.MDP_pre_active_inference;
    Ne = S.Ne;
    C = 32;
    NT = 256;
    NS = 256;
    tag = 'rgms_atari_optim1full_nr_g01';
    RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
    RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
    RDP.T = fix(NT / Ne);
    fprintf(1, '[entry12 dump] ledger NR g01 RDP T=%d Ne=%d (from %s)\n', RDP.T, Ne, preMat);
    entry12_count_and_save_vb_rand_k_(RDP, outDir, tag);
    entry12_dump_one_vb_call_(RDP, tag, outDir, 'optim1full_ledger_nr_g01', 'capture_optim1full_nr_g01_ledger');
    fprintf(1, '[entry12 dump] capture_optim1full_nr_g01_ledger finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_entry12_from_authority')
    % OPTIM1FULL — Entry **12** VB fixtures from on-disk RDP (Python authority overlay).
    % RDP mats must exist (``optim1full_capture_entry12_from_authority.py`` phase 1).
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_entry12_from_authority started %s\n', datestr(now, 31));
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    captureMode = 'capture_optim1full_entry12_from_authority';
    tags = {'rgms_atari_optim1full_call2', 'rgms_atari_optim1full_call3', 'rgms_atari_optim1full_call4'};
    rdpSources = {'optim1full_authority_call2', 'optim1full_authority_call3', 'optim1full_authority_call4'};
    for k = 1:numel(tags)
        tag = tags{k};
        rdpPath = entry12_xxx12_rdp_mat_(outDir, tag);
        if ~isfile(rdpPath)
            error('OPTIM1FULL Entry 12: missing RDP for tag %s: %s — run Python RDP phase first', tag, rdpPath);
        end
        S = load(rdpPath, 'RDP');
        fprintf(1, '[entry12 dump] authority VB dump tag=%s from %s\n', tag, rdpPath);
        entry12_count_and_save_vb_rand_k_(S.RDP, outDir, tag);
        entry12_dump_one_vb_call_(S.RDP, tag, outDir, rdpSources{k}, captureMode);
    end
    fprintf(1, '[entry12 dump] capture_optim1full_entry12_from_authority finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_mi_from_authority')
    % OPTIM1FULL — MI boundary mats from on-disk Python authority ``MDP_post_nr``.
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_mi_from_authority started %s\n', datestr(now, 31));
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    postPath = fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_post_nr.mat');
    if ~isfile(postPath)
        error('OPTIM1FULL MI from authority: missing %s', postPath);
    end
    S = load(postPath);
    if ~isfield(S, 'MDP_post_nr')
        error('OPTIM1FULL MI from authority: %s missing MDP_post_nr', postPath);
    end
    if isfield(S, 'metaPost') && isfield(S.metaPost, 'capture')
        cap = char(S.metaPost.capture);
        if ~strcmpi(strtrim(cap), 'capture_optim1full_python_product_b')
            error('OPTIM1FULL MI from authority: metaPost.capture=%s expected capture_optim1full_python_product_b', cap);
        end
    end
    MDP_post_nr = S.MDP_post_nr;
    if isfield(S, 'Nm')
        Nm = S.Nm;
    else
        Nm = numel(MDP_post_nr);
    end
    miOpts = struct();
    miOpts.savePostNr = false;
    miOpts.metaSource = 'capture_optim1full_mi_from_authority';
    miOpts.metaCapture = 'capture_optim1full_python_product_b';
    miOpts.authorityPostMat = postPath;
    entry12_save_optim1full_mi_boundaries_(MDP_post_nr, Nm, optim1Dir, miOpts);
    fprintf(1, '[entry12 dump] capture_optim1full_mi_from_authority finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_call4_extended_boundaries')
    % OPTIM1FULL call4 — re-dump with extended lean boundaries (t=10,20,30) via optim1full dump fork.
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_call4_extended_boundaries started %s\n', datestr(now, 31));
    optim1DumpDir = fullfile(repoRoot, 'matlab_custom', 'optim1full');
    addpath(optim1DumpDir, '-begin');
    dumpWhich = which('spm_MDP_VB_XXX_entry12_dump');
    fprintf(1, '[entry12 dump] dump fork: %s\n', dumpWhich);
    if isempty(dumpWhich) || ~contains(dumpWhich, [filesep, 'optim1full', filesep])
        error('OPTIM1FULL extended boundaries: expected matlab_custom/optim1full dump fork on path, got: %s', dumpWhich);
    end
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    captureMode = 'capture_optim1full_call4_extended_boundaries';
    tag = 'rgms_atari_optim1full_call4';
    rdpPath = entry12_xxx12_rdp_mat_(outDir, tag);
    if ~isfile(rdpPath)
        error('OPTIM1FULL call4 extended: missing RDP %s', rdpPath);
    end
    S = load(rdpPath, 'RDP');
    fprintf(1, '[entry12 dump] call4 extended VB dump tag=%s from %s\n', tag, rdpPath);
    if ~isfile(entry12_vb_rand_k_mat_(outDir, tag))
        entry12_count_and_save_vb_rand_k_(S.RDP, outDir, tag);
    end
    entry12_dump_one_vb_call_(S.RDP, tag, outDir, 'optim1full_call4_extended_boundary', captureMode);
    fprintf(1, '[entry12 dump] capture_optim1full_call4_extended_boundaries finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_dem_generative_ai')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_dem_generative_ai started %s\n', datestr(now, 31));
    entry12Dir = here;
    cd(repoRoot);
    if any(strcmp(entry12Dir, strsplit(path, pathsep)))
        rmpath(entry12Dir);
    end
    addpath(fullfile(repoRoot, 'matlab_custom', 'optim1full'), '-begin');
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    addpath(genpath(fullfile(repoRoot, 'matlab_src')), '-begin');
    randShadow = which('rand');
    fprintf(1, '[entry12 dump] dem_generative_ai rand shadow: %s\n', randShadow);
    if isempty(randShadow) || ~contains(randShadow, 'optim1full')
        error('OPTIM1FULL dem_generative_ai: expected optim1full/rand.m on path, got: %s', randShadow);
    end
    optim1Dir = optim1full_fixtures_dir(repoRoot);

    bufMat = fullfile(optim1Dir, 'optim1full_dem_atari_rand_buf.mat');
    if ~isfile(bufMat)
        error('OPTIM1FULL dem_generative_ai: missing %s', bufMat);
    end
    Sbuf = load(bufMat, 'dem_atari_rand_buf');
    buf = Sbuf.dem_atari_rand_buf(:);

    manifestPath = fullfile(optim1Dir, 'optim1full_rand_manifest.json');
    if ~isfile(manifestPath)
        error('OPTIM1FULL dem_generative_ai: missing %s', manifestPath);
    end
    manifest = jsondecode(fileread(manifestPath));
    k11 = 0;
    kvb = 0;
    for si = 1:numel(manifest.segments)
        sid = manifest.segments(si).id;
        if strcmp(sid, 'entries_1_11')
            k11 = double(manifest.segments(si).k);
        elseif strcmp(sid, 'vb_call1')
            kvb = double(manifest.segments(si).k);
        end
    end
    if k11 < 1 || kvb < 1
        error('OPTIM1FULL dem_generative_ai: manifest missing entries_1_11 or vb_call1 k');
    end
    kReplay = k11 + kvb;

    optim1full_rand_replay_begin(buf, 0);
    try
        OPTIONS = entry12_default_options_sp_mdp_vb_xxx();
        [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
        RDP1 = spm_set_goals(MDP, [2, 3], [C, -C]);
        RDP1 = spm_set_costs(RDP1, [2, 3], [C, -C]);
        RDP1 = spm_mdp2rdp(RDP1);
        RDP1.T = 64;
        PDP = spm_MDP_VB_XXX(spm_MDP_checkX(RDP1), OPTIONS, false, false);
        global rgms_optim1full_rand_idx
        drawsUsed = rgms_optim1full_rand_idx - 1;
        if drawsUsed ~= kReplay
            error('OPTIM1FULL dem_generative_ai: replay used %d draws, expected %d', drawsUsed, kReplay);
        end
    catch me
        optim1full_rand_replay_end();
        rethrow(me);
    end
    optim1full_rand_replay_end();

    pdpOut = fullfile(optim1Dir, 'DEMAtariIII_optim1full_dem_generative_ai_input.mat');
    metaPdp = struct();
    metaPdp.capture = 'capture_optim1full_dem_generative_ai';
    metaPdp.timestamp = datestr(now, 31);
    metaPdp.ledger_k = kReplay;
    save(pdpOut, 'PDP', 'metaPdp', '-v7');
    fprintf(1, '[entry12 dump] wrote %s\n', pdpOut);

    plotCtx = fullfile(optim1Dir, 'DEMAtariIII_optim1full_plot_ctx.mat');
    if ~isfile(plotCtx)
        error('OPTIM1FULL dem_generative_ai: missing %s (run plot_ctx D2a)', plotCtx);
    end
    oracleOut = fullfile(optim1Dir, 'DEMAtariIII_optim1full_dem_generative_ai_oracle.mat');
    visDir = fullfile(repoRoot, 'visualizations');
    if ~exist(visDir, 'dir')
        mkdir(visDir);
    end
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', optim1Dir);
    setenv('RGMS_OPTIM1FULL_FIXTURES_DIR', optim1Dir);
    setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', 'dem_generative_ai');
    setenv('RGMS_ENTRY12_12PLOT_PDP_MAT', pdpOut);
    setenv('RGMS_ENTRY12_12PLOT_CTX_MAT', plotCtx);
    setenv('RGMS_ENTRY12_12PLOT_VIS_DIR', visDir);
    setenv('RGMS_ENTRY12_12PLOT_FIGURE_TITLE', 'Generative AI');
    setenv('RGMS_ENTRY12_12PLOT_HITS_Y', '0');
    setenv('RGMS_ENTRY12_12PLOT_NT', '');
    setenv('RGMS_ENTRY12_12PLOT_MOVIE', '');
    setenv('RGMS_ENTRY12_12PLOT_ORACLE_MAT', oracleOut);
    engDir = fullfile(repoRoot, 'matlab_custom', 'entry12');
    oldDir = pwd;
    cd(engDir);
    try
        DEMAtariIII_entry12_12plot_capture();
    catch me
        cd(oldDir);
        rethrow(me);
    end
    cd(oldDir);
    if ~isfile(oracleOut)
        error('OPTIM1FULL dem_generative_ai: oracle not written: %s', oracleOut);
    end
    fprintf(1, '[entry12 dump] wrote %s\n', oracleOut);
    fprintf(1, '[entry12 dump] capture_optim1full_dem_generative_ai finished — elapsed %.1f s\n', toc(tRun));
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_optim1full_rand_ledger')
    % OPTIM1FULL Model B — one scalar ``rand()`` ledger through full compute (no plot).
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_optim1full_rand_ledger started %s\n', datestr(now, 31));
    fslDir = fullfile(repoRoot, 'matlab_custom', 'fsl_backward');
    entry12Dir = here;
    % Leave ``entry12/`` cwd — MATLAB prepends pwd and would shadow with ``entry12/rand.m``.
    cd(repoRoot);
    if any(strcmp(entry12Dir, strsplit(path, pathsep)))
        rmpath(entry12Dir);
    end
    addpath(fslDir, '-begin');
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    randShadow = which('rand');
    fprintf(1, '[entry12 dump] ledger rand shadow: %s\n', randShadow);
    if isempty(randShadow) || ~contains(randShadow, 'fsl_backward')
        error('OPTIM1FULL ledger capture: expected fsl_backward/rand.m on path, got: %s', randShadow);
    end
    optim1Dir = optim1full_fixtures_dir(repoRoot);

    % OPTIM1FULL plot-fence authority trace (env-gated; OPTIM1FULL.md § Parity-with-plots).
    % When on, save MATLAB-owned plot-fence authority at each DEM_AtariIII.m illustrate
    % fence, in-flow, no extra VB/generate / no extra rand() draws:
    %   PDP fences (…_matlab_pdp.mat): Gameplay / Generative AI / Active inference NR /
    %     before/with compression RGB
    %   Payload fences (…_matlab_payload.mat): Attractors basin NS…NH, Attractors post-sort
    %     b1/hid, Structure learning F (6×NR) — same meta.capture family
    plotFenceTrace = entry12_env_truthy_('RGMS_OPTIM1FULL_PLOT_FENCE_TRACE');
    if plotFenceTrace
        fprintf(1, '[entry12 dump] plot-fence authority trace ON -> %s\n', optim1Dir);
    end

    rng(2);
    rgms_fsl_rand_log_begin();
    segments = {};
    OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

    i0 = rgms_fsl_rand_log_count();
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_(plotFenceTrace, optim1Dir);
    segments{end + 1} = entry12_ledger_segment_(i0, 'entries_1_11'); %#ok<AGROW>
    if segments{end}.k < 1
        error('OPTIM1FULL ledger: entries_1_11 logged 0 draws (rand shadow broken)');
    end
    fprintf(1, '[entry12 dump] ledger entries_1_11 k=%d\n', segments{end}.k);

    i0 = rgms_fsl_rand_log_count();
    RDP1 = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP1 = spm_set_costs(RDP1, [2, 3], [C, -C]);
    RDP1 = spm_mdp2rdp(RDP1);
    RDP1.T = 64;
    PDP_fence_vb1 = spm_MDP_VB_XXX(spm_MDP_checkX(RDP1), OPTIONS, false, false);
    segments{end + 1} = entry12_ledger_segment_(i0, 'vb_call1'); %#ok<AGROW>
    if plotFenceTrace
        entry12_save_optim1full_plot_fence_(PDP_fence_vb1, 'dem_generative_ai', optim1Dir);
    end

    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    MDP_pre_active_inference = entry12_mdp_mat_deep_copy_(MDP);
    metaPre = struct();
    metaPre.capture = 'capture_optim1full_rand_ledger';
    metaPre.timestamp = datestr(now, 31);
    save(fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat'), ...
        'MDP_pre_active_inference', 'Nm', 'Ne', 'metaPre', '-v7');
    fprintf(1, '[entry12 dump] wrote %s (pre-NR)\n', ...
        fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_pre_active_inference.mat'));

    NT = 256;
    NS = 256;
    NR = 32;
    % OPTIM1FULL per-game NR authority trace (env-gated; OPTIM1FULL.md § "Per-game
    % NR authority trace"). Saves each game's VB input RDP, MATLAB VB output PDP, and
    % post-merge/basin MDP so the optim XXX can be localized game-by-game vs MATLAB
    % WITHOUT ever re-running the fidelity Python NR loop. No extra VB calls; RDP/PDP
    % already exist in-loop and the MDP deep-copy consumes no rand() draws.
    nrTrace = entry12_env_truthy_('RGMS_OPTIM1FULL_NR_AUTHORITY_TRACE');
    if nrTrace
        nrTraceDir = fullfile(optim1Dir, 'optim1full_nr_authority');
        if ~exist(nrTraceDir, 'dir')
            mkdir(nrTraceDir);
        end
        nrTraceMeta = cell(1, NR);
        fprintf(1, '[entry12 dump] NR authority per-game trace ON -> %s\n', nrTraceDir);
    end
    % Structure-learning plot fence: accumulate F (6×NR) like DEM_AtariIII.m 253–293
    % (after VB, before merge/basin); save after i==NR. No extra rand()/VB.
    if plotFenceTrace
        F_struct = NaN(6, NR);
    end
    for i = 1:NR
        i0 = rgms_fsl_rand_log_count();
        RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
        RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
        RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
        RDP.T = fix(NT / Ne);
        PDP = spm_MDP_VB_XXX(RDP, OPTIONS, false, false);
        if plotFenceTrace
            % DEM_AtariIII.m Structure learning numerics (same order as script).
            hHits = find(PDP.Q.o{1}(GDP.id.reward, :) > 1);
            F_struct(1, i) = size(PDP.B{1}, 2);
            F_struct(2, i) = size(PDP.B{1}, 3);
            F_struct(3, i) = PDP.Q.F + sum(PDP.F);
            F_struct(4, i) = numel(hHits);
            F_struct(5, i) = size(MDP{end}.b{1}, 2);
            F_struct(6, i) = size(MDP{end}.b{1}, 3);
        end
        O = PDP.Q.O{1};
        t = 0:(NT - Ne);
        for s = 1:Ne
            MDP = spm_merge_structure_learning(O(:, t + s), MDP);
        end
        MDP = spm_RDP_basin(MDP, [2, 3], [C, -C]);
        seg = entry12_ledger_segment_(i0, sprintf('nr_game_%02d', i));
        segments{end + 1} = seg; %#ok<AGROW>
        if nrTrace
            rdpOut = fullfile(nrTraceDir, sprintf('DEMAtariIII_optim1full_nr_game_%02d_rdp.mat', i));
            pdpOut = fullfile(nrTraceDir, sprintf('DEMAtariIII_optim1full_nr_game_%02d_pdp.mat', i));
            mdpOut = fullfile(nrTraceDir, sprintf('DEMAtariIII_optim1full_nr_game_%02d_mdp.mat', i));
            save(rdpOut, 'RDP', '-v7');
            save(pdpOut, 'PDP', '-v7');
            MDP_post_game = entry12_mdp_mat_deep_copy_(MDP);
            save(mdpOut, 'MDP_post_game', 'Nm', 'Ne', '-v7');
            gm = struct();
            gm.game = i;
            gm.segment = seg;
            gm.rdp_mat = sprintf('DEMAtariIII_optim1full_nr_game_%02d_rdp.mat', i);
            gm.pdp_mat = sprintf('DEMAtariIII_optim1full_nr_game_%02d_pdp.mat', i);
            gm.mdp_mat = sprintf('DEMAtariIII_optim1full_nr_game_%02d_mdp.mat', i);
            gm.np = entry12_count_mdp_np_(MDP, Nm);
            nrTraceMeta{i} = gm;
        end
        if plotFenceTrace && i == NR
            % DEM_AtariIII.m Active inference fence uses the final NR game VB output PDP.
            entry12_save_optim1full_plot_fence_(PDP, 'dem_active_inference_nr', optim1Dir);
            % Structure learning fence: final F traces after i==NR.
            entry12_save_optim1full_plot_fence_payload_( ...
                'dem_structure_learning', optim1Dir, struct('F', F_struct));
        end
        if mod(i, 8) == 0 || i == NR
            fprintf(1, '[entry12 dump] ledger NR game %d/%d (T=%d)\n', i, NR, RDP.T);
        end
    end
    if nrTrace
        nrMan = struct();
        nrMan.protocol = 'optim1full_nr_authority_trace_v1';
        nrMan.capture_mode = 'capture_optim1full_rand_ledger';
        nrMan.rng_seed = 2;
        nrMan.nr = NR;
        nrMan.nm = Nm;
        nrMan.ne = Ne;
        nrMan.authority_post_nr_mat = 'DEMAtariIII_optim1full_MDP_post_nr.mat';
        nrMan.timestamp = datestr(now, 31);
        nrMan.games = [nrTraceMeta{:}];
        nrManPath = fullfile(nrTraceDir, 'optim1full_nr_authority_manifest.json');
        fid2 = fopen(nrManPath, 'w');
        if fid2 < 0
            error('Cannot write NR authority manifest: %s', nrManPath);
        end
        fprintf(fid2, '%s', jsonencode(nrMan));
        fclose(fid2);
        fprintf(1, '[entry12 dump] wrote %s (%d games)\n', nrManPath, NR);
    end

    MDP_post_nr = entry12_mdp_mat_deep_copy_(MDP);
    metaPost = struct();
    metaPost.capture = 'capture_optim1full_rand_ledger';
    metaPost.timestamp = datestr(now, 31);
    metaPost.rng_seed = 2;
    save(fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_post_nr.mat'), ...
        'MDP_post_nr', 'Nm', 'Ne', 'metaPost', '-v7');
    fprintf(1, '[entry12 dump] wrote %s (post-NR)\n', ...
        fullfile(optim1Dir, 'DEMAtariIII_optim1full_MDP_post_nr.mat'));

    i0 = rgms_fsl_rand_log_count();
    RDP3 = entry12_dem_call3_rdp_post_loop_(MDP, C, NS);
    PDP_fence_vb3 = spm_MDP_VB_XXX(RDP3, OPTIONS, false, false);
    segments{end + 1} = entry12_ledger_segment_(i0, 'vb_call3'); %#ok<AGROW>
    if plotFenceTrace
        entry12_save_optim1full_plot_fence_(PDP_fence_vb3, 'dem_before_compression_rgb', optim1Dir);
    end

    i0 = rgms_fsl_rand_log_count();
    RDP4 = entry12_dem_call4_rdp_post_loop_(MDP, C, NS);
    PDP_fence_vb4 = spm_MDP_VB_XXX(RDP4, OPTIONS, false, false);
    segments{end + 1} = entry12_ledger_segment_(i0, 'vb_call4'); %#ok<AGROW>
    if plotFenceTrace
        entry12_save_optim1full_plot_fence_(PDP_fence_vb4, 'dem_with_compression_rgb', optim1Dir);
    end

    [dem_atari_rand_buf, K_total] = rgms_fsl_rand_log_finish();
    if K_total < 1
        error('OPTIM1FULL ledger capture: K_total=%d (expected >> 4096)', K_total);
    end
    fprintf(1, '[entry12 dump] ledger K_total=%d (which rand was %s)\n', K_total, randShadow);

    manifest = struct();
    manifest.protocol = 'optim1full_scalar_rand_log_v1';
    manifest.rng_seed = 2;
    manifest.plotting = 'omitted';
    manifest.k_total = K_total;
    manifest.timestamp = datestr(now, 31);
    manifest.capture_script = mfilename;
    manifest.capture_mode = 'capture_optim1full_rand_ledger';
    manifest.matlab_release = version;
    manifest.segments = [segments{:}];

    meta = struct();
    meta.note = 'OPTIM1FULL Model B ledger — actual scalar rand() values; not per-tag vb_rand_buf.';
    meta.capture_script = mfilename;
    meta.timestamp = manifest.timestamp;

    bufMat = fullfile(optim1Dir, 'optim1full_dem_atari_rand_buf.mat');
    save(bufMat, 'dem_atari_rand_buf', 'K_total', 'meta', '-v7');
    fprintf(1, '[entry12 dump] wrote %s (K_total=%d)\n', bufMat, K_total);

    jsonPath = fullfile(optim1Dir, 'optim1full_rand_manifest.json');
    fid = fopen(jsonPath, 'w');
    if fid < 0
        error('Cannot write manifest: %s', jsonPath);
    end
    fprintf(fid, '%s', jsonencode(manifest));
    fclose(fid);
    fprintf(1, '[entry12 dump] wrote %s (%d segments)\n', jsonPath, numel(segments));

    fprintf(1, '[entry12 dump] capture_optim1full_rand_ledger finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'refresh_optim1full_call2_nr')
    % Re-run script **1b** dump from paired ``RDP.mat`` (fix incomplete **12F** mats, etc.).
    tRun = tic;
    fprintf(1, '[entry12 dump] refresh_optim1full_call2_nr started %s\n', datestr(now, 31));
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    outDir = optim1Dir;
    setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);
    firstGame = entry12_env_int_('RGMS_OPTIM1FULL_CALL2_CAPTURE_FROM', 4);
    lastGame = entry12_env_int_('RGMS_OPTIM1FULL_CALL2_CAPTURE_TO', 32);
    firstGame = max(2, min(firstGame, 32));
    lastGame = max(firstGame, min(lastGame, 32));
    for i = firstGame:lastGame
        tag = entry12_call2_tag_for_game_(i);
        rdpPath = entry12_xxx12_rdp_mat_(outDir, tag);
        if ~isfile(rdpPath)
            error('Missing RDP for tag %s: %s', tag, rdpPath);
        end
        S = load(rdpPath, 'RDP');
        fprintf(1, '[entry12 dump] refresh tag=%s game %d/%d\n', tag, i, lastGame);
        entry12_count_and_save_vb_rand_k_(S.RDP, outDir, tag);
        entry12_dump_one_vb_call_(S.RDP, tag, outDir, sprintf('refresh_nr_g%02d', i), ...
            'refresh_optim1full_call2_nr');
    end
    fprintf(1, '[entry12 dump] refresh_optim1full_call2_nr finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

if nargin >= 1 && ~isempty(mode) && strcmpi(strtrim(mode), 'capture_call4')
    tRun = tic;
    fprintf(1, '[entry12 dump] capture_call4 started %s\n', datestr(now, 31));
    rng(2);
    [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
    MDP = entry12_dem_attach_generative_process_(MDP, GDP);
    NT = 256;
    NS = 256;
    NR = 32;
    MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR);
    addpath(genpath(fullfile(repoRoot, 'matlab_custom', 'demo1')), '-begin');
    optim1Dir = optim1full_fixtures_dir(repoRoot);
    entry12_save_optim1full_mi_boundaries_(MDP, Nm, optim1Dir);
    RDP4 = entry12_dem_call4_rdp_post_loop_(MDP, C, NS);
    entry12_count_and_save_vb_rand_k_(RDP4, outDir, 'rgms_atari_call4');
    entry12_dump_one_vb_call_(RDP4, 'rgms_atari_call4', outDir, 'inline_nr_loop_post_call4', 'capture_call4');
    fprintf(1, '[entry12 dump] capture_call4 finished — elapsed %.1f s (%.2f min)\n', ...
        toc(tRun), toc(tRun) / 60);
    return;
end

tRun = tic;
fprintf(1, '[entry12 dump] started %s\n', datestr(now, 31));

legacyLoad = entry12_env_truthy_('RGMS_ENTRY12_CAPTURE_LEGACY_LOAD');
skipCall2 = entry12_env_truthy_('RGMS_ENTRY12_CAPTURE_SKIP_CALL2');

if legacyLoad
    rdpMat = getenv('RGMS_ENTRY12_CAPTURE_RDP_MAT');
    if isempty(rdpMat)
        rdpMat = fullfile(outDir, 'DEMAtariIII_fsl_1_11_rdp.mat');
    end
    if ~exist(rdpMat, 'file')
        error('RDP mat not found: %s', rdpMat);
    end
    S = load(rdpMat, 'RDP');
    RDP = S.RDP;
    rdpSource = rdpMat;
    fprintf(1, '[entry12 dump] legacy load call 1 RDP from %s\n', rdpMat);
    entry12_dump_one_vb_call_(RDP, 'rgms_canonical', outDir, rdpSource, 'legacy_call1');
    if skipCall2
        fprintf(1, '[entry12 dump] SKIP_CALL2 — finished legacy call 1 only\n');
        return;
    end
    error(['Legacy load cannot continue to call 2 (MDP workspace missing). ', ...
        'Omit RGMS_ENTRY12_CAPTURE_LEGACY_LOAD for full inline ledger + call 2.']);
end

% Inline ``rng(2)`` ledger through Entry 11 (``dump_rdp_DEM_AtariIII_FSL_1_11.m`` lane).
rng(2);
[MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_();
RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP);
RDP.T = 64;
rdpSource = 'inline_rng2_DEM_AtariIII_entry11';

entry12_dump_one_vb_call_(RDP, 'rgms_canonical', outDir, rdpSource, 'inline_call1');

if ~skipCall2
    fprintf(1, '[entry12 dump] elapsed %.1f s — continue DEM_AtariIII active inference (game 1)\n', toc(tRun));
    RDP2 = entry12_dem_call2_rdp_game1_(MDP, GDP, Ne, C);
    entry12_count_and_save_vb_rand_k_(RDP2, outDir, 'rgms_atari_call2');
    entry12_dump_one_vb_call_(RDP2, 'rgms_atari_call2', outDir, 'inline_after_call1_game1', 'inline_call2');
end

fprintf(1, '[entry12 dump] finished %s — total elapsed %.1f s (%.2f min)\n', ...
    datestr(now, 31), toc(tRun), toc(tRun) / 60);
end


function PDP = entry12_dump_one_vb_call_(RDP, tag, outDir, rdpSource, captureMode)
% One VB invocation + Entry 12 subentry capture for ``tag``. Returns ``PDP`` for NR-loop merge.

setenv('RGMS_ENTRY12_CAPTURE_RUN_TAG', tag);
setenv('RGMS_ENTRY12_CAPTURE_OUT_DIR', outDir);

rdpOut = entry12_xxx12_rdp_mat_(outDir, tag);
save(rdpOut, 'RDP', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, rdpOut);

OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

meta = struct();
meta.run_tag = tag;
meta.rdp_source = rdpSource;
meta.capture_mode = captureMode;
meta.capture_script = which('DEMAtariIII_entry12_dump_all_subentries');
meta.matlab_release = version;
meta.timestamp = datestr(now, 31);
meta.subentry = '12A';

MDP = spm_MDP_checkX(RDP);

fname12A = fullfile(outDir, sprintf('DEMAtariIII_entry12_%s_12A.mat', tag));
save(fname12A, 'MDP', 'OPTIONS', 'meta', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, fname12A);

kPath = entry12_vb_rand_k_mat_(outDir, tag);
if ~isfile(kPath)
    error('Missing VB draw count K: %s\nRun entry12_preflight_vb_rand_k.py for tag %s first, or use inline count (call 2).', kPath, tag);
end
Sk = load(kPath);
K = Sk.K(1);

capture_protocol = 'entry12_v5_preamble_rewind';
entry12_sample_trace_matlab('reset');
rgms_entry12_s_pre = rng;
fprintf(1, '[entry12 dump] tag=%s starting VB + subentry dump (12B–12I)\n', tag);
PDP = spm_MDP_VB_XXX(MDP, OPTIONS, false, true);
entry12_sample_trace_matlab('finalize', tag, outDir);
rng(rgms_entry12_s_pre);
fprintf(1, '[entry12 dump] tag=%s VB + subentry dump done\n', tag);

if K > 0
    vb_rand_buf = rand(K, 1);
else
    vb_rand_buf = zeros(0, 1);
end
randOut = entry12_vb_rand_buf_mat_(outDir, tag);
rdpMat = rdpSource;
save(randOut, 'vb_rand_buf', 'K', 'rdpMat', 'tag', 'capture_protocol', 'rdpSource', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s (K=%d)\n', tag, randOut, K);

pdpOut = entry12_xxx12_pdp_mat_(outDir, tag);
metaPdp = struct();
metaPdp.capture_script = which('DEMAtariIII_entry12_dump_all_subentries');
metaPdp.source_rdp_mat = rdpOut;
metaPdp.run_tag = tag;
save(pdpOut, 'PDP', 'meta', '-v7');
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, pdpOut);

entry12_write_signoff_manifest_(tag, outDir, captureMode, K, numel(vb_rand_buf), rdpOut, pdpOut, randOut);
end


function MDP = entry12_dem_active_inference_nr_loop_call2_capture_( ...
    MDP, GDP, Ne, C, Nm, NT, NS, NR, outDir, captureMode, firstGame, lastGame)
% NR loop with Entry **12** dumps for call-2 games ``firstGame``..``lastGame`` (OPTIM1FULL **3b–3c**).

OPTIONS = entry12_default_options_sp_mdp_vb_xxx();
for i = 1:NR
    RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
    RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
    RDP.T = fix(NT / Ne);
    if i >= firstGame && i <= lastGame
        tag = entry12_call2_tag_for_game_(i);
        entry12_count_and_save_vb_rand_k_(RDP, outDir, tag);
        PDP = entry12_dump_one_vb_call_(RDP, tag, outDir, ...
            sprintf('optim1full_nr_g%02d', i), captureMode);
    else
        PDP = spm_MDP_VB_XXX(RDP, OPTIONS, false, false);
    end
    O = PDP.Q.O{1};
    t = 0:(NT - Ne);
    for s = 1:Ne
        MDP = spm_merge_structure_learning(O(:, t + s), MDP);
    end
    MDP = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if mod(i, 8) == 0 || i == NR
        fprintf(1, '[entry12 dump] active-inference game %d/%d (T=%d, capture=%d)\n', ...
            i, NR, RDP.T, i >= firstGame && i <= lastGame);
    end
end
fprintf(1, '[entry12 dump] NR loop call-2 capture finished (Nm=%d Ne=%d games %d..%d)\n', ...
    Nm, Ne, firstGame, lastGame);
end


function tag = entry12_call2_tag_for_game_(gameIndex)
% OPTIM1FULL call-2 tag: game **1** ``rgms_atari_call2``; **2–32** ``rgms_atari_call2_gNN``.
if gameIndex == 1
    tag = 'rgms_atari_call2';
elseif gameIndex >= 2 && gameIndex <= 32
    tag = sprintf('rgms_atari_call2_g%02d', gameIndex);
else
    error('entry12_call2_tag_for_game_: gameIndex must be 1..32, got %d', gameIndex);
end
end


function val = entry12_env_int_(name, defaultVal)
raw = getenv(name);
if isempty(raw)
    val = defaultVal;
    return;
end
val = str2double(strtrim(raw));
if isnan(val) || val < 1
    val = defaultVal;
end
val = round(val);
end


function entry12_write_signoff_manifest_(tag, outDir, captureMode, K, vbRandLen, rdpMat, pdpMat, randBufMat)
manifest = struct();
manifest.manifest_schema = 2;
manifest.tag = tag;
manifest.matlab_release = version;
manifest.capture_mode = captureMode;
manifest.timestamp = datestr(now, 31);
manifest.K = double(K);
manifest.vb_rand_buf_len = double(vbRandLen);
manifest.paths = struct( ...
    'rdp_mat', rdpMat, ...
    'pdp_mat', pdpMat, ...
    'rand_buf_mat', randBufMat);
manifest.checksums = struct( ...
    'rdp_mat_sha256', entry12_sha256_file_hex_(rdpMat), ...
    'pdp_mat_sha256', entry12_sha256_file_hex_(pdpMat), ...
    'rand_buf_mat_sha256', entry12_sha256_file_hex_(randBufMat), ...
    'subentry_mat', entry12_subentry_mat_checksums_(tag, outDir));

manifestPath = fullfile(outDir, sprintf('entry12_signoff_manifest_%s.json', tag));
fid = fopen(manifestPath, 'w');
if fid < 0
    error('Could not open manifest for write: %s', manifestPath);
end
cleanupObj = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '%s\n', regexprep(jsonencode(manifest, 'PrettyPrint', true), '"x(12[A-I])"', '"$1"'));
fprintf(1, '[entry12 dump] tag=%s wrote %s\n', tag, manifestPath);
end


function sub = entry12_subentry_mat_checksums_(tag, outDir)
% SHA-256 hex for ``DEMAtariIII_entry12_<tag>_12{A–I}.mat`` present after script **1b**.
% Field names ``12A`` … are invalid MATLAB identifiers — build via ``jsondecode``.
codes = {'12A','12B','12C','12D','12E','12F','12G','12H','12I'};
jsonStr = '{';
first = true;
for i = 1:numel(codes)
    code = codes{i};
    p = fullfile(outDir, sprintf('DEMAtariIII_entry12_%s_%s.mat', tag, code));
    if isfile(p)
        if ~first
            jsonStr = [jsonStr ',']; %#ok<AGROW>
        end
        first = false;
        hex = entry12_sha256_file_hex_(p);
        jsonStr = [jsonStr '"' code '":"' hex '"']; %#ok<AGROW>
    end
end
jsonStr = [jsonStr '}'];
if first
    sub = struct();
else
    sub = jsondecode(jsonStr);
end
end


function hex = entry12_sha256_file_hex_(path)
if ~isfile(path)
    error('Missing file for checksum: %s', path);
end
bytes = fileread_uint8_(path);
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(bytes);
d = typecast(md.digest(), 'uint8');
hex = lower(reshape(dec2hex(d, 2).', 1, []));
end


function bytes = fileread_uint8_(path)
fid = fopen(path, 'r');
if fid < 0
    error('Could not open file for checksum read: %s', path);
end
cleanupObj = onCleanup(@() fclose(fid)); %#ok<NASGU>
bytes = fread(fid, Inf, '*uint8');
end


function [MDP, GDP, Nm, Ne, C] = entry12_dem_ledger_through_entry11_(plotFenceTrace, optim1Dir)
% Entries 1--11 (FSL oracle lane): ``rng(2)`` already set by caller.
% Optional ``plotFenceTrace`` / ``optim1Dir``: when true (RGMS_OPTIM1FULL_PLOT_FENCE_TRACE),
% save dem_gameplay MATLAB-owned fence PDP immediately after ``spm_MDP_generate``, and
% after the Attractors basin loop save dem_attractors_basin (NS…NH) + dem_attractors_mdp_post_sort
% (b1/hid) payloads — same capture family as RGB fences. No-arg callers leave fence saves off.

if nargin < 1 || isempty(plotFenceTrace)
    plotFenceTrace = false;
end

Nr = 12;
Nc = 9;
Sc = 9;
Nd = 4;
C  = 32;

[GDP, ~, ~, ~, ~] = spm_MDP_pong(Nr, Nc, Nd, true, 0);

S = ones(4, 3);
S(1, :) = [Nr, Nc, 1];
S(2, :) = [1, 1, 1];
S(3, :) = [1, 1, 1];
S(4, :) = [1, 1, 1];

spm_get_hits = @(o, id) find(o(id.reward, :) > 1);
spm_get_miss = @(o, id) find(o(id.contraint, :) > 1);

GDP.tau = 1;
GDP.T   = 10000;
PDP = spm_MDP_generate(GDP);
if plotFenceTrace
    % DEM_AtariIII.m Gameplay fence — generate-PDP authority (not a VB-call fence).
    entry12_save_optim1full_plot_fence_(PDP, 'dem_gameplay', optim1Dir);
end

MDP = spm_faster_structure_learning(PDP.O(:, 1:1000), S, Sc);

Nm = numel(MDP);
Ne = max(2^(Nm - 1), 1);
for n = 1:Nm
    for g = 1:numel(MDP{n}.a)
        MDP{n}.a{g} = [];
    end
    for f = 1:numel(MDP{n}.b)
        MDP{n}.b{f} = [];
    end
end

r = spm_get_hits(PDP.o, GDP.id);
c = spm_get_miss(PDP.o, GDP.id);
for i = 1:numel(r)
    s = c(find(c < r(i), 1, 'last'));
    t = (s + Ne):(r(i) + Ne);
    if numel(t)
        for s = 1:Ne
            MDP = spm_merge_structure_learning(PDP.O(:, t + s), MDP);
        end
    end
end

NT = 100;
% Attractors basin plot fence (DEM_AtariIII.m 140–175): accumulate NS…NH like the
% demo script. Dump previously discarded series (only used d for break).
if plotFenceTrace
    NS = [];
    NU = [];
    NA = [];
    NO = [];
    NH = [];
end
for i = 1:128
    q = rem(i, 100 - 1);
    t = (0:(NT + Ne)) + q * NT;
    for s = 1:Ne
        MDP = spm_merge_structure_learning(PDP.O(:, t + s), MDP);
    end
    [MDP, d, o, h] = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if plotFenceTrace
        NS(end + 1) = size(MDP{Nm}.b{1}, 2); %#ok<AGROW>
        NU(end + 1) = size(MDP{Nm}.b{1}, 3); %#ok<AGROW>
        NA(end + 1) = sum(~d); %#ok<AGROW>
        NO(end + 1) = sum(~o); %#ok<AGROW>
        NH(end + 1) = numel(h); %#ok<AGROW>
    end
    if all(d)
        break;
    end
end

MDP = spm_RDP_sort(MDP);
MDP = spm_set_goals(MDP, [2, 3], [C, -C]);
if plotFenceTrace
    % dem_attractors_basin — final accumulated series after last i (break or 128).
    entry12_save_optim1full_plot_fence_payload_( ...
        'dem_attractors_basin', optim1Dir, ...
        struct('NS', NS, 'NU', NU, 'NA', NA, 'NO', NO, 'NH', NH));
    % dem_attractors_mdp_post_sort — after sort+goals; enough for orbits (b1/hid).
    % Orbits before/after reuse call3/call4 matlab_pdp (no new ledger dumps).
    entry12_save_optim1full_plot_fence_payload_( ...
        'dem_attractors_mdp_post_sort', optim1Dir, ...
        struct('b1', MDP{Nm}.b{1}, 'hid', MDP{Nm}.id.hid));
end
fprintf(1, '[entry12 dump] inline ledger through Entry 10 (Nm=%d Ne=%d)\n', Nm, Ne);
end


function MDP = entry12_dem_attach_generative_process_(MDP, GDP)
% Install Atari generative process on ``MDP{1}`` (~``DEM_AtariIII.m`` 241--246).

MDP{1}.GA = GDP.A;
MDP{1}.GB = GDP.B;
MDP{1}.GU = GDP.U;
MDP{1}.GD = GDP.D;
MDP{1}.ID = GDP.id;
MDP{1}.chi = 512;
end


function MDP = entry12_dem_active_inference_nr_loop_(MDP, GDP, Ne, C, Nm, NT, NS, NR)
% Active-inference game loop (~``DEM_AtariIII.m`` 254--325); updates ``MDP`` in place.

OPTIONS = entry12_default_options_sp_mdp_vb_xxx();
for i = 1:NR
    RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
    RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
    RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
    RDP.T = fix(NT / Ne);
    PDP = spm_MDP_VB_XXX(RDP, OPTIONS, false, false);
    O = PDP.Q.O{1};
    t = 0:(NT - Ne);
    for s = 1:Ne
        MDP = spm_merge_structure_learning(O(:, t + s), MDP);
    end
    MDP = spm_RDP_basin(MDP, [2, 3], [C, -C]);
    if mod(i, 8) == 0 || i == NR
        fprintf(1, '[entry12 dump] active-inference game %d/%d (T=%d)\n', i, NR, RDP.T);
    end
end
fprintf(1, '[entry12 dump] NR loop finished (Nm=%d Ne=%d)\n', Nm, Ne);
end


function RDP = entry12_dem_call3_rdp_post_loop_(MDP, C, NS)
% Third VB appearance (~``DEM_AtariIII.m`` 330--339): post-loop ``spm_RDP_sort``, ``T=128``.

RDP = spm_RDP_sort(MDP);
RDP = spm_set_goals(RDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = 128;
fprintf(1, '[entry12 dump] call-3 RDP assembled (T=%d, NS=%g)\n', RDP.T, NS);
end


function RDP = entry12_dem_call4_rdp_post_loop_(MDP, C, NS)
% Fourth VB appearance (~``DEM_AtariIII.m`` 381--389): sort + ``spm_RDP_MI``, ``T=128``.

RDP = spm_RDP_sort(MDP);
RDP = spm_RDP_MI(RDP);
RDP = spm_set_goals(RDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = 128;
fprintf(1, '[entry12 dump] call-4 RDP assembled (T=%d, NS=%g)\n', RDP.T, NS);
end


function entry12_assert_optim1full_python_authority_(matPath, metaField)
% Require Python Product B authority capture on ``matPath`` (``meta*.capture``).

expected = 'capture_optim1full_python_product_b';
S = load(matPath, metaField);
if ~isfield(S, metaField)
    error('OPTIM1FULL authority: %s missing field %s', matPath, metaField);
end
meta = S.(metaField);
cap = '';
try
    cap = meta.capture;
catch
end
if ~strcmp(strtrim(cap), expected)
    error('OPTIM1FULL authority: %s.%s.capture=%s expected %s', ...
        matPath, metaField, cap, expected);
end
end


function RDP = entry12_optim1full_call2_rdp_from_pre_(MDP, Ne, C)
% Call-2 game **1** RDP from ledger ``MDP_pre`` (GP already attached; no inline DEM).

NT = 256;
NS = 256;
RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = fix(NT / Ne);
fprintf(1, '[entry12 dump] call-2 from authority MDP_pre (T=%d, Ne=%d, NS=%d)\n', RDP.T, Ne, NS);
end


function RDP = entry12_dem_call2_rdp_game1_(MDP, GDP, Ne, C)
% ``DEM_AtariIII.m`` active inference, first game only (~lines 239--267).

MDP = entry12_dem_attach_generative_process_(MDP, GDP);

NT = 256;
NS = 256;

RDP = spm_set_goals(MDP, [2, 3], [C, -C]);
RDP = spm_set_costs(RDP, [2, 3], [C, -C]);
RDP = spm_mdp2rdp(RDP, 0, 1 / NS);
RDP.T = fix(NT / Ne);
fprintf(1, '[entry12 dump] call-2 RDP assembled (T=%d, Ne=%d, NS=%d)\n', RDP.T, Ne, NS);
end


function entry12_count_and_save_vb_rand_k_(RDP, outDir, tag)
% Count scalar ``rand()`` during VB (``matlab_custom/entry12/rand.m`` shadow).

global rgms_entry12_rand_count rgms_entry12_use_replay rgms_entry12_buf

MDP = spm_MDP_checkX(RDP);
OPTIONS = entry12_default_options_sp_mdp_vb_xxx();

rgms_entry12_buf = [];
rgms_entry12_use_replay = true;
rgms_entry12_rand_count = 0;

% Count only — do not dump subentries (tag env may still be call 1).
spm_MDP_VB_XXX(MDP, OPTIONS, false, false);

K = rgms_entry12_rand_count;
rgms_entry12_use_replay = false;
rgms_entry12_rand_count = 0;

kPath = entry12_vb_rand_k_mat_(outDir, tag);
save(kPath, 'K', '-v7');
fprintf(1, '[entry12 dump] tag=%s counted K=%d -> %s\n', tag, K, kPath);
end


function p = entry12_vb_rand_k_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'entry12_vb_rand_K.mat');
else
    p = fullfile(outDir, sprintf('entry12_vb_rand_K_%s.mat', tag));
end
end


function p = entry12_vb_rand_buf_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'DEMAtariIII_entry12_vb_matlab_rand_buf.mat');
else
    p = fullfile(outDir, sprintf('DEMAtariIII_entry12_vb_matlab_rand_buf_%s.mat', tag));
end
end


function p = entry12_xxx12_rdp_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'DEMAtariIII_XXX_12_rdp.mat');
else
    p = fullfile(outDir, sprintf('DEMAtariIII_XXX_12_%s_rdp.mat', tag));
end
end


function p = entry12_xxx12_pdp_mat_(outDir, tag)
if strcmp(tag, 'rgms_canonical')
    p = fullfile(outDir, 'DEMAtariIII_XXX_12_pdp.mat');
else
    p = fullfile(outDir, sprintf('DEMAtariIII_XXX_12_%s_pdp.mat', tag));
end
end


function seg = entry12_ledger_segment_(startIdx, segId)
% One manifest row for OPTIM1FULL Model B ledger (0-based ``start``, length ``k``).
n = rgms_fsl_rand_log_count();
seg = struct('id', segId, 'start', startIdx, 'k', n - startIdx);
end


function tf = entry12_env_truthy_(name)
v = getenv(name);
tf = ~isempty(v) && any(strcmpi(strtrim(v), {'1', 'true', 'yes', 'on'}));
end


function entry12_save_optim1full_plot_fence_(PDP, siteId, outDir)
% OPTIM1FULL — save the INDEPENDENT MATLAB-owned plot-fence VB output PDP for one
% DEM_AtariIII.m illustrate site, as the authority for plotting-function parity.
% This is a MATLAB-computed object (NOT a re-serialization of Python output); it is
% the reference that translated Python plot code must be compared against.
metaPdp = struct();
metaPdp.capture = 'capture_optim1full_plot_fence';
metaPdp.site_id = siteId;
metaPdp.timestamp = datestr(now, 31);
outMat = fullfile(outDir, sprintf('DEMAtariIII_optim1full_%s_matlab_pdp.mat', siteId));
save(outMat, 'PDP', 'metaPdp', '-v7');
fprintf(1, '[entry12 dump] plot-fence PDP (%s) -> %s\n', siteId, outMat);
end


function entry12_save_optim1full_plot_fence_payload_(siteId, outDir, payload)
% OPTIM1FULL — save a non-PDP MATLAB-owned plot-fence payload for one illustrate site
% (basin series, post-sort b1/hid, structure-learning F, …). Same capture family as
% entry12_save_optim1full_plot_fence_ (meta.capture = capture_optim1full_plot_fence).
% ``payload`` is a struct whose fields are written into the .mat alongside ``meta``.
% Stem: DEMAtariIII_optim1full_<siteId>_matlab_payload.mat
if ~exist(outDir, 'dir')
    mkdir(outDir);
end
meta = struct();
meta.capture = 'capture_optim1full_plot_fence';
meta.site_id = siteId;
meta.timestamp = datestr(now, 31);
payload.meta = meta;
outMat = fullfile(outDir, sprintf('DEMAtariIII_optim1full_%s_matlab_payload.mat', siteId));
save(outMat, '-struct', 'payload', '-v7');
fprintf(1, '[entry12 dump] plot-fence payload (%s) -> %s\n', siteId, outMat);
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


function entry12_save_optim1full_mi_boundaries_(MDP_post_nr, Nm, outDir, opts)
% OPTIM1FULL — ``spm_RDP_MI`` MATLAB authority at ``DEM_AtariIII.m`` 382 and 429.
% See ``OPTIM1.md`` § **11.6**. ``MDP_post_nr`` is post--NR=32 (unsorted).
% Optional ``opts.savePostNr`` (default true): when false, skip writing ``MDP_post_nr.mat``.

if nargin < 4 || isempty(opts)
    opts = struct();
end
if ~isfield(opts, 'savePostNr') || isempty(opts.savePostNr)
    opts.savePostNr = true;
end
if ~isfield(opts, 'metaSource') || isempty(opts.metaSource)
    opts.metaSource = 'DEMAtariIII_entry12_dump_all_subentries';
end
if ~isfield(opts, 'metaCapture')
    opts.metaCapture = '';
end
if ~isfield(opts, 'authorityPostMat')
    opts.authorityPostMat = '';
end

if ~exist(outDir, 'dir')
    mkdir(outDir);
end

meta = struct();
meta.source = opts.metaSource;
meta.matlab_release = version;
meta.timestamp = datestr(now, 31);
meta.rng_seed = 2;
if ~isempty(opts.metaCapture)
    meta.capture = opts.metaCapture;
end
if ~isempty(opts.authorityPostMat)
    meta.authority_post_nr_mat = opts.authorityPostMat;
end

if opts.savePostNr
    meta.boundary = 'optim1full_post_nr';
    save(fullfile(outDir, 'DEMAtariIII_optim1full_MDP_post_nr.mat'), ...
        'MDP_post_nr', 'Nm', 'meta', '-v7');
end

MDP_pre_mi429 = entry12_mdp_mat_deep_copy_(MDP_post_nr);

MDP_pre_mi382 = spm_RDP_sort(MDP_post_nr);
meta.boundary = 'optim1full_pre_mi382';
save(fullfile(outDir, 'DEMAtariIII_optim1full_MDP_pre_mi382.mat'), ...
    'MDP_pre_mi382', 'Nm', 'meta', '-v7');

mi382_causal = entry12_build_optim1full_mi_causal(MDP_pre_mi382, 1);
meta.boundary = 'optim1full_mi382_causal';
save(fullfile(outDir, 'DEMAtariIII_optim1full_mi382_causal.mat'), ...
    'mi382_causal', 'Nm', 'meta', '-v7');

MDP_post_mi382 = spm_RDP_MI(MDP_pre_mi382);
meta.boundary = 'optim1full_post_mi382';
save(fullfile(outDir, 'DEMAtariIII_optim1full_MDP_post_mi382.mat'), ...
    'MDP_post_mi382', 'Nm', 'meta', '-v7');

meta.boundary = 'optim1full_pre_mi429';
save(fullfile(outDir, 'DEMAtariIII_optim1full_MDP_pre_mi429.mat'), ...
    'MDP_pre_mi429', 'Nm', 'meta', '-v7');

mi429_causal = entry12_build_optim1full_mi_causal(MDP_pre_mi429, 1);
meta.boundary = 'optim1full_mi429_causal';
save(fullfile(outDir, 'DEMAtariIII_optim1full_mi429_causal.mat'), ...
    'mi429_causal', 'Nm', 'meta', '-v7');

MDP_post_mi429 = spm_RDP_MI(MDP_pre_mi429);
np_mi429 = entry12_count_mdp_np_(MDP_post_mi429, Nm);
meta.boundary = 'optim1full_post_mi429';
save(fullfile(outDir, 'DEMAtariIII_optim1full_MDP_post_mi429.mat'), ...
    'MDP_post_mi429', 'Nm', 'meta', '-v7');
meta.boundary = 'optim1full_np_mi429';
save(fullfile(outDir, 'DEMAtariIII_optim1full_np_mi429.mat'), ...
    'np_mi429', 'Nm', 'meta', '-v7');

fprintf(1, '[optim1full MI] wrote boundaries to %s (np_mi429=%d)\n', outDir, np_mi429);
end


function MDP_copy = entry12_mdp_mat_deep_copy_(MDP)
tmp = [tempname '.mat'];
save(tmp, 'MDP', '-v7');
S = load(tmp);
MDP_copy = S.MDP;
delete(tmp);
end


function np = entry12_count_mdp_np_(MDP, Nm)
np = 0;
for n = 1:Nm
    for g = 1:numel(MDP{n}.a)
        np = np + nnz(MDP{n}.a{g});
    end
    for f = 1:numel(MDP{n}.b)
        np = np + nnz(MDP{n}.b{f});
    end
end
end
