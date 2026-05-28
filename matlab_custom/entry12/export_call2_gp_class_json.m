% Export Entry 12 call-2 generative-process class metadata to JSON.
root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
fix = fullfile(root, 'tests', 'oracle', 'toolbox', 'DEM', 'fixtures');
S = load(fullfile(fix, 'entry12_call2_gp_matlab_class.mat'));
meta = S.meta;
outPath = fullfile(fix, 'entry12_call2_gp_matlab_class.json');
fid = fopen(outPath, 'w');
fprintf(fid, '{\n');
fprintf(fid, '  "tag": "%s",\n', meta.tag);
fprintf(fid, '  "Ng": %d,\n', meta.Ng);
fprintf(fid, '  "GA": [\n');
for g = 1:meta.Ng
    x = meta.GA(g);
    sz_json = entry12_json_size_(x.size);
    if g > 1
        fprintf(fid, ',\n');
    end
    fprintf(fid, '    {"g":%d,"matlab_class":"%s","size":%s,"No":%d,"islogical":%s}', ...
        x.g, x.matlab_class, sz_json, x.No, mat2str(x.islogical));
end
fprintf(fid, '\n  ],\n');
fprintf(fid, '  "GB": [\n');
for g = 1:numel(meta.GB)
    x = meta.GB(g);
    sz_json = entry12_json_size_(x.size);
    if g > 1
        fprintf(fid, ',\n');
    end
    fprintf(fid, '    {"g":%d,"matlab_class":"%s","size":%s,"islogical":%s}', ...
        x.g, x.matlab_class, sz_json, mat2str(x.islogical));
end
fprintf(fid, '\n  ],\n');
fprintf(fid, '  "GU": {"matlab_class":"%s","size":%s,"islogical":%s},\n', ...
    meta.GU_class, entry12_json_size_(meta.GU_size), mat2str(meta.GU_islogical));
fprintf(fid, '  "GD": [\n');
for g = 1:numel(meta.GD)
    x = meta.GD(g);
    sz_json = entry12_json_size_(x.size);
    if g > 1
        fprintf(fid, ',\n');
    end
    fprintf(fid, '    {"g":%d,"matlab_class":"%s","size":%s,"islogical":%s}', ...
        x.g, x.matlab_class, sz_json, mat2str(x.islogical));
end
fprintf(fid, '\n  ]\n}\n');
fclose(fid);
fprintf(1, 'wrote %s\n', outPath);

function s = entry12_json_size_(sz)
s = sprintf('[%s]', strjoin(arrayfun(@num2str, sz, 'UniformOutput', false), ', '));
end
