function g = oracle_spm_group(N,d)
% Verbatim copy of local spm_group from spm_faster_structure_learning.m
% for MATLAB Engine oracles only.

% defaults
%--------------------------------------------------------------------------
N((end + 1):4) = 1;
if nargin < 2

    % use 3 x 3 tiles (or smaller)
    %----------------------------------------------------------------------
    if ~rem(N(1),3), d(1) = 3; else, d(1) = 2; end
    if ~rem(N(2),3), d(2) = 3; else, d(2) = 2; end
    if ~rem(N(3),3), d(3) = 3; else, d(3) = 2; end

elseif numel(d) == 1
    d  = [d,d,d];
end

% deal with single row (or column) cases
%--------------------------------------------------------------------------
r     = cell(1,3);
s     = ones(1,3);
L     = ones(1,3);
for i = 1:3
    d(i)    = min(d(i),N(i));                 % block size
    r{i}    = 0:d(i):(N(i) - 1);              % block start
    s(i)    = numel(r{i});                    % length

end
for i = 1:3
    L(i)    = r{i}(end) + d(i);               % dim
end

% Decimate rows and columns
%--------------------------------------------------------------------------
g     = cell(s);
for i = 1:s(1)
    for j = 1:s(2)
        for k = 1:s(3)
            n{1}     = sparse((1:d(1)*N(4)) + r{1}(i)*N(4),1,1,L(1)*N(4),1);
            n{2}     = sparse((1:d(2)  )    + r{2}(j)     ,1,1,L(2)     ,1);
            n{3}     = sparse((1:d(3)  )    + r{3}(k)     ,1,1,L(3)     ,1);

            v        = spm_cross(n{1},n{2},n{3});
            v        = v(1:N(1)*N(4),1:N(2),1:N(3));
            g{i,j,k} = find(v(:));
        end
    end
end

return
