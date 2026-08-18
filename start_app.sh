#!/usr/bin/env bash
# Start de Boekhouding-app (indien nog niet actief) en opent hem in de
# standaardbrowser. Bedoeld om aangeklikt te worden via een
# bureaublad-/menu-snelkoppeling (zie boekhouding.desktop), maar werkt ook
# gewoon vanaf de command line: ./start_app.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

PORT=8000
URL="http://127.0.0.1:${PORT}"
mkdir -p "$APP_DIR/logs"
LOG_FILE="$APP_DIR/logs/launcher.log"

# Deze manier van starten (i.p.v. gewoon `python run.py` tijdens
# ontwikkelen) draait zonder --reload en sluit zichzelf automatisch af na
# een periode zonder verkeer — zie app/idle_shutdown.py. Zet op 0 om
# uit te schakelen, of exporteer een andere waarde voor het aanroepen van
# dit script om de standaard 30 minuten te overschrijven.
export BOEKHOUDING_RELOAD=0
export BOEKHOUDING_IDLE_TIMEOUT_MINUTES="${BOEKHOUDING_IDLE_TIMEOUT_MINUTES:-30}"

open_browser() {
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 &
    elif command -v gio >/dev/null 2>&1; then
        gio open "$URL" >/dev/null 2>&1 &
    fi
}

# Draait de server al (bijv. eerder gestart)? Dan alleen de browser openen.
if curl --silent --fail --output /dev/null "$URL" 2>/dev/null; then
    echo "Boekhouding draait al op $URL — browser openen..."
    open_browser
    exit 0
fi

if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    echo "Geen virtualenv gevonden op .venv — volg eerst de installatiestappen in README.md." >&2
    exit 1
fi

echo "Boekhouding starten..." | tee -a "$LOG_FILE"
# shellcheck disable=SC1091
source "$APP_DIR/.venv/bin/activate"
nohup python run.py >>"$LOG_FILE" 2>&1 &
disown

# Wacht tot de server reageert (max ~20 seconden).
for _ in $(seq 1 40); do
    if curl --silent --fail --output /dev/null "$URL" 2>/dev/null; then
        open_browser
        exit 0
    fi
    sleep 0.5
done

echo "De server reageert nog niet na 20 seconden — bekijk logs/launcher.log en logs/app.log." >&2
open_browser
