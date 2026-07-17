# Retrieve Intel MKL link + runtime artifacts into tools/eig_mkl_staging/ (B5.1).
# Policy: eig.md §3.2 — only approved MKL staging path.
# Does NOT mutate shared conda env rgms.
param(
    [string]$DevelVersion = "2024.2.2.14",
    [string]$RedistVersion = "2024.2.2.14"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$NugetDir = Join-Path $Root "nuget"
$DevelPkg = "intelmkl.devel.win-x64"
$RedistPkg = "intelmkl.redist.win-x64"
$ManifestPath = Join-Path $Root "STAGING_MANIFEST.json"

function Get-NuGetPackage {
    param([string]$Id, [string]$Version, [string]$Dest)
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $nupkg = Join-Path $Dest "$Id.$Version.nupkg"
    if (-not (Test-Path $nupkg)) {
        $url = "https://www.nuget.org/api/v2/package/$Id/$Version"
        Write-Host "Downloading $url ..."
        Invoke-WebRequest -Uri $url -OutFile $nupkg -UseBasicParsing
    }
    $extract = Join-Path $Dest "extracted"
    $marker = Join-Path $extract "$Id.nuspec"
    if (-not (Test-Path $marker)) {
        if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $extract | Out-Null
        $zip = Join-Path $Dest "$Id.$Version.zip"
        Copy-Item -Path $nupkg -Destination $zip -Force
        Expand-Archive -Path $zip -DestinationPath $extract -Force
    }
    return $extract
}

Write-Host "MKL NuGet staging under $NugetDir"
$develExtract = Get-NuGetPackage -Id $DevelPkg -Version $DevelVersion -Dest (Join-Path $NugetDir "devel")
$redistExtract = Get-NuGetPackage -Id $RedistPkg -Version $RedistVersion -Dest (Join-Path $NugetDir "redist")

$libDir = Join-Path $develExtract "build\native\win-x64"
$libCandidates = @(
    (Join-Path $libDir "mkl_rt.lib"),
    (Join-Path $develExtract "runtimes\win-x64\native\mkl_rt.lib"),
    (Join-Path $develExtract "lib\intel64\mkl_rt.lib")
)
$mklRtLib = $libCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $mklRtLib) {
    $found = Get-ChildItem $develExtract -Recurse -Filter "mkl_rt.lib" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $mklRtLib = $found.FullName }
}
if (-not $mklRtLib) {
    throw "mkl_rt.lib not found under $develExtract - inspect NuGet layout or bump version pin"
}

$redistNative = Join-Path $redistExtract "runtimes\win-x64\native"
if (-not (Test-Path $redistNative)) {
    throw "Missing $redistNative in redist package"
}
$dllCandidates = Get-ChildItem $redistNative -Filter "mkl_rt*.dll" -ErrorAction SilentlyContinue
if (-not $dllCandidates) {
    throw "mkl_rt*.dll not found under $redistNative"
}
$allRuntimeDlls = Get-ChildItem $redistNative -Filter "*.dll" -ErrorAction SilentlyContinue

$includeDir = $null
$includeCandidates = @(
    (Join-Path $develExtract "build\native\include"),
    (Join-Path $develExtract "include")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($includeCandidates) { $includeDir = $includeCandidates }

$runtimeCopyDir = Join-Path $Root "runtime"
New-Item -ItemType Directory -Force -Path $runtimeCopyDir | Out-Null
foreach ($dll in $allRuntimeDlls) {
    Copy-Item $dll.FullName -Destination (Join-Path $runtimeCopyDir $dll.Name) -Force
}
$mklRtDll = Join-Path $runtimeCopyDir "mkl_rt.2.dll"
if ((Test-Path $mklRtDll) -and -not (Test-Path (Join-Path $runtimeCopyDir "mkl_rt.dll"))) {
    Copy-Item $mklRtDll (Join-Path $runtimeCopyDir "mkl_rt.dll") -Force
}

$manifest = [ordered]@{
    retrieved_utc = (Get-Date).ToUniversalTime().ToString("o")
    method = "nuget"
    devel_package = "$DevelPkg/$DevelVersion"
    redist_package = "$RedistPkg/$RedistVersion"
    mkl_rt_lib = $mklRtLib
    mkl_lib_dir = $libDir
    mkl_rt_dlls = @($dllCandidates | ForEach-Object { $_.FullName })
    runtime_copy_dir = $runtimeCopyDir
    include_dir = $includeDir
    mklroot_for_build = $develExtract
    acceptance = [ordered]@{
        mkl_rt_lib_present = $true
        mkl_rt_dll_present = ($dllCandidates.Count -gt 0)
        runtime_copied = (Test-Path $runtimeCopyDir)
    }
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Host "OK: mkl_rt.lib -> $mklRtLib"
Write-Host "OK: $($dllCandidates.Count) mkl_rt DLL(s)"
Write-Host "Manifest: $ManifestPath"
