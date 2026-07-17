param(
    [string]$VendorSubdir = $(if ($env:RGMS_EIG_LAPACK_VENDOR) { $env:RGMS_EIG_LAPACK_VENDOR } else { "lapack-3.11.0-dgeevx" }),
    [string]$CondaPrefix = ""
)
# B5.1 — vendored LAPACK + MKL BLAS (mkl_rt) -> _eig_lapack_nobalance.dll
# Requires: conda env rgms (m2w64-gcc-fortran); MKL staged per eig.md §3.2.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $Root "..\.."))
$Vendor = Join-Path $Root "vendor\$VendorSubdir"
$Build = Join-Path $Root "build_mkl"
$SrcDriver = Join-Path $Root "src\rgms_eig_nobalance.f"
$SrcDebug = Join-Path $Root "src\rgms_dtrevc3_debug.f"
$OutDir = Join-Path $Root "..\..\python_src\utils\eig_lapack_nobalance"
$OutDll = Join-Path $OutDir "_eig_lapack_nobalance.dll"
$OutDll = [System.IO.Path]::GetFullPath($OutDll)
$ManifestPath = Join-Path $RepoRoot "tools\eig_mkl_staging\STAGING_MANIFEST.json"

# Reference BLAS in Netlib closure — provided by MKL instead (B5.1).
$BlasExclude = @{
    "dasum.f" = $true; "daxpy.f" = $true; "dcopy.f" = $true; "ddot.f" = $true
    "dgemm.f" = $true; "dgemv.f" = $true; "dger.f" = $true; "dnrm2.f90" = $true
    "drot.f" = $true; "dscal.f" = $true; "dswap.f" = $true; "dtrmm.f" = $true
    "dtrmv.f" = $true; "idamax.f" = $true
}

if (-not (Test-Path $Vendor)) {
    Write-Error "Missing $Vendor - run fetch_lapack_dgeevx_311.ps1"
}
if (-not (Test-Path $ManifestPath)) {
    Write-Error "Missing $ManifestPath - run tools/eig_mkl_staging/fetch_mkl_nuget.ps1"
}
$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
if (-not $manifest.acceptance.mkl_rt_lib_present) {
    Write-Error "MKL staging acceptance failed - see eig.md §3.2"
}
$MklRtLib = $manifest.mkl_rt_lib
$MklLibDir = $manifest.mkl_lib_dir
$RuntimeCopyDir = $manifest.runtime_copy_dir
if (-not (Test-Path $MklRtLib)) { Write-Error "Missing $MklRtLib" }
if (-not (Test-Path $RuntimeCopyDir)) { Write-Error "Missing $RuntimeCopyDir" }

Write-Host "Vendor tree: $VendorSubdir"
Write-Host "MKL lib dir: $MklLibDir"

$prefix = $CondaPrefix
if (-not $prefix) { $prefix = $env:CONDA_PREFIX }
if (-not $prefix -or -not (Test-Path (Join-Path $prefix "Library\mingw-w64\bin\gfortran.exe"))) {
    $rgmsGuess = Join-Path $env:USERPROFILE "anaconda3\envs\rgms"
    if (Test-Path (Join-Path $rgmsGuess "Library\mingw-w64\bin\gfortran.exe")) {
        $prefix = $rgmsGuess
    }
}
if (-not $prefix -or -not (Test-Path (Join-Path $prefix "Library\mingw-w64\bin\gfortran.exe"))) {
    Write-Error "Activate conda env rgms before building (or pass -CondaPrefix)"
}
$MingwBin = Join-Path $prefix "Library\mingw-w64\bin"
if (-not (Test-Path (Join-Path $MingwBin "gfortran.exe"))) {
    Write-Error "gfortran.exe not found in $MingwBin"
}
$env:PATH = "$MingwBin;$env:PATH"

New-Item -ItemType Directory -Force -Path $Build | Out-Null

# MinGW: link Intel SDL import lib (MSVC COFF) via -Xlinker.
$MklLinkArgs = @("-Xlinker", $MklRtLib)

$Objs = New-Object System.Collections.Generic.List[string]

function Compile-Source {
    param([string]$Path)
    $base = [System.IO.Path]::GetFileNameWithoutExtension($Path)
    $obj = Join-Path $Build "$base.o"
    & gfortran -c -O2 -fno-second-underscore -J $Build -o $obj $Path
    if ($LASTEXITCODE -ne 0) { throw "compile failed: $Path" }
    $Objs.Add($obj) | Out-Null
}

Write-Host "Compiling RGMs driver..."
Compile-Source $SrcDriver
Compile-Source $SrcDebug

$vendorFiles = Get-ChildItem -Path $Vendor -Recurse -Include *.f,*.f90
$skipped = 0
foreach ($src in $vendorFiles) {
    $leaf = $src.Name
    if ($BlasExclude.ContainsKey($leaf)) {
        $skipped++
        continue
    }
    Compile-Source $src.FullName
}
Write-Host "Compiled $($Objs.Count) objects (skipped $skipped reference BLAS sources)"

Write-Host "Linking $OutDll with MKL RT ..."
$objArgs = $Objs.ToArray()
& gfortran -shared -O2 -fno-second-underscore -o $OutDll @objArgs @MklLinkArgs
if ($LASTEXITCODE -ne 0) { throw "link failed" }

Write-Host "Copying MKL runtime DLLs to $OutDir ..."
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Get-ChildItem $RuntimeCopyDir -Filter "*.dll" | ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $OutDir $_.Name) -Force
}
# Loader alias expected by some tooling / older names.
$mklRt2 = Join-Path $OutDir "mkl_rt.2.dll"
if ((Test-Path $mklRt2) -and -not (Test-Path (Join-Path $OutDir "mkl_rt.dll"))) {
    Copy-Item $mklRt2 (Join-Path $OutDir "mkl_rt.dll") -Force
}

Write-Host "OK: $OutDll ($((Get-Item $OutDll).Length) bytes) [B5.1 MKL BLAS link]"
