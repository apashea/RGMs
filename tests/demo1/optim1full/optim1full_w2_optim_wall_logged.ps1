# XXX_comp optim-wall with HOST PRE/POST snapshots (does not modify xxx_comp_call4.py timing).
# One VB process only. Host checks run outside perf_counter.
param(
    [Parameter(Mandatory = $true)]
    [string]$Label,

    [string]$Date = (Get-Date -Format 'yyyyMMdd'),

    [string]$RepoRoot = 'C:\Users\andre\.cursor\RGMs'
)

$ErrorActionPreference = 'Stop'

# Ensure conda rgms is available when invoked via powershell -File
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    $condaHook = Join-Path $env:USERPROFILE 'anaconda3\shell\condabin\conda-hook.ps1'
    if (Test-Path $condaHook) { . $condaHook }
}

$snapScript = Join-Path $RepoRoot 'tests\demo1\optim1full\optim1full_host_snapshot.ps1'
$compScript = 'tests/demo1/optim1full/xxx_comp_call4.py'
$logDir = Join-Path $RepoRoot 'logs'
$logPath = Join-Path $logDir "optim1full_w2_XXX_comp_optim_wall_${Label}_${Date}.log"

if (-not (Test-Path $snapScript)) {
    throw "Missing host snapshot script: $snapScript"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Invoke-Logged {
    param([scriptblock]$Block)
    & $Block 2>&1 | ForEach-Object {
        $_ | Out-String -Stream | ForEach-Object { Write-Output $_ }
    }
}

function Parse-HostBlock {
    param([string[]]$Lines)
    $h = @{}
    foreach ($line in $Lines) {
        if ($line -match '^\[HOST\]\s+(\w+)=(.+)$') {
            $h[$Matches[1]] = $Matches[2]
        }
    }
    return $h
}

$allLines = [System.Collections.Generic.List[string]]::new()

function Append-Lines {
    param([string[]]$Lines)
    foreach ($l in $Lines) {
        if ($null -ne $l -and $l -ne '') {
            [void]$allLines.Add($l)
            Write-Output $l
        }
    }
}

Write-Output "[WRAPPER] optim-wall with host PRE/POST label=$Label log=$logPath"

# --- HOST PRE ---
Append-Lines @('=== HOST PRE ===')
$preOut = & $snapScript -Phase pre -Label $Label
Append-Lines $preOut
$pre = Parse-HostBlock $preOut

Set-Location $RepoRoot
conda activate rgms

# --- OPTIM-WALL (single VB process; timing unchanged inside xxx_comp_call4.py) ---
Append-Lines @('=== OPTIM-WALL ===')
$wallExit = 0
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $wallOut = & python $compScript --mode optim-wall 2>&1
    $wallExit = $LASTEXITCODE
    if ($null -eq $wallExit) { $wallExit = 0 }
    foreach ($line in @($wallOut)) {
        Append-Lines @([string]$line)
    }
}
finally {
    $ErrorActionPreference = $prevEap
}
if ($wallExit -ne 0) {
    Append-Lines @("[WRAPPER] optim-wall exit_code=$wallExit")
}

# --- HOST POST ---
Append-Lines @('=== HOST POST ===')
$postOut = & $snapScript -Phase post -Label $Label
Append-Lines $postOut
$post = Parse-HostBlock $postOut

# --- SUMMARY ---
Append-Lines @('=== HOST SUMMARY ===')
$optimWall = ($allLines | Where-Object { $_ -match '\[XXX_comp\] optim_wall_s=' } | Select-Object -Last 1)
if ($optimWall -match 'optim_wall_s=([\d.]+)') {
    Append-Lines @("[HOST_SUMMARY] optim_wall_s=$($Matches[1])")
}
else {
    Append-Lines @('[HOST_SUMMARY] optim_wall_s=UNKNOWN')
}

foreach ($key in @('ram_avail_mb', 'commit_avail_mb', 'python_count', 'rgms_python_count')) {
    $preVal = $pre[$key]
    $postVal = $post[$key]
    if ($preVal -and $postVal) {
        Append-Lines @("[HOST_SUMMARY] ${key}_pre=$preVal post=$postVal")
    }
    elseif ($preVal) {
        Append-Lines @("[HOST_SUMMARY] ${key}_pre=$preVal")
    }
}

# Flags (diagnostic only — thresholds calibrated later)
$flags = @()
if ($pre['python_count'] -and [int]$pre['python_count'] -gt 1) {
    $flags += 'CONCURRENT-PY-PRE'
}
if ($pre['rgms_python_count'] -and [int]$pre['rgms_python_count'] -gt 1) {
    $flags += 'CONCURRENT-RGMS-PRE'
}
if ($pre['ram_avail_mb'] -and [double]$pre['ram_avail_mb'] -lt 4096) {
    $flags += 'LOW-RAM-PRE'
}
if ($pre['commit_avail_mb'] -and [double]$pre['commit_avail_mb'] -lt 2048) {
    $flags += 'COMMIT-PRESSURE-PRE'
}
if ($pre['ram_avail_mb'] -and $post['ram_avail_mb']) {
    $preRam = [double]$pre['ram_avail_mb']
    $postRam = [double]$post['ram_avail_mb']
    if ($preRam -gt 0 -and (($preRam - $postRam) / $preRam) -gt 0.30) {
        $flags += 'POST-RAM-DEGRADED'
    }
}
if ($optimWall -match 'optim_wall_s=([\d.]+)') {
    $wall = [double]$Matches[1]
    if ($wall -gt 30.0) {
        $flags += 'FINGERPRINT-SLOW'
    }
}
if ($flags.Count -gt 0) {
    Append-Lines @("[HOST_SUMMARY] flags=$($flags -join ',')")
}
else {
    Append-Lines @('[HOST_SUMMARY] flags=none')
}

Append-Lines @("[WRAPPER] exit_wall=$wallExit log=$logPath")

$allLines | Set-Content -Path $logPath -Encoding utf8

if ($wallExit -ne 0) { exit $wallExit }
exit 0
