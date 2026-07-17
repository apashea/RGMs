function r = rand(varargin)
%OPTIM1FULL rand shadow — replay scalar draws from ``optim1full_dem_atari_rand_buf``.
global rgms_optim1full_rand_buf rgms_optim1full_rand_idx rgms_optim1full_rand_active

if nargin ~= 0
    r = builtin('rand', varargin{:});
    return;
end

if ~isempty(rgms_optim1full_rand_active) && rgms_optim1full_rand_active
    if isempty(rgms_optim1full_rand_buf)
        error('optim1full rand replay: empty buffer');
    end
    idx = rgms_optim1full_rand_idx;
    if idx < 1 || idx > numel(rgms_optim1full_rand_buf)
        error('optim1full rand replay: index %d out of range (buf len %d)', ...
            idx, numel(rgms_optim1full_rand_buf));
    end
    r = rgms_optim1full_rand_buf(idx);
    rgms_optim1full_rand_idx = idx + 1;
    return;
end

r = builtin('rand', varargin{:});
end
