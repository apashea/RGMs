function n = rgms_fsl_rand_log_count()
%RGMS_FSL_RAND_LOG_COUNT  Current scalar ``rand()`` log length (FSL backward ledger).
global rgms_fsl_rand_log
if isempty(rgms_fsl_rand_log)
    n = 0;
else
    n = numel(rgms_fsl_rand_log(:));
end
end
