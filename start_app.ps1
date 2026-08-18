# Start de Boekhouding-app (indien nog niet actief) en opent hem in de
# standaardbrowser. Bedoeld om via start_app.bat aangeklikt te worden
# (zie daar), maar werkt ook direct: powershell -File start_app.ps1

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $AppDir

$Port = 8000
$Url = "http://127.0.0.1:$Port"
$LogDir = Join-Path $AppDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$StdOutLog = Join-Path $LogDir "launcher-stdout.log"
$StdErrLog = Join-Path $LogDir "launcher-stderr.log"

function Test-ServerUp {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Draait de server al (bijv. eerder gestart)? Dan alleen de browser openen.
if (Test-ServerUp) {
    Write-Host "Boekhouding draait al op $Url — browser openen..."
    Start-Process $Url
    exit 0
}

$VenvPython = Join-Path $AppDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Geen virtualenv gevonden op .venv — volg eerst de installatiestappen in README.md." -ForegroundColor Red
    Read-Host "Druk op Enter om af te sluiten"
    exit 1
}

Write-Host "Boekhouding starten..."
# Draait zonder --reload en sluit zichzelf automatisch af na een periode
# zonder verkeer — zie app/idle_shutdown.py. Zet op "0" om uit te
# schakelen, of zet de omgevingsvariabele vooraf om de standaard 30
# minuten te overschrijven.
$env:BOEKHOUDING_RELOAD = "0"
if (-not $env:BOEKHOUDING_IDLE_TIMEOUT_MINUTES) {
    $env:BOEKHOUDING_IDLE_TIMEOUT_MINUTES = "30"
}
Start-Process -FilePath $VenvPython -ArgumentList "run.py" -WorkingDirectory $AppDir `
    -WindowStyle Hidden -RedirectStandardOutput $StdOutLog -RedirectStandardError $StdErrLog

# Wacht tot de server reageert (max ~20 seconden).
for ($i = 0; $i -lt 40; $i++) {
    if (Test-ServerUp) {
        Start-Process $Url
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "De server reageert nog niet na 20 seconden — bekijk logs\launcher-stdout.log en logs\launcher-stderr.log." -ForegroundColor Yellow
Start-Process $Url
