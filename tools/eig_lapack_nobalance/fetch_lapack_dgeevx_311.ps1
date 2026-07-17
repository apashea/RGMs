# B5.4 — pin LAPACK 3.11.0 dgeevx closure (same file list as 3.12 baseline MANIFEST).
# Does not mutate conda. Requires network once.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Root "vendor"
$RefManifest = Join-Path $Vendor "lapack-3.12.0-dgeevx\MANIFEST.txt"
$Dest = Join-Path $Vendor "lapack-3.11.0-dgeevx"
$Cache = Join-Path $Vendor "_cache"
$TarGz = Join-Path $Cache "lapack-3.11.0.tar.gz"
$ExtractRoot = Join-Path $Cache "lapack-3.11.0-src"

if (-not (Test-Path $RefManifest)) {
    Write-Error "Missing $RefManifest - run fetch_lapack_dgeevx.ps1 (3.12 baseline) first"
}

New-Item -ItemType Directory -Force -Path $Dest, $Cache | Out-Null

if (-not (Test-Path $ExtractRoot)) {
    if (-not (Test-Path $TarGz)) {
        $Url = "https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.11.0.tar.gz"
        Write-Host "Downloading $Url ..."
        Invoke-WebRequest -Uri $Url -OutFile $TarGz -UseBasicParsing
    }
    if (Test-Path $ExtractRoot) { Remove-Item -Recurse -Force $ExtractRoot }
    New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
    Write-Host "Extracting $TarGz ..."
    tar -xzf $TarGz -C $ExtractRoot
}

$SrcRoots = @(
    (Get-ChildItem -Path $ExtractRoot -Directory | Select-Object -First 1).FullName
)
if (-not $SrcRoots[0]) { Write-Error "lapack-3.11 extract layout unexpected" }

function Find-LapackFile {
    param([string]$Rel)
    $name = Split-Path -Leaf $Rel
    foreach ($root in $SrcRoots) {
        $hits = Get-ChildItem -Path $root -Recurse -Filter $name -File -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match [regex]::Escape($name) }
        foreach ($h in $hits) {
            if ($h.Name -eq $name) { return $h.FullName }
        }
    }
    return $null
}

$paths = @()
foreach ($line in Get-Content $RefManifest) {
    $t = $line.Trim()
    if ($t -eq "") { continue }
    $parts = $t -split '\s+', 2
    if ($parts.Length -ge 2) { $paths += $parts[1].Trim() }
}

if ($paths.Count -eq 0) {
    Write-Error "Could not parse paths from $RefManifest"
}

$copied = 0
$missing = @()
foreach ($rel in $paths) {
    $src = Find-LapackFile -Rel $rel
    if (-not $src) {
        # lapack-3.11 tree: SRC/double/... vs lapack/double/...
        $alt = $rel -replace '^lapack/', 'SRC/'
        $leaf = Split-Path -Leaf $rel
        $src = Get-ChildItem -Path $SrcRoots[0] -Recurse -Filter $leaf -File -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($src) { $src = $src.FullName }
    }
    if (-not $src) { $missing += $rel; continue }
    $outPath = Join-Path $Dest $rel
    $outDir = Split-Path -Parent $outPath
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    Copy-Item -Force $src $outPath
    $copied++
}

if ($missing.Count -gt 0) {
    Write-Warning "Missing $($missing.Count) files:"
    $missing | ForEach-Object { Write-Warning "  $_" }
}

Write-Host "Copied $copied files to $Dest"
& python (Join-Path $Root "list_vendor_manifest.py") --vendor lapack-3.11.0-dgeevx
if ($LASTEXITCODE -ne 0) { throw "list_vendor_manifest failed" }
Write-Host "B5.4 extract done."
