function outDir = optim1full_fixtures_dir(repoRoot)
%OPTIM1FULL_FIXTURES_DIR  Resolve OPTIM1FULL Product B fixture root.
%
% Order: RGMS_OPTIM1FULL_FIXTURES_DIR, then shipped tests/demo1/optim1full/fixtures.

raw = strtrim(getenv('RGMS_OPTIM1FULL_FIXTURES_DIR'));
if ~isempty(raw)
    outDir = char(raw);
else
    outDir = fullfile(repoRoot, 'tests', 'demo1', 'optim1full', 'fixtures');
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end
end
