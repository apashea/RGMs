function [buf, K] = rgms_fsl_rand_log_finish()
% Stop logging and return captured scalar ``rand()`` stream (FSL backward 1b).
global rgms_fsl_rand_log rgms_fsl_rand_active
rgms_fsl_rand_active = false;
if isempty(rgms_fsl_rand_log)
    buf = zeros(0, 1);
else
    buf = rgms_fsl_rand_log(:);
end
K = numel(buf);
end
