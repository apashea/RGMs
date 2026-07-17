function rgms_fsl_rand_log_begin()
% Start logging scalar ``rand()`` for FSL backward 1b (not Entry 12 VB replay).
global rgms_fsl_rand_log rgms_fsl_rand_active
rgms_fsl_rand_log = zeros(0, 1);
rgms_fsl_rand_active = true;
end
