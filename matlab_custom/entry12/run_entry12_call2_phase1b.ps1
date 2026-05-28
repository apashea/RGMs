# Phase 1b — call 2 is captured inside script 1b (same run as call 1).
# From repo root (PowerShell): conda activate rgms
#
# Full chain (one long MATLAB 1b, then Python per tag):
#   python tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py
#   matlab -batch "addpath(genpath('matlab_src')); cd('matlab_custom/entry12'); DEMAtariIII_entry12_dump_all_subentries"
#   $env:RGMS_ATARI_RUN_XXX_12='1'; $env:RGMS_ENTRY12_CAPTURE_RUN_TAG='rgms_atari_call2'
#   python -m pytest tests/oracle/toolbox/DEM/test_DEM_AtariIII_XXX_12.py -q
#   python tests/oracle/toolbox/DEM/XXX_12_compare_pdp_pkl_to_mat.py --coerce-sparse-to-dense-for-compare
#
# Legacy call-1-only from FSL mat: RGMS_ENTRY12_CAPTURE_LEGACY_LOAD=1 RGMS_ENTRY12_CAPTURE_SKIP_CALL2=1

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\andre\.cursor\RGMs"
Set-Location $Repo
conda activate rgms

Write-Host "[1/2] Python preflight K (call 1 / rgms_canonical)..." -ForegroundColor Cyan
python tests/oracle/toolbox/DEM/entry12_preflight_vb_rand_k.py

Write-Host "[2/2] MATLAB script 1b (inline ledger + call 1 + call 2) — long run..." -ForegroundColor Cyan
matlab -batch "addpath(genpath('matlab_src')); cd('matlab_custom/entry12'); DEMAtariIII_entry12_dump_all_subentries"

Write-Host "1b done. Run script 3 then 4 per tag (see README_entry12_matlab_capture.md)." -ForegroundColor Green
