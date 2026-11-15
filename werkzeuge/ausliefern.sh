#!/usr/bin/env bash
# Den Trainer auf den Familienserver bringen.
#
#   werkzeuge/ausliefern.sh
#
# Warum ein Skript und kein rsync von Hand: weil der von Hand schon
# einmal schiefgegangen ist. `rsync --delete` hat am 15.11.2026 die
# `.env` auf dem Server gelöscht — sie steht (richtigerweise) nicht im
# Repo, also sah rsync eine Datei, die es "nicht mehr gibt". Damit war
# VOKABEL_ACCESS_TEAM leer, und der Trainer sah die geprüfte
# Mailadresse von Cloudflare Access nicht mehr an: alle, die von außen
# kamen, landeten auf der Profilliste statt in ihrem eigenen Profil.
#
# Die Lehre ist nicht "vorsichtiger sein", sondern: was nur auf dem
# Server lebt, gehört in eine Ausnahmeliste, die man nicht jedes Mal
# neu tippt.
set -euo pipefail

ZIEL=${1:-familienserver}
ORT=/srv/vokabeltrainer
HIER=$(cd "$(dirname "$0")/.." && pwd)

# Was auf dem Server bleibt, egal was hier steht.
#   daten  — die Datenbank. Niemals anfassen.
#   .env   — die Anlage: Access-Team und öffentliche MCP-Adresse.
#   ZUGANGSDATEN.txt — die Anlagenbeschreibung, falls vorhanden.
NUR_DORT=(--exclude daten --exclude .env --exclude 'ZUGANGSDATEN*')
# Was nur hier lebt und dort nichts verloren hat.
NUR_HIER=(--exclude .git --exclude .venv --exclude __pycache__
          --exclude .pytest_cache --exclude '*.pyc' --exclude .DS_Store)

cd "$HIER"
echo "→ Prüfen, bevor etwas hinausgeht"
./werkzeuge/js-pruefen.sh
.venv/bin/python -m pytest -q

echo
echo "→ Probelauf: was würde gelöscht?"
geloescht=$(rsync -a --delete --dry-run --itemize-changes \
  "${NUR_DORT[@]}" "${NUR_HIER[@]}" ./ "$ZIEL:$ORT/" | grep '^\*deleting' || true)
if [ -n "$geloescht" ]; then
  echo "$geloescht"
  echo
  read -r -p "Diese Dateien auf dem Server löschen? [nein/ja] " antwort
  [ "$antwort" = "ja" ] || { echo "Abgebrochen."; exit 1; }
fi

echo "→ Übertragen"
rsync -a --delete "${NUR_DORT[@]}" "${NUR_HIER[@]}" ./ "$ZIEL:$ORT/"

echo "→ Neu bauen und starten"
ssh "$ZIEL" "cd $ORT && docker compose up -d --build 2>&1 | tail -2"

echo "→ Nachsehen, ob er steht und die Anlage noch kennt"
ssh "$ZIEL" "sleep 3
  curl -s -o /dev/null -w 'Zustand: HTTP %{http_code}\n' http://127.0.0.1:8030/api/zustand
  for v in VOKABEL_ACCESS_TEAM VOKABEL_MCP_URL VOKABEL_WEB_URL; do
    wert=\$(docker exec vokabeltrainer printenv \$v || true)
    [ -n \"\$wert\" ] && echo \"\$v: gesetzt\" || echo \"\$v: LEER — Anlage prüfen!\"
  done"
