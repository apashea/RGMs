# B1 helper — download Netlib "DGEEVX + dependencies" into vendor/ (maintainer machine).
# Does not mutate conda. Requires network.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Root "vendor"
$Dest = Join-Path $Vendor "lapack-3.12.0-dgeevx"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

# Netlib "dgeevx.f plus dependencies" (lapack/double path)
$Url = "https://www.netlib.org/cgi-bin/netlibfiles.tgz?format=tgz&filename=/lapack/double/dgeevx.f"
$Tgz = Join-Path $Vendor "dgeevx.tgz"
Write-Host "Downloading $Url ..."
Invoke-WebRequest -Uri $Url -OutFile $Tgz -UseBasicParsing
Write-Host "Extracting to $Dest ..."
tar -xzf $Tgz -C $Dest
Write-Host "Done. Run: python tools/eig_lapack_nobalance/list_vendor_manifest.py"
