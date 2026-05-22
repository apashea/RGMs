function r = rand(varargin)
%RGMS_ENTRY12_RAND Shadow built-in rand for vb_rand_buf replay (scalar lane only).
global rgms_entry12_use_replay rgms_entry12_buf rgms_entry12_rand_count
if nargin ~= 0
    if ~isempty(rgms_entry12_use_replay) && rgms_entry12_use_replay
        error('rgms_entry12 rand replay: only scalar rand() supported');
    end
    r = builtin('rand', varargin{:});
    return;
end
if ~isempty(rgms_entry12_use_replay) && rgms_entry12_use_replay
    if ~isempty(rgms_entry12_buf)
        r = rgms_entry12_rand_scalar();
        return;
    end
    if ~isempty(rgms_entry12_rand_count)
        rgms_entry12_rand_count = rgms_entry12_rand_count + 1;
    end
    r = builtin('rand', varargin{:});
    return;
end
r = builtin('rand', varargin{:});
