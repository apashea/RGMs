






# 4/18/2026


matlab_custom/ contains all editted .m files based on spm12 code
Created:
- DEM_AtariIII.m : dump the RDP and PDP outputs (e.g., around line ~386 for the final call of spm_MDP_VB_XXX)
- spm_MDP_VB_XXX_debug.m : version of spm_MDP_VB_XXX with debug statements for printing/inspecting/dumping intermediate inputs/outputs
- matlab_object_inspection.m : standalone script for comprehensive .mat loading and object inspection


#### DEM_AtariIII.m edits:

- around L386 in original:
```
%%%%%%%%%%%%%%%%% edit: dump the fully assembled RDP exactly as it exists before fourth inference call
work_dir = pwd;
rdp_file = fullfile(work_dir, 'DEMAtariIII_RDP_before_fourth_spm_MDP_VB_XXX.mat');

fprintf('Attempting dump of %s...\n', rdp_file);
save(rdp_file, 'RDP', '-v7.3');
if isfile(rdp_file)
    fprintf('Confirmed: created %s\n', rdp_file);
else
    fprintf('WARNING: file not found after save: %s\n', rdp_file);
end
%%%%%%%%%%%%%%%%%% edit end
PDP   = spm_MDP_VB_XXX(RDP);
%%%%%%%%%%%%%%%%%% edit: dump the fully assembled PDP exactly as it exists after fourth inference call
pdp_file = fullfile(work_dir, 'DEMAtariIII_PDP_after_fourth_spm_MDP_VB_XXX.mat');

fprintf('Attempting dump of %s...\n', pdp_file);
save(pdp_file, 'PDP', '-v7.3');
if isfile(pdp_file)
    fprintf('Confirmed: created %s\n', pdp_file);
else
    fprintf('WARNING: file not found after save: %s\n', pdp_file);
end
%%%%%%%%%%%%%%%%%% edit end
```



