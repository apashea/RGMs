param(
    [string]$VendorSubdir = $(if ($env:RGMS_EIG_LAPACK_VENDOR) { $env:RGMS_EIG_LAPACK_VENDOR } else { "lapack-3.11.0-dgeevx" })
)
# B2 — compile vendored LAPACK + RGMs driver → _eig_lapack_nobalance.dll
# Requires: conda env rgms with m2w64-gcc-fortran (conda-forge).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Root "vendor\$VendorSubdir"
$Build = Join-Path $Root "build"
$SrcDriver = Join-Path $Root "src\rgms_eig_nobalance.f"
$SrcDebug = Join-Path $Root "src\rgms_dtrevc3_debug.f"
$OutDll = Join-Path $Root "..\..\python_src\utils\eig_lapack_nobalance\_eig_lapack_nobalance.dll"
$OutDll = [System.IO.Path]::GetFullPath($OutDll)

if (-not (Test-Path $Vendor)) {
    Write-Error "Missing $Vendor - run fetch_lapack_dgeevx.ps1 (3.12) or fetch_lapack_dgeevx_311.ps1 (3.11)"
}
Write-Host "Vendor tree: $VendorSubdir"
if (-not $env:CONDA_PREFIX) {
    Write-Error "Activate conda env rgms before building"
}
$MingwBin = Join-Path $env:CONDA_PREFIX "Library\mingw-w64\bin"
if (-not (Test-Path (Join-Path $MingwBin "gfortran.exe"))) {
    Write-Error "gfortran not found in $MingwBin - conda install -c conda-forge m2w64-gcc-fortran"
}
$env:PATH = "$MingwBin;$env:PATH"

New-Item -ItemType Directory -Force -Path $Build | Out-Null
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

Write-Host "Compiling vendored LAPACK (66 files)..."
Get-ChildItem -Path $Vendor -Recurse -Include *.f,*.f90 | ForEach-Object {
    Compile-Source $_.FullName
}

Write-Host "Linking $OutDll ..."
$objArgs = $Objs.ToArray()
& gfortran -shared -O2 -fno-second-underscore -o $OutDll @objArgs
if ($LASTEXITCODE -ne 0) { throw "link failed" }

Write-Host "OK: $OutDll ($((Get-Item $OutDll).Length) bytes)"
