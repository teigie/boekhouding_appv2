@echo off
rem Dubbelklikbare snelkoppeling: start de Boekhouding-app en opent hem
rem in de browser. Logica staat in start_app.ps1 (PowerShell is nodig
rem om zonder extra tools de server-status te checken en de browser te
rem openen) — dit bestand is alleen de dubbelklikbare ingang.
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start_app.ps1"
