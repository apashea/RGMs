function outDir = demo1_fixtures_dir(repoRoot)
%DEMO1_FIXTURES_DIR  Resolve fixture root for DEMO1 parity producers.
%
% Order: RGMS_DEMO1_FIXTURES_DIR, RGMS_ENTRY12_CAPTURE_OUT_DIR, then shipped
% greenfield default tests/demo1/fixtures (empty on fresh clone).

raw = strtrim(getenv('RGMS_DEMO1_FIXTURES_DIR'));
if isempty(raw)
    raw = strtrim(getenv('RGMS_ENTRY12_CAPTURE_OUT_DIR'));
end
if ~isempty(raw)
    outDir = char(raw);
else
    outDir = fullfile(repoRoot, 'tests', 'demo1', 'fixtures');
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end
end
