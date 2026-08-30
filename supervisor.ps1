# supervisor.ps1 — restarts watchdog.py if its process ever disappears, for
# ANY reason (crash, kill, external termination, or a hang inside a subprocess
# call that no Python-level try/except can catch).
#
# This script intentionally does not depend on watchdog.py's own correctness:
# it does not import it, parse its output, or trust its exit code beyond
# "did the process end". It is the outer layer of a two-tier supervision
# design:
#
#   supervisor.ps1  -> watches watchdog.py  (this file)
#   watchdog.py     -> watches run_noise_floor.py
#
# watchdog.py writes its own log directly to results/watchdog.log (safe
# open-append-close pattern — see watchdog.py's log() function). This script
# does NOT also redirect stdout there (that would truncate the log's history
# on every restart); it only captures stderr, per restart, so an uncaught
# Python traceback that killed a previous instance is preserved for
# diagnosis without corrupting the persistent log.
#
# Usage:
#   powershell -NoExit -File supervisor.ps1
#
# Logs:
#   results/supervisor.log        — this script's own restart history
#   results/watchdog.log          — watchdog.py's persistent log (append-only)
#   results/watchdog_stderr.log   — stderr of the MOST RECENT watchdog.py run only

$ErrorActionPreference = "Continue"
$root = "C:\Users\user\Desktop\Sapir\Full_SRPS-ALNS"
Set-Location $root
$logPath = Join-Path $root "results\supervisor.log"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

Write-Log "============================================================"
Write-Log "Supervisor started - will restart watchdog.py if it ever exits"
Write-Log "============================================================"

$restartCount = 0
$pythonExe = "C:\Users\user\AppData\Local\Programs\Python\Python310\python.exe"
while ($true) {
    $restartCount++
    Write-Log "Launching watchdog.py (supervisor restart #$restartCount) via $pythonExe"

    $stderrPath = Join-Path $root "results\watchdog_stderr.log"

    # Run watchdog.py as a CHILD of this script (not a detached new console),
    # so this loop can reliably observe when it exits, for any reason.
    # Pinned to the explicit Python 3.10 path -- bare "python" resolution
    # depends on this process's inherited PATH, which caused a real,
    # repeated crash (2026-08-28): a different Python (3.13) has a known
    # Windows multiprocessing spawn regression (OSError: WinError 87).
    $proc = Start-Process -FilePath $pythonExe -ArgumentList "watchdog.py" `
        -WorkingDirectory $root -PassThru -NoNewWindow `
        -RedirectStandardError $stderrPath

    $proc.WaitForExit()
    Write-Log "watchdog.py exited (PID $($proc.Id), exit code $($proc.ExitCode)) - restarting in 5s"

    if (Test-Path $stderrPath) {
        $stderrContent = Get-Content $stderrPath -Raw -ErrorAction SilentlyContinue
        if ($stderrContent -and $stderrContent.Trim().Length -gt 0) {
            Write-Log "  stderr from crashed instance (see $stderrPath for full text):"
            Write-Log "  $($stderrContent.Substring(0, [Math]::Min(500, $stderrContent.Length)))"
        }
    }

    Start-Sleep -Seconds 5
}
