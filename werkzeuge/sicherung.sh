#!/bin/sh
# Konsistenter Abzug der Vokabeldatenbank.
#
# Die Datenbank läuft im WAL-Modus. Ein einfaches Kopieren der Datei während
# eines Schreibvorgangs ergibt einen unvollständigen Stand — die Änderungen
# stehen dann noch im Begleitprotokoll. `sqlite3 .backup` nimmt dagegen einen
# in sich stimmigen Abzug, auch während gelernt wird.
#
# Vor die bestehende /srv-Sicherung hängen, etwa in
# /usr/local/sbin/familienserver-sichern vor dem borg-Aufruf:
#
#     /srv/vokabeltrainer/werkzeuge/sicherung.sh
#
set -eu

QUELLE="${VOKABEL_DB:-/srv/vokabeltrainer/daten/vokabeltrainer.db}"
ZIEL="${1:-$(dirname "$QUELLE")/abzug/vokabeltrainer-$(date +%F).db}"

[ -f "$QUELLE" ] || { echo "Keine Datenbank unter $QUELLE" >&2; exit 1; }
mkdir -p "$(dirname "$ZIEL")"

sqlite3 "$QUELLE" ".backup '$ZIEL'"

# Der Abzug erbt den WAL-Modus und legte sonst -wal und -shm daneben.
# Eine Sicherung soll eine einzelne Datei sein.
sqlite3 "$ZIEL" "PRAGMA journal_mode=DELETE;" > /dev/null
ERGEBNIS=$(sqlite3 "$ZIEL" "PRAGMA integrity_check;" | head -1)
rm -f "$ZIEL-wal" "$ZIEL-shm"      # sqlite lässt die -shm-Datei stehen
[ "$ERGEBNIS" = "ok" ] || { echo "Abzug unbrauchbar: $ERGEBNIS" >&2; exit 1; }

# Nur die letzten sieben Abzüge behalten — die Langzeitsicherung macht Borg.
# Bewusst ohne `head -n -7` und `xargs -r`: beides gibt es nur bei GNU, und
# das Skript soll auch auf dem Mac laufen.
VERZEICHNIS="$(dirname "$ZIEL")"
ANZAHL=$(find "$VERZEICHNIS" -name 'vokabeltrainer-*.db' -type f | wc -l)
if [ "$ANZAHL" -gt 7 ]; then
  find "$VERZEICHNIS" -name 'vokabeltrainer-*.db' -type f | sort \
    | head -n "$((ANZAHL - 7))" \
    | while IFS= read -r alt; do rm -- "$alt"; done
fi

echo "Abzug in Ordnung: $ZIEL ($(du -h "$ZIEL" | cut -f1))"
