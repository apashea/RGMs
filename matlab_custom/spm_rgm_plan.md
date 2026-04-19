1. Verify how to check all matlab fields: Test 1. on a modified .m (pick DEM_AtariIII.m), saving RDP.mat (and PDP.at) and then...
3. Write object_inspect.m -> load RDP.mat -> inspect fully (save this object_inspect.m for later)
3. Load RDP.mat in a truncated XXX_only.m (codename XXXO) which is only load RDP.mat -> load PDP =  spm_MDP_VB_XXX(RDP) -> full inspection (using object_inspect.m) at start + inspection of PDP at end
4. Change XXXO to call spm_MDP_VB_XXX_debug, then make this a copied .m for XXXOD (the debug version) to have debug statements throughout, including names of the (sub)functions called called fstring-literal-style value printouts (use diary correctly to collect it all). *this makes XXXOD fully multi-purpose where you can plug in ANY RDP.mat and PDP.mat to review them*
5. This then allows you multiple paths:
--> start extending XXXOD backwards for earlier inputs
--> extend forwards for later inputs (especially good, to ensure PDP is good
-->try same approach for the Lorenz/MNIST/etc. examples' RDP and PDP simply simply during each as .mat and then reusing in XXXOD 
--> use as LLM fodder for building a XXX-only spm_rgm library. Use a file_structure.md , a logging system, and PLAN your testing strategy fully in advance. Use chatgpt ONLY to continue with the "reread rules (which contains strategy) + docs, include all commands run, files editted and created", etc. commands and enforce the same RGMs/ repo structure. Build to spm_MDP_checkX, and on from there. Segment the code out in dev stages based on the order of functions that show in the debug printouts.