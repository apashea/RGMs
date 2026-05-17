function r = rand(varargin)
%RGMS_ENTRY12_RAND Shadow built-in rand for vb_rand_buf replay (scalar lane only).
global rgms_entry12_use_replay
if ~isempty(rgms_entry12_use_replay) && rgms_entry12_use_replay
    if nargin ~= 0
        error('rgms_entry12 rand replay: only scalar rand() supported');
    end
    r = rgms_entry12_rand_scalar();
    return;
end
r = builtin('rand', varargin{:});
