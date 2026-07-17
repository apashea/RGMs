function r = rand(varargin)
% Shadow ``rand`` for FSL backward capture only (``matlab_custom/fsl_backward`` on path).
% Logs **scalar** ``rand()`` when ``rgms_fsl_rand_active``; passes matrix ``rand(...)`` through
% without logging (Python 1a counts scalar ``np.random.rand()`` only).
global rgms_fsl_rand_log rgms_fsl_rand_active
if nargin == 0
    r = builtin('rand');
    if ~isempty(rgms_fsl_rand_active) && rgms_fsl_rand_active
        rgms_fsl_rand_log(end + 1, 1) = r; %#ok<AGROW>
    end
else
    r = builtin('rand', varargin{:});
end
end
