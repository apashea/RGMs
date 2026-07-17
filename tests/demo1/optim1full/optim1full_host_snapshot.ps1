# Host snapshot for XXX_comp optim-wall runs (PRE/POST only — never during VB).
# Prints fixed [HOST] lines to stdout. No mid-run sampling; no new Python deps.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('pre', 'post')]
    [string]$Phase,

    [string]$Label = ''
)

function Write-HostLine {
    param([string]$Line)
    Write-Output $Line
}

$ts = (Get-Date).ToString('o')

# Physical RAM (KB -> MB)
$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$ramAvailMb = $null
$ramTotalMb = $null
if ($os) {
    $ramAvailMb = [math]::Round($os.FreePhysicalMemory / 1024, 1)
    $ramTotalMb = [math]::Round($os.TotalVisibleMemorySize / 1024, 1)
}

# Commit headroom (bytes -> MB)
$commitAvailMb = $null
$commitLimitMb = $null
$commitUsedMb = $null
try {
    $ctr = Get-Counter '\Memory\Committed Bytes', '\Memory\Commit Limit' -ErrorAction Stop
    foreach ($sample in $ctr.CounterSamples) {
        if ($sample.Path -like '*Committed Bytes*') {
            $commitUsedMb = [math]::Round($sample.CookedValue / 1MB, 1)
        }
        elseif ($sample.Path -like '*Commit Limit*') {
            $commitLimitMb = [math]::Round($sample.CookedValue / 1MB, 1)
        }
    }
    if ($null -ne $commitLimitMb -and $null -ne $commitUsedMb) {
        $commitAvailMb = [math]::Round($commitLimitMb - $commitUsedMb, 1)
    }
}
catch {
    # Counter unavailable — leave commit fields null
}

# Python / rgms process inventory
$pythonCount = 0
$rgmsCount = 0
$rgmsWsMb = 0.0
try {
    $pyProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue
    if ($pyProcs) {
        if ($pyProcs -isnot [System.Array]) { $pyProcs = @($pyProcs) }
        $pythonCount = @($pyProcs).Count
        foreach ($p in $pyProcs) {
            $exe = [string]$p.ExecutablePath
            if ($exe -match 'envs\\rgms\\') {
                $rgmsCount++
                try {
                    $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
                    if ($proc) {
                        $rgmsWsMb += $proc.WorkingSet64 / 1MB
                    }
                }
                catch { }
            }
        }
        $rgmsWsMb = [math]::Round($rgmsWsMb, 1)
    }
}
catch { }

# CPU contention proxy (instant — no 1 s sample)
$procQueue = $null
try {
    $q = Get-Counter '\System\Processor Queue Length' -ErrorAction Stop
    $procQueue = [math]::Round($q.CounterSamples[0].CookedValue, 2)
}
catch { }

Write-HostLine "[HOST] phase=$Phase ts=$ts"
if ($Label) { Write-HostLine "[HOST] label=$Label" }
if ($null -ne $ramAvailMb) { Write-HostLine "[HOST] ram_avail_mb=$ramAvailMb" }
if ($null -ne $ramTotalMb) { Write-HostLine "[HOST] ram_total_mb=$ramTotalMb" }
if ($null -ne $commitAvailMb) { Write-HostLine "[HOST] commit_avail_mb=$commitAvailMb" }
if ($null -ne $commitLimitMb) { Write-HostLine "[HOST] commit_limit_mb=$commitLimitMb" }
if ($null -ne $commitUsedMb) { Write-HostLine "[HOST] commit_used_mb=$commitUsedMb" }
Write-HostLine "[HOST] python_count=$pythonCount"
Write-HostLine "[HOST] rgms_python_count=$rgmsCount"
Write-HostLine "[HOST] rgms_python_ws_mb=$rgmsWsMb"
if ($null -ne $procQueue) { Write-HostLine "[HOST] proc_queue=$procQueue" }
