param(
    [string]$CondaPrefix = ""
)
# E2 / B5.3b — RGMs driver only; LAPACK from Intel MKL (mkl_rt), not vendored Netlib .f
# Contrast: build_windows_mkl.ps1 = Netlib LAPACK + MKL BLAS (K19 closed at 51/58).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $Root "..\.."))
$Build = Join-Path $Root "build_mkl_lapack"
$SrcDriver = Join-Path $Root "src\rgms_eig_nobalance.f"
$OutDir = Join-Path $Root "..\..\python_src\utils\eig_lapack_nobalance"
$OutDll = [System.IO.Path]::GetFullPath((Join-Path $OutDir "_eig_lapack_nobalance.dll"))
$ManifestPath = Join-Path $RepoRoot "tools\eig_mkl_staging\STAGING_MANIFEST.json"

if (-not (Test-Path $ManifestPath)) {
    Write-Error "Missing $ManifestPath - run tools/eig_mkl_staging/fetch_mkl_nuget.ps1"
}
$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$MklRtLib = $manifest.mkl_rt_lib
$RuntimeCopyDir = $manifest.runtime_copy_dir

$prefix = $CondaPrefix
if (-not $prefix) { $prefix = $env:CONDA_PREFIX }
if (-not $prefix -or -not (Test-Path (Join-Path $prefix "Library\mingw-w64\bin\gfortran.exe"))) {
    $rgmsGuess = Join-Path $env:USERPROFILE "anaconda3\envs\rgms"
    if (Test-Path (Join-Path $rgmsGuess "Library\mingw-w64\bin\gfortran.exe")) { $prefix = $rgmsGuess }
}
if (-not $prefix) { Write-Error "Need rgms gfortran (-CondaPrefix)" }
$MingwBin = Join-Path $prefix "Library\mingw-w64\bin"
$env:PATH = "$MingwBin;$env:PATH"

New-Item -ItemType Directory -Force -Path $Build | Out-Null
$DrvObj = Join-Path $Build "rgms_eig_nobalance.o"
& gfortran -c -O2 -fno-second-underscore -J $Build -o $DrvObj $SrcDriver
if ($LASTEXITCODE -ne 0) { throw "compile driver failed" }

Write-Host "Linking $OutDll (MKL LAPACK via mkl_rt only) ..."
& gfortran -shared -O2 -fno-second-underscore -o $OutDll $DrvObj "-Xlinker" $MklRtLib
if ($LASTEXITCODE -ne 0) { throw "link failed" }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Get-ChildItem $RuntimeCopyDir -Filter "*.dll" | ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $OutDir $_.Name) -Force
}
$mklRt2 = Join-Path $OutDir "mkl_rt.2.dll"
if ((Test-Path $mklRt2) -and -not (Test-Path (Join-Path $OutDir "mkl_rt.dll"))) {
    Copy-Item $mklRt2 (Join-Path $OutDir "mkl_rt.dll") -Force
}
Write-Host "OK: $OutDll ($((Get-Item $OutDll).Length) bytes) [MKL LAPACK path]"
