function out = entry12_induction_only_probe()
%ENTRY12_INDUCTION_ONLY_PROBE Call entry12_spm_induction on frozen inputs.
%
% Reads matlab_custom/entry12_12f_induction_inputs.mat (from
% entry12_12f_induction_compare.py). Falls back to XXX_12 RDP if missing.

here = fileparts(mfilename('fullpath'));
repoRoot = fileparts(fileparts(here));
inpPath = fullfile(repoRoot, 'matlab_custom', 'entry12_12f_induction_inputs.mat');

addpath(here, '-begin');
addpath(genpath(fullfile(repoRoot, 'matlab_src')));

if ~isfile(inpPath)
    error('Missing %s — run entry12_12f_induction_compare.py first.', inpPath);
end

S = load(inpPath);
B = entry12_coerce_B_cell(S.B);
H = entry12_coerce_H_cell(S.H);
Q = entry12_coerce_Q_cell(S.Q);
N = double(S.N(1));
id = entry12_coerce_id_struct(S);

[R, hif] = entry12_spm_induction(B, H, Q, N, id);

out = struct();
out.hif = hif;
out.R_shape = size(R);
out.R_sum = sum(R(:));
out.R_nz = find(R(:) > 0)';
out.R_max = max(R(:));
if isempty(out.R_nz)
    out.R_nz = [];
end

fprintf('[entry12 induction frozen] R_sum=%.6g R_nz=%s\n', out.R_sum, mat2str(out.R_nz(:)'));

end


function B = entry12_coerce_B_cell(B)
if iscell(B) && ndims(B) == 3 && size(B, 1) == 1
    return;
end
if iscell(B) && isvector(B)
    B = B(:);
    nf = numel(B);
    nk = size(B{1}, 3);
    if iscell(B{1})
        nk = numel(B{1});
    end
    B3 = cell(1, nf, nk);
    for f = 1:nf
        Bf = B{f};
        if iscell(Bf)
            for k = 1:nk
                B3{1, f, k} = Bf{k};
            end
        else
            for k = 1:nk
                B3{1, f, k} = Bf(:, :, k);
            end
        end
    end
    B = B3;
end
end


function H = entry12_coerce_H_cell(H)
if iscell(H) && iscolumn(H)
    return;
end
if iscell(H) && isrow(H)
    H = H(:);
end
end


function Q = entry12_coerce_Q_cell(Q)
Q = entry12_coerce_H_cell(Q);
for f = 1:numel(Q)
    Q{f} = full(Q{f}(:));
end
end


function id = entry12_coerce_id_struct(S)
if isfield(S, 'id') && isstruct(S.id)
    id = S.id;
    return;
end
id = struct();
if isfield(S, 'id_hid')
    id.hid = S.id_hid;
end
if isfield(S, 'id_cid')
    id.cid = S.id_cid;
end
if isfield(S, 'id_D')
    id.D = S.id_D;
end
end
