#!/bin/sh
# Syntaxprüfung fürs Frontend.
#
# `node --check datei.js` ist WERTLOS für dieses Projekt: es parst .js
# als CommonJS-Skript und meldet bei einem kaputten ES-Modul trotzdem
# exit 0. Genau so ist am 15.11.2026 eine Datei mit einem Syntaxfehler
# ausgeliefert worden — die Oberfläche blieb leer, und der Prüfer hatte
# vorher grünes Licht gegeben.
#
# Mit der Endung .mjs parst node als Modul und findet den Fehler.
fehler=0
for datei in frontend/js/*.js; do
  kopie=$(mktemp -t jspruef).mjs
  cp "$datei" "$kopie"
  if ! node --check "$kopie" 2>/tmp/js-pruefen.fehler; then
    echo "FEHLER in $datei:"
    sed "s|$kopie|$datei|" /tmp/js-pruefen.fehler | head -5
    fehler=1
  fi
  rm -f "$kopie"
done
[ "$fehler" = 0 ] && echo "Alle Dateien syntaktisch in Ordnung."
exit $fehler
