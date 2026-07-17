function outDir = optim1_fixtures_dir(repoRoot)
%OPTIM1_FIXTURES_DIR  Resolve OPTIM1-owned fixture root (OPTIM1FULL MI boundaries).
%
% Order: RGMS_OPTIM1_FIXTURES_DIR, then shipped tests/demo1/optim1/fixtures.

raw = strtrim(getenv('RGMS_OPTIM1_FIXTURES_DIR'));
if ~isempty(raw)
    outDir = char(raw);
else
    outDir = fullfile(repoRoot, 'tests', 'demo1', 'optim1', 'fixtures');
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end
end
