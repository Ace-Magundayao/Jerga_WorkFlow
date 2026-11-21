# Launch the WORKFLOW system with PUBLIC internet access.
#
# Starts the Flask app + a Cloudflare Quick Tunnel, then prints the
# public https://...trycloudflare.com URL that works from ANY network.
#
# Usage:  powershell -ExecutionPolicy Bypass -File start_public.ps1
#         (or right-click -> Run with PowerShell)

$ErrorActionPreference = "Stop"
$project = $PSScriptRoot
$cloudflared = Join-Path $env:LOCALAPPDATA "cloudflared.exe"

# 1. Start the Flask app in a new window (visible for logs)
Write-Host "Starting WORKFLOW app on http://127.0.0.1:5000 ..." -ForegroundColor Green
Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$project'; if (Test-Path 'venv\Scripts\python.exe') { .\venv\Scripts\python.exe app.py } else { python app.py }"
)

# 2. Wait for the app to come up
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { break }
    } catch {}
}

# 3. Start the tunnel in a new window; it prints the public URL
Write-Host "Opening the Cloudflare tunnel (a new window will show your public URL)..." -ForegroundColor Green
Start-Process -FilePath $cloudflared -ArgumentList @(
    "tunnel", "--url", "http://127.0.0.1:5000", "--no-autoupdate"
)

# 4. Try to fetch and print the URL from the tunnel logs too
Start-Sleep -Seconds 6
Write-Host ""
Write-Host "=============================================" -ForegroundColor Yellow
Write-Host " WORKFLOW is now on the PUBLIC internet."      -ForegroundColor Yellow
Write-Host " Look in the 'cloudflared' window for a line" -ForegroundColor Yellow
Write-Host " like:  https://xxxx-xxxx.trycloudflare.com" -ForegroundColor Yellow
Write-Host " Anyone on ANY network can open that URL."    -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Enter to stop BOTH the app and the tunnel..." -ForegroundColor Cyan
Read-Host

# 5. Cleanup on exit
Get-Process -Name cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name python  -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Stopped. The URL is no longer active (quick tunnels are temporary)." -ForegroundColor Gray
