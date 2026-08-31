@echo off
rem Dubbelklikbare snelkoppeling: start de Boekhouding-app (indien nog niet
rem actief) en opent hem in de standaardbrowser.
rem
rem Bewust pure batch/cmd, geen PowerShell: op bedrijfsmachines kan Group
rem Policy de PowerShell-executionpolicy op "AllSigned" zetten, waardoor
rem elk ongetekend .ps1-script weigert te laden - ook met
rem "-ExecutionPolicy Bypass" op de commandoregel, want een Machine-scope
rem policy wint altijd van die vlag. cmd.exe kent geen executionpolicy, dus
rem dit werkt overal. Gebruikt curl.exe (standaard aanwezig sinds Windows
rem 10 1803 / Windows 11) om de serverstatus te checken.
rem
rem Let op: dit bestand bevat bewust alleen ASCII-tekens (geen kaderstreepjes
rem of "slimme" aanhalingstekens) - niet-ASCII tekens in een .bat kunnen op
rem sommige systemen/codepages verkeerd geparsed worden, waarbij cmd.exe
rem stukken van een rem-regel als losse commando's interpreteert.

setlocal EnableExtensions
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

set "PORT=8000"
set "URL=http://127.0.0.1:%PORT%"
set "LOG_DIR=%APP_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "STDOUT_LOG=%LOG_DIR%\launcher-stdout.log"
set "STDERR_LOG=%LOG_DIR%\launcher-stderr.log"

rem Draait de server al (bijv. eerder gestart)? Dan alleen de browser openen.
curl.exe --silent --fail --max-time 2 --output NUL "%URL%"
if not errorlevel 1 (
    echo Boekhouding draait al op %URL% - browser openen...
    start "" "%URL%"
    exit /b 0
)

set "VENV_PYTHONW=%APP_DIR%.venv\Scripts\pythonw.exe"
if not exist "%VENV_PYTHONW%" (
    echo Geen virtualenv gevonden op .venv - volg eerst de installatiestappen in README.md.
    pause
    exit /b 1
)

echo Boekhouding starten...
rem Draait zonder --reload en sluit zichzelf automatisch af na een periode
rem zonder verkeer - zie app/idle_shutdown.py. Zet op 0 om uit te
rem schakelen, of zet de omgevingsvariabele vooraf om de standaard 30
rem minuten te overschrijven.
set "BOEKHOUDING_RELOAD=0"
if not defined BOEKHOUDING_IDLE_TIMEOUT_MINUTES set "BOEKHOUDING_IDLE_TIMEOUT_MINUTES=30"

rem pythonw.exe (i.p.v. python.exe) heeft geen console nodig, dus dit
rem start volledig onzichtbaar - geen zwart schermpje, geen taakbalk-item.
rem Let op: "start" direct op pythonw.exe zetten (zonder deze cmd /c-laag)
rem geeft de I/O-omleiding niet goed door aan een GUI-subsysteem-exe - het
rem proces krijgt dan ongeldige stdout/stderr-handles en crasht meteen bij
rem het opstarten (uvicorn schrijft zijn eigen statusregels naar stderr).
rem Via "cmd /c" doet cmd zelf de omleiding voor zijn eigen kind-proces,
rem wat wel correct werkt; "start /B" eromheen houdt dat cmd-venster zelf
rem onzichtbaar.
start "" /B cmd /c ""%VENV_PYTHONW%" run.py > "%STDOUT_LOG%" 2> "%STDERR_LOG%""

rem Wacht tot de server reageert (max ~20 seconden).
for /L %%i in (1,1,20) do (
    curl.exe --silent --fail --max-time 2 --output NUL "%URL%"
    if not errorlevel 1 (
        start "" "%URL%"
        exit /b 0
    )
    ping -n 2 127.0.0.1 >nul
)

echo De server reageert nog niet na 20 seconden - bekijk logs\launcher-stdout.log, logs\launcher-stderr.log en logs\app.log.
pause
start "" "%URL%"
